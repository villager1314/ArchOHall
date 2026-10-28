# ArchOHall Android 测试版开发复盘（0.01—0.06）

整理日期：2026-10-28。本文保存开发中的故障、失败尝试、修复依据与验证边界，供后续维护使用；用户安装步骤以 `android/README.md` 为准。

本文根据仓库提交、构建结果及开发会话中的手机日志整理。没有为每个版本补造发布日期。“已合入”“CI 通过”“手机确认”分别表示不同的验证程度；不将构建成功写作硬件实测成功。

## 版本脉络

| 阶段 | 当时的问题 | 处理与结论 |
| --- | --- | --- |
| 0.01 / 0.01.1 | 本地导入与基础运行环境；导入器误拒绝含反斜杠的 Linux 文件名，如 systemd 的 `\x2d` 路径 | 修正归档路径判断，保留真正的越界路径防护；原镜像仍可使用 |
| 0.01.2 | X11 Java 声明与 native 库不一致，缺少 `nativeSetLaunchWindowingModeFreeform`，导致 JNI 注册失败和 SIGABRT | 使用供体 APK 发布正文对应的源码提交，新增 native 方法名、签名和 static 标志对照检查 |
| 0.02 | Activity 能启动，但后台 app_process 无法加载压缩在 APK 中的 libXlorie.so | 禁用原生库提取，保留未压缩、16 KiB 对齐的库条目；校验实际 APK ZIP 内容 |
| 0.03 | 宿主软件源与首次环境配置不统一 | 默认迁移至清华 TUNA 的 Termux 主仓库/X11 仓库，备份一次并保留后续用户换源；不因此升级容器的软件包 |
| 0.04 | am 仍以 com.termux 身份调用；共享存储只出现 Toast、未完成实际授权；KWin 启动崩溃 | 修正 TermuxAm 调用身份，加入系统权限页和升级修复；打包离线 KWin 6.7.5 兼容组件 |
| 0.05 | 应用图标不可见、虚拟键盘和音频组件缺失、快捷设置只认识不可用的 Linux 硬件服务 | 分离 KWin 与 Plasma 的渲染配置，加入宿主状态/动作通道、UPower facade、键盘启动器和桌面组件更新入口 |
| 0.06 | 应用列表复发、设置模块名错误、电池顶栏 -1、sudo 无法提权、声音/剪贴板与任务入口不完整 | 合并菜单缓存、Shell、模块路由、BatteryLevel、模拟 sudo、音频认证、文字剪贴板、通知任务和临时多任务修复 |

## 关键排查与失败尝试

### 1. KWin 崩溃：修改 Mesa 参数不等于补上后端

手机日志涉及 KWin 6.8.1、Qt 6.12.0 和 Mesa 26.2.5。先发现空 UdevMonitor，增加保护后仍遇到 X11WindowedOutput 的空 RenderDevice。该 X11 后端不再提供原先所需的 QPainter 路径；单纯更换 llvmpipe/环境变量不能制造缺失的渲染设备。

最终保留系统软件包记录，另将固定的 KWin 6.7.5 装入 `/opt/archohall-kwin-compat`，通过 wrapper 使用 QPainter。兼容构建关闭了一些功能，包括全局快捷键集成和 tabbox；这也是后来原生移动多任务不可直接调用的背景。详见 [兼容实验](../../diagnostics/KWIN-COMPAT.md)。

### 2. 图标与应用列表：两个问题不能混为一谈

将 `QT_QUICK_BACKEND=software` 同时用于 Plasma 会影响图标、着色器和遮罩。手机验证可用的配置为：KWin 保持 QPainter；Plasma/键盘取消该变量，使用 `QSG_RHI_BACKEND=opengl`、`LIBGL_ALWAYS_SOFTWARE=1`、`GALLIUM_DRIVER=llvmpipe`。默认输出缩放为 1.5。

之后应用列表仍曾消失。处理还包括检查 Plasma 的实际环境与插件搜索路径，并在正常用户环境中重建默认 KService 缓存。0.06 在启动 Folio 前执行默认 `kbuildsycoca6 --noincremental`，不将临时探针缓存路径固化进启动脚本。图标渲染修好不能代替应用枚举验证。

### 3. 设置打开了错误的地方

曾出现“无法找到插件 usr”和不存在的 `kcm_mobile_onscreenkeyboard`。前者与通用设置启动路径解析有关，后者是模块名与实际安装版本不匹配。实际模块列表包含 `kcm_virtualkeyboard` 和 `kcm_plasmakeyboard`。

0.06 明确区分设置首页与单模块启动；旧键盘名称映射到现有模块。Android 桥接磁贴的长按使用绝对路径的宿主命令，避免又落入不具备硬件服务的 Linux 网络设置页。厂商 Android 设置入口和部分 Linux 模块仍需实机检查。

### 4. 键盘、终端和电池的不同故障

- 键盘依赖 KWin 输入法协议与适当的 Qt Quick 渲染环境。通过 wrapper 启动，保留用户自行选择的输入法；未配置语言时才补入英语/中文默认值。手机曾确认切换到英语布局。
- Konsole 的空命令警告与缺失的 `SHELL` 环境有关，启动链补入 `/bin/bash` 后，后续手机截图未再显示该警告。
- 快捷磁贴有正确电量而顶栏显示 -1：UPower 的 `BatteryLevel=UNKNOWN` 会使 Solid 返回未知值。存在有效百分比时改为 NONE（1），缺失数据仍为 UNKNOWN（0）；后续手机截图显示了正常百分比。
- 完整终端功能键布局仍未完成；不能将“英语布局可用”写成“终端键盘已完善”。

### 5. sudo：容器 root 与 Android root

