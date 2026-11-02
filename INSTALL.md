# Farway 安装与启动（新手版）

本文只讲三件事：**一键安装、一键启动、网页里填配置**。
全程不需要编辑 `.env`、代码或任何配置文件；API Key 都在 Farway 网页的设置界面中填写。

> 适用系统：Windows 10 / 11 x64。

---

## 1. 安装前准备

需要两个运行时：

| 依赖 | 版本 | 说明 |
|---|---|---|
| Python | **3.10.x 64 位** | 运行后端；安装脚本会优先自动查找 |
| Node.js | **18+**（推荐 20/22/24 LTS） | 构建前端、运行小红书签名；npm 随 Node 一起安装 |

如果电脑上没有 Python 或 Node.js，不用手动折腾：运行 `install.cmd` 时脚本会提示用 `winget` 自动安装；没有 `winget` 时会给出官网下载地址。

> 安装过程中如果弹出 Windows SmartScreen 提示，点击“更多信息”→“仍要运行”。

---

## 2. 一键安装

1. 把项目解压到一个**路径不含中文和空格**的目录，例如 `D:\Apps\farway`；
2. 进入该目录，双击 **`install.cmd`**；
3. 如果提示安装 Python / Node.js，输入 `Y` 并等待；
4. 看到“安装完成”后关闭窗口。

安装脚本会自动完成：

- 检查 Python 3.10 与 Node.js/npm；
- 创建 `backend\.venv` 并安装 Python 依赖（若已有虚拟环境不可用，会自动重建）；
- 安装后端小红书签名所需的 Node 依赖；
- 安装前端依赖并构建 `frontend\dist`；
- 生成不含任何密钥的 `backend\.env`；
- 创建运行数据目录。

> **从其他电脑复制项目时**：建议只复制源码，不要复制 `.venv`、`node_modules`、`dist`。`install.cmd` 会自动检测并重建不可用的虚拟环境；如果仍失败，删除 `backend\.venv`、`backend\node_modules`、`frontend\node_modules`、`frontend\dist` 后重新运行即可。
>
> **重复执行安全**：已经安装好的部分会自动跳过。只有代码或依赖更新后需要强制重建前端时，才运行：
>
> ```powershell
> powershell -ExecutionPolicy Bypass -File .\install.ps1 -Rebuild
> ```
>
> 安装失败时，窗口会停在错误信息处。请先看最后几行红色提示；常见处理见第 6 节。

---

## 3. 一键启动

双击 **`start.cmd`**。

脚本会：

1. 检查安装是否完整；
2. 在**新窗口**中启动后端；
3. 等待服务就绪后自动打开浏览器：<http://127.0.0.1:8000>。

停止 Farway：**关闭新打开的后端命令行窗口**即可。

> 如果 Farway 已经在运行，再次双击 `start.cmd` 只会打开浏览器，不会重复启动。
>
> 如果 8000 端口被其他程序占用，可以换端口启动：
>
> ```powershell
> start.cmd -Port 8001
> ```
>
> 然后访问 <http://127.0.0.1:8001>。

---

## 4. 首次配置：在网页里填写

打开首页后，点击右上角的**齿轮按钮**，在“配置”窗口中填写以下内容，然后点击 **保存并应用**：

| 设置项 | 是否必填 | 用途 |
|---|---|---|
| LLM API Key | 是 | AI 模型密钥，用于生成行程 |
| LLM Base URL | 是 | OpenAI 兼容接口地址，例如 `https://api.deepseek.com/v1` |
| LLM Model | 是 | 模型名称，例如 `deepseek-chat` |
| 高德地图 Web Service Key | 是 | 地理编码、POI、天气、路线 |
| 高德地图 JS Key | 是（用地图时） | 网页地图渲染 |
| 高德地图安全密钥 | 是（用地图时） | 高德 JS API 安全密钥 |
| 小红书 Cookie | 否 | 抓取小红书攻略；不填也能生成行程，但攻略内容会减少 |
| 后端地址 | 否 | 单端口部署保持默认/留空即可 |

填写说明：

- **LLM**：在模型服务商控制台创建 API Key；Base URL 和模型名以服务商文档为准。
- **高德**：在高德开放平台创建应用，分别获取 **Web 服务 Key** 和 **Web 端（JS API）Key**；JS API 还需配置**安全密钥**。
- **小红书**：可选。需要时从浏览器登录小红书后复制 Cookie；不填不影响基本行程生成。
- LLM/高德等配置保存在本机 `backend\runtime_settings.json`，小红书 Cookie 加密保存在 `backend\data\xhs.db`；**不需要手动编辑任何文件**。
- 修改地图相关配置后，**刷新页面**再打开地图；其他配置保存后立即生效。

