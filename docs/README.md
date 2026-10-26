# 项目支持文档

- [图表自动发现：第一期实现与验证](16_VISUAL_DISCOVERY_IMPLEMENTATION.md)：本地扫描、原页目录、人工修订、暂停续扫、已实现接口与后续边界。

- [图表自动发现与科学审核模块开发纲领](VISUAL_RECOGNITION_CHARTER.md)：后续图表识别开发须遵循的流程、原页坐标、图注关联、人工纠错、分期与验收约定。

- [Complex Word preview](15_COMPLEX_WORD_PREVIEW.md): offline conversion of linked charts/images, readable fallback and current rendering limits.

- [1.2.1 Editable demo and API integration](14_VERSION_1_2_1_EDITABLE_DEMO.md): current real-data workflow, configuration, verified paths and remaining provider-key requirement.

- **当前界面版本：[Labwise 1.2.1 UI 大纲](UI_VERSION_1_2.md)**：取消团队与校准；保留该模块的 1.2.2 已独立记录。

- [13 Editable teacher product](13_EDITABLE_TEACHER_PRODUCT.md): connected individual-use workflow, editable fields, persistence, outputs and verification limits.

- [引用验证模块开发纲领](CITATION_VERIFICATION_CHARTER.md)：后续引用验证相关开发必须遵循的总体架构、证据要求、分期和验收约定；详细方案以此为准。

- [文档结构识别模块开发纲领](DOCUMENT_STRUCTURE_RECOGNITION_CHARTER.md)：定义结构解析、规则优先级、AI 辅助边界、规范输出、样本标注和后续训练验证的上位约束。

本目录将 `PROJECT_BRIEF.md` 的项目方向拆成后续产品设计、开发和试点可直接查阅的工作文档。开始新任务前，先阅读项目概要，再查阅与任务相对应的文档。

- [01 产品与网站体验](01_PRODUCT_AND_EXPERIENCE.md)：定义教师使用的网站、页面职责和关键交互。
- [02 教师工作流与运营](02_WORKFLOW_AND_OPERATIONS.md)：定义从准备课程到完成批改和持续改进的实际工作流程。
- [03 数据与 AI 分析](03_DATA_AND_AI_ANALYSIS.md)：定义资料准备、AI 输出、证据要求和质量控制。
- [04 试点与验证](04_PILOT_AND_VALIDATION.md)：定义试点如何开展、怎样收集教师反馈和判断是否扩大。
- [05 Turnitin 与教学平台接入](05_PLATFORM_INTEGRATION.md)：定义独立使用、LMS 接入和未来 Turnitin 工作流衔接的路径。
- [06 引用核验与外部文献检索](06_CITATION_VERIFICATION.md)：定义引文—条目—外部来源—内容证据链、接口边界、建设阶段和验收指标。

- [09 Navigation and domain model](09_NAVIGATION_AND_DOMAIN_MODEL.md): six teacher modules, page actions, entity relationships, invariants and current implementation boundaries.
- [10 Identity and institutional access](10_IDENTITY_AND_INSTITUTIONAL_ACCESS.md): school sign-in, course permissions, LMS access, Turnitin authorization and rollout requirements.

## 使用原则

- 所有设计都应服务于教师辅助批改，而不是自动替代教师评分。
- AI 产生的建议必须能回到作业要求、rubric 和报告原文。
- 先完成一门课程的完整闭环，再扩大支持范围。
- 新功能若改变数据范围、教师责任或学校系统接入方式，先在相应文档中补充设计并确认。


- [Turnitin 同步与批改接续预留](12_TURNITIN_SYNC_RESERVATION.md)


## 2026-10-25 — Automatic report analysis (1.2.1)

Uploads and batch imports now queue DeepSeek text analysis automatically. File status and saved results are visible directly; the manual analysis selector/button is removed. Teacher review and confirmation remain required. See [automatic analysis workflow](17_AUTOMATIC_AI_ANALYSIS.md).


## 2026-10-25 — Continuous assignment review (1.2.1)

Added per-assignment start/resume actions, persistent unfinished-report checkpoints, grading status filters and automatic progression after successful teacher confirmation. Stable import order is independent of background AI updates. Save drafts before closing; confirmation still requires complete scores and reviewed feedback. See [continuous review workflow](18_CONTINUOUS_REVIEW.md).


## 2026-10-25 — Word-first automatic review (1.2.1)

Adopted DOCX-only submissions, automatic text/table/image inputs with source anchors, explicit immutable suggestion decisions, continuous grading and original/annotated Word plus score-package export. Manual crop-and-send image analysis is retired from the active UI. See [complete workflow and limits](19_WORD_FIRST_REVIEW_WORKFLOW.md).
