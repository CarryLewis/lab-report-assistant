# Turnitin 与教学平台接入路径

## 目标

本产品应尊重教师现有的 Turnitin 与学校教学平台工作流。短期重点是帮助教师完成分析和反馈草稿；查重、正式批注与正式成绩仍在学校既有系统中完成。

## 第一阶段：独立工作台

教师从 Turnitin 或学校教学平台下载报告，再上传至本产品。教师在本产品中查看结构、证据与反馈草稿，随后回到 Turnitin 完成正式批注和提交。

这个阶段最适合 Demo，因为它无需改变学校现有系统，也能验证辅助批改是否真正有用。

## 第二阶段：从 LMS 进入工具

当试点被认可后，优先研究从学校 LMS 课程页面一键进入本产品的方式。理想的体验是：

```text
学校 LMS 课程页
├─ Turnitin：原始提交、查重与正式批注
└─ AI 辅助批改：结构理解、rubric 对照、证据与反馈草稿
```

这一步的目标是减少重复登录和手动选择课程，而不是绕过 Turnitin。

## 第三阶段：学校级评估

在学校 LMS 管理员、Turnitin 管理员和数据负责人确认后，评估是否可以安全地：

- 带入教师身份、课程与作业信息；
- 取得明确授权的报告文件；
- 将教师确认后的成绩或反馈摘要回传教学平台；
- 与学校已有 Turnitin 配置形成可维护的工作流。

具体能力取决于学校购买的服务、管理员配置和正式技术审批，不能在产品设计阶段预设一定可用。

## 明确禁止的方式

- 不要求教师在本产品中输入 Turnitin 用户名或密码。
- 不通过网页抓取、模拟登录或浏览器自动化读取 Turnitin 的学生报告和反馈。
- 不假定可以直接向 Turnitin 写入批注、分数或学生数据。

## 接入决策原则

先验证产品价值，再申请学校级接入。任何平台接入都必须改善教师真实工作流、经过学校授权，并保留对学生数据流向的清晰控制。

---

## 2026 接入能力判断

### 可以通过公开能力完成

- 通过 Turnitin Core API 创建提交、上传文件、请求相似度报告、接收 webhook，并生成临时 Viewer Launch URL。
- 在本产品中为教师提供“查看 Turnitin 相似度报告”的受控入口。
- 通过 LMS LTI 1.3 将本产品作为独立教学工具启动。
- 通过 LTI Assignment and Grade Services 将最终成绩回传 LMS 成绩册。
- 在本产品中保存逐段证据、rubric 决策、教师反馈和学生查看记录。

### 不能依据公开文档假定可用

- 将第三方 UI 嵌套进 Turnitin Feedback Studio 的原生评分侧栏。
- 通过 Turnitin Core API 创建或修改 Feedback Studio 的逐段 comment、QuickMark、rubric decision 或 summary feedback。
- 从 Turnitin Viewer 页面抓取段落、相似来源或教师批注，再映射到本产品。
- 保证本产品中的批注在 Turnitin 学生视图中以完全相同的原生样式出现。

Turnitin 官方明确禁止通过程序化操作 Viewer 来提取报告数据；这种实现可能导致集成被阻止。任何 Feedback Studio 写入能力必须由 Turnitin 针对学校许可证或正式合作伙伴计划书面确认。

## 推荐架构：LMS 作为共同入口

```text
学生提交
   │
   ▼
学校 LMS ────────────────┐
   │                     │
   ├─ Turnitin           ├─ 原文件、相似度报告、Turnitin 原生反馈
   │                     │
   └─ Labwise            ├─ 内容理解、证据锚点、rubric 评分、详细反馈
                         │
                         └─ LTI AGS → LMS 最终成绩
```

教师从同一门 LMS 课程进入两个工具，不需要重复选择学生或作业。学生在 LMS 中看到：

- Turnitin 相似度报告入口；
- Labwise 详细反馈入口；
- LMS 中的最终成绩。

这能保证学生看到与教师确认内容完全一致的反馈，但详细反馈的呈现位置在 Labwise，而不是强行写入 Turnitin 原生批注层。

## Turnitin Viewer 嵌入 Labwise

如果学校获得 Turnitin Core API 许可，可采用：

1. Labwise 保存 `turnitin_submission_id` 和处理状态。
2. 后端通过 webhook 获取提交与相似度报告完成事件。
3. 教师点击“查看 Turnitin 相似度”时，后端即时申请 Viewer Launch URL。
4. 在新标签页或符合 Turnitin 要求的受控容器中打开 Viewer。
5. Labwise 不读取 Viewer DOM，不覆盖 Turnitin 页面，也不把自己的批注绘制到 Turnitin 文档层上。

