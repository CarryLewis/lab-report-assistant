# Labwise 1.4.1 Beta 测试版

日期：2026-11-05（Asia/Shanghai）。**主流稳定版仍为 1.3.7；1.4.1 为测试版。** 该版本以 GitHub Pre-release 交付，不设置为 Latest，也不替换已安装的稳定应用。分线规则见 [1.3 稳定线与 1.4 测试线](RELEASE_CHANNELS.md)。

## 本版内容

- 修复“各维度按百分制评价，再按权重计入总分”的量表误拦截；区分原始评价量表和报告总分贡献。100 分制、20 分制、原始候选分换算与教师评分保留详见 [量表修复记录](30_WEIGHTED_EVALUATION_SCALE_FIX.md)。
- 收入 iCloud Drive 文件夹、OneDrive 客户端文件夹的网盘快照备份、历史查看、定时备份和独立副本恢复。工作数据库仍在本机，不通过网盘共享实时 SQLite 文件。
- 应用运行期间可选择每 15／60 分钟备份；默认关闭定时任务。写入文件夹不代表实际云端上传完成，需在系统网盘客户端确认。
- 包含 OneDrive 账号直连的试验实现，但仍需正式公共客户端 ID 配置与真实账号/学校租户验收。本次构建不内置账号密钥，不承诺账号直连已经可用；文件夹方式不依赖该设置。
- 保留完整包内 LibreOffice，提供 Word 分页和评阅 PDF 导出。

这些网盘能力是快照传输与恢复，**不是实时双向合并、多人协作或跨设备自动合并编辑**。恢复建立独立副本，不覆盖正在使用的资料目录。原生 iCloud 容器、云端状态探测及真实异机往返不在本轮已验收范围内。[网盘实现与边界](29_CLOUD_BACKUP_IMPLEMENTATION.md)

## 与 1.3.7 并存

- 测试应用名：`Labwise Beta.app`，Bundle ID：`com.carrylewis.labwise.beta`。
- 测试版默认资料：`~/Library/Application Support/Labwise Beta/data`。
- 稳定版仍使用 `Labwise.app` 与 `~/Library/Application Support/Labwise/data`。
- 测试版不会自动复制、迁移或直接打开稳定版资料。需要测试已有课程时，先在稳定版生成备份，再在测试版恢复为独立副本核对；不要让两个版本同时使用同一资料目录。
- 重新运行源码仍保留原源码工作区路径。明确提供 `LABWISE_DATA_DIR` 或 `--data-dir` 时会使用指定路径，维护者应避免把它指向正在使用的稳定工作区。
- 现有 1.3.7 安装文件及其发布状态保留。

## 安装文件

本地交付目录：`output/beta-1.4.1/`。

- `Labwise-1.4.1-beta-macOS-arm64-trial.dmg`
- `Labwise-1.4.1-beta-macOS-arm64-trial.zip`
- 同目录保存构建清单、校验值、安装说明和验收记录。

打开 DMG，将 `Labwise Beta.app` 拖入应用程序目录；或解压 ZIP 后移动测试应用。当前仅针对 macOS Apple Silicon，使用本机临时签名，尚未完成 Developer ID 签名及 Apple 公证。

## 验证方式

构建前运行完整 Python 回归和全部前端检查。构建后检查包内版本、Beta 渠道、稳定版基线与独立默认资料目录；实际调用包内 LibreOffice 转换虚构 DOCX 并检查移动应用路径后的签名。

安装验收使用临时资料及虚构报告，覆盖包内加权量表保存、iCloud/OneDrive 文件夹快照与独立恢复、重启资料保留、重复启动与导出。不会向真实网盘传输教师资料或调用真实模型；真实模型的小样本核验见量表修复记录。

最终执行结果与安装包 SHA-256 以同目录验收 JSON 和 `SHA256SUMS.txt` 为准。真实 iCloud 异机下载、OneDrive 账号/租户权限及真实长报告效果仍需单独验收。

## 本次实际验收结果

- 完整 Python 回归 127 项通过，前端检查 10 个脚本通过。
- 构建后的测试应用通过 16 类安装验收，ZIP 解压后的应用再次通过相同 16 类验收。
- 包内 LibreOffice 实际 DOCX 到 PDF 转换、中文路径移动后的转换及签名完整性检查通过。
- DMG 只读挂载与 ZIP 解压后自检通过；版本、Beta 渠道、独立默认资料目录及主要程序资源哈希一致。
- 原 1.3.7 DMG、ZIP 和清单的 SHA-256 与构建前一致。打包验收阶段没有替换已安装的稳定应用；GitHub 交付按预发布处理。
- 记录：`installation-smoke-test.json`、`zip-installation-smoke-test.json`、`distribution-verification.json` 和构建 manifest。
