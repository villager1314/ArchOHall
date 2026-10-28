package com.termux.app.archohall;

import android.content.Context;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;

public final class GuestCompatibility {
    public static void install(Context c, OfflineRuntime.Monitor monitor) throws Exception {
        File work = new File(c.getFilesDir(), "compat-work");
        SafeTar.deleteTree(work); work.mkdirs();
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            org.json.JSONObject metadata;
            try (InputStream in = c.getAssets().open("native-component.json")) {
                ByteArrayOutputStream data = new ByteArrayOutputStream();
                byte[] bytes = new byte[4096]; int length;
                while ((length = in.read(bytes)) != -1) data.write(bytes, 0, length);
                metadata = new org.json.JSONObject(new String(data.toByteArray(), StandardCharsets.UTF_8));
            }
            String expectedHash = metadata.getString("sha256");
            if (!expectedHash.matches("[0-9a-f]{64}")) throw new IOException("无效的原生组件清单");
            try (OutputStream out = new FileOutputStream(new File(work, "native-component.json"))) {
                out.write(metadata.toString().getBytes(StandardCharsets.UTF_8));
            }
            long total = -1, count = 0;
            try (InputStream in = c.getAssets().open("desktop-compat.tar.xz"); OutputStream out = new FileOutputStream(new File(work, "desktop-compat.tar.xz"))) {
                byte[] buffer = new byte[131072]; int n;
                while ((n = in.read(buffer)) != -1) {
                    if (monitor.cancelled()) throw new IOException("已取消");
                    digest.update(buffer, 0, n); out.write(buffer, 0, n); count += n;
                    monitor.phase("读取桌面兼容组件", count, total, "完全离线");
                }
            }
            if (!expectedHash.equals(OfflineRuntime.hex(digest.digest()))) throw new IOException("内置桌面兼容组件校验失败");
            for (String name : new String[]{"install", "mobile", "session"}) {
                try (InputStream in = c.getAssets().open("compat-" + name); OutputStream out = new FileOutputStream(new File(work, name))) {
                    byte[] b = new byte[8192]; int n; while ((n = in.read(b)) != -1) out.write(b, 0, n);
                }
            }
            monitor.phase("安装桌面兼容组件", 0, -1, "保留原容器和原启动脚本");
            ProcessBuilder builder = new ProcessBuilder(new File(OfflineRuntime.prefix(c), "bin/bash").getAbsolutePath(), new File(work, "install").getAbsolutePath()).redirectErrorStream(true);
            builder.environment().clear(); builder.environment().putAll(OfflineRuntime.environment(c));
            builder.environment().put("ARCHOHALL_ROOTFS", new File(c.getFilesDir(), "containers/archohall").getAbsolutePath());
            builder.environment().put("ARCHOHALL_COMPAT_WORK", work.getAbsolutePath());
            Process child = builder.start(); monitor.process(child);
            try (BufferedReader reader = new BufferedReader(new InputStreamReader(child.getInputStream(), StandardCharsets.UTF_8))) {
                String line; while ((line = reader.readLine()) != null) monitor.log(line);
            }
            int rc = child.waitFor(); monitor.process(null);
            if (rc != 0) throw new IOException("安装兼容组件失败，退出码 " + rc + "；请查看操作日志");
        } finally { SafeTar.deleteTree(work); }
    }
}
