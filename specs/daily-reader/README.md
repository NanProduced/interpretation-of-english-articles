# Daily Reader (每日精读)

建议 agent 按以下顺序阅读并执行：

1. [requirements.md](requirements.md)
2. [review.md](review.md)
3. [design.md](design.md)
4. [tasks.md](tasks.md)

执行原则：

- 先做 Phase 1：文章拉取 Pipeline + 专用 Workflow + 数据入库
- 再做 Phase 2：后端 Daily Reader API
- 再做 Phase 3：前端每日精读页面
- 最后做 Phase 4：验证与收尾
- 每日精读页面不复用主线结果页布局，不复用 `/analyze` 主流程
- 正文标注必须比主线克制（每段不超过 3-5 个高亮），重解析收口到文末
- 内容采用预生成模式，不在用户打开页面时实时运行全流程分析
- 词典查询能力复用现有 `/dict` API，但交互边界与阅读目标一致

约束条件：

- 每日精读是独立产品线，与主线用户输入解析完全隔离
- Daily Reader payload 独立于 `render_scene`，不混用
- 文章来源通过 RSS/API 自动拉取 + AI 筛选，不走人工编辑
- Guardian API 非商用免费（5000次/天），BBC/NPR RSS 免费
- 正文提取使用 trafilatura（纯 Python，无浏览器依赖）
- 封面图优先使用文章自带图，无图时用氛围渐变色
- 版权合规：标注原文来源和链接，不直接展示原文全文
