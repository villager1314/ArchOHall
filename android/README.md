# ArchOHall Android 0.01.2

实验性 ARM64 安卓应用，包名 `com.archoh`，可以与现有 Termux、Termux:X11 和 `com.phoshx` 并装。

0.01.2 将 X11 Java 源码固定到官方 APK release 正文的实际构建提交，而非陈旧的 target_commitish；修复 JNI 注册缺少 nativeSetLaunchWindowingModeFreeform 导致的 SIGABRT。CI 对照官方 APK 与集成 APK 的全部 X11 native 声明及签名，发现不一致即停止。

0.01.1 修复 Linux 文件名中反斜杠被错误拒绝的问题（例如 systemd 的 `\x2d` 单元名）。原 rootfs 导入包可以继续使用。

## 使用

1. 从本仓库 Actions 的 **Build ArchOHall Android 0.01.2** 下载 APK 构建产物并安装。
2. 首次启动会从 APK 展开内置运行包并配置软件，整个过程不执行 `pkg install` 或联网下载。
3. 点击“选择本地导入包”，通过安卓 SAF 选择 ArchOHall 的 `tar.xz`，或此前 rootfs Actions 生成的 ZIP。
4. 观察分阶段进度与日志；导入完成后点击“启动 Plasma Mobile”。
5. 出错时导出导入日志，或打开内置终端查看桌面进程输出。

APK 内置 ARM64 Termux 用户空间、PRoot、X11 原生显示组件、音频及依赖。Arch + Plasma Mobile 的大镜像通过本地文件导入，不塞进 APK。
默认使用软件渲染。此版本不依赖手机上已有的 Termux，不会修改其数据。

SAF 支持直接的 `tar.xz`，或包含 `archohall-aarch64.tar.xz` 的 ZIP。分卷需先合并。
解压显示当前路径、项目数和基于 tar 展开字节的进度；未知长度的 SAF 流使用不定进度。
切换界面或旋转后重新连接前台导入任务；系统杀死进程时不会将半成品标记为已安装，可重新导入。
失败和取消保留已有容器；成功替换时旧容器保留在应用私有目录的备份中。

## 构建

`prepare_project.py` 根据 `source-lock.json` 获取固定上游源码并应用本仓库覆盖文件。
`build_runtime.py` 校验官方 APK 和 Termux 软件源签名，再解析、下载完整依赖集，重定位后打包为离线运行环境。
构建阶段需要网络，安装和导入阶段不需要。软件包版本和运行包校验值随 APK 的 `runtime-manifest.json` 提供。
APK 尚需 ARM64 实机验证；CI 测试不能证明安卓 GPU、触摸和所有 PRoot 系统调用都可用。

当前使用 CI 调试签名；配置持久发布密钥前，不同构建可能不能直接覆盖安装。不要把其他应用的数据迁移进此实验版本。

## 许可与来源

本目录新增 Android 代码与其集成衍生部分按 GPL-3.0-or-later 提供，参见 Termux 上游 LICENSE.md；仓库根目录 MIT 仅覆盖原有独立 rootfs 脚本。
Termux 和 Termux:X11 的固定源码提交记录在 `source-lock.json`。预编译 JNI 从匹配的官方 APK 提取，保留 Java/JNI 命名空间，仅重定位文件系统和私有 IPC 路径。
APT 软件包重定位器沿用此前自有集成项目的实现。
与 Arch Linux ARM、KDE、Termux 无官方关联。
