# 小程序联调与用户体验开发设计文档

> 文档定位：用于指导 Claread透读 微信小程序侧的真实联调、用户主链路建设与平台能力接入。  
> 生效范围：本稿用于和 workflow 输出优化并行推进的小程序产品开发，不替代后端 workflow 设计文档。  
> 核心目标：在 `/analyze` 仍持续优化的情况下，先建立一个真实可跑、可回看、可恢复、可交互的小程序产品闭环。

补充范围说明：

- 本文档当前只覆盖“用户输入解析结果页”相关链路
- “每日精读结果页”暂不纳入本稿范围，后续单独设计与开发
- 每日精读不按“用户点击后实时调用 `/analyze` 再渲染”的模式处理，而更适合走独立内容生产、拉取与展示链路
- 因此，本文档讨论的 `/analyze` 联调默认面向 `user_input` 场景，不把 `daily_article` 作为当前联调对象

## 1. 背景

当前项目已经进入两条主线并行推进阶段：

- 后端主线：继续优化 workflow 输出质量与稳定性
- 小程序主线：完成真实接口联调与用户完整体验开发

这两条主线不能再互相阻塞。

原因很明确：

- workflow 质量还需要持续迭代，但小程序产品开发量本身已经足够大
- 真实用户体验问题不会只出现在 `/analyze` 输出质量上，还会出现在 loading、错误恢复、回看、分享、登录态、页面跳转与微信平台能力接入上
- 如果继续等待 workflow “完全满意”再做联调，小程序整体进度会被单点问题长期卡住

因此本阶段的产品策略是：

- 不等待 `/analyze` 达到最终理想质量
- 先把“从输入到得到可交互结果页”的完整链路跑通
- 用前端容错、状态设计和平台接入，把产品主路径真正搭起来
- 当前主路径特指“用户输入文本 -> 提交 `/analyze` -> 查看解析结果”

## 2. 设计目标

本阶段目标按优先级排序如下：

1. 小程序前端从 mock 切换到真实后端接口
2. 用户从输入文本到查看结果的主链路完整可跑
3. 对空结果、warning、降级结果、失败重试都有明确体验设计
4. 形成最小可用的用户资产闭环，包括历史记录与回看
5. 把微信小程序平台能力接入成工程任务，而不是后期补丁

## 3. 非目标

本阶段明确不追求以下内容：

- 不等待 `/analyze` 输出质量达到“上线级”再开始联调
- 不一次性做完全部运营、学习、推荐能力
- 不在这一阶段把所有用户配置都开放给前端
- 不把复杂平台能力如 OCR、订阅消息作为当前 MVP 阻塞项
- 不在这一阶段处理“每日精读结果页”的产品设计与联调
- 不把每日文章点击后的阅读体验强行并入 `/analyze` 实时解析链路

## 4. 总体拆分

小程序联调与用户体验开发拆成四条主线：

1. 接口联调与数据适配
2. 结果页与分析流程体验
3. 用户态与内容资产管理
4. 微信小程序平台能力接入

这四条主线的关系如下：

```mermaid
flowchart TD
  A["接口联调与数据适配"] --> B["结果页与分析流程体验"]
  A --> C["用户态与内容资产管理"]
  A --> D["微信小程序平台能力接入"]
  C --> B
  D --> B
```

解释：

- `接口联调与数据适配` 是前置基础
- `结果页与分析流程体验` 是用户直接感知的主链路
- `用户态与内容资产管理` 决定产品是否只是一次性工具
- `微信小程序平台能力接入` 决定产品是否真正适配小程序环境

## 5. 主线一：接口联调与数据适配

### 5.1 目标

让“用户输入解析结果页”不再依赖 mock，而是消费真实 `/analyze` 响应，并具备稳定的协议适配能力。

### 5.2 核心任务

- 建立小程序前端统一 API 层
- 接入真实 `/analyze` 请求
- 建立后端响应到前端视图模型的 adapter
- 统一 snake_case 到前端消费结构的转换规则
- 明确请求的超时、重试、取消和去重策略
- 准备固定联调样本集

补充说明：

- 此处 `/analyze` 只用于用户主动提交文本后的解析链路
- 每日精读若后续上线，建议走“预生成内容 + 页面拉取渲染”链路，而不是复用这里的实时解析流程

### 5.3 必须处理的结果类型

前端不能只适配“理想结果”，必须明确接住以下场景：

- 正常结果
- 有 warning 的结果
- 无标注但有翻译的结果
- 局部降级结果
- 后端错误
- 超时与重试

补充约定：

- 后端内部 `warnings`、异常码和局部失败信号不应直接原样暴露给用户
- 前端结果页只展示产品级状态，不展示工程级错误细节
- 当前结果页以 `loading / normal / degraded_light / degraded_heavy / empty / failed / timeout / network_fail` 作为唯一页面状态入口
- 当前成功态已经开始消费后端 `user_facing_state`，但 `empty / failed / timeout / network_fail` 仍由前端页面状态机负责聚合

### 5.4 前后端状态边界

当前建议的边界如下：

- 后端负责产出稳定的正文结构、翻译、行内标注、句尾入口、warnings、错误码，以及成功态下的 `user_facing_state`
- 前端负责把这些技术信号聚合为用户可理解的状态、提示文案和交互入口，并继续兜底 `empty` 与错误态
- 后续需要继续收敛 `user_facing_state` 的判定规则，避免仅因非关键 warning 就触发降级 banner

当前页面状态映射原则：

