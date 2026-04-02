# 回归集使用说明

版本：`v1.0.0`

状态：当前有效。本文档描述的是 **本地调试与输出质量提升** 用的回归集组件，不属于生产主链。

## 1. 定位

这套回归集只用于：

1. 固定样本回归
2. Prompt / few-shot 调整后的效果比较
3. 模型切换实验
4. LangSmith 实验管理

它**不属于**：

1. 线上接口逻辑
2. 正式业务 schema
3. 前端运行时依赖
4. 生产监控链路

代码与样本都故意放在主运行链路之外，避免污染核心实现。

## 2. 目录

### 2.1 样本

本地固定样本集放在：

- [server/.sample/regression/regression-dataset.json](C:\Users\nanpr\miniprogram\interpretation-of-english-articles\server\.sample\regression\regression-dataset.json)

### 2.2 脚本

回归工具脚本放在：

- [server/scripts/regression_suite.py](C:\Users\nanpr\miniprogram\interpretation-of-english-articles\server\scripts\regression_suite.py)

### 2.3 输出

本地回归运行结果默认写入：

- `server/.sample/regression/runs/<timestamp>/`

每次运行会生成：

1. `summary.json`
2. `summary.md`
3. 每个 sample 的 `*.response.json`

## 3. 样本格式

每个 sample 包含三部分：

1. `id`
2. `inputs`
3. `expectations`

示例结构：

```json
{
  "id": "movie_excerpt_core",
  "description": "综合样本，关注语境义、句尾入口和低价值词过滤。",
  "inputs": {
    "text": "...",
    "reading_goal": "daily_reading",
    "reading_variant": "intermediate_reading",
    "source_type": "user_input"
  },
  "expectations": {
    "must_hit": [
      {
        "kind": "inline_mark",
        "annotation_type": "context_gloss",
        "lookup_text": "rendered"
      }
    ],
    "must_not_hit": [
      {
        "kind": "inline_mark",
        "annotation_type": "vocab_highlight",
        "lookup_text": "review"
      }
    ],
    "count_bounds": {
      "sentence_entry.grammar_note": {
        "min": 1,
        "max": 4
      }
    },
    "max_warning_count": 4,
    "require_full_translation": true
  }
}
```

## 4. expectation 字段说明

### 4.1 `must_hit`

表示输出中必须命中的目标。

支持三种 `kind`：

1. `inline_mark`
2. `sentence_entry`
3. `warning`

常用匹配字段：

#### `inline_mark`

- `annotation_type`
- `sentence_id`
- `lookup_text`
- `visual_tone`
- `render_type`
- `anchor_text`
- `anchor_text_contains`
- `glossary_contains`

#### `sentence_entry`

- `entry_type`
- `sentence_id`
- `label`
- `label_contains`
- `content_contains`

#### `warning`

- `code`
- `level`
- `message_contains`

### 4.2 `must_not_hit`

表示明确不希望出现的输出，用于压制低价值标注。

典型用途：

1. 不要把 `review` 标成 `VocabHighlight`
2. 不要把简单句误做 `SentenceAnalysis`
3. 不要出现明显不该有的 warning

### 4.3 `count_bounds`

表示数量边界。

当前支持的 metric key：

1. `inline_mark.<annotation_type>`
2. `sentence_entry.<entry_type>`
3. `warning.total`

示例：

```json
{
  "inline_mark.vocab_highlight": {"min": 1, "max": 8},
  "sentence_entry.grammar_note": {"min": 1, "max": 4}
}
```

### 4.4 `max_warning_count`

控制单个 sample 允许出现的 warning 总量。

### 4.5 `require_full_translation`

若为 `true`，要求所有句子都有翻译。

## 5. 本地运行

### 5.1 跑整个回归集

在仓库根目录执行：

```bash
cd server
rtk test .venv\Scripts\python.exe scripts\regression_suite.py run-local
```

### 5.2 只跑一个 sample

```bash
cd server
rtk test .venv\Scripts\python.exe scripts\regression_suite.py run-local --sample-id movie_excerpt_core
```

