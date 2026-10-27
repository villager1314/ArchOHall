package com.termux.app.archohall;

import android.content.Context;
import java.io.*;
import java.nio.file.*;
import java.util.*;
import java.util.zip.*;

/** Install only the versioned desktop-support files bundled by the APK. */
public final class GuestDesktopSupport {
    public static void install(Context c, OfflineRuntime.Monitor monitor) throws Exception {
        File root=new File(c.getFilesDir(),"containers/archohall");
        if(!new File(root,"usr/bin/kwin_wayland").isFile())throw new IOException("请先导入容器");
        String base=root.getCanonicalPath()+File.separator;
        monitor.phase("应用桌面桥接配置",0,-1,"备份原文件，保留现有容器和应用");
        long total=0;
        try(ZipInputStream zip=new ZipInputStream(c.getAssets().open("desktop-support.zip"))){
            ZipEntry entry;
            while((entry=zip.getNextEntry())!=null){
                if(monitor.cancelled())throw new IOException("已取消");
                String name=entry.getName();
                if(entry.isDirectory()||name.startsWith("/")||name.contains("..")||!name.startsWith("usr/local/"))throw new IOException("无效的桌面支持文件路径");
                File target=new File(root,name);
                if(!target.getCanonicalPath().startsWith(base))throw new IOException("桌面支持路径越界");
                File parent=target.getParentFile();if(!parent.mkdirs()&&!parent.isDirectory())throw new IOException("无法创建桌面支持目录");
                if(target.exists()&&!new File(target.getPath()+".before-support-005").exists())Files.copy(target.toPath(),new File(target.getPath()+".before-support-005").toPath());
                File temp=File.createTempFile(".support-",".tmp",parent);
                try{
                    try(OutputStream out=new FileOutputStream(temp)){byte[] b=new byte[65536];int n;while((n=zip.read(b))!=-1){total+=n;if(total>8388608)throw new IOException("桌面支持文件过大");out.write(b,0,n);}}
                    if(name.startsWith("usr/local/bin/"))temp.setExecutable(true,false);
                    Files.move(temp.toPath(),target.toPath(),StandardCopyOption.REPLACE_EXISTING);
                }finally{temp.delete();}
            }
        }
        run(c,monitor,"/usr/local/bin/archohall-install-tiles");
        monitor.phase("安装缺失的桌面组件",0,-1,"使用容器现有软件源；不自动升级 Qt/KDE");
        run(c,monitor,"/usr/local/bin/archohall-install-extras");
    }
    private static void run(Context c,OfflineRuntime.Monitor monitor,String script)throws Exception{
        String prefix=OfflineRuntime.prefix(c).getAbsolutePath();
        String root=new File(c.getFilesDir(),"containers/archohall").getAbsolutePath();
        List<String> args=Arrays.asList(prefix+"/bin/proot","--link2symlink","-0","-r",root,"-b","/dev","-b","/proc","-b",prefix+"/tmp:/tmp","-w","/root","/usr/bin/env","-i","HOME=/root","PATH=/usr/local/bin:/usr/bin:/bin","LANG=zh_CN.UTF-8","/bin/bash",script);
        ProcessBuilder builder=new ProcessBuilder(args).redirectErrorStream(true);
        builder.environment().clear();builder.environment().putAll(OfflineRuntime.environment(c));builder.environment().remove("LD_PRELOAD");
        Process child=builder.start();monitor.process(child);
        try(BufferedReader reader=new BufferedReader(new InputStreamReader(child.getInputStream(),java.nio.charset.StandardCharsets.UTF_8))){String line;while((line=reader.readLine())!=null)monitor.log(line);}
        int rc=child.waitFor();monitor.process(null);if(rc!=0)throw new IOException("组件安装未完成，退出码 "+rc+"；桥接脚本已备份，请查看日志");
    }
}