| 输入信号 | 页面状态 | 用户表现 |
|------|------|----------|
| 有可渲染结果且无明显异常 | `normal` | 正常渲染结果页 |
| 有结果但部分深度讲解缺失 | `degraded_light` | 顶部轻提示 banner |
| 有结果但内容完整度明显不足 | `degraded_heavy` | 明显降级提示 + 重新分析入口 |
| 请求成功但无有效内容 | `empty` | 空状态页 + 修改重试 |
| 非网络型服务失败 | `failed` | 错误状态页 + 重试 |
| 请求超时 | `timeout` | 超时状态页 + 重试 |
| 网络异常 | `network_fail` | 网络错误页 + 重试 |

### 5.5 交付物

- 统一 API client
- `render_scene` adapter
- 联调样本清单
- 联调说明文档

### 5.6 验收标准

- 结果页已可切换为真实接口数据源
- mock 与真实接口的切换集中在单一入口
- 页面与组件不再各自散落字段转换逻辑
- warning / 空态 / 降级结果可稳定渲染

## 6. 主线二：结果页与分析流程体验

### 6.1 目标

把“输入文本 -> 等待分析 -> 查看结果 -> 用户继续操作”的体验做成完整产品链路。

### 6.2 核心任务

- 输入页到结果页的真实跳转打通
- 设计分析中的 loading 态
- 明确超时与失败提示
- 为空结果、warning、部分成功结果提供独立状态页或组件
- 补齐重试机制
- 补齐结果页核心交互
- 增加用户反馈入口

本节默认的“结果页”均指用户输入后的解析结果页，不包含每日精读阅读页。

### 6.3 分析中状态要求

分析中页面至少要覆盖：

- 初始发起中
- 正在分析中
- 超时等待中
- 分析失败可重试

不能只有一个统一 spinner。

### 6.3.1 前后端异步 analyze 协同约定

当前前端已经具备“先进入结果页，再展示 loading 态”的交互基础。  
后端正式方案不应继续把 `/analyze` 维持为“同步等待最终 `render_scene` 返回”的语义，而应升级为“提交任务 -> 轮询状态 -> 回填快照”的异步链路。

推荐协同方式：

- 输入页提交后，后端立即返回 `task_id + record_id`
- 结果页根据 `task_id` 轮询任务状态，而不是重发 analyze 请求
- 历史页直接读取 `record_id` 对应的云端记录，处理中也要可见
- 用户切后台、退出结果页或进入其他页面后，前端恢复时先查 `task_id / record_id` 当前状态
- 如果同一用户已有活跃 analyze 任务，后端直接返回当前活跃任务，前端跳转回该任务对应结果页

这条协同约定的核心价值：

- 防止多次点击导致重复解析
- 让 loading 过程可追溯、可恢复、可回看
- 让“记录 tab 可找到处理中任务”变成后端真能力，而不只是前端临时态

### 6.4 结果页状态要求

结果页至少要支持：

- 正常结果页
- 仅翻译结果页
- 带 warning 的结果页
- 空结果说明页
- 网络或服务异常页

当前联调阶段观察到的结果页问题：

- 页面已经能渲染真实 `/analyze` 结果，但信息层级仍偏混杂，正文、翻译、句尾入口和底部操作栏之间的视觉主次不够清晰
- 句尾入口当前以内联 chip 形式直接插入正文流，真实数据一多会打断阅读节奏
- 当前成功态虽然已经开始消费后端 `user_facing_state`，但降级规则仍不够稳定，结果完整度表达还需要继续收敛
- 结果页上的“收藏全文”“记入生词本”等能力已接入本地资产闭环，但词典查询和云端同步尚未补齐

当前优化方向：

- 前端优先重构阅读布局，拆分正文层、翻译层、句解入口层，降低信息混排
- 前后端一起收敛结果完整度表达，避免后端非关键 warning 直接触发降级提示
- 将结果页 CTA 从本地闭环升级为完整能力，并与词典服务、历史记录、收藏、生词本进一步打通

### 6.5 结果页交互范围

第一阶段建议纳入：

- inline mark 点击
- 全文英文单词点按查词
- 底部详情弹层
- 句子翻译查看
- warning 展开与收起
- 一键重新分析
- 返回修改文本
- 用户反馈入口

### 6.6 交付物

- 输入页到结果页完整主链路
- loading / error / empty / degraded 组件
- 结果页真实联调版本
- 统一错误文案与状态文案

### 6.7 验收标准

- 从输入文本到查看结果完整可跑
- 所有主要状态都有对应 UI
- 结果页不再假设“每次一定有丰富标注”
- warning 和失败信息对用户可见、可理解

## 7. 主线三：用户态与内容资产管理

### 7.1 目标

让 Claread透读 不只是一次性分析工具，而是具有回看、保存与持续使用价值的产品。

### 7.2 核心任务

- 设计最小登录策略
- 建立分析记录保存能力
- 提供最近记录列表
- 支持收藏 / 删除 / 再次查看
- 支持重新分析历史文本
- 预留用户配置入口，但 baseline 默认固定

### 7.3 登录策略原则

当前阶段建议：

- 允许用户先体验主流程
- 登录态不要成为第一次使用的阻塞项
- 需要保存、同步、收藏等动作时，再逐步引导进入登录态

进一步约束：

- 不要把登录放在输入页或首次进入结果页之前
- 不要以“先做完整账号体系”作为历史记录、收藏、生词本开发前提
- 第一阶段默认采用“匿名可用、登录增强”的产品策略
- 登录的价值应明确绑定到“跨设备同步、长期保存、恢复个人资产”，而不是为了完成一次分析

推荐登录触发时机：

- 用户首次点击“收藏全文”
- 用户首次点击“记入生词本”
- 用户首次尝试将本地历史同步到云端
- 用户进入“我的”页并主动选择登录

不推荐的触发时机：

