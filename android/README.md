# ArchOHall Android 0.06

ARM64 Android 实验版，包名 `com.archoh`，最低 Android 8.0。APK 集成 Termux、PRoot 与 Termux:X11，无需另外安装宿主应用。

## 下载与安装

从 [0.06 Release](https://github.com/villager1314/ArchOHall/releases/tag/android-0.06) 下载 `ArchOHall-0.06-arm64.apk`。Release 同时提供 `SHA256SUMS` 和 `runtime-manifest.json`；构建与检查记录见 [Actions 40523515699](https://github.com/villager1314/ArchOHall/actions/runs/40523515699)。

已发布 APK 对应源码提交 `81e67eec69c47bc5689fa0a42a4652d1e64f87d8`、versionCode 8。后续文档和发布流程的整理没有改动这份 APK。

### 首次使用

1. 打开应用，等待内置离线运行环境展开。
2. 点击 **选择本地导入包**，通过 Android 文件选择器选取 ArchOHall 的 `tar.xz`，或含 `archohall-aarch64.tar.xz` 的 Actions ZIP。
3. 等待导入完成，点击 **应用桌面修复与 Android 桥接**，联网补齐缺失组件。
4. 点击 **启动 Plasma Mobile**；控制页可打开桌面、内置终端、显示设置与日志。

镜像单独下载，建议预留至少 12 GiB。分卷先校验、合并再导入。展开内置环境与导入本地文件可离线完成；安装缺失组件和 Linux 软件需要网络。

### 覆盖升级

停止桌面 → 覆盖安装相同固定签名的新版 APK → 点击一次 **应用桌面修复与 Android 桥接** → 重新启动桌面。保留原容器、应用和个人文件，不需要重新导入镜像。

早期 Actions 临时签名构建无法覆盖固定签名版本，应先备份再迁移。卸载应用会删除私有数据。不要将其他应用的私有环境直接迁入本应用。

### 文件与权限

- **共享存储访问**：Android 11+ 使用系统所有文件访问授权页面；镜像 SAF 文件选择不依赖此权限。
- **导入终端文件**：通过 SAF 复制单个文件到内置终端 `~/downloads`，单文件上限 64 MiB。
- 导入进度、取消和失败原因显示在控制页；失败或取消不将未完成的容器标为可用。成功替换容器时保留旧容器备份并继续占用空间。

## 0.06 内容与边界

- 默认 150% 缩放；KWin 使用 QPainter，Plasma 与键盘使用 llvmpipe OpenGL；启动时重建正常用户的应用菜单缓存。
- 修复 Shell 环境、电池 BatteryLevel、设置首页和键盘模块路由；语言默认值仅在未设置时补入。
- 配置容器 `arch` 用户免密 sudo，恢复已知 sudo 程序被导入器移除的 setuid 位。此为 PRoot 模拟身份，不授予 Android root。
- 补齐 plasma-settings、fastfetch、wl-clipboard 等组件，拒绝更改任何已安装包的版本。
- PulseAudio 使用私有 cookie 认证的本机 TCP；加入 Linux 内部亮度/媒体音量滑块和反向文字剪贴板通道。
- 通知名称与任务标签改为 ArchOHall，控制页和桌面分属不同 Android 任务，通知增加控制台入口。
- 方框键接入临时窗口列表；后续优先恢复 Plasma Mobile 原生任务切换器。

音频传输、协议和构建检查通过，不代表扬声器、蓝牙路由、Wayland 剪贴板、滑块或窗口激活已在手机上全部验证。图片/文件剪贴板、完整终端键盘和 Discover 商店未在本版实现。Wi-Fi、蓝牙等通过 Android 设置入口管理。

完整实现范围见 [0.06 技术记录](../diagnostics/ANDROID-006.md)。开发中的失败尝试、原因与版本演进另存于 [测试版开发复盘](../docs/development/ANDROID-EXPERIMENTS.md)。

## 日志与回退

控制页可查看桌面日志、导出导入日志。内置终端中的相关文件为：

- `~/.archohall/session.log` 与 `session.previous.log`：桌面启动和 Qt/KDE 日志。
- `~/.archohall/audio.log`：宿主音频后端和客户端连接诊断。

0.06 的受管理脚本备份后缀为 `.before-support-006`，配置备份为 `.before-config-006`。在停止桌面后，可在容器模拟 root 下运行 `/usr/local/bin/archohall-restore-desktop-support` 恢复已备份的文件和 sudo 模式。额外安装的软件包保留，工具不会回滚整个容器。

音频检查在 Linux 终端运行 `archohall-audio-check`；明确要播放短测试音时再执行 `archohall-audio-check --test`。不要单独升级 Qt/KDE 库；整体升级也应先备份并核对兼容组件版本。

## 构建与签名

完整命令顺序以 [Android 工作流](../.github/workflows/android.yml) 为准，使用 Python 3、JDK 17 与 Android SDK 36。

1. `prepare_project.py` 按 `source-lock.json` 组合固定的 Termux / Termux:X11 源码和本仓库覆盖文件。
2. 工作流下载并校验锁定的 KWin 兼容组件与此前验证的 0.04 X11 JNI 供体；这里的 0.04 是有意保留的依赖版本。
3. `build_runtime.py` 校验软件源签名，构建离线运行包；`build_desktop_support.py` 将受管理的容器文件打入 APK。
4. 执行桥接测试、Android 单元测试、构建、X11 JNI 声明/16 KiB 对齐检查和固定签名检查。

仓库管理员需配置 `ARCHOHALL_SIGNING_BUNDLE` Secret。密钥缺失或证书不匹配时构建停止，不使用临时密钥替代。密钥不提交仓库、不放入发布附件。分发证书 SHA-256：

```text
395043a9142654bea4cf43699c719dd77fd7276b4dc286f4399dfb273732de02
```

APK 的软件包版本与校验信息记录在 `runtime-manifest.json`。兼容组件与旧 JNI 供体由历史 Actions 产物提供，保留期结束后需维护供体来源；不能忽略校验或直接替换成新的 nightly。

## 许可

Android 集成衍生代码为 GPL-3.0-or-later，见 [LICENSE.md](LICENSE.md)。根目录 MIT 许可证只覆盖原有独立 rootfs 脚本与配置；各上游软件适用各自许可证。项目与 Arch Linux ARM、KDE、Termux 无官方关联。
