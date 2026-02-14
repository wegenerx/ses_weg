# auto_002_llmchat

从 [wegenerx/nonebot-plugin-nyaturingtest](https://github.com/wegenerx/nonebot-plugin-nyaturingtest) 的 `src/nonebot_plugin_nyaturingtest` 克隆。

## 依赖（需手动安装）

```bash
pip install nonebot-plugin-localstore nonebot-plugin-uninfo hipporag-nyabot openai pillow transformers anyio
```

## 配置 (.env)

- `nyaturingtest_chat_openai_api_key` - OpenAI API Key（必填）
- `nyaturingtest_chat_openai_base_url` - 对话 API 根地址，如 `https://api.siliconflow.cn/v1`（勿含 /chat/completions）
- `nyaturingtest_siliconflow_api_key` - 硅基流动 API Key（嵌入模型用，必填）
- `nyaturingtest_enabled_groups` - 启用群号列表
