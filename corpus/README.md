# Lab report 评分与反馈语料库

这是项目的首版可扩充语料库。当前内容均为原创种子材料，不是 Turnitin 官方文本，也未使用真实学生报告。以英文学生反馈为主，配中文评分维度说明。

## 文件

- `rubric.seed.json`：9 个维度、四档表现描述及示例权重，总计 100 分。仅供建立课程 rubric 时参考，未经教师批准不得直接用于正式评分。
- `feedback.seed.jsonl`：36 条结构化反馈，包括优点、改进建议、证据定位模板与教师核查提示。
- `STYLE_GUIDE.md`：反馈语言、检索和教师审核规范。
- `historical/`：由用户提供的历史 academic writing、教师批注、明确可见的 rubric 与评分方式整理出的去标识化基础分析语料。该目录把正式评分信息与从批注归纳的评价关注点分开保存，并提供可复用的分析 JSON 模板。

## 添加材料

每条评语保留唯一 id、维度、用途、语言、文本、来源、适用范围、审核状态与审核人。当前 `original_seed` 表示原创示例；历史教师评语必须另记原始来源、使用授权、去标识化情况及 rubric 版本。未经授权的材料不导入。

建议用途标签：strength、improvement、evidence_linked、verification。新增课程材料时补充 course_id、assignment_id、rubric_version、source_reference、authorization、reviewed_at；不得把课程专属结论混入通用种子材料。

检索顺序：先限制当前课程与作业授权范围，再匹配当前 rubric 维度、问题类型、反馈用途与语言。通用材料只能作语言参考。不得借用历史报告中的事实、分数或结论。

所有占位符必须替换并经教师核查。无当前报告证据时只能提出待核查提示。生成反馈应保存所用语料 id、当前 rubric 版本及当前报告段落 id；教师确认后才可导出为学生评语。

## 使用示例

选用 `discussion.improvement.001`，根据当前报告证据改写：

> In paragraph P18, the increase in temperature is described, but the explanation is not connected to the recorded measurements. Explain the pattern using specific results and the relevant scientific principles.

上述 P18 与内容为虚构演示，不能当作真实报告证据。

## 后续校准

由授课教师按具体实验修订评分描述与分档边界，再补充经授权的典型评语。记录教师接受、修改和拒绝的原因；用这些记录改进语料适用性。当前版本未接入应用检索、数据库或自动评分流程。

## 历史样本与通用种子的关系

`historical/` 中的材料优先用于作者写作模式分析、回归测试和教师审核流程验证。它们不替换 `rubric.seed.json`，也不应合并成一个跨课程的自动评分表。使用历史样本分析新报告时，应先匹配当前课程、作业和 rubric 版本；无法确认匹配关系时，只能把历史反馈作为语言或检查项参考。
