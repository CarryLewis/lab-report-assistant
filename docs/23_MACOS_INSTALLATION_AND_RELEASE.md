# macOS 本机试用安装交付

交付日期：2026-10-27。应用版本：1.2.1，本机试用构建。目标架构：Apple Silicon／arm64。

本轮在 macOS 26.3 上构建并验证，未验收 Intel Mac 和其他 macOS 版本。安装包自带 Python 3.12 及运行依赖，使用者不需要安装 Python。当前只完成本机试用交付，未进行 Developer ID 签名和 Apple 公证，不视为公开正式发布。

## 安装文件

构建产物位于项目的 `output/installers/`：

- `Labwise-1.2.1-macOS-arm64-trial.dmg`：约 46 MB，包含应用和 Applications 拖入入口。
- `Labwise-1.2.1-macOS-arm64-trial.zip`：约 39 MB，备用应用压缩包。
- `安装与使用说明.txt`：随包中文说明。
- `Labwise-1.2.1-macOS-arm64-trial-manifest.json`：文件摘要、构建环境、依赖检查及验收结果。
- `installation-smoke-test.json`：9 类包内实际验收记录。

这些文件为当前工作区生成的交付物，未上传公开下载站或 GitHub Release。构建目录和安装文件已排除出源码版本控制，避免将本机二进制与教师资料混入源码提交。

## 用户安装与首次使用

1. 打开 DMG，将 `Labwise.app` 拖入 Applications（应用程序）。也可将 ZIP 解压后的应用放入自己的应用程序目录。
2. 从应用程序目录启动，等待启动窗口显示“工作区已就绪”。应用会打开本机教师工作台，也可点击“打开教师工作台”。
3. 在工作台配置获准使用的分析服务，再创建作业、核对评分细则、导入 DOCX。完整步骤在“帮助与反馈”中离线可查。
4. 使用后先保存草稿，再在启动窗口退出。关闭网页不会结束后台应用；退出会中断尚未完成的分析，重开后可以重试。

如果系统安全检查阻止打开此试用构建，应由维护者提供正式签名版本；本交付说明不要求关闭或绕过系统安全检查。

## 资料与保留数据的更新

安装版默认资料目录为 `~/Library/Application Support/Labwise/data`，独立于应用程序。设置页和启动窗口都显示实际位置。API 密钥保存在本机后台，不内置于安装包。

更新前先保存并下载备份，退出旧应用，再替换 `Labwise.app`。不应在替换程序时清理资料目录。删除应用不自动删除教师资料。

源码运行保持原 `.labwise` 目录，安装时不自动搬迁或合并旧课程。源码版转入安装版时，先从原版本导出备份，再恢复为独立副本核对。恢复后的启动脚本已经区分源码 Python 和打包应用，不再要求安装包旁边存在 `server.py`。

本轮实际验证了同版本程序文件替换后已保存资料保留，不承诺未来任意版本间的数据库升级或降级兼容。未来版本仍需要针对其数据变化完成升级验收。

## 启动和组件检查

- 应用只绑定 `127.0.0.1`，不因打包开放到局域网。
- 预留端口被占用时选择备用端口，以启动窗口实际地址为准，不打开其他软件占用的页面。
- 同一资料目录使用文件锁和实例身份检查，重复启动复用现有工作区，避免第二个分析队列。
- 检查界面资源、运行库、TLS 证书校验和原文分页组件；基础依赖不完整时停止启动并提示。
- Word 阅读、评分和 Word 批改包可以直接使用。分页转换及评阅 PDF 仍依赖外部 LibreOffice，未捆绑到安装包；缺失时说明受影响的能力。可从 [LibreOffice 官方下载页](https://www.libreoffice.org/download/)选择本机版本。
- 启动日志保存在资料目录 `startup.log`，有大小轮转限制，不自动上传。

本机受管理的 Python 在 TLS 初始化时需要额外的公共证书策略文件；打包保留该文件和现有证书校验规则。没有通过关闭证书验证来解决打包问题。

## 已执行的交付验收

应用的临时代码签名完整性检查、DMG 校验及 ZIP 完整性检查通过；分发清单记录了 DMG／ZIP 的 SHA-256。

**75 项 Python、4 项 JavaScript 回归测试全部通过。** 包内另通过依赖、TLS、隐藏原生启动窗口和资料目录分离的自检。

实际验收将应用复制到隔离的“应用程序”目录，清除 Python 开发环境变量，从临时工作目录启动，并用虚构报告完成以下 9 类检查：

1. 包内运行及真实端口冲突后的备用端口。
2. 离开源码目录后加载界面和阅读器资源。
3. 导入 DOCX、手动评分确认、Word 批改包导出，以及学生反馈不包含私人笔记。
4. 刻意缺少转换组件时，PDF 返回可操作的错误。
5. 包内完整备份和独立副本恢复，恢复脚本不引用源码 `server.py`。
6. 重复启动复用同一个已运行工作区。
7. 重开后评分、确认状态、反馈、私人笔记保留。
8. 模拟替换同版本程序文件后，上述资料仍保留。
9. 独立恢复副本能够启动并读取评分与笔记。

以上检查不使用现有教师资料，不调用真实 AI，也没有写入实际 Applications 或安装版默认资料目录。仍需在目标用户电脑做真实安装试用、复杂 Word 与获准 AI 服务验收。原生窗口完成了隐藏初始化自检，其完整人工交互流程仍需教师试用确认。

## 构建和复验

构建机需要 macOS、与目标架构匹配的 Python 3.12、项目依赖，以及 `requirements-build.txt` 固定的 PyInstaller。构建遵循 [PyInstaller 资源定位说明](https://pyinstaller.org/en/stable/runtime-information.html)和[macOS 构建选项](https://pyinstaller.org/en/stable/usage.html#macos-specific-options)。

在准备好独立构建环境后执行：

```sh
.venv/bin/python -m pip install -r requirements.txt -r requirements-build.txt
.venv/bin/python packaging/build_macos.py
.venv/bin/python packaging/smoke_macos.py output/build/macos-dist/Labwise.app --report output/installers/installation-smoke-test.json
```

本工作区已将构建工具安装在隔离的 `output/build-tools`，可用 `PYTHONPATH=output/build-tools .venv/bin/python packaging/build_macos.py` 重建。打包采用明确的公开资源清单和运行库，不复制整个工作区。安装包内有第三方组件与许可证说明；教师报告、数据库、历史语料和密钥不进入分发包。

正式公开分发仍待配置 Developer ID 签名、公证与发布流程，并完成目标系统和版本兼容验收。本轮没有自动升级安装器，也没有发布 App Store 应用。
