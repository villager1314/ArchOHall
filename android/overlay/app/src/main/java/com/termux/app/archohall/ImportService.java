package com.termux.app.archohall;

import android.app.*;
import android.content.*;
import android.database.Cursor;
import android.net.Uri;
import android.os.*;
import android.provider.OpenableColumns;
import androidx.core.app.NotificationCompat;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.security.*;
import java.text.SimpleDateFormat;
import java.util.*;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.zip.*;

public final class ImportService extends Service implements OfflineRuntime.Monitor {
    public static final String PREPARE="prepare", IMPORT="import", CANCEL="cancel";
    private static final int NOTICE=4101;
    private final AtomicBoolean cancelled=new AtomicBoolean();
    private volatile Process child;
    private BufferedWriter log;
    private PowerManager.WakeLock wake;
    private long lastNotice;
    private final OperationState state=OperationState.INSTANCE;
    public static void start(Context c,String action,Uri uri){
        Intent intent=new Intent(c,ImportService.class).setAction(action);
        if(uri!=null)intent.setData(uri).addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
        if(Build.VERSION.SDK_INT>=26)c.startForegroundService(intent);else c.startService(intent);
    }
    @Override public IBinder onBind(Intent intent){return null;}
    @Override public void onCreate(){super.onCreate();NotificationManager manager=getSystemService(NotificationManager.class);manager.createNotificationChannel(new NotificationChannel("import","容器导入",NotificationManager.IMPORTANCE_LOW));}
    @Override public int onStartCommand(Intent intent,int flags,int startId){
        if(intent==null){stopSelf();return START_NOT_STICKY;}
        if(CANCEL.equals(intent.getAction())){cancelled.set(true);Process process=child;if(process!=null)process.destroyForcibly();if(!state.busy)stopSelf();return START_NOT_STICKY;}
        if(state.busy)return START_NOT_STICKY;
        cancelled.set(false);state.busy=true;state.phase="准备离线环境";state.progress=-1;state.changed(true);
        startForeground(NOTICE,notification());
        wake=((PowerManager)getSystemService(POWER_SERVICE)).newWakeLock(PowerManager.PARTIAL_WAKE_LOCK,"ArchOHall:import");wake.acquire(60*60*1000L);
        Uri source=intent.getData();
        new Thread(()->runOperation(source),"archohall-import").start();return START_NOT_STICKY;
    }
    private Notification notification(){
        PendingIntent open=PendingIntent.getActivity(this,0,new Intent(this,ArchActivity.class),PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE);
        PendingIntent cancel=PendingIntent.getService(this,1,new Intent(this,ImportService.class).setAction(CANCEL),PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE);
        return new NotificationCompat.Builder(this,"import").setSmallIcon(com.termux.R.drawable.archohall_icon).setContentTitle("ArchOHall · "+state.phase).setContentText(state.detail).setContentIntent(open).setOnlyAlertOnce(true).setOngoing(true).setProgress(1000,Math.max(0,state.progress),state.progress<0).addAction(0,"取消",cancel).build();
    }
    @Override public void phase(String name,long done,long total,String detail) throws IOException {
        if(cancelled())throw new IOException("已取消");
        state.phase=name;state.progress=total>0?(int)Math.min(999,done*1000/total):-1;state.detail=detail+(total>0?"\n"+size(done)+" / "+size(total):done>0?"\n"+size(done):"");state.changed(false);
        long now=SystemClock.uptimeMillis();if(now-lastNotice>1000){lastNotice=now;getSystemService(NotificationManager.class).notify(NOTICE,notification());if(log!=null)log.flush();}
    }
    @Override public void log(String line) throws IOException {
        String clean=line.replace('\0','?');String stamp=new SimpleDateFormat("HH:mm:ss",Locale.ROOT).format(new Date());
        String full=stamp+"  "+clean;state.log(full);if(log!=null){log.write(full);log.newLine();}state.changed(false);
    }
    @Override public boolean cancelled(){return cancelled.get();}
    @Override public void process(Process process){child=process;}
    private static String size(long bytes){return String.format(Locale.ROOT,"%.1f MiB",bytes/1048576.0);}
    private void runOperation(Uri source){
        File work=new File(getFilesDir(),"import-work");
        try{
            log=new BufferedWriter(new OutputStreamWriter(new FileOutputStream(new File(getFilesDir(),"import.log"),true),StandardCharsets.UTF_8));
            log("──── ArchOHall 0.01 ────");
            if(SessionController.running(this))throw new IOException("请先停止桌面，再导入容器");
            OfflineRuntime.ensure(this,this);state.runtimeReady=true;
            if(source!=null){SafeTar.deleteTree(work);work.mkdirs();importRootfs(source,work);}
            state.phase=source==null?"离线环境已就绪":"导入完成";state.detail=source==null?"请选择本地 ArchOHall 导入包":"可以启动 Plasma Mobile";state.progress=1000;log(state.phase);
        }catch(Exception error){state.phase=cancelled()?"已取消":"操作失败";state.detail=error.getMessage()==null?error.toString():error.getMessage();state.progress=-1;try{log(state.phase+"："+state.detail);StringWriter trace=new StringWriter();error.printStackTrace(new PrintWriter(trace));log(trace.toString());}catch(IOException ignored){} }
        finally{
            child=null;
            if(source!=null){try{getContentResolver().releasePersistableUriPermission(source,Intent.FLAG_GRANT_READ_URI_PERMISSION);}catch(SecurityException ignored){}}
            try{SafeTar.deleteTree(work);}catch(IOException error){try{log("临时文件清理未完成："+error.getMessage());}catch(IOException ignored){}}
            try{if(log!=null)log.close();}catch(IOException ignored){}log=null;
            if(wake!=null&&wake.isHeld())wake.release();
            state.runtimeReady=OfflineRuntime.ready(this);state.installed=new File(getFilesDir(),"containers/archohall/.archohall-installed").isFile();state.busy=false;state.changed(true);stopForeground(true);stopSelf();
        }
    }
    private long documentSize(Uri uri){
        try(Cursor cursor=getContentResolver().query(uri,new String[]{OpenableColumns.SIZE},null,null,null)){if(cursor!=null&&cursor.moveToFirst()&&!cursor.isNull(0))return cursor.getLong(0);}catch(Exception ignored){}return -1;
    }
    private void copy(InputStream in,File out,String phase,long total) throws Exception {
        long count=0;byte[] buffer=new byte[131072];int n;
        try(OutputStream stream=new FileOutputStream(out)){
            while((n=in.read(buffer))!=-1){if(count+n>8L*1024*1024*1024)throw new IOException("导入包超过 8 GiB");stream.write(buffer,0,n);count+=n;phase(phase,count,total,"正在读取本地文件");}
        }
    }
    private String checksum(File file) throws Exception {
        MessageDigest digest=MessageDigest.getInstance("SHA-256");long count=0;byte[] buffer=new byte[131072];int n;
        try(InputStream in=new FileInputStream(file)){while((n=in.read(buffer))!=-1){digest.update(buffer,0,n);count+=n;phase("校验导入包",count,file.length(),"SHA-256");}}return OfflineRuntime.hex(digest.digest());
    }
    private void importRootfs(Uri uri,File work) throws Exception {
        long total=documentSize(uri);
        if(total>0&&new StatFs(work.getAbsolutePath()).getAvailableBytes()<total+256L*1024*1024)throw new IOException("空间不足，无法复制导入包");
        File input=new File(work,"input.bin");
        try(InputStream in=getContentResolver().openInputStream(uri)){if(in==null)throw new IOException("无法打开所选文件");copy(in,input,"复制导入包",total);}
        File archive=input;String expected=null;
        try(RandomAccessFile file=new RandomAccessFile(input,"r")){
            if(file.length()>=4&&file.readInt()==0x504b0304){
                archive=new File(work,"rootfs.tar.xz");
                try(ZipFile zip=new ZipFile(input)){
                    ZipEntry payload=null,sums=null;Enumeration<? extends ZipEntry> entries=zip.entries();
                    while(entries.hasMoreElements()){
                        ZipEntry entry=entries.nextElement();String basename=entry.getName().substring(entry.getName().lastIndexOf('/')+1);
                        if(basename.equals("archohall-aarch64.tar.xz")){if(payload!=null)throw new IOException("ZIP 中存在多个 rootfs");payload=entry;}
                        if(basename.equals("SHA256SUMS"))sums=entry;
                    }
                    if(payload==null)throw new IOException("ZIP 中没有 archohall-aarch64.tar.xz；分卷请先合并");
                    if(sums!=null){try(InputStream in=zip.getInputStream(sums)){String text=new String(OfflineRuntime.readSmall(in,1024*1024),StandardCharsets.UTF_8);for(String line:text.split("\n")){String[] parts=line.trim().split("\\s+",2);if(parts.length==2&&parts[0].matches("[0-9a-fA-F]{64}")&&parts[1].replaceFirst("^[*]", "").replaceFirst("^\\./", "").equals("archohall-aarch64.tar.xz"))expected=parts[0].toLowerCase(Locale.ROOT);}}}
                    if(payload.getSize()>0&&new StatFs(work.getAbsolutePath()).getAvailableBytes()<payload.getSize()+256L*1024*1024)throw new IOException("空间不足，无法展开 ZIP");
                    try(InputStream in=zip.getInputStream(payload)){copy(in,archive,"展开 ZIP",payload.getSize());}
                }
            }
        }
        if(archive!=input)Files.delete(input.toPath());
        String hash=checksum(archive);log("rootfs SHA-256："+hash);
        if(expected!=null&&!expected.equals(hash))throw new IOException("rootfs 校验不匹配，请重新下载导入包");
        log(expected==null?"独立 rootfs：已记录本地校验值":"导入包 SHA-256 校验通过");
        long expanded=SafeTar.expandedSize(archive);log("预计解压数据："+size(expanded));
        if(new StatFs(work.getAbsolutePath()).getAvailableBytes()<expanded+256L*1024*1024)throw new IOException("解压空间不足，需要额外约 "+size(expanded));
        File staged=new File(work,"rootfs");final String[] previous={""};
        SafeTar.extract(archive,staged,(path,files,bytes,all)->{
            phase("解压 rootfs",bytes,all,"已处理 "+files+" 项 · "+path);
            if(!previous[0].equals(path)){previous[0]=path;log(path);}
        });
        phase("检查容器",0,-1,"检查架构、桌面文件和用户");SafeTar.validate(staged);
        Files.write(new File(staged,".archohall-installed").toPath(),hash.getBytes(StandardCharsets.US_ASCII));
        if(cancelled())throw new IOException("已取消");
        File parent=new File(getFilesDir(),"containers");parent.mkdirs();File current=new File(parent,"archohall");File backup=new File(parent,"backup-"+System.currentTimeMillis());
        boolean hadCurrent=current.exists();
        if(hadCurrent&&!current.renameTo(backup))throw new IOException("无法保留现有容器");
        if(!staged.renameTo(current)){if(hadCurrent)backup.renameTo(current);throw new IOException("无法启用新容器，已尝试恢复旧容器");}
        if(hadCurrent)log("原容器保留在应用私有目录："+backup.getName());
        log("容器完整性检查通过，已启用");
    }
}
