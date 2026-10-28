# ArchOHall Android 0.06（实验版）

面向 ARM64 Android 8.0+ 的 Arch Linux ARM + Plasma Mobile 实验版本。包名 `com.archoh`，versionCode 8，沿用固定签名，可覆盖相同签名的旧版本。

## 安装与升级

下载附件 `ArchOHall-0.06-arm64.apk`。已有容器：停止桌面 → 覆盖安装 → 点击 **应用桌面修复与 Android 桥接**，联网补齐组件 → 重新启动桌面。保留容器和应用，不需要重新导入镜像。首次安装需另行准备兼容的 ArchOHall 镜像；本次不发布 rootfs 镜像。

## 本版内容

- 合并 150% 缩放、KWin QPainter / Plasma llvmpipe OpenGL、默认应用菜单缓存和 Shell 环境修复。
- 修正电池显示、设置模块路由、键盘默认语言及容器模拟 sudo 配置。
- 加入带 cookie 认证的本机音频连接、Linux 内部亮度/媒体音量滑块和反向文字剪贴板通道。
- 通知与任务名称改为 ArchOHall，增加返回控制台入口；KDE 方框键提供临时应用窗口列表。
- 更新器备份受管理文件，拒绝更改已安装的软件包版本。

## 验证和限制

APK 来自 [成功构建 40523515699](https://github.com/villager1314/ArchOHall/actions/runs/40523515699)，源码提交 `81e67eec69c47bc5689fa0a42a4652d1e64f87d8`。桥接测试、Android 单元测试、固定签名及 X11 接口/打包检查通过。

实际扬声器输出、蓝牙路由、反向文字剪贴板、滑块、窗口激活和完整 sudo 调用仍需手机验证。当前多任务为临时窗口列表，原生 Plasma Mobile 多任务恢复尚未实施。未提供图片/文件剪贴板、完整终端功能键布局、Discover 商店或已验证的 GPU 加速。

附件包含 `SHA256SUMS` 与 `runtime-manifest.json`。APK SHA-256：

```text
e4310fa9a9c28b2ed26380729a6aa7bb8c7d5e9ce60265c2c709e427b2901484
```

开发复盘另见 [测试版开发记录](https://github.com/villager1314/ArchOHall/blob/main/docs/development/ANDROID-EXPERIMENTS.md)，不放在仓库首页。Release 标签包含后续文档与 CI 整理；发布流程会检查应用源码与上述原构建提交一致。文档与发布流程整理没有改变这份已验证 APK。