- 打开小程序即强制登录
- 输入文章前强制登录
- 查看结果页前强制登录

### 7.4 内容资产范围

建议最小保存内容包括：

- 原始文本
- 分析请求参数
- 返回的 `render_scene`
- 生成时间
- 当前状态
- 基础反馈信息

建议补充字段边界：

- `record_id`: 历史记录主键，由前端本地生成或后端统一生成
- `source_text`: 原始输入文本
- `request_payload`: 发给 `/analyze` 的稳定请求参数
- `render_scene`: 当前后端返回的渲染结果快照
- `page_state_snapshot`: 当次展示时的页面状态
- `created_at`: 创建时间
- `updated_at`: 最近一次重新分析时间
- `is_favorited`: 是否收藏全文
- `vocab_refs`: 结果页中被加入生词本的词条引用
- `sync_state`: `local_only / syncing / synced / sync_failed`

资产建模原则：

- 结果回看默认读取“快照”，而不是每次重新请求 `/analyze`
- “重新分析”是显式操作，不要在回看历史时自动刷新旧结果
- 历史记录、收藏、生词本是三种能力，不要混成同一张逻辑表
- 第一阶段允许历史记录与收藏只在本地存在，但数据结构要为未来云端同步预留主键和状态字段

推荐的最小数据模型拆分：

#### 分析记录 `analysis_records`

- 存一条完整分析快照
- 作为历史记录页和结果回看页的数据来源

#### 收藏全文 `favorite_records`

- 只存对 `analysis_records.record_id` 的引用
- 不复制整份 `render_scene`

#### 生词本 `vocabulary_book`

- 存词条级资产
- 记录来源 `record_id`、词条文本、词性、释义、加入时间、是否已掌握

这样拆的原因：

- 历史记录关注“一次分析”
- 收藏关注“保留某篇结果”
- 生词本关注“词条级学习资产”

如果一开始把三者混到一起，后续重构成本会明显上升

### 7.5 第一阶段不强制开放的内容

- 全部阅读配置切换
- 学习统计
- 复杂标签分类
- 高级搜索与筛选

### 7.6 交付物

- 用户记录数据模型草案
- 历史记录页
- 收藏与删除能力
- 回看与重新分析能力
- 登录态与匿名态策略说明

### 7.7 实施导向与边界

为了避免后续重构困难，主线三建议按以下顺序落地：

#### 第一步：本地历史闭环

- 先把 `analysis_records` 落到小程序本地存储
- 历史记录页只消费本地记录
- 结果页支持从历史记录进入“回看模式”
- 回看模式默认不重新请求接口

补充约束：

- 一旦后端 analyze 升级为异步任务中心，云端 `analysis_records` 也应在提交时立即创建
- 这样历史页既能显示“已完成结果”，也能显示“处理中 / 失败”的云端记录
- 本地记录与云端记录都应保留稳定 `record_id`，不能在任务完成后再临时换主键

#### 第二步：结果页资产动作真接线

- “收藏全文”接到 `favorite_records`
- “记入生词本”接到 `vocabulary_book`
- 三者共用稳定的 `record_id`

#### 第三步：登录增强

- 引入登录后，优先做“本地资产同步到云端”
- 不要先做复杂个人中心，再回头补数据结构

#### 第四步：云端同步

- 先同步 `analysis_records`
- 再同步 `favorite_records`
- 最后同步 `vocabulary_book`

推荐这样排序的原因：

- 历史记录是结果页闭环的基础
- 收藏和生词本依赖历史记录主键
- 登录和云同步是增强层，不应反向决定本地数据结构

明确禁止的做法：

- 让 history 页点击后重新调用 `/analyze` 代替结果回看
- 收藏时整份复制 `render_scene` 到另一套结构
- 用散落的 `Taro.setStorageSync` key 拼接出多套不一致的数据源
- 先做 UI 占位页，再临时改数据结构去适配

### 7.8 验收标准

- 用户离开结果页后仍可回看历史内容
- 切后台或重新进入小程序后，主路径上下文不会完全丢失
- 保存与回看能力和真实接口结构兼容

### 7.9 Workflow 之外的新开发路线图

推荐按以下顺序推进：

#### Phase A：匿名态本地资产闭环

- 保存最近一次分析请求参数与结果快照
- 建立本地历史记录列表
- 支持结果页回看、重新分析、异常恢复
- 将历史页从静态卡片替换为真实本地数据源

#### Phase B：结果页真能力接入

- 接入词典查询接口，替换当前词典 fallback
- 接通“收藏全文”“记入生词本”等 CTA 的真实数据流
- 明确结果页与历史/收藏/生词本的数据主键与回看策略

##### Phase B.1：TECD3 本地词典接入改造清单

目标：

- 词典能力统一收口到后端 `/dict`
- MVP 阶段改为本地英中词典优先，不依赖第三方在线词典 API
- 词典查询结果既能服务结果页弹层，也能服务生词本快照落库
- 通过本地索引与缓存降低查询延迟，保证结果页点词体验稳定

设计原则：

- 小程序前端只调用自有服务域名下的 `/dict`
- MVP 默认数据源调整为本地 `TECD3`，不再依赖在线词典 provider
- 前端只消费稳定的词典视图模型，不感知词典底层存储结构
- 生词本保存“渲染快照”，不要保存整份原始词典记录
- 词典数据结构优先服务“结果页小卡片 + 底部详情页 + 生词本”，不追求学术级完整性
- `phrase_gloss` 应由 workflow / vocabulary agent 直接提供可渲染的 glossary，并默认不走词典查询主路径

为什么必须走后端服务：

