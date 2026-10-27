package com.termux.app.archohall;

import android.content.Context;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;

public final class HostRuntimeFixes {
    private static String quote(String s) { return "'" + s.replace("'", "'\\''") + "'"; }
    public static synchronized void apply(Context context) throws IOException {
        File pointer=new File(context.getFilesDir(), "apk-path");
        apply(OfflineRuntime.prefix(context), pointer);
        File launch=new File(context.getFilesDir(), "home/.archohall/launch.sh");
        if(launch.isFile()) {
            String before=new String(Files.readAllBytes(launch.toPath()),StandardCharsets.UTF_8);
            String after=rewriteLaunch(before,pointer.getAbsolutePath());
            if(!after.equals(before)) {
                Path backup=new File(launch.getParentFile(),"launch.sh.before-004").toPath();
                if(!Files.exists(backup))Files.copy(launch.toPath(),backup);
                atomic(launch,after);
            }
        }
    }
    public static synchronized void apply(File prefix, File apkPath) throws IOException {
        File am = new File(prefix, "bin/am");
        if (!am.isFile()) return;
        String original = new String(Files.readAllBytes(am.toPath()), StandardCharsets.UTF_8);
        String updated = wrapAm(original, prefix.getAbsolutePath(), apkPath.getAbsolutePath());
        if (!updated.equals(original)) {
            Path backup = new File(prefix, "bin/am.before-004").toPath();
            if (!Files.exists(backup)) Files.copy(am.toPath(), backup);
            atomic(am, updated);
        }
        File amApk = new File(prefix, "libexec/termux-am/am.apk");
        if (amApk.isFile()) OfflineRuntime.permissions(amApk.toPath(), 0400);
        File x11 = new File(prefix, "bin/termux-x11");
        String script = "#!" + prefix + "/bin/bash\nset -eu\nexport PREFIX=" + quote(prefix.getAbsolutePath()) + "\n" +
            "export TMPDIR=\"$PREFIX/tmp\" XKB_CONFIG_ROOT=\"$PREFIX/share/X11/xkb\"\n" +
            "export CLASSPATH=\"$(cat " + quote(apkPath.getAbsolutePath()) + ")\"\nunset LD_LIBRARY_PATH LD_PRELOAD\n" +
            "exec /system/bin/app_process /system/bin --nice-name=archohall-x11 com.termux.x11.CmdEntryPoint \"$@\"\n";
        if (!x11.isFile() || !new String(Files.readAllBytes(x11.toPath()), StandardCharsets.UTF_8).equals(script)) {
            Path backup = new File(prefix, "bin/termux-x11.before-004").toPath();
            if (x11.isFile() && !Files.exists(backup)) Files.copy(x11.toPath(), backup);
            atomic(x11, script);
        }
        String repair = "#!" + prefix + "/bin/bash\nset -eu\nexport PREFIX=" + quote(prefix.getAbsolutePath()) + "\n" +
            "export CLASSPATH=\"$(cat " + quote(apkPath.getAbsolutePath()) + ")\"\nunset LD_LIBRARY_PATH LD_PRELOAD\n" +
            "exec /system/bin/app_process /system/bin com.termux.app.archohall.HostRuntimeFixes\n";
        atomic(new File(prefix, "bin/archohall-repair-host-tools"), repair);
        File conf = new File(prefix, "etc/apt/apt.conf.d/99archohall-hostfix");
        conf.getParentFile().mkdirs();
        Files.write(conf.toPath(), ("DPkg::Post-Invoke {\"" + prefix + "/bin/archohall-repair-host-tools\";};\n").getBytes(StandardCharsets.UTF_8));
    }
    static String wrapAm(String source, String prefix, String apkPath) throws IOException {
        if (source.contains("com.termux.app.archohall.AmCompat")) return source;
        boolean entry = source.contains("com.termux.termuxam.Am") || source.contains("com.archoh.compat.TermuxAmLauncher");
        if (!entry || !source.contains("export CLASSPATH=")) throw new IOException("无法识别内置 am 启动脚本，原文件已保留");
        StringBuilder result = new StringBuilder();
        for (String line : source.split("\n")) {
            if (line.startsWith("export CLASSPATH=")) {
                result.append("export PREFIX=").append(quote(prefix)).append('\n');
                result.append("export CLASSPATH=\"$AM_APK_PATH:$(cat ").append(quote(apkPath)).append(")\"\n");
            } else result.append(line.replace("com.termux.termuxam.Am", "com.termux.app.archohall.AmCompat")
                .replace("com.archoh.compat.TermuxAmLauncher", "com.termux.app.archohall.AmCompat")).append('\n');
        }
        return result.toString();
    }
    static String rewriteLaunch(String source,String pointer) {
        StringBuilder result=new StringBuilder();
        for(String line:source.split("\n")) {
            if(line.contains("com.termux.x11.CmdEntryPoint")) {
                int from=line.indexOf("CLASSPATH="),end=line.indexOf(" /system/bin/app_process",Math.max(from,0));
                if(from>=0&&end>from)line=line.substring(0,from)+"CLASSPATH=\"$(cat "+quote(pointer)+")\""+line.substring(end);
            }
            result.append(line).append('\n');
        }
        return result.toString();
    }
    private static void atomic(File target, String text) throws IOException {
        File stage = new File(target.getParentFile(), target.getName() + ".004-new");
        Files.write(stage.toPath(), text.getBytes(StandardCharsets.UTF_8));
        OfflineRuntime.permissions(stage.toPath(), 0700);
        Files.move(stage.toPath(), target.toPath(), StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
    }
    public static void main(String[] args) throws Exception {
        String prefix = System.getenv("PREFIX");
        if (!"/data/data/com.archoh/files/usr".equals(prefix) && !"/data/user/0/com.archoh/files/usr".equals(prefix)) throw new IOException("Invalid ArchOHall prefix");
        apply(new File(prefix), new File(new File(prefix).getParentFile(), "apk-path"));
    }
}
