# 小红书抓取失败排查

## 典型报错

```text
旅行计划生成失败：小红书数据抓取失败：SyntaxError: 缺少 ':'
```

这个报错**不是**小红书账号或 Cookie 直接返回的业务错误，而是签名 JS 还没有真正执行就失败了。

## 根因

小红书请求签名依赖 [sign_util.py](../backend/app/services/xhs_sign/sign_util.py) 通过 PyExecJS 执行：

- `xhs_xs_xsc_56.js`
- `xhs_xray.js`

PyExecJS 在 Windows 上会按运行时列表选择引擎。如果后端进程的 `PATH` 里没有 Node.js，它会回退到 **JScript / cscript**。JScript 只支持旧版 ES 语法，无法解析签名包里的现代 JS，调用 `traceId` 或 `get_request_headers_params` 时抛出：

```text
execjs._exceptions.ProgramError: SyntaxError: 缺少 ':'
```

真正出错的调用栈是：

```text
xhs_service.search_notes()
  -> generate_request_params()
    -> generate_headers()
      -> generate_xs_xs_common()
        -> _xs_js.call("get_request_headers_params", ...)
          -> execjs JScript ProgramError
```

所以它不是：

- 小红书接口返回的 JSON 少了冒号；
- Cookie 字符串格式错误；
- 小红书搜索请求已经发出但响应解析失败。

## 可排查方向

### 1. 确认实际 JS 运行时

看后端启动日志：

```text
[XHS_SIGN] JS runtime: Node.js (V8) (node)
```

如果是 `JScript`、`cscript`，就是本问题。

也可以直接运行：

```powershell
cd backend
.\.venv\Scripts\python.exe -c "from app.services.xhs_sign.sign_util import _RUNTIME; print(_RUNTIME.name, _RUNTIME._command)"
```

### 2. 确认 Node 是否可用

```powershell
node -v
where.exe node
```

如果没有 Node，或后端启动时没有把便携 Node 加进 `PATH`，就会回退 JScript。

本项目 `start.ps1` 会自动查找：

```text
<repo>\..\tools\node-*-win-x64\node.exe
<repo>\tools\node-*-win-x64\node.exe
PATH 中的 node
```

手动启动后端时，需要自己保证 Node 在 `PATH` 中。

### 3. 确认不是响应格式问题

如果日志中的错误是：

```text
Expecting ':' delimiter
```

且栈顶在：

```python
res_json = response.json()
```

才说明小红书返回了 HTML、空响应或被风控页面，不是 JSON。此时应检查：

- HTTP 状态码、`content-type`；
- 响应前 500 字符；
- Cookie 是否过期；
- 是否被重定向到登录/验证码页。

### 4. 确认不是模型提纯 JSON 问题

`search_xhs_attractions()` 里对 LLM 输出有独立的 `json.loads()`：

```python
json_match = re.search(r'\[.*\]', content, re.DOTALL)
if json_match:
    extracted = json.loads(json_match.group())
else:
    extracted = json.loads(content)
```

如果模型输出带 Markdown 代码围栏、注释、尾逗号，异常会被捕获并降级为：

```text
尝试提取小红书结构化数据失败，降级回常规处理。
```

它不会以“小红书数据抓取失败”抛给前端，因此和本错误不是同一条路径。

### 5. 确认 Cookie 不是致命错误

Cookie 过期/风控会抛出：

```text
小红书 Cookie 已被风控拦截 (code=300011)
```

与 `SyntaxError: 缺少 ':'` 明显不同。

## 修复方式

本次已在 `sign_util.py` 中强制使用 Node：

1. 依次查找便携 Node、`PATH` 中的 node、`C:\Program Files\nodejs`；
2. 把 Node 目录前置到 `PATH`；
3. 新建 `execjs` Node runtime 实例（不能直接用缓存过的 `execjs.get("Node")`，因为它的 `_available` 在 import 时已缓存）；
4. 找不到 Node 时直接抛出可操作的中文错误，而不是回退 JScript：

```text
小红书签名引擎需要 Node.js。请安装 Node 18+，
或把便携版 Node 放到 ../tools/node-*-win-x64，然后重启后端。
```

## 验证

```powershell
cd backend
.\.venv\Scripts\python.exe -c "from app.services.xhs_service import get_xhs_client; c=get_xhs_client(); r=c.search_notes('南京 景点'); print(r.get('success'), len(r.get('data',{}).get('items',[])))"
```

修复后签名阶段返回：

```text
[XHS_SIGN] JS runtime: Node.js (V8) (node)
success True
```

如果 `success=True` 但 `items=0`，说明签名已经正常，问题转为搜索关键词/Cookie 权限/小红书返回空结果，不再是 JS 运行时错误。
