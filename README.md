# ArchOHall

面向免 root Android 的 **Arch Linux ARM + Plasma Mobile** 预装 rootfs 实验。
宿主使用 **PRoot / proot-distro + Termux:X11**；后续计划开发 Material 3 Expressive 安卓管理界面。

## 当前阶段

这是镜像构建与实机验证阶段，尚未提供独立 APK。CI 构建通过不代表桌面已经在手机上验证。
内部为 KWin Wayland + Plasma Mobile，外部通过 KWin 嵌套 X11 后端输出到 Termux:X11。
默认使用 llvmpipe 软件渲染；骁龙 8 Elite GPU 加速后续单独验证。
当前启动的是最小 mobile shell，不是完整的 systemd/SDDM 登录会话；部分设置和后台服务可能不可用。

## 构建和下载

修改构建相关文件会触发测试构建；也可以在 Actions → Build ArchOHall rootfs → Run workflow 手动运行。
构建使用 `ubuntu-24.04-arm` 原生 ARM64 runner，在临时 chroot 中安装软件，再导出普通根目录 tar.xz。
这不要求运行镜像的手机拥有 root。

成功后在运行页面的 Artifacts 下载 `archohall-aarch64-编号`，解开外层 ZIP。
手动运行时勾选 `publish_release` 可发布实验性预发行版，方便手机直接下载附件。
没有定时构建。Arch 为滚动发行版，不承诺不同时刻构建的字节一致；每次记录包版本、源码提交、基础镜像 SHA-256 和时间。

产物包含：

- `archohall-aarch64.tar.xz`：预装 rootfs；超过 Release 单文件限制时自动拆为 `.part000` 等 1 GiB 分卷。
- `SHA256SUMS`：所有分发文件的校验和。
- `packages.txt`、`build-info.txt`：完整包版本与构建信息。
- `start-termux.sh`：原版 Termux 的宿主启动脚本。

基础镜像来自 Arch Linux ARM 官方 HTTPS 下载地址。构建必须验证其签名以及固定的完整签名密钥指纹；验证失败即停止。pacman 保留软件包签名验证。

## 手机导入

需要 ARM64 安卓、Termux、另行安装的官方 Termux:X11 APK，以及支持本地 tar 导入的新版 proot-distro（5.x 及以上）。旧版本先查看 `proot-distro install --help`，不要把该 tar 当成专用 backup/restore 归档。
建议先预留 12 GiB 空间用于压缩包、解压和后续更新；以实际构建包大小为准。

在 Termux 安装宿主组件：

```bash
pkg install x11-repo
pkg install proot-distro termux-x11-nightly xorg-xdpyinfo pulseaudio
```

将产物放入 Termux 可访问的同一个目录，进入该目录：

```bash
sha256sum -c SHA256SUMS
# 仅在下载的是分卷时执行下面一行；全部分卷必须在场且校验通过。
# cat archohall-aarch64.tar.xz.part[0-9][0-9][0-9] > archohall-aarch64.tar.xz
proot-distro install ./archohall-aarch64.tar.xz --name archohall
bash ./start-termux.sh
```

容器中普通用户是 `arch`。不预设登录密码、不启动 SSH、不提供免密 sudo。
需要安装软件时通过宿主进入容器 root（PRoot 模拟身份，不是安卓 root）：

```bash
proot-distro login archohall
pacman -Syu
```

不要只升级单个 KDE 库。需要密码/Polkit 的图形设置可能无法在 PRoot 中正常工作。
终端中 Ctrl+C 结束会话；关闭显示窗口不一定停止全部后台进程。

## 显示和诊断

默认外层显示 `:0`，窗口 720×1280，软件渲染。可用下面方式调低分辨率：

```bash
ARCHOHALL_WIDTH=540 ARCHOHALL_HEIGHT=960 bash ./start-termux.sh
```

检查已有图形环境后才试 `ARCHOHALL_RENDERER=auto`；该选项只是不强制 llvmpipe，不会安装或自动配置 Turnip/VirGL。
黑屏时保留完整日志：

```bash
set -o pipefail
bash ./start-termux.sh 2>&1 | tee archohall-start.log
```

优先排查 X11 连接、EGL 初始化、KWin 编译时的 X11 后端及 Qt 插件/动态库版本。
当前未接入安卓亮度、无线开关、电量、传感器或完整手机权限桥接；不能当作替代 Android 的系统镜像。

## 目录

- `packages.txt`：显式安装的软件包。
- `scripts/build-rootfs.sh`、`scripts/provision.sh`：构建与容器内配置。
- `rootfs/`：镜像覆盖文件和最小桌面会话。
- `scripts/start-termux.sh`：宿主显示、音频和 PRoot 启动。
- `.github/workflows/rootfs.yml`：构建、打包和可选发布。

## 上游与许可

ArchOHall 与 Arch Linux ARM、KDE、Termux 无官方关联。
镜像包含的软件分别适用各自许可证，保留 `/usr/share/licenses`；分发者应履行相应源码提供等义务。
本仓库新增脚本和配置使用 MIT 许可证，见 LICENSE；此许可证不覆盖镜像内的上游软件。
