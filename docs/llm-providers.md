# LLM 供应商与免费模型参考（当前版本未启用）

> 本文只是**选型与迁移参考**。当前项目仍使用 `.env` 中已配置的 DeepSeek 兼容端点，调用方式不变。
> 所有额度、上下文、输出上限以各平台开通页为准；上线前请用 `/api/llm/health` 实测。

## 1. 为什么可以直接换

后端所有 LLM 调用都走 OpenAI 兼容协议：

```
POST {LLM_BASE_URL}/chat/completions
Authorization: Bearer {LLM_API_KEY}
```

代码里没有 DeepSeek 专有字段，也没有依赖 `response_format` 或 OpenAI `tools`。因此换供应商通常只需要改三个环境变量：

```dotenv
LLM_BASE_URL=...
LLM_API_KEY=...
LLM_MODEL_ID=...
```

需要同时满足的硬条件：

| 条件 | 要求 | 原因 |
|---|---|---|
| 上下文 | ≥ 16K（建议 32K+） | 规划 Prompt 含景点/天气/酒店原文 |
| 最大输出 | ≥ 6K（建议 8K+） | 整份行程 JSON 约 4–8K tokens，过小会被截断 |
| 流式 | 支持 SSE（或关闭流式） | 代码默认 `stream=true` |
| 协议 | OpenAI `/chat/completions` | 现有客户端直接复用 |

## 2. 可选方案

| 方案 | Base URL / 模型示例 | 上下文/输出（约） | 免费方式 | 适用场景 | 国内直连 |
|---|---|---|---|---|---|
| 智谱 GLM-4.5-Flash | `https://open.bigmodel.cn/api/paas/v4` / `glm-4.5-flash` | 128K / 最高 96K | 免费额度 | 长 JSON 规划、中文提纯 | ✅ |
| 硅基流动 Qwen2.5-14B | `https://api.siliconflow.cn/v1` / `Qwen/Qwen2.5-14B-Instruct` | 32K / 4–8K | 免费额度 + 限流 | 问答、偏好提取、小城市规划 | ✅ |
| 阿里百炼 qwen-flash | `https://dashscope.aliyuncs.com/compatible-mode/v1` / `qwen-flash` | 1M / 8K | 新用户免费 tokens | 规划备用、长上下文 | ✅ |
| 百度千帆 ERNIE-Speed | `https://qianfan.baidubce.com/v2` / `ernie-speed-128k` | 128K / 2–8K | 免费额度 | 问答、短任务 | ✅ |
| 腾讯混元 Lite | `https://api.hunyuan.cloud.tencent.com/v1` / `hunyuan-lite` | 32K / 4K | 免费额度 | 问答、提纯 | ✅ |
| 火山方舟 Doubao-lite | `https://ark.cn-beijing.volces.com/api/v3` / `doubao-lite-32k` | 32K / 4K | 免费额度（需接入点） | 问答、提纯 | ✅ |
| Gemini 2.5 Flash | `https://generativelanguage.googleapis.com/v1beta/openai/` / `gemini-2.5-flash` | 1M / 65K | 免费层（RPM/RPD 限制） | 最佳免费规划质量 | ❌ 需代理 |
| Groq Llama-3.3-70B | `https://api.groq.com/openai/v1` / `llama-3.3-70b-versatile` | 128K / 32K | 免费层（日 token 限额低） | 快速 JSON、低并发 | ❌ 需代理 |
| OpenRouter `:free` | `https://openrouter.ai/api/v1` / 例如 `meta-llama/llama-3.3-70b-instruct:free` | 视模型 | 免费模型每日次数限制 | 备用/长尾 | ❌ 需代理 |
| Ollama 本地 | `http://127.0.0.1:11434/v1` / `qwen2.5:14b-instruct` | 32K / 8K | 永久免费（自付硬件/电费） | 隐私、无限调用 | 本机 |

**推荐组合**

- 低流量公网：智谱 GLM-4.5-Flash 为主，硅基流动 Qwen2.5-14B 兜底。
- 境外网络：Gemini 2.5 Flash（需给 LLM 单独配代理）。
- 有 GPU：Ollama Qwen2.5-32B（规划）+ Qwen2.5-7B（问答/提纯）。
- 无 GPU 的本机不适合面向公网自托管：CPU 跑 7B 约 5 tok/s，一次规划要 10–30 分钟。

## 3. 切换步骤（未来执行，当前不做）

1. 注册平台并创建 API Key。
2. 修改 `backend/.env` 三个变量（或在设置页热更新）。
3. 若模型输出上限 < 6K，先降低单次行程规模（少城市/少天数），否则会被截断。
4. 运行 `GET /api/llm/health` 确认连通；再用 2 天行程做一次完整规划。
5. 观察 `backend/data/trip_tasks/*.json` 是否完整、结果页 28 项断言是否通过。

## 4. 后续接入 GPU 服务器时

**部署侧**

- 安装 Ollama（或 vLLM），监听 `0.0.0.0:11434`（vLLM 常用 `:8000`）。
- Ollama 必须显式放大上下文，否则默认 2K/4K 会静默截断：
  `OLLAMA_CONTEXT_LENGTH=32768`，或在 Modelfile 中 `PARAMETER num_ctx 32768`。
- `OLLAMA_KEEP_ALIVE=30m` 避免频繁冷启动；vLLM 用 `--max-model-len 32768`。
- 给端点加防火墙/鉴权，不要直接暴露公网。

**配置侧（只改环境变量）**

```dotenv
LLM_BASE_URL=http://gpu-host:11434/v1
LLM_MODEL_ID=qwen2.5:32b-instruct
LLM_API_KEY=ollama
TRIP_PLANNER_TIMEOUT=900
MAX_CONCURRENT_PLANS=1
```

- 现有代码无需改动即可调用。
- 按显存调整 `MAX_CONCURRENT_PLANS`；保持 `PUBLIC_MODE=true` 的限流与排队。
- 若要保留 DeepSeek 作为备用，需要后续阶段实现 fallback 链（当前未实现）。

**代码侧（可选，后续阶段）**

- provider 预设与能力校验（上下文/输出门槛）。
- `LLM_PROXY`（仅 LLM 生效，境外免费 API 需要）。
- Ollama `extra_body.options.num_ctx` 透传。

## 5. 公开发布注意事项

- 免费层通常禁止转售/高频滥用，且可能将数据用于产品改进；公网部署请加限流与隐私说明。
- 免费额度会被公共流量迅速耗尽，建议保留 `PUBLIC_MODE=true` + 按 IP 限额，或让访客自备 Key（BYOK，后续阶段）。
- 当前发布加固只覆盖：设置写保护、按 IP 限流、全局并发与排队；不包含多实例共享限流（需 Redis）。
