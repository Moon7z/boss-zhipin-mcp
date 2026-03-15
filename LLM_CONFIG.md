# 多厂商LLM配置指南

## 支持的LLM厂商

| 厂商 | 标识符 | 推荐模型 | 特点 |
|------|--------|----------|------|
| **火山方舟** | `doubao` | doubao-1-5-pro-32k | 中文优化，速度快 |
| **OpenAI** | `openai` | gpt-4/gpt-3.5-turbo | 功能强大，稳定 |
| **Anthropic** | `anthropic` | claude-3-sonnet | 推理能力强 |
| **阿里云** | `qwen` | qwen-turbo | 中文优秀，便宜 |
| **本地模型** | `ollama` | llama2/mistral | 隐私安全，免费 |

---

## 快速配置

### 1. 复制环境变量文件

```bash
cp .env.example .env
```

### 2. 选择LLM提供商

编辑 `.env` 文件：

```bash
# 选择提供商
LLM_PROVIDER=doubao  # 或 openai, anthropic, qwen, ollama

# 配置对应API Key
ARK_API_KEY=your_key_here  # 火山方舟
```

---

## 各厂商配置详情

### 火山方舟（推荐）

```bash
LLM_PROVIDER=doubao
ARK_API_KEY=65a13723-8fe6-467e-b6bd-e9ff299eeef7
ARK_MODEL=doubao-1-5-pro-32k-250115
```

**获取API Key**: https://console.volcengine.com/ark/

---

### OpenAI

```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4
```

**获取API Key**: https://platform.openai.com/

---

### Anthropic Claude

```bash
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-your-key
ANTHROPIC_MODEL=claude-3-sonnet-20240229
```

**获取API Key**: https://console.anthropic.com/

---

### 阿里云通义千问

```bash
LLM_PROVIDER=qwen
DASHSCOPE_API_KEY=sk-your-key
DASHSCOPE_MODEL=qwen-turbo
```

**获取API Key**: https://dashscope.aliyun.com/

---

### 本地Ollama（免费）

```bash
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2
```

**安装Ollama**:
```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama2
```

---

## 代码中使用

```python
from boss_mcp.llm_adapter import LLMFactory, chat_with_llm

# 方式1: 从环境变量自动创建
llm = LLMFactory.create_from_env()

# 方式2: 手动指定
llm = LLMFactory.create(
    provider='openai',
    api_key='your-key',
    model='gpt-4'
)

# 使用
messages = [
    {"role": "user", "content": "评估这个岗位匹配度"}
]
response = await llm.chat(messages)
print(response.content)
```

---

## 切换LLM

只需修改 `.env` 中的 `LLM_PROVIDER`：

```bash
# 切换到OpenAI
LLM_PROVIDER=openai

# 切换到阿里云
LLM_PROVIDER=qwen

# 切换到本地模型
LLM_PROVIDER=ollama
```

无需修改代码，自动适配！
