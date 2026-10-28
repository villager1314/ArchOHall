<div align="center">

<img src="docs/assets/archohall.svg" width="128" alt="ArchOHall 应用图标"/>

# ArchOHall

**在 Android 手机上运行 Arch Linux ARM 与 KDE Plasma Mobile，无需 root。**

[![Version](https://img.shields.io/badge/version-0.07-4961AC?style=for-the-badge)](https://github.com/villager1314/ArchOHall/releases/tag/android-0.07)
[![Android](https://img.shields.io/badge/Android-8.0%2B-3DDC84?style=for-the-badge&logo=android&logoColor=white)](#-设备要求)
[![Architecture](https://img.shields.io/badge/architecture-ARM64-1793D1?style=for-the-badge&logo=archlinux&logoColor=white)](#-工作原理)
[![License](https://img.shields.io/badge/license-MIT_%2F_GPL--3.0-4961AC?style=for-the-badge)](#-许可证)

[下载 APK](https://github.com/villager1314/ArchOHall/releases/tag/android-0.07) · [快速开始](#-快速开始) · [已知限制](#-当前状态与已知限制) · [反馈问题](https://github.com/villager1314/ArchOHall/issues)

</div>

---

ArchOHall 将 Termux 用户空间、PRoot、Termux:X11 和音频组件集成到一个 Android 应用中，通过 Material 3 界面管理容器、导入镜像和启动桌面。导入预装的 ArchOHall 镜像后，即可尝试在手机上使用 Plasma Mobile 桌面和 ARM64 Linux 应用。

APK 内置宿主运行环境，Arch Linux 桌面镜像单独导入。运行时无需另外安装 Termux 或 Termux:X11。

## ✨ 功能

- **移动端 Linux 桌面**：Arch Linux ARM + Plasma Mobile，内置终端，默认 150% 缩放。
- **Material 3 管理界面**：本地镜像选择、导入进度、取消操作、桌面启停及日志查看。
- **本地导入**：支持 ArchOHall 的 `tar.xz` 和 Actions ZIP，通过 Android 文件选择器读取。
- **独立运行环境**：Termux、PRoot 和 X11 显示组件随 APK 提供；展开运行环境和导入本地镜像可离线完成。
- **实验性 Android 桥接**：电池状态、媒体音量、桌面窗口亮度、保持亮屏、系统设置入口和 Android 应用启动。
- **保留现有容器的更新方式**：APK 部署桌面修复脚本并备份旧文件，补齐缺失组件时拒绝升级已安装的软件包。

## 📥 下载

| 内容 | 下载入口 | 说明 |
| --- | --- | --- |
| Android 0.07 APK | [0.07 实验版 Release](https://github.com/villager1314/ArchOHall/releases/tag/android-0.07) | 下载并安装 `ArchOHall-0.07-arm64.apk` |
| 配套 ARM64 rootfs | [0.07 同页下载](https://github.com/villager1314/ArchOHall/releases/tag/android-0.07) | 下载 `archohall-aarch64.tar.xz`；分卷需校验并合并 |
| 后续 APK 构建 | [Android 构建记录](https://github.com/villager1314/ArchOHall/actions/workflows/android-007.yml) | 可查看测试结果、版本和构建产物 |

APK 通过 GitHub Release 提供直接下载，并附带校验和与运行环境清单。Actions 保留构建日志和限期产物；下载 Actions 产物通常需要登录 GitHub。0.07 为实验性预发行版，APK 与配套 rootfs 由同一流水线构建，并发布组件版本清单。

**首次使用请选择同一 0.07 Release 的 APK 和 rootfs。** 旧容器版本检查通过后可就地更新；不匹配时先备份/迁移个人文件，再导入配套镜像，避免混装 Qt/KDE 组件。

## 🚀 快速开始

### 首次安装

1. 下载并安装 ARM64 APK，打开 **ArchOHall**，等待内置运行环境展开。
2. 将 ArchOHall 镜像下载到手机，点击 **选择本地导入包**，选中 `tar.xz` 或 Actions ZIP。
3. 等待导入完成。镜像较大，过程中可查看进度和操作日志。
4. 点击 **应用桌面修复与 Android 桥接**，联网补齐缺失组件；完成后点击 **启动 Plasma Mobile**。
5. 使用 **打开桌面** 返回 Linux，使用 **停止桌面** 结束会话；**内置终端** 和 **显示设置** 可在控制页打开。

下载的是镜像分卷时，先校验并合并全部分卷，再选择合并后的 `tar.xz` 导入。应用不直接导入单个分卷。

### 从旧版本升级

1. 停止桌面，使用相同固定签名的新版 APK 覆盖安装。
2. 打开控制页，点击一次 **应用桌面修复与 Android 桥接**，等待配置与组件安装完成。
3. 重新启动桌面，保留原有容器、应用和个人文件。

卸载应用会删除其私有数据，请先做好备份。早期使用临时签名的构建不能直接覆盖固定签名版本，迁移前请阅读 [安装说明](android/README.md)。

## 📋 设备要求

- Android **8.0 及以上**，支持 **arm64-v8a** 的设备。
- 建议预留至少 **12 GiB** 存储空间，用于压缩包、展开后的容器及后续软件安装；保留旧容器备份还会额外占用空间。
- 首次下载镜像、补齐 Linux 组件和安装新软件需要网络。
- 当前默认软件渲染，桌面流畅度和发热情况取决于设备性能、分辨率与应用负载。

## ⚙️ 工作原理

PRoot 在 Android 应用权限内提供 Linux 文件系统与模拟用户身份，运行 Arch Linux ARM 的程序。容器内使用 KWin Wayland 和 Plasma Mobile，KWin 的嵌套 X11 后端将画面输出到应用集成的 Termux:X11。

0.07 的 **KWin、Plasma 与虚拟键盘均使用 Mesa llvmpipe OpenGL**。KWin 通过共享内存读回向 X11 输出，保留原生多任务 effect 所需的 OpenGL 合成。音频经 Android 宿主的 PulseAudio 输出；Android 状态与控制通过应用私有桥接传递。

容器普通用户为 `arch`。0.07 桌面修复会配置容器内的免密 `sudo`，用于 PRoot 模拟 root；Android 应用仍保持普通应用权限。当前会话独立于 systemd 用户服务和 SDDM，部分依赖完整系统服务的 Linux 功能不可用。

## 🧪 当前状态与已知限制

Plasma Mobile 已在 ARM64 手机上启动，软件渲染、缩放和应用列表经过排查。发布流程检查原生任务切换、桥接、Android、固定签名和 X11 原生接口；Android 上的触摸、性能与设备行为仍需实机验证。

| 项目 | 当前状态 |
| --- | --- |
| 声音、亮度与音量 | 已加入音频传输修复和 Linux 内部滑块；实际扬声器输出、设备路由与交互效果待验证。亮度调节作用于桌面窗口 |
| 剪贴板 | 已加入 Linux → Android 的文字同步通道；端到端效果待验证，暂未实现图片、文件及历史记录同步 |
| Wi-Fi、蓝牙等设置 | 通过 Android 系统设置入口管理；设备和厂商系统可能影响跳转行为 |
| 多任务界面 | 0.07 使用 Plasma Mobile 原生任务切换器，删除临时窗口列表；原生快捷键与 OpenGL 合成共同提供支持 |
| 虚拟键盘 | 提供输入法组件与语言默认配置；完整终端功能键布局仍待完善 |
| GPU 加速 | 当前以软件渲染为兼容基线，Turnip、VirGL 等加速路径尚未作为已验证功能提供 |

需要密码、Polkit、设备节点或 systemd 服务的设置页，可能无法在 PRoot 中正常工作。暂未内置 Discover 应用商店。不要单独升级 Qt/KDE 库；整体升级也可能破坏当前兼容环境，应先备份并核对兼容要求。

实现范围、备份与验证记录见 [0.07 实现与迁移说明](diagnostics/ANDROID-007.md)。

## 🛠️ 从源码构建

推荐使用仓库的 [0.07 构建工作流](.github/workflows/android-007.yml)。开发源码可通过以下方式获取；复现已发布 APK 时，请使用下方注明的原构建提交：

```bash
git clone https://github.com/villager1314/ArchOHall.git
cd ArchOHall
# 复现发布版本：git checkout android-0.07
```

构建使用 Python 3、JDK 17 和 Android SDK 36。工作流会组合锁定的 Termux / Termux:X11 源码、校验离线运行包与兼容组件，执行测试，再使用配置好的固定密钥签名。

正式分发构建要求配置 `ARCHOHALL_SIGNING_BUNDLE` Secret；缺少配置会停止构建，不会改用临时签名。详细步骤与签名要求见 [Android 构建说明](android/README.md)。0.07 的 APK 与 rootfs 使用同一流水线，分别完成检查后一起发布。

<details>
<summary>项目目录</summary>

| 目录 / 文件 | 用途 |
| --- | --- |
| `android/` | Android 管理应用、运行环境打包和宿主桥接 |
| `rootfs/usr/local/` | 容器启动脚本、受管理的配置工具与桌面支持文件 |
| `scripts/` | rootfs 构建、配置及原版 Termux 启动脚本 |
| `tests/` | 桥接、音频和 PRoot 身份模拟测试 |
| `diagnostics/` | 故障排查、兼容组件与版本修复记录 |
| `.github/workflows/` | APK 和 rootfs 构建工作流 |

</details>

## 🙏 致谢

ArchOHall 基于以下开源项目构建：

- [Arch Linux ARM](https://archlinuxarm.org/)：ARM64 Linux 发行版与软件仓库。
- [KDE Plasma Mobile](https://plasma-mobile.org/) 与 [KWin](https://invent.kde.org/plasma/kwin)：移动桌面、窗口管理与合成。
- [Termux](https://github.com/termux/termux-app) 与 [Termux:X11](https://github.com/termux/termux-x11)：Android 用户空间、终端与显示组件。
- [PRoot](https://github.com/termux/proot)、[Mesa](https://www.mesa3d.org/) 与 [PulseAudio](https://www.freedesktop.org/wiki/Software/PulseAudio/)：免 root 运行环境、软件渲染与音频。

## 🔗 项目链接

- [源代码](https://github.com/villager1314/ArchOHall)
- [构建与下载](https://github.com/villager1314/ArchOHall/actions)
- [问题反馈](https://github.com/villager1314/ArchOHall/issues)
- [Android 使用与版本记录](android/README.md)

## 📄 许可证

原有独立 rootfs 脚本和配置采用 [MIT](LICENSE) 许可证；Android 集成衍生部分采用 [GPL-3.0-or-later](android/LICENSE.md)。镜像中的各个软件分别适用其上游许可证，并保留相应许可文件。

ArchOHall 与 Arch Linux ARM、KDE、Termux 无官方关联；相关名称与商标属于各自所有者。
