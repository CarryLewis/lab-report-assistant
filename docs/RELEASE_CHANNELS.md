# 1.3 稳定线与 1.4 测试线

生效日期：2026-11-05。**当前推荐使用 1.3.7；1.4.1 为主动选择的 Beta 测试版。**

## 两个版本分别包含什么

### 1.3.7：当前主流稳定版

- 适合继续日常教师评阅，当前稳定安装入口为 [v1.3.7](https://github.com/CarryLewis/lab-report-assistant/releases/tag/v1.3.7)。
- 已有 DOCX 导入、作业与 Rubric、AI 候选分析、教师核对确认、草稿与版本、批改包和 PDF 导出。
- 内置完整 LibreOffice，无需另装转换器即可进行 Word 分页与 PDF 导出。
- 应用名为 `Labwise.app`，默认资料位于 `~/Library/Application Support/Labwise/data`。
- 不包含 1.4.1 新增的网盘快照备份，也不包含本次独立评价量表与加权贡献分的修复。
- 原 1.3.7 安装文件和标签保留；“稳定”表示本项目当前推荐的产品线，不代表自动评分正确性认证或 Apple 公证。

### 1.4.1：Beta 测试版

- 适合主动验证新功能的使用者，下载入口为 [v1.4.1 预发布](https://github.com/CarryLewis/lab-report-assistant/releases/tag/v1.4.1)。
- 包含 1.3.7 的主要评阅与包内 LibreOffice 能力，并修复“每项按百分制评价，再按权重合计”的量表误拦截。
- 区分原始评价满分与总分贡献，核对候选分换算，并显示原始分与折算分；不覆盖教师已填写的分数。
- 新增 iCloud Drive 文件夹和 OneDrive 客户端文件夹的快照备份、备份历史、应用运行期间的定时备份，以及独立副本恢复。
- 这不是实时双向同步或多人合并。文件夹写入成功也不等于云端上传成功。
- OneDrive 账号直连实现仍待正式公共客户端 ID 配置、真实账号及学校租户验收；本测试包不承诺账号直连可用。
- 应用名为 `Labwise Beta.app`，默认资料位于 `~/Library/Application Support/Labwise Beta/data`，Bundle ID 与稳定版不同，可并存。
- 127 项 Python 回归、10 个前端检查脚本、应用及 ZIP 各 16 类安装检查通过；这些不等于真实长报告评分质量或真实网盘异机同步已验证。

两个安装包目前均仅提供 macOS Apple Silicon 构建，采用本机临时签名，尚未完成 Developer ID 签名和 Apple 公证。

## 后续更新怎样分线

- `main`：保持面向稳定用户的入口与说明，当前代码基线为 1.3.7。
- [`release/1.3`](https://github.com/CarryLewis/lab-report-assistant/tree/release/1.3)：1.3.x 稳定维护。后续修复依次使用 1.3.8、1.3.9 等版本号，优先处理稳定性、兼容与明确缺陷。
- [`release/1.4`](https://github.com/CarryLewis/lab-report-assistant/tree/release/1.4)：1.4.x 测试维护。当前为 1.4.1 Beta，后续测试更新使用独立的 1.4.x 补丁号。
- 1.4 测试发布必须勾选 GitHub **Pre-release**，不得设置为 Latest；当前 Latest 保留 1.3.7。
- 功能按所属分支开发，公共缺陷修复可以选择性回移，但每条线分别测试、打包和更新说明。不得将整条 1.4 功能线自动合入 1.3。
- 每次发布都创建与源码对应的独立标签，附安装包、校验值、构建清单和验收范围；已发布标签及安装文件不复用、不覆盖。
- 只有在明确决定推广为正式版，并完成约定验收后，才调整 1.4 的测试状态和主流版本；版本号更大不自动代表应升级。

## 资料与升级

稳定版和测试版默认互不打开对方资料。要用既有课程试用，请先在稳定版生成备份，再在测试版恢复为独立副本核对。不要让两个版本同时使用同一资料目录。

保留稳定版应用和原始备份。测试版产生的新增字段与资料，不承诺可以直接回写旧版或双向合并；恢复操作应先在副本验证。

源码、安装包和数据分开管理：安装包只进入 Releases，真实报告、数据库、服务密钥、网盘令牌及本机工作目录不提交仓库。

详细范围见 [1.4.1 Beta 说明](31_RELEASE_1_4_1_BETA.md)、[量表修复记录](30_WEIGHTED_EVALUATION_SCALE_FIX.md) 和 [网盘实现边界](29_CLOUD_BACKUP_IMPLEMENTATION.md)。
