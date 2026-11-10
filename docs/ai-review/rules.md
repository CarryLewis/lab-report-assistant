# 后端 AI 评阅规则

作业保存教师确认的评分细则。报告导入时保存对应版本的快照，模型按当前报告的快照生成候选反馈。文字建议需要能回到原文，图表建议需要引用已知的 Word 对象。教师审核候选建议并确认最终反馈与分数。

- [评阅入口](../../pilot_backend.py)组装评分上下文、提交模型请求、校验证据及记录提示词版本。
- [评分表解析](../../rubric_ai.py)保留量表、分档、权重与例外。已通过校验的解析结果按工作区、API 凭据、模型和评分上下文隔离，并短时复用。
- [评分表适配](../../review_guidance.py)按已保存的作业标识和评分项组合选择课程专属指导。修改指导时同步更新规则版本。已有评分表仍决定权重和分档。
- [Word 证据](../../word_source.py)提取正文、结构化表格和图表缓存。[图表审核](../../word_review.py)核对可明确匹配的均值及观测数，并为漏检对象准备定向复查。
- [候选分数校验](../../rubric_scoring.py)区分原量表和加权分数，校验扣分、上限和原文证据。图表证据未完成时暂缓建议总分。

在仓库根目录运行以下测试。测试替换外部模型请求，可以离线运行。

```sh
python3 -m unittest discover -s tests -p 'test_review_guidance.py'
python3 -m unittest discover -s tests -p 'test_rubric_understanding.py'
python3 -m unittest discover -s tests -p 'test_word_review.py'
```
