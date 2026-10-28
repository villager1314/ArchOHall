# ArchOHall Android 0.07：原生移动多任务与配套 rootfs

## 实现

移除 0.06 的 `archohall-task-switcher`、自建 D-Bus 接收器和 `usr/local/share/archohall/TaskSwitcher.qml`。0.07 通过正常的 KWin KGlobalAccel 服务调用上游 `Mobile Task Switcher`，界面来自 Plasma Mobile 自带的 `mobiletaskswitcher` SceneEffect，其 QML 和任务模型没有被替换。

原生 SceneEffect 要求 OpenGL 合成。旧的 KWin 6.7.5 QPainter 兼容组件不能满足该要求；0.07 构建 KWin 6.8.1（`1b798c05c19b1124edb1e16623191fcd2c128fd0`），保留全局快捷键和 tabbox，使用 llvmpipe 软件 OpenGL。合成器输出经 FBO 读回至 SHM 缓冲区，再通过 X11 Present 交给 Termux:X11。这是显示传输的兼容补丁，不是另写任务切换界面。

补丁仅在 wrapper 显式设置 `ARCHOHALL_KWIN_SHM=1` 时启用软件 X11 路径；正常 DRM 路径保留。仍保护不可用的 UdevMonitor。源码和构建脚本位于 `diagnostics/native007/`，发布附件提供上游源码与补丁。

## 配套镜像与升级

rootfs、原生合成器和 APK 在同一流水线构建；APK 内组件与 rootfs 使用同一份 `native-component.json` 清单。安装前及运行时检查 KWin、Plasma Mobile、Qt 与 KGlobalAccelD 版本，拒绝把不匹配的二进制写入旧桌面，也不会自动部分升级 Qt/KDE。

- 新安装使用同一 0.07 Release 的 APK 和 rootfs。
- 已有容器先停止桌面、覆盖安装 APK，再执行“应用桌面修复与 Android 桥接”。版本完全匹配时可就地安装原生组件。
- 若版本检查失败，先备份/迁移个人文件，再导入同一 Release 的配套 rootfs。导入器会保留旧容器备份，额外占用空间。
- `.archohall-native-007` 标记表示原生组件已经安装。旧组件目录和启动器保留版本化备份；自建窗口列表的两个已知文件被移至 `.before-native-007`，不再参与启动。
- 0.07 的受管理脚本与配置备份改为 `.before-support-007` / `.before-config-007`。该文件级恢复工具不等同于回滚整套合成器；需要完整回退时使用原容器备份。

初始化在 KWin 配置中启用 `mobiletaskswitcherEnabled=true`，保留其他插件设置。默认分辨率 720×1280，缩放 150%。软件 OpenGL 的 CPU 占用和流畅度仍取决于设备。

## 发布检查

发布前要求以下检查全部通过：

1. ARM64 环境构建匹配版本的 KWin。
2. 确认 Xvfb 不提供 DRI3、注入空 udev monitor，验证无 DRM 的软件 OpenGL 合成。
3. 通过真实 `org.kde.kglobalaccel.Component.invokeShortcut("Mobile Task Switcher")` 检查上游 effect 加载、激活及关闭；保留原生日志和截图。
4. 桥接与配置测试，确认不再打包临时窗口列表，旧文件迁移与原生插件配置可重复执行。
5. Android 单元测试、固定签名、X11 JNI 声明和原生库打包检查。
6. rootfs 归档完整性、APK 与组件清单一致性及发布附件 SHA-256。

Linux CI 测试不能代替 Android 触摸、驱动、功耗和实际窗口切换实测。未新增 GPU 硬件加速，也不将此前尚待设备验证的音频/剪贴板功能标为全部稳定。

## 先本地检查，再做集成验证

在准备好 `dbus-fast`、ShellCheck、Mesa 软件 EGL 的开发机运行：

```sh
bash scripts/check-native-local.sh /path/to/kwin-git-checkout
```

该入口检查 Python/Bash 语法、ShellCheck、配置/桥接/候选组件复用测试，并实际创建软件 EGL 上下文、绘制 FBO、读回并核对像素；补丁在临时目录中的固定提交原文件上应用，不重置开发者的 KWin 工作树。这些检查不替代完整 KWin 编译和原生效果集成测试。

本次执行环境是 x86_64，禁止创建 Unix socket 和 chroot。本地可显式设置 `ARCHOHALL_ALLOW_RESTRICTED_SOCKET_SKIP=1`，仅跳过音频、D-Bus、PRoot 三项受限测试；2026-10-28 执行结果为 13 项通过、3 项跳过，软件 EGL/FBO 读回和固定源码补丁应用通过。CI 不设置该跳过变量。

构建在运行测试前导出 `native-007-candidate`，即使测试失败也保留编译产物。此附件是未认证的候选组件，不是 Release。手动运行构建时可填写原构建的 `candidate_run_id` 复用组件；先验证归档哈希、补丁/构建参数/wrapper 哈希和六个关键软件包的精确版本，再重新运行当前测试。任何编译输入或依赖变化都拒绝复用，不能通过复用跳过验证。
