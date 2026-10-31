package app.polarbear

import android.app.*
import android.content.Intent
import android.os.Build
import android.view.Gravity
import android.widget.*
import java.util.concurrent.atomic.AtomicBoolean

/** Android-owned debug entry points, independent of Plasma/Wayland health. */
object ArchDebug {
    private const val EXTRA = "archohall_debug_action"
    private const val CHANNEL = "archohall-debug"
    private const val ID = 2007
    private const val BUILD = "@ARCHOHALL_BUILD@"
    private val busy = AtomicBoolean(false)
    @JvmStatic private external fun nativeCommand(command: String, root: Boolean): String

    fun attach(activity: PortalActivity) {
        val host = activity.window.decorView as? android.view.ViewGroup ?: return
        if (host.findViewWithTag<android.view.View>("arch-debug") == null) {
            val button = Button(activity).apply {
                text = "调试"; tag = "arch-debug"; alpha = 0.85f
                contentDescription = "ArchOHall2 调试与诊断"
                setOnClickListener { show(activity) }
            }
            val size = activity.resources.displayMetrics.density
            val params = android.widget.FrameLayout.LayoutParams((72 * size).toInt(), (48 * size).toInt(), Gravity.TOP or Gravity.RIGHT)
            params.topMargin = (32 * size).toInt()
            host.addView(button, params)
        }
        publish(activity)
    }

    private fun action(activity: Activity, label: String, command: String, request: Int): Notification.Action {
        val intent = Intent(activity, PortalActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_CLEAR_TOP
            putExtra(EXTRA, command)
        }
        val pending = PendingIntent.getActivity(activity, request, intent, PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
        return Notification.Action.Builder(android.R.drawable.ic_menu_manage, label, pending).build()
    }

    fun publish(activity: PortalActivity) {
        try {
            val manager = activity.getSystemService(android.content.Context.NOTIFICATION_SERVICE) as NotificationManager
            if (Build.VERSION.SDK_INT >= 26) manager.createNotificationChannel(NotificationChannel(CHANNEL, "ArchOHall2 调试", NotificationManager.IMPORTANCE_LOW))
            val builder = if (Build.VERSION.SDK_INT >= 26) Notification.Builder(activity, CHANNEL) else Notification.Builder(activity)
            val version = activity.packageManager.getPackageInfo(activity.packageName, 0).versionName
            manager.notify(ID, builder.setSmallIcon(activity.applicationInfo.icon)
                .setContentTitle("ArchOHall2 · 调试入口")
                .setContentText("$version · $BUILD · 无需进入 Linux 桌面")
                .setOngoing(true).setOnlyAlertOnce(true)
                .setContentIntent(action(activity, "调试", "debug", 2007).actionIntent)
                .addAction(action(activity, "导出诊断", "export", 2008))
                .addAction(action(activity, "调试命令", "debug", 2009))
                .addAction(action(activity, "控制页", "control", 2010)).build())
        } catch (error: Exception) { android.util.Log.w("ArchDebug", "Notification unavailable; on-screen button remains", error) }
    }

    fun handle(activity: PortalActivity, intent: Intent?) {
        val action = intent?.getStringExtra(EXTRA) ?: return
        intent.removeExtra(EXTRA)
        activity.window.decorView.post {
            when (action) {
                "export" -> ComposeOverlay.exportDiagnostics()
                "control" -> ComposeOverlay.showReturn(activity)
                else -> show(activity)
            }
        }
    }

    fun show(activity: PortalActivity) {
        val version = activity.packageManager.getPackageInfo(activity.packageName, 0)
        AlertDialog.Builder(activity).setTitle("ArchOHall2 调试 · ${version.versionName} (${version.longVersionCodeCompat()}) · $BUILD")
            .setItems(arrayOf("导出诊断包", "调试命令（arch / 容器 root）", "查看桌面日志", "返回控制页", "允许通知栏入口")) { _, which ->
                when (which) {
                    0 -> ComposeOverlay.exportDiagnostics()
                    1 -> console(activity, "id")
                    2 -> console(activity, "tail -n 100 /var/lib/localdesktop/session/kwin.log /var/lib/localdesktop/session/plasma.log")
                    3 -> ComposeOverlay.showReturn(activity)
                    4 -> { SetupService.requestNotificationPermission(activity); publish(activity) }
                }
            }.setNegativeButton("返回桌面", null).show()
    }

    private fun android.content.pm.PackageInfo.longVersionCodeCompat(): Long =
        if (Build.VERSION.SDK_INT >= 28) longVersionCode else versionCode.toLong()

    private fun console(activity: PortalActivity, initial: String) {
        val layout = LinearLayout(activity).apply { orientation = LinearLayout.VERTICAL; setPadding(20, 12, 20, 12) }
        val root = CheckBox(activity).apply { text = "容器 root（不是 Android root）" }
        val input = EditText(activity).apply { setText(initial); hint = "输入 Linux 命令（非交互，最长 20 秒）"; minLines = 2 }
        val output = TextView(activity).apply { setTextIsSelectable(true); typeface = android.graphics.Typeface.MONOSPACE; text = "命令在独立 shell 中运行；不保存 shell 会话。" }
        val scroll = ScrollView(activity).apply { addView(output) }
        layout.addView(root); layout.addView(input); layout.addView(scroll, LinearLayout.LayoutParams(-1, (240 * activity.resources.displayMetrics.density).toInt()))
        val dialog = AlertDialog.Builder(activity).setTitle("Linux 调试命令").setView(layout).setPositiveButton("执行", null).setNeutralButton("导出诊断") { _, _ -> ComposeOverlay.exportDiagnostics() }.setNegativeButton("关闭", null).create()
        dialog.setOnShowListener {
            dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener {
                if (!busy.compareAndSet(false, true)) { output.text = "已有命令正在执行，请稍候。"; return@setOnClickListener }
                val command = input.text.toString(); val asRoot = root.isChecked
                output.text = "执行中…（最多 20 秒）"
                Thread {
                    val result = try { nativeCommand(command, asRoot) } catch (error: Throwable) { "命令失败：$error" }
                    busy.set(false)
                    activity.runOnUiThread { if (dialog.isShowing) output.text = result }
                }.start()
            }
        }
        dialog.show()
    }
}