### 5.3 指定模型 preset

```bash
cd server
rtk test .venv\Scripts\python.exe scripts\regression_suite.py run-local --model-preset qwen35_plus_default
```

### 5.4 指定默认 profile

```bash
cd server
rtk test .venv\Scripts\python.exe scripts\regression_suite.py run-local --default-profile kimi-k25
```

### 5.5 输出结果

脚本执行后会输出本次 run 的目录，例如：

```json
{
  "output_dir": ".../server/.sample/regression/runs/20260401-210000",
  "total_samples": 3,
  "passed_samples": 2,
  "failed_samples": 1
}
```

重点看：

1. `summary.md`
2. `summary.json`
3. 某个 sample 的 `*.response.json`

## 6. 如何解读结果

### 6.1 通过不代表可上线

这套回归集的作用是：

1. 避免明显退化
2. 记录 prompt / 模型切换的影响
3. 快速验证关键组件是否还在产出

它不能单独证明“已经达到上线标准”。

### 6.2 失败优先级

建议按这个顺序判断问题：

1. schema 是否通过
2. translations 是否完整
3. `ContextGloss / GrammarNote / SentenceAnalysis` 是否命中关键点
4. 是否出现低价值 `VocabHighlight`
5. warning 是否异常增多

## 7. 使用 LangSmith

可以，且推荐，但建议作为**实验管理层**而不是唯一执行入口。

### 7.1 同步本地回归集到 LangSmith dataset

```bash
cd server
rtk test .venv\Scripts\python.exe scripts\regression_suite.py sync-langsmith --dataset-name "Claread Regression Suite"
```

如果要覆盖已有 dataset：

```bash
cd server
rtk test .venv\Scripts\python.exe scripts\regression_suite.py sync-langsmith --dataset-name "Claread Regression Suite" --replace
```

说明：

1. 该命令会读取本地 JSON
2. 将其转换为 LangSmith dataset examples
3. 每条 example 的 `inputs` 保留请求参数
4. 每条 example 的 `outputs` 写入 `expectations`

### 7.2 用 LangSmith evaluate 跑实验

```bash
cd server
rtk test .venv\Scripts\python.exe scripts\regression_suite.py run-langsmith --experiment-prefix "v2.1-prompt-pass-01"
```

也可以指定模型：

```bash
cd server
rtk test .venv\Scripts\python.exe scripts\regression_suite.py run-langsmith --experiment-prefix "kimi-pass-01" --default-profile kimi-k25
```

当前内置的 evaluator 是 deterministic code evaluator：

1. `schema_valid_evaluator`
2. `must_hit_evaluator`
3. `must_not_hit_evaluator`
4. `translation_coverage_evaluator`

这套 evaluator 的目标是先保证：

1. 结构不退化
2. 关键组件不消失
3. 低价值标注不过度反弹

注意：

1. `run-local` 不依赖 LangSmith，可独立用于本地 smoke 与 prompt 调试。
2. `sync-langsmith` 和 `run-langsmith` 需要本地可用的 LangSmith SDK 与相应环境变量。

## 8. 何时增加新 sample

建议只在以下情况新增 sample：

1. 线上或联调中出现了一类明确退化
2. 新增了一个重要 annotation 能力
3. 新模型在某类句子上明显不稳定

不要为了“看起来更全面”无限加样本。

推荐控制在：

1. `3-5` 个核心 smoke samples
2. `5-10` 个扩展 regression samples

## 9. 维护原则

1. 样本集是本地调试资产，不进入生产链路。
2. 评测目标是“发现退化”，不是替代人工评审。
3. 每次只修改一类 prompt 或模型因素，再跑回归，避免无法归因。
4. 若样本长期不能反映当前产品目标，应直接调整或删除，不保留历史包袱。

## 10. 建议的下一步

当前这套工具搭好后，建议按这个顺序使用：

1. 先用 `run-local` 调 prompt
2. 再用 `run-langsmith` 记录实验
3. 当 sample 稳定后，再考虑补 LLM-as-judge evaluator

这样成本最低，也最不容易把评测系统本身做得过重。
