# ArchOHall Android 0.07（实验版）

本版将 0.06 的临时窗口列表替换为 **Plasma Mobile 原生 Mobile Task Switcher**，并在同一 Release 提供匹配的 ARM64 rootfs。

## 本版更改

- 删除临时多任务 QML 和自建 D-Bus 接收器；升级时停用已知旧文件并保留备份。
- 启用 KWin 原生全局快捷键和 Plasma Mobile 上游任务切换 effect。
- 使用匹配的 KWin 6.8.1 与 llvmpipe OpenGL，通过 SHM 读回兼容无 DRM 的 X11 显示环境。
- APK、原生组件与 rootfs 使用同一依赖清单；安装前与启动时检查版本，拒绝不匹配的组件混装。
- 保留固定包名 `com.archoh`、分发签名、720×1280 默认分辨率与 150% 缩放；versionCode 9。

## 下载与使用

下载 `ArchOHall-0.07-arm64.apk` 和同一页面的 `archohall-aarch64.tar.xz`。若镜像被拆为 `.part000` 等分卷，需要全部下载并校验，再按顺序合并为 `archohall-aarch64.tar.xz`；单个分卷不能直接导入。

```bash
sha256sum -c rootfs-SHA256SUMS
# 仅在下载的是分卷时执行：
cat archohall-aarch64.tar.xz.part[0-9][0-9][0-9] > archohall-aarch64.tar.xz
```

已有容器：停止桌面 → 覆盖安装 APK → 执行“应用桌面修复与 Android 桥接”。检查通过可继续使用原容器；若提示依赖不匹配，应先备份/迁移个人文件，再导入本页配套 rootfs。导入器保留旧容器备份并占用额外空间。

首次安装：展开 APK 内置运行环境 → 选择本地 rootfs 导入 → 启动 Plasma Mobile。配套镜像已经包含桌面与桥接依赖。

## 附件与验证范围

附件包含 APK、rootfs、各自 SHA-256、运行环境清单、原生组件版本清单，以及 KWin 上游源码和补丁。发布流水线要求原生 effect 经真实快捷键完成打开/关闭测试，并通过桥接、Android、签名、JNI 和归档检查。

这仍是实验版：Android 实际触摸切换、软件渲染性能、声音和剪贴板需在手机上验证。采用原生界面不代表已经实现硬件 GPU 加速。

[实现与迁移说明](https://github.com/villager1314/ArchOHall/blob/main/diagnostics/ANDROID-007.md) · [开发复盘](https://github.com/villager1314/ArchOHall/blob/main/docs/development/ANDROID-EXPERIMENTS.md)