- 微信小程序对合法请求域名、鉴权方式和网络细节有约束，前端不适合直接查询词典数据源
- 本地词典虽然不需要第三方 API key，但查询归一化、词形还原、缓存、生词本复用都属于服务端职责
- 前端只需要关心“点词能否稳定返回中文释义”，不应该感知词库文件或 SQLite 结构

改造范围：

#### 前端侧

- 将 `WordPopup` 中的本地 fallback 替换为真实 `/dict` 请求
- mini 卡片优先展示 `word`、`phonetic`、`short_meaning`
- full bottom sheet 展示 `meanings[]`，每个词性块限制释义条数，优先保证排版稳定
- “记入生词本”按钮保存词典快照字段，而不是仅保存临时截断文本
- 在页面会话内允许增加轻量内存缓存，避免同页反复点击同一个词时重复请求
- `fetchDict` 继续服务普通词查询，`phrase_gloss` 点击不再以 `/dict` 为主解释来源
- `grammar_note` 等结构标注不能阻断词级点击
- 前端全文点词切分已从简单双正则升级为轻量 lexer，当前已覆盖 `U.S.`、`U.K.`、`state-owned`、`world's` 等特殊 token；后续继续补 alias normalization 与更多边界样例

#### 后端侧

- 保留 `/dict` 作为唯一词典接口入口
- 将当前“服务骨架 + 第三方 provider”的实现切换为 `route -> service -> local provider -> cache`
- 本地 / 正式 provider 负责读取 `TECD3` 离线解析后导入的词典表，并归一化返回
- `TECD3` 的 `.mdx/.mdd` 资源默认通过 `mdict-utils` 做离线解包/导出，再由 `import_tecd3.py` 解析导入 PostgreSQL
- cache 层至少支持：
  - L1：进程内 TTL cache，用于热点词重复点击
  - L2：正式环境优先考虑 `PostgreSQL` 真源；`Redis` 作为第二阶段可选缓存层，不再继续扩展磁盘 JSON 文件缓存
- service 层负责：
  - 查询词归一化
  - 先查缓存，再查本地 provider
  - 统一词形还原、未命中回退和错误映射
  - 输出稳定 DTO
- workflow 需要保证 `phrase_gloss` 输出中自带可直接渲染的 glossary

推荐的最小后端目录拆分：

- `server/app/api/routes/dict.py`
- `server/app/services/dictionary/service.py`
- `server/app/services/dictionary/cache.py`
- `server/app/services/dictionary/providers/base.py`
- `server/app/services/dictionary/providers/tecd3.py`
- `server/app/services/dictionary/normalizer.py`
- `server/app/services/dictionary/lemma.py`
- `server/scripts/import_tecd3.py`
- 正式环境中的 `dict_entries / dict_aliases` 表

推荐的统一返回结构：

```json
{
  "query": "paradigm",
  "entry": {
    "word": "paradigm",
    "lemma": "paradigm",
    "phonetic": "/ˈpærədaɪm/",
    "audio_url": null,
    "short_meaning": "范式；思维模式",
    "meanings": [
      {
        "part_of_speech": "n.",
        "definitions": [
          {
            "meaning": "范式；典范",
            "example": null
          }
        ]
      }
    ],
    "tags": ["CET4"],
    "exchange": ["paradigm", "paradigms"]
  },
  "provider": "tecd3",
  "cached": true,
  "cache_expires_at": "2026-04-06T12:00:00Z"
}
```

字段边界说明：

- `short_meaning`：服务 mini 卡片与生词本列表，不要求严格词典级专业度
- `meanings[]`：服务 full 详情弹层
- `lemma`：如后续需要词形归并可保留，否则允许为空
- `tags`：非核心字段，可后置
- `exchange`：非核心字段，可后置
- `provider`：用于问题排查和后续多 provider 策略
- `cached`：用于调试与观测，不强制前端展示

生词本建议最小快照字段：

- `word`
- `lemma`
- `phonetic`
- `audio_url`
- `part_of_speech`
- `short_meaning`
- `tags`
- `exchange`
- `source_provider`
- `record_id`
- `added_at`

缓存策略建议：

- 查询 key：`provider + normalized_query`
- 归一化规则：`trim + lowercase`
- L1 TTL：`24h`
- L2：正式环境优先以 `PostgreSQL` 为真源；高频热点缓存后续按需接 `Redis`
- 对 `not_found` 结果也允许短 TTL 缓存，避免重复查空词

provider 选型建议：

- MVP 默认 provider：`TECD3`
- 开发期可用本地 MDX 离线解析验证，正式上线目标是迁入 `PostgreSQL`
- 中期如需增强，可在 `TECD3` 之上补语境释义增强或第二数据源
- 当前阶段不建议继续依赖第三方在线词典 API 作为主 provider

当前推荐决策：

- 先将后端 `/dict` 切换为本地 `TECD3` provider，完成结果页真实接线
- 不在小程序前端开放用户自配 API key
- 如后续需要更丰富词典能力，再评估第二 provider 或语境增强
- 短语标注直接以 glossary 解释为主，不再把 phrase 是否命中词典作为稳定性前提

文档维护要求：

- 主线词典策略、`/dict` 协议和页面数据边界以本文档为准
- 本次 `TECD3` 接入的详细执行方案见 `docs/architecture/tecd3-local-dictionary-integration.md`
- 正式上线架构、登录、云端数据和部署决策见 `docs/architecture/production-architecture-and-deployment-plan.md`
- 如果后续新增第二 provider，应先更新本文档与 `TECD3` 执行方案文档，再进入开发
- 如果生词本模型扩展字段，应同步更新本节和主线三的数据模型边界

#### Phase C：登录与身份态

