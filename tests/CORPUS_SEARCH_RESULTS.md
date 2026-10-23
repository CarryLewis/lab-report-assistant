# 语料库引用检索实测（2026-10-23）

范围：本项目 samples 中四份去标识化写作（含疟疾报告原稿和修订稿）。只向外部发送参考文献 DOI。脚本：`python3 tests/corpus_search_probe.py`。

## 结果

抗生素敏感性报告含六条 DOI 文献；每条均在 Crossref、PubMed、Europe PMC 精确命中，共 18/18 次成功，按 DOI 合并为六条记录，六条均取得摘要。

- Otto 2009：10.1038/nrmicro2182；PMID 19609257；PMC2807625。
- Jorgensen & Ferraro 2009：10.1086/647952；PMID 19857164。
- Brand et al. 2025：10.1093/jac/dkaf068；PMID 40053699；PMC12046405。
- Alhumaid et al. 2021：10.1186/s12941-021-00450-x；PMID 34118930；PMC8196925。
- Salam et al. 2023：10.3390/healthcare11131946；PMID 37444780；PMC10340576。
- Breijyeh et al. 2020：10.3390/molecules25061340；PMID 32187986；PMC7144564。

Alhumaid 查询在 Europe PMC 返回两条候选，只有一条 DOI 相等；说明必须验证标识符，不能直接接受第一条或所有候选。

## 语料审阅发现（人工分析，非自动检测结果）

- 抗生素报告 References 有 Brand 2025、Tripathi 2023，但正文未见对应作者引文，应复核是否为未使用条目。
- 正文将 Breijyeh 2020 描述为“Gram staining test”，检索摘要及文章类型显示其为关于耐药性的综述。来源性质表述需要修改；摘要关于革兰阴性菌耐药性的论述不能直接证明本实验两种菌对 SXT 的特定差异。
- 报告对 Alhumaid 2021 使用“proves the correctness”等措辞；检索摘要涉及多医院感染监测，不能仅凭摘要将其推广为本实验结论已被证明。需要阅读全文并限定适用范围。
- 疟疾原稿引用 WHO 2024、Hayer 2025、Nkrumah 2011，但当前样本没有参考文献列表。缺少题名/DOI，无法唯一核定来源；样本为两页提交文本，不据此断言原始完整作业缺失。
- stress 样本以调查结果为主，当前样本文本未发现 DOI；本轮未执行外部查询。
- WHO、Drugs.com、NCBI Bookshelf 属非期刊来源，六条 DOI 成功不能代表这些网页和章节也已核验。

## 能力边界

本轮验证了真实文献检索、DOI 精确比对、摘要返回和跨库合并。尚未验证自动 DOCX 抽取、引用格式规则、全文内容支持判定。上述人工观察不能写成系统自动判定，也不能据此宣布报告整体“通过”。
