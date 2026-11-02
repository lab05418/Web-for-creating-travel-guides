# 远行 Farway

个人向 AI 旅行规划助手：填写出发地、目的地、日期与偏好，多智能体自动收集景点、天气、酒店与攻略，生成完整行程（预算、3D 地图）。

> 这是个人定制版，基于 GPL-2.0 代码库改造，保留 `LICENSE`；不含任何上游品牌与仓库链接。

## 功能

- 出发地 + 多城市目的地、日期与停留天数
- 城际交通与市内交通分开选择；高铁、火车、飞机使用独立席别
- 小红书攻略提纯、景点实拍图、天气与酒店推荐
- 行程概览、景点详解、热门景点发现
- 地点管理、预算明细、按天路线与高德 3D 地图
- 重要提醒、攻略 PNG 导出
- 公开发布模式：设置写保护、按 IP 限流、并发与排队

## 快速开始

前置：Windows 10/11、Python 3.10 64 位、Node.js 18+（推荐 20/22/24 LTS）。缺少 Python/Node 时，安装脚本会提示用 `winget` 自动安装。

1. **一键安装**：双击 `install.cmd`，等待出现“安装完成”。
2. **一键启动**：双击 `start.cmd`，浏览器会自动打开 <http://127.0.0.1:8000>。
3. **填写配置**：点击网页右上角齿轮，在设置中填写 LLM 与高德 Key，保存并应用。

```text
install.cmd   首次安装（重复运行安全）
start.cmd     启动并打开浏览器；关闭后端命令行窗口即停止
```

> 完整的新手安装、启动与排障说明见 [INSTALL.md](INSTALL.md)。
>
> 不需要手动编辑 `.env` 或代码；所有密钥都在网页设置中填写和修改。

## 网页设置项

| 设置项 | 必填 | 用途 |
|---|---|---|
| LLM API Key / Base URL / Model | 是 | AI 生成行程 |
| 高德地图 Web Service Key | 是 | 地理编码、POI、天气、路线 |
| 高德地图 JS Key | 用地图时 | 网页地图渲染 |
| 高德地图安全密钥 | 用地图时 | 高德 JS API 安全密钥 |
| 小红书 Cookie | 否 | 抓取小红书攻略 |
| 后端地址 | 否 | 单端口部署保持默认/留空 |

LLM/高德等配置保存在本机 `backend\runtime_settings.json`，小红书 Cookie 加密保存在 `backend\data\xhs.db`；修改后立即生效，地图相关配置保存后刷新页面。

## 项目结构

```text
install.cmd / install.ps1   一键安装
start.cmd / start.ps1       一键启动
backend\                    后端源码、.venv、node_modules、data（后三项由脚本生成）
frontend\                   前端源码、node_modules、dist（后两项由脚本生成）
docs\                       设计与专项说明
INSTALL.md                  新手安装与启动教程
```

## 数据

- 任务与结果：`backend\data\trip_tasks\`
- 地点/会话：`backend\data\farway.db`
- 小红书加密会话：`backend\data\xhs.db` + `backend\data\xhs_cookie.key`
- 运行时设置：`backend\runtime_settings.json`
- 图片与攻略缓存：`backend\data\photo_cache\`、`poi_photos\`、`guides\`

迁移或备份时，关闭 Farway 后复制 `backend\data`、`backend\runtime_settings.json`、`backend\.env` 即可。

## 常见问题

- **双击脚本没反应 / 被 SmartScreen 拦截**：点击“更多信息”→“仍要运行”；或在项目目录执行 `powershell -ExecutionPolicy Bypass -File .\install.ps1`。
- **从其他电脑复制项目后安装/启动失败**：运行 `install.cmd`，它会自动重建不可用的 `.venv`；仍失败时删除 `backend\.venv`、`backend\node_modules`、`frontend\node_modules`、`frontend\dist` 后重试。
- **提示缺少 Python 3.10 / Node.js**：按安装脚本提示用 `winget` 安装，或从官网安装后重新运行 `install.cmd`。
- **端口被占用**：`start.cmd -Port 8001`。
- **页面打不开或地图空白**：先运行 `install.cmd`，再检查网页设置中的高德 Key 与安全密钥，保存后刷新。
- **生成行程失败**：检查网页设置中的 LLM API Key、Base URL 与模型名。
- **想强制重建前端**：`powershell -ExecutionPolicy Bypass -File .\install.ps1 -Rebuild`。

更多排障步骤见 [INSTALL.md](INSTALL.md)。

## 许可

本项目基于 GPL-2.0 代码库改造，个人使用与二次分发请遵守 `LICENSE`：

- 分发二进制或修改版时，需保留 `LICENSE` 与版权声明，并按 GPL-2.0 提供对应源代码；
- 第三方 Python/Node 依赖分别遵循其各自许可证；
- 仓库不包含上游品牌、私有素材或真实用户数据；
- 小红书 Cookie、LLM Key、高德 Key 等凭据仅保存在本机，不随仓库分发。
