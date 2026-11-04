# 安装包内置 LibreOffice

2026-11-04，Labwise 1.3.7，macOS Apple Silicon 本机试用构建。

安装包包含完整独立的 LibreOffice.app，位于 `Labwise.app/Contents/Helpers/LibreOffice.app`。安装 Labwise 后即可离线执行 DOCX 分页转换和评阅 PDF 导出。转换仍使用临时隔离配置与经清理的文档副本；复杂对象和缺失字体的显示需要在导出预览中核对。

运行时依次使用：显式的 `LABWISE_SOFFICE`、包内组件、系统命令路径、系统与用户 Applications 目录。显式配置无效时仍报错，不默默忽略配置。源码运行继续依赖外部 LibreOffice。

构建时 `LABWISE_LIBREOFFICE_APP` 指定完整原版 LibreOffice.app（默认 `/Applications/LibreOffice.app`）。构建检查架构，完整复制组件、字体、插件与原许可文件，针对本机试用副本重新签名，再封装外层应用。不会修改系统 LibreOffice。无需将第三方二进制提交到代码仓库。如果项目位于会改写应用图标元数据的系统同步目录，可设置 `LABWISE_BUILD_DIR` 为独立临时构建目录；安装包仍输出至项目的 `output/installers`，验证记录保留在 `output/build`。

许可证、第三方声明、对应源码版本与获取地址保存在 `Contents/Resources/third-party-licenses/LibreOffice`，原组件中的许可文件也完整保留。LibreOffice 源码未修改；签名属于本机试用包的封装步骤。此版本沿用现有本机临时签名，不代表已完成 Developer ID 签名或 Apple 公证。

构建交付前自动执行 `packaging/smoke_bundled_converter.py`：将应用移到包含中文和空格的临时路径，清除外部转换器配置及命令路径，确认选用包内组件，使用虚构 DOCX 完成导入、评分确认和 PDF 导出，检查原文存在、私人笔记过滤、保存状态不变及转换后签名完整性。该验证不会读取教师资料或调用真实 AI。