导入器有意剥离任意 setuid 位，普通会话又以 PRoot UID 1000 运行，sudo 因而报所属用户和 setuid 错误。0.06 仅恢复已知 sudo 程序的 setuid 位，使用 visudo 校验 `arch` 的免密规则；不通过 chown 获取 Android root，也不预设登录密码。

最初 CI 使用 Ubuntu 的旧 PRoot，身份测试失败。改为校验并编译 APK 所用版本的 Termux PRoot 5.1.107.101 后，普通 UID 1000 / setuid 模拟 UID 0 的检查通过。这个测试验证的是匹配版本的机制，手机上的完整 sudo 调用仍需确认。

包安装同时处理 PRoot 与 pacman 下载沙箱兼容性：禁用 DownloadUser/沙箱，而不关闭包签名校验。安装额外组件前核对计划，拒绝更改任何已安装包版本，避免部分升级 Qt/KDE。

### 6. 音频：宿主有输出，不等于容器已连通

此前“Android audio output connected”只能证明宿主存在 sink，不能解释 Plasma 的 `context kaput`。0.06 将宿主管理留在私有 UNIX socket，容器客户端改用仅监听 loopback 的 TCP 和随机私有 cookie，并关闭跨 PRoot 的共享内存/memfd 假设。客户端和 D-Bus 激活程序继承相同端点，启动时实际执行容器 pactl 连接检查。

CI 使用真实 PulseAudio null sink 验证正确 cookie 接受、错误 cookie 拒绝。此结果不验证 Android 扬声器、蓝牙路由、AAudio/OpenSL ES 的设备行为或延迟。

### 7. 剪贴板和 Android 控制

手机 → Linux 文字粘贴曾可用，反向复制失败。参考其他项目的 X11 剪贴板实现后，考虑嵌套 Wayland 路径，0.06 加入 `wl-paste --watch` 到私有动作通道的文字出口。Android 端只在桌面前台接收，校验 UTF-8 和 256 KiB 上限，避免记录内容。若 KWin 不提供所需协议，观察器退出并报告，不声称同步成功。

亮度、媒体音量可由 Linux 窗口内滑块发送数值；Wi-Fi、蓝牙等仍使用 Android 系统设置入口。桥接并不要求每项都跳出应用，但系统权限和可用 API 决定各项方式。端到端剪贴板和滑块仍待手机验证。

### 8. 通知、任务与临时多任务

通知残留 Termux 标题，控制页与 X11 窗口的任务身份也不清晰。0.06 更新显示名称，为控制页和桌面指定独立 taskAffinity，并在桌面通知加入返回控制台动作。最终 APK 的实际 manifest 已检查。

KDE 方框键通过 KGlobalAccel 调用 `Mobile Task Switcher`；当前兼容 KWin 的相关集成未启用。0.06 接入只处理该快捷动作的 D-Bus 接收器和窗口列表。它是临时方案，不是 Plasma Mobile 原生缩略图界面的恢复。后续优先核对原生 KWin effect、全局快捷键链路和合成器依赖，再移除临时替代；目前未实施这项替换。

### 9. 更新安装和回退流程中的遗漏

复查发现 Python 配置器曾被 `/bin/bash` 启动，已改为按各脚本自身 shebang 执行。回退脚本改为原子替换，避免运行时覆盖自身，并解析保存的 `0o755` 权限形式。

受管理脚本和配置分别保留 `.before-support-006` / `.before-config-006`；回退不删除新增软件包、不恢复完整快照。0.06 通过 APK 部署覆盖文件，不另行重做用户容器。

## 0.06 发布证据与未完成事项

| 项目 | 依据 / 状态 |
| --- | --- |
| 构建 | [Actions 40523515699](https://github.com/villager1314/ArchOHall/actions/runs/40523515699)，全部构建步骤成功 |
| APK 源码 | `81e67eec69c47bc5689fa0a42a4652d1e64f87d8`，versionCode 8 |
| APK SHA-256 | `e4310fa9a9c28b2ed26380729a6aa7bb8c7d5e9ce60265c2c709e427b2901484` |
| CI 覆盖 | 14 项 Python 桥接检查、Android 单元测试、固定签名、X11 JNI 和 16 KiB 原生库打包检查 |
| 最终包复查 | 68 个受管理文件与源码匹配；应用标签/独立任务配置正确；X11 原生库与已验证供体一致 |
| 手机仍需验证 | 声音、反向文字剪贴板、滑块、窗口激活、完整 sudo 与厂商设置跳转 |
| 后续开发 | 优先原生移动多任务；终端键盘、更多设备桥接与 GPU 加速另行验证 |

截图/录屏使用 Linux X11 捕获，录屏当前无麦克风；输出效果未列为本次完整实测。Waydroid、完整 systemd/Polkit 会话和 Discover 商店不属于已完成事项。

## 2026-10-28 仓库复查

- 将 APK 中现有 vector 图标转换成可在 README 展示的 SVG，没有重画或替换应用图标。
- 清理 Android 使用说明里的 0.03 下载入口，将历史版本过程移到本文；0.04 JNI 供体和 6.7.5 KWin 是有意锁定的依赖，不应批量改成 0.06。
- 给早期 KWin/0.05 桥接记录标注历史范围，避免旧的 Qt Quick 软件渲染和 UNIX-only 音频说明被当作当前配置。
- 主分支同步已验证的 0.06 实现与文档。rootfs 构建保持手动，按实际脚本类型执行检查，避免将 Python 当作 Bash。
- 发布流程只取既有成功构建、验证 APK 哈希与证书后上传；文档更新不重新签名或修改已分发 APK。
- 历史兼容组件和 JNI 供体依赖 Actions 保留期，长期归档仍需后续维护；此次 APK Release 不消除源码重建的供体保留期限制。
