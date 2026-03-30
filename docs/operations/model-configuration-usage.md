# 模型配置教程

本文档介绍如何在后端配置多个模型，并在调用 `/analyze` 接口时灵活切换。

## 架构概述

后端采用**分层配置架构**，支持多模型 profile、preset 和灵活的路由切换：

| 组件 | 作用 |
|------|------|
| `ModelProfileConfig` | 定义单个模型的配置（provider、model_name、base_url、api_key等） |
| `ModelPresetConfig` | 定义预设配置，可为不同路由指定不同的 profile |
| `ModelRegistry` | 注册表，管理所有 profiles 和 presets |

### 模型路由

系统定义了三个路由：

| 路由 | 用途 |
|------|------|
| `preprocess_guardrails` | 预处理守护 rails |
| `analysis_core` | 核心分析 |
| `analysis_translation` | 翻译 |

### 配置优先级

模型选择优先级（从高到低）：

```
请求中的 route_override → preset中的route配置 → default_profile → 环境变量默认配置
```

---

## 配置流程

### 方式一：使用外部 JSON 配置文件（推荐）

将模型配置放在独立的 JSON 文件中，更易于维护。

#### 1. 创建配置文件

在 `server/config/` 目录下创建 `model-profiles.json`：

```json
{
  "minimax_m27": {
    "provider": "openai_compatible",
    "model_name": "MiniMax-M2.7",
    "base_url": "https://api.minimax.io/v1",
    "api_key": "your-minimax-key",
    "model_settings": {
      "temperature": 0.1,
      "max_tokens": 4000
    }
  },
  "vllm-qwen3-8b": {
    "provider": "openai_compatible",
    "model_name": "Qwen/Qwen3-8B",
    "base_url": "http://127.0.0.1:8000/v1",
    "api_key": ""
  }
}
```

#### 2. 在 .env 中引用配置文件

```bash
# 引用 config/ 目录下的 JSON 文件（推荐）
MODEL_PROFILES_JSON="config/model-profiles.json"

# 也可以直接写内联 JSON（不推荐，难维护）
MODEL_PROFILES_JSON="{\"minimax_m27\":{...}}"
```

---

### 方式二：内联 JSON（仅适用于简单场景）

如果模型很少，可以直接在 `.env` 中写 JSON：

```bash
DEFAULT_MODEL_PROFILE="minimax_m27"
MODEL_PROFILES_JSON="{\"minimax_m27\":{\"provider\":\"openai_compatible\",\"model_name\":\"MiniMax-M2.7\",\"base_url\":\"https://api.minimax.io/v1\",\"api_key\":\"your-key\",\"model_settings\":{\"temperature\":0.1}}}"
```

---

### 步骤2：设置默认模型

```bash
# 设置全局默认模型
DEFAULT_MODEL_PROFILE="minimax_m27"

# 也可以为不同路由设置不同默认模型
PREPROCESS_MODEL_PROFILE="vllm-qwen3-8b"
CORE_MODEL_PROFILE="minimax_m27"
TRANSLATION_MODEL_PROFILE="minimax_m27"
```

---

### 步骤3：调用接口时切换模型

在调用 `/analyze` 接口时，通过 `model_selection` 参数灵活切换：

#### 方式1：使用 preset（最简单）

```json
{
  "text": "Your English article...",
  "model_selection": {
    "preset": "minimax_eval"
  }
}
```

#### 方式2：指定特定路由的 profile

```json
{
  "text": "Your English article...",
  "model_selection": {
    "routes": {
      "analysis_core": {"profile": "local_qwen"},
      "analysis_translation": {"profile": "minimax_m27"}
    }
  }
}
```

#### 方式3：使用 default_profile

```json
{
  "text": "Your English article...",
  "model_selection": {
    "default_profile": "local_qwen"
  }
}
```

#### 方式4：组合使用（preset + 特定路由覆盖）

```json
{
  "text": "Your English article...",
  "model_selection": {
    "preset": "minimax_eval",
    "routes": {
      "analysis_translation": {"profile": "local_qwen"}
    }
  }
}
```

#### 方式5：配置 fallback（自动切换）

当主模型失败时，自动切换到 fallback 模型：

```json
{
  "text": "Your English article...",
  "model_selection": {
    "routes": {
      "analysis_core": {
        "profile": "local_qwen",
        "fallback_profiles": ["minimax_m27"]
      }
    }
  }
}
```

---

## 完整配置示例

### 场景：本地测试 vs 生产环境

假设你想配置两套模型方案：

| 场景 | Profile | 模型 |
|------|---------|------|
| 本地测试 | `local_qwen` | Qwen3-8B (本地) |
| 生产环境 | `minimax_m27` | MiniMax M2.7 |

#### 环境变量配置

```bash
DEFAULT_MODEL_PROFILE="minimax_m27"
MODEL_PROFILES_JSON='{
  "local_qwen": {
    "provider": "openai_compatible",
    "model_name": "Qwen/Qwen3-8B",
    "base_url": "http://127.0.0.1:8000/v1",
    "api_key": ""
  },
  "minimax_m27": {
    "provider": "openai_compatible",
    "model_name": "MiniMax-Text-01",
    "base_url": "https://api.minimax.io/v1",
    "api_key": "your-key"
  }
}'
```

#### 调用示例

```bash
# 使用本地模型
curl -X POST /analyze \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello world","model_selection":{"default_profile":"local_qwen"}}'

# 使用生产模型（使用默认配置）
curl -X POST /analyze \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello world"}'
```

---

## ModelProfileConfig 完整字段

```json
{
  "provider": "openai_compatible",
  "model_name": "模型名称",
  "base_url": "API地址",
  "api_key": "API密钥",
  "model_settings": {
    "temperature": 0.1,
    "max_tokens": 4000,
    "top_p": 0.9,
    "timeout": 60.0,
    "seed": 42,
    "presence_penalty": 0.0,
    "frequency_penalty": 0.0,
    "stop_sequences": ["STOP"],
    "extra_headers": {},
    "extra_body": {}
  },
  "provider_options": {}
}
```

### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `provider` | string | 是 | 当前仅支持 `openai_compatible` |
| `model_name` | string | 是 | 模型标识符 |
| `base_url` | string | 是（openai_compatible） | API 基础地址 |
| `api_key` | string | 否 | API 密钥 |
| `model_settings` | object | 否 | 模型运行参数 |
| `provider_options` | object | 否 | 提供商特定选项 |

---

## 最佳实践

1. **生产环境**：使用 `DEFAULT_MODEL_PROFILE` 设置默认模型
2. **开发调试**：使用 `model_selection.default_profile` 快速切换
3. **A/B测试**：使用不同的 preset 对比不同模型效果
4. **稳定性保障**：配置 `fallback_profiles` 防止单点故障

---

## 相关文件

- 模型类型定义：`app/llm/types.py`
- 模型注册：`app/llm/registry.py`
- 模型路由：`app/llm/router.py`
- 提供商工厂：`app/llm/provider_factory.py`
- 配置文件：`app/config/settings.py`