进入 Phase C 之前，先执行 [production-architecture-and-deployment-plan.md](./production-architecture-and-deployment-plan.md) 中的 “P0 开发前置清单”，优先收口：

- 数据模型与索引
- `/auth` 协议
- 开发期本地资产导入策略
- API contract
- 部署与环境变量约定

- 设计不阻塞首用的微信登录策略
- 在需要同步保存、跨设备回看时再触发登录
- 完成 token/session 注入，替换当前预留的认证头空实现

#### Phase D：云端内容资产

- 建立云端分析记录、收藏、生词本的最小数据模型
- 支持本地与云端数据对齐
- 支持删除、再次查看、重新分析和基础筛选

#### Phase E：平台化与发布准备

- 增加分享、页面恢复、埋点、异常上报
- 补齐弱网、切后台、重进小程序后的恢复策略
- 完成真机性能、包体、合规检查

### 7.10 官方参考资料

主线三在实现时，建议至少对照以下微信官方文档：

- 小程序登录 `wx.login`：
  [https://developers.weixin.qq.com/miniprogram/dev/api/open-api/login/wx.login.html](https://developers.weixin.qq.com/miniprogram/dev/api/open-api/login/wx.login.html)
- 服务端换取会话 `auth.code2Session`：
  [https://developers.weixin.qq.com/miniprogram/dev/api-backend/open-api/login/auth.code2Session.html](https://developers.weixin.qq.com/miniprogram/dev/api-backend/open-api/login/auth.code2Session.html)
- 本地存储 `wx.setStorageSync`：
  [https://developers.weixin.qq.com/miniprogram/dev/api/storage/wx.setStorageSync.html](https://developers.weixin.qq.com/miniprogram/dev/api/storage/wx.setStorageSync.html)
- 本地存储 `wx.getStorageSync`：
  [https://developers.weixin.qq.com/miniprogram/dev/api/storage/wx.getStorageSync.html](https://developers.weixin.qq.com/miniprogram/dev/api/storage/wx.getStorageSync.html)

阅读建议：

- 登录方案设计时同时看 `wx.login` 和 `auth.code2Session`
- 本地历史、收藏、生词本设计时同时看 `setStorageSync/getStorageSync` 的容量和生命周期约束
- 不要只看 API 用法，要把“本地资产结构”和“登录触发时机”一起设计

## 8. 主线四：微信小程序平台能力接入

### 8.1 目标

把产品真正放进微信小程序环境，而不是只做一套页面壳。

### 8.2 核心任务

- 登录与身份态接入
- 本地缓存策略
- 分享能力接入
- 剪贴板与粘贴体验优化
- 路由与页面栈恢复
- 前后台切换状态恢复
- 埋点与异常上报
- 真机性能与包体检查
- 平台合规项检查

主线四的核心目标不是“多接几个微信能力”，而是建立一套稳定的小程序运行机制，确保结果页、历史页和未来资产能力在真实环境里不会因为生命周期或弱网问题失效。

### 8.3 必须关注的微信平台问题

以下内容不能后期随意补：

- 小程序登录链路
- 页面切后台后的分析状态恢复
- 分享结果页的入口设计
- 本地缓存与请求重放
- 真机性能问题
- 审核与合规敏感点

### 8.4 平台接入总原则

主线四建议遵循以下原则：

- 先保证状态恢复，再考虑平台花活
- 先做最小闭环，再做分享、埋点、合规增强
- 所有平台能力都要围绕“输入 -> 分析 -> 查看 -> 保存/回看”主链路服务
- 不要为了小程序特性改坏结果页和数据层的通用结构

运行时状态建议分层：

#### 临时会话态

用于：

- 当前输入框内容
- 当前分析中的请求状态
- 当前结果页交互态

特点：

- 允许丢失
- 由 store 管理
- 不作为历史资产

#### 本地持久态

用于：

- 最近输入草稿
- 历史分析记录
- 收藏记录
- 生词本
- onboarding 状态

特点：

- 进入 storage
- 可以在重启小程序后恢复

#### 云端同步态

用于：

- 登录后的跨设备数据
- 长期保留资产

特点：

- 与本地持久态分开管理
- 要有 `sync_state`

这样分层的目的，是避免把“当前页面状态”和“长期用户资产”混在一起

### 8.5 平台能力建议分层

#### 小程序前端层

负责：

- 页面
- 交互
- 本地缓存
- 页面路由
- 分享入口

#### 轻服务或云函数层

可负责：

- 简单 CRUD
- 登录态辅助
- 内容安全审核调用

#### 核心后端层

负责：

- `/analyze`
- workflow
- 业务规则
- 结构化输出
- 模型调用

补充说明：

- 每日精读结果页若采用预生产内容模式，其内容获取、缓存、下发与展示可以走独立逻辑
- 该能力不应反向约束当前 `/analyze` 联调设计

### 8.6 关键能力实施导向

#### 8.6.1 本地缓存策略

建议至少拆成三类 key：

- 输入草稿
- 历史分析记录
- 用户偏好与 onboarding

不要把所有内容塞进单一大对象。推荐原因：

- 输入草稿与历史记录生命周期不同
- 偏好配置变更频率低，不应和大体积结果快照共用写入路径

#### 8.6.2 页面恢复策略

建议明确以下恢复规则：

- 输入页：恢复最近一次未提交草稿
- 结果页：如果上一次分析已成功，优先恢复结果快照；如果分析进行中但没有可靠恢复机制，直接转成可重试状态
- 历史页：从本地持久化数据直接渲染

不建议：

- 小程序回前台后盲目续跑上一次网络请求
- 结果页自动再次发起 `/analyze`

#### 8.6.3 登录与身份态接入

建议拆成两层：

- 小程序身份获取：微信登录、拿到 code 或会话标识
- 业务身份绑定：你们自己的 session/token

约束：

- 不要让前端直接承担复杂身份编排
- 登录成功后只通过统一请求头注入身份态
- 业务接口不要同时支持多种前端临时拼接认证方式

#### 8.6.4 分享能力

第一阶段建议只支持：

- 分享历史记录或结果回看页入口
- 分享后打开的是稳定可恢复页面，而不是一次性会话态

不建议第一阶段就做：

- 分享实时分析中的页面
- 分享临时结果态且依赖内存 store 才能打开的链接

#### 8.6.5 埋点与异常上报

建议最少覆盖：

- 输入提交
- 分析成功
- 分析失败
- 重试
- 收藏全文
- 加入生词本
- 查看历史记录

异常上报至少要带：

- 页面名
- request_id
- page_state
- 接口错误码
- 是否为回看模式

#### 8.6.6 真机性能与包体

结果页属于高密度渲染场景，专项关注：

- 长文本滚动性能
- 底部弹层与词典弹层叠加时的交互流畅性
- 大体积历史快照写入 storage 的耗时
- 首次进入结果页的渲染抖动

如果这部分不提前约束，后续最容易出现“功能都接上了，但真机不可用”的问题

### 8.7 交付物

- 平台接入清单
- 生命周期处理方案
- 埋点与异常上报方案
- 发布前检查清单

### 8.8 验收标准

- 关键主路径可在真机稳定运行
- 切后台、弱网、重进小程序不导致主流程直接报废
- 分享、缓存、路由返回符合产品预期

### 8.9 官方参考资料

主线四在实现时，建议至少对照以下微信官方文档：

- App 生命周期：
  [https://developers.weixin.qq.com/miniprogram/dev/reference/api/App.html](https://developers.weixin.qq.com/miniprogram/dev/reference/api/App.html)
- 页面生命周期：
  [https://developers.weixin.qq.com/miniprogram/dev/framework/app-service/page-life-cycle.html](https://developers.weixin.qq.com/miniprogram/dev/framework/app-service/page-life-cycle.html)
- 小程序运行机制：
  [https://developers.weixin.qq.com/miniprogram/dev/framework/runtime/operating-mechanism.html](https://developers.weixin.qq.com/miniprogram/dev/framework/runtime/operating-mechanism.html)
- 小程序更新机制：
  [https://developers.weixin.qq.com/miniprogram/dev/framework/runtime/update-mechanism.html](https://developers.weixin.qq.com/miniprogram/dev/framework/runtime/update-mechanism.html)
- 转发与分享能力：
  [https://developers.weixin.qq.com/miniprogram/dev/framework/open-ability/share.html](https://developers.weixin.qq.com/miniprogram/dev/framework/open-ability/share.html)
- 分享到朋友圈：
  [https://developers.weixin.qq.com/miniprogram/dev/framework/open-ability/share-timeline.html](https://developers.weixin.qq.com/miniprogram/dev/framework/open-ability/share-timeline.html)
- 启动参数 `wx.getEnterOptionsSync`：
  [https://developers.weixin.qq.com/miniprogram/dev/api/base/app/life-cycle/wx.getEnterOptionsSync.html](https://developers.weixin.qq.com/miniprogram/dev/api/base/app/life-cycle/wx.getEnterOptionsSync.html)
- 场景值列表：
  [https://developers.weixin.qq.com/miniprogram/dev/reference/scene-list.html](https://developers.weixin.qq.com/miniprogram/dev/reference/scene-list.html)
- 开发者工具下载：
  [https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html](https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html)

阅读建议：

- 页面恢复策略至少要同时参考 App 生命周期、页面生命周期和运行机制
- 分享能力设计时同时看“转发给朋友”和“分享到朋友圈”，两者能力边界不同
- 真机验证和发布前检查不要只依赖模拟器，应结合开发者工具和真实场景值验证

## 9. 依赖关系与并行建议

### 9.1 强依赖

- `接口联调与数据适配` 是其他三条主线的共同底座

### 9.2 可并行推进

- `结果页与分析流程体验`
- `用户态与内容资产管理`
- `微信小程序平台能力接入`

### 9.3 建议的并行分工

如果按 2 个 agent 分工：

- Agent 1：接口联调与结果页体验
- Agent 2：用户态与微信平台能力

如果按 3 个 agent 分工：

- Agent 1：`/analyze` 联调与 adapter
- Agent 2：结果页状态与交互体验
- Agent 3：登录、历史记录与微信平台能力

## 10. MVP 与非 MVP 边界

### 10.1 当前阶段建议纳入 MVP

- 真实 `/analyze` 联调
- API adapter
- loading / error / empty / degraded 状态
- 结果页核心交互
- 历史记录最小闭环
- 登录策略说明与基础落地
- 小程序基础平台能力接入

说明：这里的 MVP 结果页仅指用户输入解析结果页。

### 10.2 当前阶段可延后

- OCR
- 订阅消息
- 学习统计
- 高级配置中心
- 复杂推荐与运营能力
- 复杂多端统一体验
- 每日精读结果页的独立产品形态与联调方案

## 11. 评审关注点

评审这份文档时，建议重点看以下问题：

1. 是否已经覆盖真实用户主路径，而不是只覆盖“分析成功”理想态
2. 是否把 mock 思维切换成了真实接口思维
3. 是否把 warning / 空结果 / 降级结果纳入产品设计
4. 是否把历史记录和回看纳入最小产品闭环
5. 是否把微信平台能力作为独立工程任务对待
6. 是否仍存在会被 `/analyze` 质量持续阻塞的开发依赖

## 12. 最终结论

小程序联调与用户体验开发，不应继续等待 workflow 输出达到最终理想状态再开始。

当前更合理的策略是：

- workflow 继续独立优化
- 小程序侧同步建立真实接口、真实状态、真实用户路径和真实平台能力
- `/analyze` 当前只承担用户输入解析主路径
- 每日精读后续按独立页面与独立内容链路处理

这样做的价值是：

- 不让模型质量问题长期阻塞产品开发
- 尽早暴露真实链路里的体验问题
- 把 Claread透读 从”后端可跑”推进到”产品可用”

---

## 13. 实现状态跟踪

> 以下记录本文档各主线的实际实现进度，用于团队对齐。

### 主线一：接口联调与数据适配

| 任务 | 状态 | 文件位置 |
|------|------|----------|
| 统一 API client (`fetchAnalyze`) | ✅ 完成 | `client/src/services/api/client.ts` |
| `AnalyzeResponseDto` 类型定义 | ✅ 完成 | `client/src/types/api/analyze-response.dto.ts` |
| `RenderSceneVm` 前端视图模型 | ✅ 完成 | `client/src/types/view/render-scene.vm.ts` |
| `analyzeResponseDtoToVm` 适配器 | ✅ 完成 | `client/src/services/api/adapters/render-scene.adapter.ts` |
| 环境配置 (local/dev/prod) | ✅ 完成 | `client/src/config/env.ts` |
| 前端页面状态机聚合 | ✅ 完成 | `client/src/stores/article.ts` |
| 后端聚合状态字段 (`user_facing_state`) | 🟡 已部分收敛 | `server/app/workflow/analyze_nodes.py`， informational warnings（LOW_ENGLISH_RATIO / HIGH_NOISE_RATIO / UNSUPPORTED_TEXT_TYPE / DRAFT_VALIDATION）不再触发降级。但任何非 informational 列表内的 warning（如 REPAIR_AGENT_FAILED）仍会触发 degraded_light，规则边界比"仅 agent 失败"更宽 |

**类型边界已确立：**
- `types/api/` = 后端 DTO (snake_case)
- `types/view/` = 前端 VM (camelCase)
- 转换只在 `render-scene.adapter.ts` 一处

**当前缺口：**
- 已完成从 mock 设计转向真实接口联调，后端也已开始提供 `user_facing_state`
- 降级规则已部分收敛：informational warnings（LOW_ENGLISH_RATIO / HIGH_NOISE_RATIO / UNSUPPORTED_TEXT_TYPE / DRAFT_VALIDATION）不再触发降级，但 any non-informational warning（如 REPAIR_AGENT_FAILED，level=warning）仍会触发 degraded_light，规则边界比"仅 agent 失败"更宽
- 当前缺口是” `/dict` 端到端真机验证”、”前后台恢复策略落地”和”结果页 UI/UX 布局优化”

### 主线二：结果页与分析流程体验

| 任务 | 状态 | 文件位置 |
|------|------|----------|
| Store 迁移到 `RenderSceneVm` | ✅ 完成 | `client/src/stores/article.ts` |
| Input 页调用 `store.analyze()` | ✅ 完成 | `client/src/pages/input/index.tsx` |
| Result 页连接 Store | ✅ 完成 | `client/src/pages/result/index.tsx` |
| **独立状态机** (idle/loading/success/empty/error) | ✅ 完成 | `client/src/stores/article.ts` |
| **”先跳结果页再发请求”** 流程 | ✅ 完成 | `input/index.tsx` |
| Loading 状态 UI | ✅ 完成 | `result/index.tsx` |
| Error 状态 UI | ✅ 完成 | `result/index.tsx` |
| **Empty 状态 UI** | ✅ 完成 | `result/index.tsx` |
| 降级状态 banner | ✅ 完成 | `client/src/pages/result/index.tsx` |
| **source_type 边界注释** | ✅ 完成 | `client.ts`, `render-scene.vm.ts` |
| 全文点词查词（含普通词 + 标注词） | ✅ 完成 | `ParagraphBlock` + `InlineMark` + `ClickableWord` + `WordPopup`，`onWordClick` 统一 payload |
| 底部详情弹层 | ✅ 完成 | `BottomSheetDetail` |
| “重新分析” 按钮 | ✅ 完成 | `result/index.tsx` |
| 页面模式切换 (沉浸/双语/精读) | ✅ 完成 | `result/index.tsx` |
| 结果页布局针对真实数据优化 | 🟡 进行中 | 已能渲染真实数据，但 UI/UX 仍需重构 |
| 历史页"去粘贴文章"导航 | ✅ 已修复 | `history/index.tsx` 从 `switchTab` 改为 `navigateTo`（input 非 tabBar 页面） |
| `/dict` 真接口接入 | ✅ 完成 | `WordPopup` 已接入真实 `/dict` API，失败时降级显示 fallback |
| 收藏全文 / 生词本真实能力 | ✅ 完成 | 结果页 CTA 已接线到本地存储闭环，云端同步未开始 |
| 历史页筛选 Tab（全部 / 已收藏） | ✅ 完成 | `history/index.tsx`，`activeTab` 状态 + 筛选逻辑 |

**组件类型已统一：**
- 所有组件 (`ParagraphBlock`, `InlineMark`, `WordPopup`, `BottomSheetDetail`, `SentenceActionChip`) 从 `@/types/view/render-scene.vm` 导入类型
- `SpanRef.anchorText` 统一使用 `anchorText` 字段

**当前联调结论：**
- 结果页主链路已通，可以稳定渲染真实后端返回
- 当前问题已从“能不能显示”切换为“如何更好显示”
- 下一阶段重点应放在布局层级、信息密度和结果完整度表达，而不是继续维护旧的 mock 调试设施

### 主线三：用户态与内容资产管理

| 任务 | 状态 | 说明 |
|------|------|------|
| Onboarding 完成标记本地存储 | ✅ 完成 | `Taro.getStorageSync/setStorageSync('user_configured')` |
| 历史记录页注册 | ✅ 完成 | 已切换为真实本地数据源，支持删除、下拉刷新、回看 |
| 个人中心页注册 | 🟡 占位完成 | 页面已存在，但用户信息和统计均为静态文案 |
| 分析请求参数保存在 store | ✅ 完成 | 当前支持结果页就地重试 |
| 本地分析结果持久化 | ✅ 完成 | 已建立 storage 服务封装，分析后自动保存并支持 `loadRecord` 回看 |
| 收藏 / 删除 / 再次查看 | ✅ 完成 | 收藏全文、历史删除、回看已接线，云端同步仍未开始 |
| 生词本数据模型 | ✅ 完成 | `VocabEntry` 已落地，本地“记入生词本”已接线 |
| 云端历史记录接口 | 🔲 未开始 | 后端当前无对应路由 |
| 输入草稿自动保存与离开保护 | ✅ 完成 | 输入页支持 500ms 防抖自动保存和离开提示 |
| 词典前端接线 | ✅ 完成 | `WordPopup` 已接入真实 `/dict` API（`fetchDict` + `dict.adapter.ts`），失败降级 fallback |
| 词典后端服务骨架 | ✅ 完成 | `/dict` 已切换到本地 `TECD3` provider，运行时查询 `dict_entries / dict_aliases` |
| TECD3 迁入正式词典库 | ✅ 完成 | 已补齐 `TECD3` 导入脚本、PostgreSQL schema 与 `/dict` 查询链路 |

### 主线四：微信小程序平台能力接入

| 任务 | 状态 | 说明 |
|------|------|------|
| 页面路由骨架 | ✅ 完成 | onboarding / home / input / result / history / profile 已注册 |
| 基础本地缓存能力使用 | ✅ 完成 | 已用于 onboarding、输入草稿、历史记录、收藏、生词本 |
| 登录态请求头注入预留 | 🟡 已预留 | `getAuthHeaders()` 仍为空实现 |
| 前后台状态恢复 | 🟡 部分完成 | `app.tsx` 已注册 `Taro.onAppShow`，但当前只有 console.log，无实际恢复逻辑。Result 页正在分析中时切后台，回来可能丢失状态 |
| 分享能力接入 | ✅ 完成 | `result/index.tsx` 已注册 `useShareAppMessage`，配置 `enableShareAppMessage: true` |
| 埋点与异常上报 | 🟡 console 占位完成 | `services/analytics.ts` 仅 `console.log` stub，无真实 SDK，无上报链路。真实埋点和异常上报需在 Phase C/D 接入 |
| 真机性能与包体检查 | 🔲 未开始 | 仍需专项验收 |
| Android 兼容性渲染修复 | ✅ 完成 | 结果页已移除 `backdrop-filter`，改为更稳定的阴影方案 |

---

**最后更新：** 2026-04-07（完成 `/dict` 切换到 `TECD3`，移除 `ECDICT` 运行时代码，并保持结果页点词与生词本链路可用）

### Bug 修复记录

| 日期 | Bug | 修复文件 | 说明 |
|------|-----|---------|------|
| 2026-04-05 | `user_facing_state` 降级规则过激 | `server/app/workflow/analyze_nodes.py` | informational warnings 不再触发 degraded_light |
| 2026-04-05 | 历史页导航使用 `switchTab`（input 非 tabBar 页）| `client/src/pages/history/index.tsx` | 改为 `navigateTo` |
| 2026-04-05 | 源目录残留 .js 编译产物（stale compiled output）| `client/src/` | 删除 32 个过时编译文件，保留所有 `.config.js` |
| 2026-04-05 | 文档状态失真：analytics 标 ✅ 实为 console stub | `docs/.../mini-program-integration-and-ux-design.md` | 改为 🟡 console 占位完成 |
| 2026-04-05 | 文档状态失真：user_facing_state 标"规则已收敛" | `docs/.../mini-program-integration-and-ux-design.md` | 改为 🟡 已部分收敛，补充 REPAIR_AGENT_FAILED 等非 informational warning 仍触发降级的说明 |
| 2026-04-05 | 新增全文点词查词：结果页所有英文词均可点击查词 | `ParagraphBlock` + `ClickableWord` + `InlineMark` | 普通词触发 `/dict` mini 弹层，标注词保留 glossary + examTags + AI 增强，payload 统一为 `{ word, mark, event }` |
| 2026-04-05 | 全文点词分词正则导致模拟器卡死 | `client/src/components/ParagraphBlock/utils.ts` | `[^a-zA-Z]*` 改为 `[^a-zA-Z]+`，消除零长度匹配导致的 `exec()` 死循环 |
| 2026-04-05 | 词典后端服务化落地 | `server/app/api/routes/dict.py` + `server/app/services/dictionary/*` | `/dict` 已升级为 route → service → provider → cache 结构，支持缓存命中标记 |
| 2026-04-07 | `/dict` 默认 provider 切换为 `TECD3` | `server/app/services/dictionary/*` + `server/scripts/import_tecd3.py` | 运行时查询收口到 PostgreSQL `dict_entries / dict_aliases`，并删除 `ECDICT` 旧代码 |
| 2026-04-06 | 全文点词切分升级为轻量 lexer | `client/src/components/ParagraphBlock/utils.ts` | 不再依赖单条正则分词，改为面向阅读交互的扫描器，支持缩写、连字符词、撇号与特殊 token |
