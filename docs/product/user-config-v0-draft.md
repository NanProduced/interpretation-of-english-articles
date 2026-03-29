# 初版用户配置草案

版本：`v0.1.0-draft`

状态：草案。当前用于指导 Prompt 注入、Profile 映射和输出 Schema 设计，后续根据真实调试结果继续迭代。

## 文档目的

在定义正式 `schema v0` 前，先收敛第一版用户配置项。原因是：

- Prompt 需要知道“在为谁解释”
- 输出中的优先级、解释风格、默认展示层级都依赖用户配置
- 如果用户配置不先收敛，Workflow 和 Schema 会一起漂移

## 设计原则

### 1. 用户侧配置尽量少

用户不应被要求手动选择过多选项，更不应该直接设置复杂参数。

### 2. 系统侧配置要足够清晰

前端只收集少量配置项，后端再把这些配置映射为 `profile_key` 和一组解释规则。

### 3. 先支持“足够驱动差异化”的最小集合

当前阶段的目标不是覆盖所有用户细分，而是让 Prompt 与输出优先级具备稳定的差异化依据。

## 初版用户配置项

## 配置项 1：使用目的 `usage_purpose`

枚举值：

- `exam`
- `daily_reading`
- `academic`

解释：

- `exam`：备考导向，强调考点、考试词汇、主干提取和应试理解
- `daily_reading`：日常阅读提升，强调易懂、自然、降低理解门槛
- `academic`：学术/专业阅读，强调结构、逻辑、术语和学术语境

## 配置项 2：使用细分 `usage_variant`

### 当 `usage_purpose = exam`

枚举值：

- `gaokao`
- `cet4`
- `cet6`
- `kaoyan`
- `ielts`
- `toefl`

### 当 `usage_purpose = daily_reading`

枚举值：

- `beginner_reading`
- `intermediate_reading`
- `intensive_reading`

### 当 `usage_purpose = academic`

枚举值：

- `general`

## 初版不纳入的用户配置

以下配置先不进入第一版：

- 用户手动自评英语等级滑杆
- 词汇量自评
- “简洁解释 / 详细解释”独立开关
- 是否显示全部语法标签
- 专业领域标签
- 个性化显示偏好

这些能力未来都可能有价值，但当前会明显增加 Prompt、Schema 和前端交互复杂度。

## 后端映射结果

前端提交的用户配置在后端统一映射为系统使用的 Profile。

## 推荐的系统映射字段

- `profile_key`
- `implicit_level`
- `explanation_style`
- `translation_style`
- `focus_rules`
- `priority_mapping_key`

## 映射草案

| 用户配置 | profile_key | implicit_level | explanation_style | translation_style |
| --- | --- | --- | --- | --- |
| exam + gaokao | exam_gaokao | beginner_to_intermediate | exam_oriented_basic | exam_reading |
| exam + cet4 | exam_cet4 | intermediate | exam_oriented | exam_reading |
| exam + cet6 | exam_cet6 | upper_intermediate | exam_oriented_advanced | exam_reading |
| exam + kaoyan | exam_kaoyan | upper_intermediate | exam_oriented_advanced | exam_reading |
| exam + ielts | exam_ielts | upper_intermediate_to_advanced | exam_oriented_international | exam_reading |
| exam + toefl | exam_toefl | upper_intermediate_to_advanced | exam_oriented_international | exam_reading |
| daily_reading + beginner_reading | daily_beginner | beginner | plain_and_supportive | natural |
| daily_reading + intermediate_reading | daily_intermediate | intermediate | plain_and_balanced | natural |
| daily_reading + intensive_reading | daily_advanced | advanced | detailed_reading | natural |
| academic + general | academic | advanced | structural_and_academic | academic |

## 这套配置如何影响 Workflow

### Prompt 注入

用户配置不会直接原样拼进 Prompt，而是通过 `profile_key` 注入规则片段，例如：

- 词汇解释风格
- 语法说明风格
- 长难句拆解方式
- 翻译倾向

### 输出优先级

标注本身的客观难度由模型判断，后处理再结合 `profile_key` 映射出：

- `core`
- `expand`
- `reference`

### 前端默认展示层

例如：

- `core` 默认高亮或优先展开
- `expand` 默认折叠但可展开
- `reference` 默认弱化展示

## 当前结论

第一版用户配置只保留两层：

- 用户层：`usage_purpose` + `usage_variant`
- 系统层：`profile_key` 与派生规则

这已经足够支撑：

- Prompt 差异化注入
- 优先级映射
- Schema 中的 profile 快照
- 前端默认展示策略

