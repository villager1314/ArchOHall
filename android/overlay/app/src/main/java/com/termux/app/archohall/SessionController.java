package com.termux.app.archohall;

import android.content.*;
import android.net.Uri;
import com.termux.app.TermuxService;
import com.termux.app.TermuxApplication;
import com.termux.x11.Prefs;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;

public final class SessionController {
    private static long startingUntil;
    private static File directory(Context c){return new File(c.getFilesDir(),"home/.archohall");}
    private static String quote(String value){return "'"+value.replace("'","'\\''")+"'";}
    public static boolean running(Context c){
        if(android.os.SystemClock.uptimeMillis()<startingUntil)return true;
        try{
            File pid=new File(directory(c),"session.pid");if(!pid.isFile())return false;
            String value=new String(Files.readAllBytes(pid.toPath()),StandardCharsets.US_ASCII).trim();if(!value.matches("[1-9][0-9]{0,8}"))return false;
            byte[] cmd=Files.readAllBytes(new File("/proc/"+value+"/cmdline").toPath());
            return new String(cmd,StandardCharsets.UTF_8).contains(new File(directory(c),"launch.sh").getAbsolutePath());
        }catch(IOException error){return false;}
    }
    public static void start(Context c,int width,int height) throws Exception {
        if(running(c))throw new IOException("桌面已在运行，请直接打开桌面显示");
        File dir=directory(c);dir.mkdirs();new File(dir,"stop-requested").delete();
        String prefix=OfflineRuntime.prefix(c).getAbsolutePath();String root=new File(c.getFilesDir(),"containers/archohall").getAbsolutePath();
        new File(root,"run/archohall-host").mkdirs();
        String hostBridge=AndroidHostBridge.directory(c).getAbsolutePath();
        Prefs prefs=((TermuxApplication)c.getApplicationContext()).builtInPrefs;
        prefs.displayResolutionMode.put("custom");prefs.displayResolutionCustom.put(width+"x"+height);prefs.touchMode.put("3");prefs.fullscreen.put(true);prefs.hideCutout.put(true);prefs.displayStretch.put(true);prefs.adjustResolution.put(false);
        String script="#!/"+prefix.substring(1)+"/bin/bash\nset -euo pipefail\n"+
            "export PREFIX="+quote(prefix)+"\nexport HOME="+quote(new File(c.getFilesDir(),"home").getAbsolutePath())+"\n"+
            "export PATH=\"$PREFIX/bin:/system/bin:/system/xbin\" TMPDIR=\"$PREFIX/tmp\" PROOT_TMP_DIR=\"$PREFIX/tmp\"\n"+
            "TASK_DIR="+quote(dir.getAbsolutePath())+"\nROOTFS="+quote(root)+"\nHOST_BRIDGE="+quote(hostBridge)+"\nmkdir -p \"$PREFIX/tmp\"\n"+
            "echo $$ > \"$TASK_DIR/session.pid\"\n[[ ! -f \"$TASK_DIR/session.log\" ]] || mv -f \"$TASK_DIR/session.log\" \"$TASK_DIR/session.previous.log\"\nexec > >(tee \"$TASK_DIR/session.log\") 2>&1\necho \"ArchOHall session $(date -Iseconds)\"\n"+
            "x11_pid=\"\"\nguest_pid=\"\"\npulse_pid=\"\"\npulse_tcp_module=\"\"\ncleanup() { trap - EXIT INT TERM; [[ -z $pulse_tcp_module ]] || pactl unload-module \"$pulse_tcp_module\" 2>/dev/null || true; [[ -z $guest_pid ]] || kill -TERM \"$guest_pid\" 2>/dev/null || true; [[ -z $x11_pid ]] || kill -TERM \"$x11_pid\" 2>/dev/null || true; [[ -z $pulse_pid ]] || kill -TERM \"$pulse_pid\" 2>/dev/null || true; rm -f \"$TASK_DIR/session.pid\"; }\ntrap cleanup EXIT INT TERM\n"+
            "[[ ! -e \"$TASK_DIR/stop-requested\" ]] || exit 0\n"+
            "export XKB_CONFIG_ROOT=\"$PREFIX/share/X11/xkb\"\n"+
            "env -u LD_LIBRARY_PATH -u LD_PRELOAD CLASSPATH=\"$(cat \"$PREFIX/../apk-path\")\" /system/bin/app_process /system/bin --nice-name=archohall-x11 com.termux.x11.CmdEntryPoint :0 &\nx11_pid=$!\n"+
            "ready=0\nfor ((attempt=0;attempt<100;attempt++)); do\n [[ ! -e \"$TASK_DIR/stop-requested\" ]] || exit 0\n kill -0 \"$x11_pid\" 2>/dev/null || { echo 'X11 server exited'; exit 1; }\n if [[ -S \"$PREFIX/tmp/.X11-unix/X0\" ]] && env -u LD_PRELOAD proot --link2symlink -r \"$ROOTFS\" -b /dev -b /proc -b \"$PREFIX/tmp:/tmp\" -w / /usr/bin/env -i PATH=/usr/bin:/bin DISPLAY=:0 /usr/bin/xdpyinfo >/dev/null 2>&1; then ready=1; break; fi\n sleep 0.1\ndone\n((ready==1)) || { echo 'X11 did not answer a client connection'; exit 1; }\necho 'X11 client connection verified'\n"+
            readAsset(c,"host-audio.sh")+"\n"+
            "unset LD_PRELOAD\nextra=()\nif proot --help 2>&1 | grep -q -- '--sysvipc'; then extra+=(--sysvipc); fi\nif proot --help 2>&1 | grep -q -- '--kill-on-exit'; then extra+=(--kill-on-exit); fi\n"+
            "base=(--link2symlink \"${extra[@]}\" -r \"$ROOTFS\" -b /dev -b /proc -b /sys -b \"$PREFIX/tmp:/tmp\" -b \"$HOST_BRIDGE:/run/archohall-host\" -b \"$TASK_DIR/pulse-cookie:/tmp/archohall-pulse-cookie\")\n"+
            "proot -0 \"${base[@]}\" -w /root /usr/bin/env -i HOME=/root PATH=/usr/local/sbin:/usr/local/bin:/usr/bin:/bin TERM=xterm-256color LANG=zh_CN.UTF-8 /usr/local/bin/archohall-init\n"+
            "if [[ -n $ARCHOHALL_GUEST_PULSE_SERVER ]]; then\n proot -i 1000:1000 \"${base[@]}\" -w /home/arch /usr/bin/env -i HOME=/home/arch PATH=/usr/bin:/bin PULSE_SERVER=\"$ARCHOHALL_GUEST_PULSE_SERVER\" PULSE_COOKIE=/tmp/archohall-pulse-cookie /usr/bin/pactl info >> \"$TASK_DIR/audio.log\" 2>&1 && echo 'Linux audio client authenticated' || echo 'Linux audio client failed; see audio.log'\nfi\n"+
            "[[ ! -e \"$TASK_DIR/stop-requested\" ]] || exit 0\n"+
            "proot -i 1000:1000 \"${base[@]}\" -w /home/arch /usr/bin/env -i HOME=/home/arch USER=arch LOGNAME=arch SHELL=/bin/bash PATH=/usr/local/sbin:/usr/local/bin:/usr/bin:/bin TERM=xterm-256color LANG=zh_CN.UTF-8 DISPLAY=:0 PULSE_SERVER=\"${ARCHOHALL_GUEST_PULSE_SERVER:-unix:/tmp/archohall-pulse.sock}\" PULSE_COOKIE=/tmp/archohall-pulse-cookie PULSE_LATENCY_MSEC=60 ARCHOHALL_RENDERER=software ARCHOHALL_WIDTH="+width+" ARCHOHALL_HEIGHT="+height+" /usr/local/bin/archohall-mobile &\nguest_pid=$!\nwait \"$guest_pid\"\n";
        File launch=new File(dir,"launch.sh");Files.write(launch.toPath(),script.getBytes(StandardCharsets.UTF_8));launch.setExecutable(true,true);
        startingUntil=android.os.SystemClock.uptimeMillis()+7000;
        execute(c,launch.getAbsolutePath(),"ArchOHall Plasma Mobile");
    }
    public static void stop(Context c) throws Exception {
        startingUntil=0;File dir=directory(c);dir.mkdirs();Files.write(new File(dir,"stop-requested").toPath(),new byte[]{1});
        String prefix=OfflineRuntime.prefix(c).getAbsolutePath();
        String script="#!/"+prefix.substring(1)+"/bin/bash\nset -eu\nPID_FILE="+quote(new File(dir,"session.pid").getAbsolutePath())+"\nif [[ -f $PID_FILE ]]; then pid=$(cat \"$PID_FILE\"); if [[ $pid =~ ^[1-9][0-9]*$ ]] && tr '\\0' ' ' < \"/proc/$pid/cmdline\" | grep -Fq -- "+quote(new File(dir,"launch.sh").getAbsolutePath())+"; then kill -TERM -- \"-$pid\" 2>/dev/null || kill -TERM \"$pid\"; fi; fi\n";
        File stop=new File(dir,"stop.sh");Files.write(stop.toPath(),script.getBytes(StandardCharsets.UTF_8));execute(c,stop.getAbsolutePath(),"停止 ArchOHall");
    }
    static Intent executionIntent(Context c,String script,String label){
        Intent i=new Intent(c,TermuxService.class).setAction("com.archoh.service_execute");
        i.setData(Uri.fromFile(new File(OfflineRuntime.prefix(c),"bin/bash")));
        i.putExtra("com.archoh.execute.arguments",new String[]{"--noprofile","--norc",script});i.putExtra("com.archoh.execute.cwd",new File(c.getFilesDir(),"home").getAbsolutePath());
        i.putExtra("com.archoh.execute.background",true);i.putExtra("com.archoh.execute.session_action","2");i.putExtra("com.archoh.execute.command_label",label);return i;
    }
    private static String readAsset(Context c,String name) throws IOException {try(InputStream in=c.getAssets().open(name)){return new String(OfflineRuntime.readSmall(in,65536),StandardCharsets.UTF_8);}}
    private static void execute(Context c,String script,String label){c.startService(executionIntent(c,script,label));}
}
