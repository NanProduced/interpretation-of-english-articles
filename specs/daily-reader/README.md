# Daily Reader (每日精读)

## 当前实现基准

每日精读正在进行一次整体重构。新的实现请优先阅读并遵循：

1. [redesign-tracker.tmp.md](redesign-tracker.tmp.md)
2. [assets/daily-reader-design-reference.png](assets/daily-reader-design-reference.png)

核心方向：

- 单列小程序杂志阅读器，不做左右批注栏。
- 正文是沉浸英文阅读，词汇/短语/语境高亮低干扰且覆盖全篇。
- 每段只放轻量“透读”和可展开译文，不在正文插入重解析。
- 文末是“今日精读收束”，只展示少量高价值语言点。
- workflow 从“全文解读报告”改为“英语精读教案生成器”。

## 旧文档说明

以下文档是每日精读第一版实现与探索文档，仅作历史参考，不应作为当前重构的直接实现规范：

- [requirements.md](requirements.md)
- [review.md](review.md)
- [design.md](design.md)
- [tasks.md](tasks.md)
- [redesign-footer.md](redesign-footer.md)

如果旧文档与 [redesign-tracker.tmp.md](redesign-tracker.tmp.md) 冲突，以 `redesign-tracker.tmp.md` 为准。

## 仍然有效的基础约束

- 先做 Phase 1：文章拉取 Pipeline + 专用 Workflow + 数据入库
- 再做 Phase 2：后端 Daily Reader API
- 再做 Phase 3：前端每日精读页面
- 最后做 Phase 4：验证与收尾
- 每日精读页面不复用主线结果页布局，不复用 `/analyze` 主流程
- 正文标注必须比主线克制，重解析收口到文末
- 内容采用预生成模式，不在用户打开页面时实时运行全流程分析
- 词典查询能力复用现有 `/dict` API，但交互边界与阅读目标一致

- 每日精读是独立产品线，与主线用户输入解析完全隔离
- Daily Reader payload 独立于 `render_scene`，不混用
- 文章来源通过 RSS/API 自动拉取 + AI 筛选，不走人工编辑
- Guardian API 非商用免费（5000次/天），BBC/NPR RSS 免费
- 正文提取使用 trafilatura（纯 Python，无浏览器依赖）
- 封面图优先使用文章自带图，无图时用氛围渐变色
- 版权合规：标注原文来源和链接，不直接展示原文全文
