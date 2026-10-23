# 引用核验与外部文献检索

本文件为详细实施参考，须遵循[引用验证模块开发纲领](CITATION_VERIFICATION_CHARTER.md)。阶段与架构约定冲突时以纲领为准。

## 第一版实施进度（2026-10-23）

真实试点入口 `/pilot.html` 已接入 `citation_core.py`：对已解析 DOCX 段落执行基础作者—年份提取，保留位置、上下文和输入哈希；支持完整/片段输入、孤立及歧义关联、未使用条目和重复 DOI。可选择未指定样式或 APA 7 基础字段规则（年份括号与 DOI URL）。结果随报告写入本地数据库，教师逐条修正说明进入版本历史。每条参考文献可触发三库检索并显示摘要。

新增接口：`POST /api/pilot/reports/{id}/citations`（revision/style/completeness）；`POST /api/pilot/reports/{id}/citation-review`（revision/reference_id/note）。两者均校验报告修订号，保存前创建快照，并取消原反馈确认状态。

第一版仍在建设，尚不满足完整验收：CSL 完整排版规则、跨段条目、ibid、编号制、手工重关联与来源候选确认持久化尚待实现。当前来源检索结果不等于身份已确认；教师复核说明也不自动产生内容支持结论。新增测试覆盖歧义、重复、片段输入、格式字段与原文偏移；连同既有回归共 13 项通过。浏览器交互尚待验收。

当前实现更新：检索入口已并发接入 Crossref、PubMed E-utilities 与 Europe PMC，按 DOI/PMID/PMCID 合并记录并保留来源；单库失败返回其余结果。PubMed 使用进程内共享限流，支持服务端 `NCBI_API_KEY` 和 `LABWISE_CONTACT_EMAIL`。当前取得元数据及可用摘要，尚未自动下载全文或生成内容支持结论。生产多进程部署需使用共享限流器。

## 目标与边界

引用核验帮助教师回答三个彼此独立的问题：

1. **引用是否完整对应**：正文引文能否找到唯一的参考文献条目，参考文献是否在正文出现。
2. **书目信息与格式是否正确**：作者、年份、题名、来源、卷期页、DOI 等字段是否可信，并符合本次作业指定的 APA 7、Harvard、Vancouver 等格式。
3. **引用内容是否恰当**：学生紧邻引文提出的主张，是否被被引来源的摘要或全文实际支持，是否夸大了范围或把相关性写成因果性。

系统只能生成候选判断。检索到同名文献只能证明存在候选来源；元数据一致只能提高身份匹配置信度；只有取得合法可用的摘要或全文并定位到支持片段后，才能生成“可能支持/部分支持/可能不支持”的内容判断，最终仍由教师确认。

## 教师工作流

```text
DOCX 解析
  → 抽取正文引文与 References
  → 建立正文引文 ↔ 参考条目关系
  → 按作业指定样式做确定性格式检查
  → 用 DOI / 题名 / 作者年份检索外部元数据
  → 取得许可范围内的摘要或开放全文
  → 抽取“学生主张 ↔ 来源证据片段”
  → 教师查看原文、来源与解释，确认或驳回
```

界面按严重程度展示：缺少条目或无法唯一识别为红色；字段冲突、内容范围可疑或只有摘要为黄色；对应关系和关键字段已核对为绿色。绿色不等于内容已经被全文证实。

## 外部服务分工