Viewer URL 是临时会话入口，不应长期保存或作为学生永久链接。

## Rubric 与反馈模板的对应

Turnitin Feedback Studio 原生支持将 QuickMark 或 comment 关联到 rubric criterion。Labwise 应在自己的数据层保留同样的关系：

```text
Labwise Criterion
  ├─ Teacher Decision
  ├─ Evidence Anchor
  ├─ Feedback Item
  └─ Optional External Mapping
       ├─ Turnitin rubric criterion ID
       ├─ QuickMark set/name
       └─ provider feedback ID（仅在正式 API 支持时）
```

对于“参考资料库中的模板”，建议：

- 在 Labwise 中维护版本化的 `Feedback Template Library`；
- 每个模板绑定一个或多个 rubric criterion；
- 保存适用条件、英文反馈、中文解释、需要的证据类型；
- 可按学校允许的方式导出为 QuickMark/rubric Excel，用于人工导入 Turnitin；
- 不把 QuickMark 文本本身视为评分证据，教师仍需关联学生原文。

Turnitin 新版 Feedback Studio 支持 rubric 和 QuickMark 集合的 Excel 下载/更新，这可用于“模板库对齐”，但不等于逐份作业批注的自动双向同步。

## 稳定的原文锚点

不能只用“第 3 段”作为跨系统定位，因为 DOCX、PDF 和 Turnitin 渲染后的分页可能不同。每条反馈应同时保存：

- 原始文件 SHA-256；
- 文档版本；
- 页码与 bounding box；
- 精确引用文本；
- 前后文各一段短文本；
- 规范化文本哈希；
- rubric criterion ID；
- 可选的 Turnitin submission/assignment ID。

同步或重新渲染时按“文件版本 → 精确文本 → 前后文 → 页面坐标”逐级匹配。匹配不唯一时必须进入人工确认，不能把反馈自动贴到错误段落。

## 同步数据模型

- `external_integrations(id, organization_id, provider, tenant_url, status)`
- `external_assignments(id, assignment_id, provider, external_id)`
- `external_submissions(id, submission_id, provider, external_id, content_hash, status)`
- `external_rubric_mappings(id, criterion_id, provider, external_criterion_id)`
- `feedback_sync_records(id, feedback_item_id, provider, external_feedback_id, status, last_error)`
- `integration_outbox(id, event_type, payload, idempotency_key, status, attempts)`

不要把 API key 保存在浏览器；由学校管理员在后端配置，并使用密钥管理服务加密。

## 三种交付级别

### Level 1：现在即可实现

- 教师从 Turnitin/LMS 下载报告后上传 Labwise。
- Labwise 完成证据型评分。
- 导出反馈 PDF、DOCX 或结构化报告。
- 教师将最终分数或摘要录入既有系统。

### Level 2：推荐的学校试点

- Labwise 作为 LMS LTI 1.3 工具。
- 自动带入教师、课程、作业和学生上下文。
- Turnitin 与 Labwise 并列显示。
- Labwise 将最终成绩回传 LMS；学生从 LMS 查看详细反馈。

### Level 3：需 Turnitin 合作确认

- Turnitin submission、rubric 和 Labwise assessment 建立正式映射。
- 教师确认的 comments/QuickMarks/rubric decisions 写入 Feedback Studio。
- 学生在 Turnitin 原生页面看到相同反馈。
- 所有写入使用正式、受支持的 API，并通过 Turnitin 验证/认证流程。

在获得正式接口文件和 sandbox 前，不应承诺 Level 3。

## 采购与技术确认清单

向学校 Turnitin 管理员和 Turnitin 技术代表确认：

1. 学校购买的是哪一种 Turnitin 产品和许可证？
2. 是否已启用 LTI 1.3，当前 LMS 是 Canvas、Moodle、Blackboard 还是 D2L？
3. 是否可以申请 Turnitin Core API tenant、API key 和 sandbox？
4. 许可证是否允许提交索引、学生查看报告和 Viewer Launch？
5. 是否存在受支持的 Feedback Studio 写入接口，可创建 comments、QuickMarks 和 rubric decisions？
6. 是否允许导入/更新 rubric 与 QuickMark Excel？
7. 成绩的最终真源是 LMS、Turnitin 还是学校 SIS？
8. 学生数据处理区域、保留期限和 EULA 流程是什么？
9. 匿名评分时哪些身份字段必须隐藏？
10. 集成是否需要 1EdTech 认证、Turnitin 合作伙伴验证或学校安全评审？
