# 项目支持文档

- [AI 评阅开发档案](ai-review/README.md)记录后端规则、评分细则校准和图表评阅迭代。

- [1.3 稳定线与 1.4 测试线](RELEASE_CHANNELS.md)：1.3.7 与 1.4.1 的功能差异、分支、版本号与预发布规则。

- [加权评价量表核查与修复（2026-11-05）](30_WEIGHTED_EVALUATION_SCALE_FIX.md)：原始百分制与贡献分分离、候选分换算、界面显示，以及离线与真实模型核验范围。

当前开发版本：**1.4.1 Beta（测试版）**；主流稳定版仍为 **1.3.7**。

- [1.4.1 测试版说明](31_RELEASE_1_4_1_BETA.md)：量表修复、网盘备份、独立测试目录与安装验收。

查看[本次开发进度与验证记录](26_RELEASE_1_3_6.md)及[AI 评价语言规则](25_EVALUATION_LANGUAGE.md)。

- [macOS 安装交付与验证](23_MACOS_INSTALLATION_AND_RELEASE.md)：本机试用 DMG／ZIP、启动与资料位置、保留数据的程序替换、验收结果及签名公证边界。

- [iCloud 与 OneDrive 接入设计规划](28_CLOUD_BACKUP_DESIGN_1_4_1.md)：个人网盘备份、异机恢复、接入方式、接口契约、分期开发与验收清单。当前为设计稿，文件名中的版本号不代表已发布；双向增量同步另行规划。

- [网盘备份首轮实现与构建记录](29_CLOUD_BACKUP_IMPLEMENTATION.md)：已实现能力、试用步骤、隔离测试和 macOS 安装包验收，以及真实账号、原生 iCloud 与持续连接的待验收范围。

**当前交付决策（2026-10-27）：** 教师下载应用并在自己电脑上独立使用，资料与批改进度本机保存。请优先阅读[本机应用交付纲领](21_LOCAL_APP_DELIVERY.md)。Turnitin 同步、平台登录、LMS 和中央多人部署暂缓；旧接入文档仅作历史参考。

- [APP 用户流程、使用指引与开发者反馈方案](22_APP_USER_WORKFLOW_GUIDANCE_AND_FEEDBACK_PLAN.md)：第 11、12 节记录两轮实施及最新验证结果。

- [图表自动发现：第一期实现与验证](16_VISUAL_DISCOVERY_IMPLEMENTATION.md)：本地扫描、原页目录、人工修订、暂停续扫、已实现接口与后续边界。

- [图表自动发现与科学审核模块开发纲领](VISUAL_RECOGNITION_CHARTER.md)：后续图表识别开发须遵循的流程、原页坐标、图注关联、人工纠错、分期与验收约定。

- [Complex Word preview](15_COMPLEX_WORD_PREVIEW.md): offline conversion of linked charts/images, readable fallback and current rendering limits.

- [1.2.1 Editable demo and API integration](14_VERSION_1_2_1_EDITABLE_DEMO.md): current real-data workflow, configuration, verified paths and remaining provider-key requirement.

- **历史界面基线：[Labwise 1.2.1 UI 大纲](UI_VERSION_1_2.md)**：取消团队与校准；保留该模块的 1.2.2 已独立记录。

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

- [多文体写作批改（1.3.0）](24_MULTI_GENRE_WRITING.md)：文体模板、原创语料、版本快照及试用范围。

- [Dual rubric processing: code and AI versions](25_DUAL_RUBRIC_PROCESSING.md)