- **Crossref（首个原型已接入）**：以完整书目信息查询作品，并返回 DOI、题名、作者、年份、期刊等元数据；部分记录含摘要。适合身份解析，不应单独用于内容判断。公开 REST API 无需注册，生产环境应配置联系邮箱并遵守调用礼仪。[Crossref REST API](https://www.crossref.org/documentation/retrieve-metadata/rest-api/)
- **OpenAlex（下一阶段）**：补充跨学科作品发现、开放获取位置和摘要倒排索引。其摘要覆盖并不完整，因此必须保留 `content_unavailable` 状态。[OpenAlex API](https://help.openalex.org/api/)
- **Europe PMC（生命科学优先）**：在当前试点学科中优先补充摘要、MeSH、全文链接；开放获取子集可取得结构化全文 XML。[Europe PMC REST API](https://europepmc.org/RestfulWebService)
- **Unpaywall（已知 DOI 后）**：寻找合法开放版本。API 按 DOI 查询且要求邮箱；搜索端点已经停用，因此不能承担通用检索。[Unpaywall API](https://data.unpaywall.org/products/api)
- **学校图书馆/订阅数据库（需校方授权）**：只通过正式 API、链接解析器或馆内代理接入。不抓取登录页面，不保存教师密码，不绕过付费或访问控制。

## 数据契约

每个核验对象至少保存：

```json
{
  "citation_id": "cit_p004_02",
  "report_paragraph_id": "p004",
  "citation_text": "(Monod, 1949)",
  "claim_text": "The slower increase ... may indicate nutrient limitation ...",
  "reference_entry_id": "ref_02",
  "requested_style": "apa-7",
  "link_check": {"status": "matched", "method": "author_year"},
  "format_check": {
    "status": "pass_with_warnings",
    "rule_results": [{"rule_id": "apa7.doi.url", "status": "pass"}]
  },
  "resolution": {
    "status": "matched",
    "provider": "crossref",
    "external_id": "10.1146/annurev.mi.03.100149.002103",
    "candidate_score": 0.98,
    "metadata_snapshot_id": "snapshot_..."
  },
  "content_check": {
    "status": "needs_review",
    "basis": "abstract",
    "verdict": "partial_support",
    "source_spans": [],
    "rationale": "摘要未覆盖学生列出的全部机制"
  },
  "review": {"status": "pending", "reviewer_id": null}
}
```

`candidate_score` 只用于候选排序，不能显示成“正确概率”。外部元数据、摘要和全文片段需记录来源、抓取时间、许可范围及哈希，以便复核和避免服务更新后结果不可解释。

## API 设计

当前原型提供：

```http
GET /api/scholarly/search?q=<bibliographic query>&limit=5
```

返回统一字段：`title`、`authors`、`year`、`doi`、`container_title`、`url`、`abstract`、`source`。服务端固定上游域名、限制查询长度和结果数，并设置超时；浏览器不直接携带第三方密钥。

生产版建议拆为异步任务：

- `POST /reports/{id}/citation-checks`：启动整份报告核验；
- `GET /citation-checks/{job_id}`：读取阶段、错误和进度；
- `GET /citations/{id}`：读取对应、格式、解析与内容证据；
- `POST /citations/{id}/reviews`：保存教师确认、驳回、修改理由；
- `POST /citations/{id}/search`：只发送最小化的书目信息或检索词。

## 判定规则

### 对应关系

- 作者—年份制同时比较规范化作者、年份和同年后缀；编号制校验编号范围、重复编号与条目顺序。
- 多个候选相同时要求教师选择，不能静默采用检索第一条。
- 正文孤立引文、未被正文引用的参考条目、重复条目分别报告。

### 格式

- 作业档案必须明确 `citation_style` 和版本；未知时只报告字段完整性，不宣称格式错误。
- 使用 CSL/样式规则生成期望形式，再以字段级差异解释问题；不要只做整行字符串比较。
- 标题大小写、作者截断、网页日期、数据集和软件等特殊类型要有单独规则与测试样本。

### 内容支持

- 先从引文所在句及必要的相邻句抽取最小主张，不把整段多个主张合并判断。
- 证据层级明确区分 `metadata`、`abstract`、`full_text`；没有摘要或全文时状态为 `content_unavailable`。
- 输出只允许 `supported`、`partial_support`、`contradicted`、`not_addressed`、`insufficient_source`、`needs_review`，并必须附来源片段位置。
- 二手引用、综述转述、引文放置歧义和跨句引文默认进入人工复核。

## 隐私、版权与安全

- 外部检索默认只发送题名、作者、年份、DOI 或最小关键词，不发送学生姓名、学号、报告全文或教师笔记。
- 只缓存核验所需的元数据与许可允许的短证据片段；受限全文不复制进长期语料库。
- 外部返回内容视为不可信数据：不执行其中的指令、不渲染不安全 HTML、不允许返回 URL 驱动服务端任意抓取。
- 报告中的 DOI 和 URL 不能直接成为服务端请求目标；先解析标识符，再通过白名单提供方请求。
- 引用问题不自动推断抄袭或学术不端，也不自动扣分。

## 分阶段建设

### P0：交互原型（当前完成）

- “引用核验”页签、摘要指标、问题卡片和正文/参考条目联动；
- Crossref 元数据检索代理及失败状态；
- 三类示例：格式完整但内容待查、身份匹配但支持范围待查、正文孤立引文。

### P1：确定性核验

- DOCX 引文/参考文献抽取；
- 作者—年份制与编号制对应；
- 可配置 APA 7 首批规则、CSL 渲染对比；
- DOI/ISBN/PMID 规范化和 Crossref/OpenAlex 候选消歧；
- 教师复核记录和导出。

### P2：内容证据

- Europe PMC 与开放全文接入；
- 主张拆分、摘要/全文证据检索和片段定位；
- “部分支持/未涉及/矛盾/证据不足”的可解释候选判断；
- 对受限全文提供学校链接，不复制内容。

### P3：校内试点

- 接入学校授权数据库或链接解析器；
- 用教师标注集校准候选排序和提示阈值；
- 审计、配额、缓存、服务降级、数据保留与删除策略。

## 验收指标

- 引文与条目抽取：按引用对象计算 precision、recall、F1；
- 对应关系：正确匹配率、歧义候选召回率、孤立引文漏报率；
- 格式检查：按规则统计准确率，并单列误报；
- 内容检查：由两名教师独立标注，统计各 verdict 的一致率、错误严重度和证据片段可定位率；
- 工作流：教师每份报告核验时间、打开来源比例、修改/驳回原因；
- 安全与可靠性：第三方超时率、缓存命中率、受限内容误存储事件（目标为 0）。

首轮上线门槛应优先控制误报：系统宁可显示“证据不足”，也不能把元数据命中包装成内容正确。
