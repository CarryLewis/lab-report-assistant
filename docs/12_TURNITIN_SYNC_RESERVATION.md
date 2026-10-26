# Turnitin 同步与批改接续预留

当前交付是主评阅页的本机交互原型：原文工具栏的「Turnitin 同步与接续」入口支持阶段、总评、总分和阅读位置的接续保存，两种工作视角切换，以及版本冲突演示。数据仅存于浏览器 localStorage，不代表 Turnitin 的真实状态。原型按文档名隔离；正式实现必须使用内部报告 ID 和外部 submission ID，禁止沿用文件名作为身份键。

## 正式适配器边界

正式接入前需确认机构授权及平台提供的集成能力。不得假设 iframe 嵌入、QuickMark、Rubric、相似度或成绩回传可用；按平台实际授权返回能力清单，不可用项隐藏或禁用。

建议服务层契约：

- Connection：provider、institution_id、connection_status、capabilities；凭据只在服务端保存。
- SubmissionMapping：report_id、assignment_id、external_submission_id、external_assignment_id、rubric_mapping_version。
- ReviewCheckpoint：report_revision、remote_revision、stage、criterion_scores、overall_score、feedback、annotations、document_anchor、updated_at、updated_by。
- Annotation：内部 paragraph_id、引用原文、页码与位置（如提供）、comment、QuickMark 映射 ID。锚点失效需人工复核。
- SyncJob：job_id、idempotency_key、direction、base_local_revision、base_remote_revision、status、last_success_at、retry_at、error、audit_id。

同步状态预留：未连接 → 待同步 → 同步中 → 已同步；失败进入可重试状态，任一端基线版本变化进入冲突状态。只有平台确认成功并记录双方版本后，才能显示「已同步」。重试复用幂等键，不能重复发布。

## 批改与切换规则

批改阶段独立于同步状态：未开始、批改中、待教师确认、已确认待回传。未保存或保存失败时阻止跨端接续；切换时先保存草稿、批注锚点、当前 Rubric 项、阅读位置，再加载目标端能力。断网保留本机草稿并显示未同步。正式版按用户、机构和提交隔离数据，并提供清除缓存能力。

同一提交两端都有变更时，暂停写入，提供逐字段对比与教师选择；不以时间戳覆盖远端。恢复或修改已确认内容须撤销确认。教师确认、平台回传与学生发布是三个独立动作，确认前禁止回传，禁止自动发布。审计记录包含操作者、双方版本、变更字段与回传结果，不记录访问令牌。

当前面板的核心功能清单仅预留入口说明；分项评分、批注及 QuickMark 尚未接入。总分使用独立的 0–100 演示字段，不自动写入主评阅区，也不构成真实 Rubric 换算。
