# Reading Tools & User Annotations

建议 agent 按以下顺序阅读并执行：

1. [requirements.md](requirements.md)
2. [design.md](design.md)
3. [data-api.md](data-api.md)
4. [tasks.md](tasks.md)

本规格覆盖三组能力：

- 阅读设置：字号、行距、段距、译文显示、背景、标注强度，保存到用户 profile 的 metadata/settings 扩展中。
- 阅读工具栏：长按句子、译文或段落后的复制、收藏、写笔记、反馈入口。
- 用户自行批注：用户选择句子/段落后创建高亮、收藏和笔记；后端需要新增用户批注表。

执行原则：

- 阅读面优先，工具只在用户主动选择文本后出现。
- AI 标注和用户批注必须视觉分层，避免两套标注互相污染。
- 小程序首版仅做句子/段落级操作，不做原生文本拖选、拖拽手柄、任意范围选区。
- 收藏复用现有 `favorite_records` 表；用户笔记/高亮新建表。
- 阅读设置不进入 workflow schema，不影响后端解析结果，只影响前端渲染偏好。