> 如果页面右上角没有齿轮或设置不可编辑，说明站点开启了公共只读模式；本地部署默认不会开启。

---

## 5. 验证是否成功

打开 <http://127.0.0.1:8000> 后：

1. 首页能正常显示，不报错；
2. 右上角“设置”能打开并保存；
3. 填写 LLM Key 后，提交一个简单行程，能进入结果页看到行程与预算；
4. 填写高德两个 Key 与安全密钥并刷新后，景点地图能显示标记和路线。

也可以在浏览器访问：

```text
http://127.0.0.1:8000/health
```

看到 `"status":"healthy"` 即表示后端已启动。生成行程失败时，先检查 LLM Key、Base URL、模型名和网络。

---

## 6. 常见问题

### 6.1 双击 `install.cmd` 没反应或提示脚本被禁止

`install.cmd` 已使用 PowerShell 的 `-ExecutionPolicy Bypass`，通常不会被拦。如果仍被 SmartScreen 拦截，点击“更多信息”→“仍要运行”。

也可以右键项目文件夹，选择“在终端中打开”，执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

### 6.2 提示找不到 Python 3.10

按提示让脚本用 `winget` 安装；或手动安装：

```powershell
winget install --id Python.Python.3.10 -e
```

安装时勾选 **Add python.exe to PATH**，装完后重新运行 `install.cmd`。

### 6.3 提示找不到 Node.js / npm

```powershell
winget install --id OpenJS.NodeJS.LTS -e
```

或从 <https://nodejs.org/> 下载 LTS 安装包，安装时勾选 **Add to PATH**。装完后重新运行 `install.cmd`。

### 6.4 安装依赖很慢或失败

国内网络可先换镜像，再重新运行 `install.cmd`：

```powershell
# Python 镜像
.\backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# Node 镜像
npm config set registry https://registry.npmmirror.com
```

如果仍失败，删除 `backend\.venv` 和 `frontend\node_modules` 后重新运行 `install.cmd`。

### 6.5 启动提示“尚未安装”或“前端页面尚未构建”

说明安装没有完成。重新双击 `install.cmd`，看到“安装完成”后再启动。

### 6.6 启动提示端口被占用

关闭占用 8000 端口的程序，或换端口：

```powershell
start.cmd -Port 8001
```

### 6.7 页面能打开，但地图空白

1. 打开右上角设置，确认 **高德地图 JS Key** 与 **高德地图安全密钥** 都已填写；
2. 保存后刷新页面；
3. 在高德开放平台确认 Key 已启用 JS API，且域名白名单包含 `127.0.0.1` / `localhost`；
4. 后端 **Web 服务 Key** 也必须填写，否则天气、POI、路线会失败。

### 6.8 生成行程时报 LLM 错误

打开设置，检查：

- `LLM API Key` 是否正确、是否过期；
- `LLM Base URL` 是否以 `/v1` 结尾（以服务商要求为准）；
- `LLM Model` 是否是服务商实际提供的模型名。

保存后重新提交一次。仍失败时，查看后端命令行窗口的最后几行错误。

### 6.9 想重新安装 / 重置

- 重复运行 `install.cmd` 是安全的，已完成的步骤会跳过；
- 需要强制重建前端：`powershell -ExecutionPolicy Bypass -File .\install.ps1 -Rebuild`；
- 需要彻底重装：关闭 Farway，删除 `backend\.venv`、`frontend\node_modules`、`frontend\dist`，再运行 `install.cmd`。

> 删除 `backend\runtime_settings.json` 会清除网页里保存的配置；删除 `backend\data` 会清除任务与小红书会话。操作前请确认。

---

## 7. 文件与脚本说明

```text
install.cmd / install.ps1   一键安装
start.cmd / start.ps1       一键启动
backend\                    后端（.venv、node_modules、data 由脚本生成）
frontend\                   前端（node_modules、dist 由脚本生成）
docs\                       设计与专项说明
```

`install.cmd` / `start.cmd` 是双击入口；`.ps1` 是实际执行脚本。安装或启动出错时，窗口会保留错误信息，方便截图反馈。

---

## 8. 许可

本项目基于 GPL-2.0 代码库改造，分发或修改后发布请遵守 [LICENSE](LICENSE)：
保留许可证与版权声明，并按 GPL-2.0 提供对应源代码。第三方 Python/Node 依赖遵循各自许可证。
