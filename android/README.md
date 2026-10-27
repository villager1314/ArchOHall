## Android 0.04

保持 `com.archoh` 和固定签名，可覆盖安装并保留现有运行环境及容器。

- 首页“共享存储访问”与 `termux-setup-storage` 使用同一授权流程；Android 11+ 打开系统所有文件访问页面。SAF 导入不依赖此权限。
- 覆盖安装会修复现有 `am` 调用身份与内置 X11 命令入口；APT 更新后也会重新修复。
- “导入终端文件”通过 SAF 复制单个文件到私有 `~/downloads`，上限 64 MiB。
- “安装软件兼容组件”完全离线安装 KWin 6.7.5 QPainter，并保留原桌面启动脚本。适用于之前 6.8.1 的 udev/RenderDevice 崩溃；要求 Qt Base 6.12.0-3、Declarative 6.12.0-2、Wayland 6.12.0-1。
- 兼容组件暂未启用装饰、锁屏、全局快捷键服务等功能，Android 实机行为仍需验证。系统 KWin/Plasma 的 pacman 记录不改动。
- 桌面启动实际验证 X11 客户端连接，每次启动保留上一份日志为 `session.previous.log`。

兼容包来自 Actions 40464534205，锁定 SHA256 `8997a9cbf09361ce8614fda5925f21eb8bcd652ccd303f54433c40a1f58d28e4`。构建依赖该产物仍可下载；过期时需重新构建并更新锁定信息，校验失败会停止 APK 构建。

# ArchOHall Android 0.03

实验性 ARM64 安卓应用，包名 `com.archoh`，可以与现有 Termux、Termux:X11 和 `com.phoshx` 并装。

0.01.2 将 X11 Java 源码固定到官方 APK release 正文的实际构建提交，而非陈旧的 target_commitish；修复 JNI 注册缺少 nativeSetLaunchWindowingModeFreeform 导致的 SIGABRT。CI 对照官方 APK 与集成 APK 的全部 X11 native 声明及签名，发现不一致即停止。

0.01.1 修复 Linux 文件名中反斜杠被错误拒绝的问题（例如 systemd 的 `\x2d` 单元名）。原 rootfs 导入包可以继续使用。

0.02 修复继承 Termux 的 extractNativeLibs=true 导致 JNI 库被压缩、后台 app_process 无法直接 dlopen APK 内 libXlorie.so 的问题。原生库以未压缩、16 KiB 对齐的方式打包，CI 检查最终 APK 的实际 ZIP 条目。版本名按 0.01、0.02、0.03 递增。

0.03 默认采用清华 TUNA 的 Termux 主仓库和 X11 仓库，并固定 pkg 的镜像选择。覆盖安装后会对已有运行环境离线迁移一次，旧配置保存在 `$PREFIX/etc/termux/archohall-before-003/`；后续手动换源不会被反复覆盖。不自动执行 apt update 或升级软件，也不修改 Arch 容器源。构建时仍从经过签名校验的上游仓库取包，安装与配置保持离线。

## 使用

1. 从本仓库 Actions 的 **Build ArchOHall Android 0.03** 下载 APK 构建产物并安装。
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

Actions 分发产物现在必须使用保留的固定签名，与单独提供的 0.01.2 / 0.02 固定签名 APK 相同。缺少签名 Secret 或证书校验失败时构建停止，不会回退到 runner 临时签名。此前的 Actions 临时签名 APK 无法覆盖迁移到此签名，需要一次卸载重装。不要把其他应用的数据迁移进此实验版本。

仓库管理员在 Settings → Secrets and variables → Actions 添加 `ARCHOHALL_SIGNING_BUNDLE`，其值为私密提供的 JSON 文件全文（alias、password、keystore_base64）。不要把文件提交到仓库或上传到公开构建产物。`sign_apk.py` 在临时目录使用密钥并在结束时清理，校验证书 SHA-256 为 `395043a9142654bea4cf43699c719dd77fd7276b4dc286f4399dfb273732de02`。

## 许可与来源

本目录新增 Android 代码与其集成衍生部分按 GPL-3.0-or-later 提供，参见 Termux 上游 LICENSE.md；仓库根目录 MIT 仅覆盖原有独立 rootfs 脚本。
Termux 和 Termux:X11 的固定源码提交记录在 `source-lock.json`。预编译 JNI 从匹配的官方 APK 提取，保留 Java/JNI 命名空间，仅重定位文件系统和私有 IPC 路径。
APT 软件包重定位器沿用此前自有集成项目的实现。
与 Arch Linux ARM、KDE、Termux 无官方关联。
