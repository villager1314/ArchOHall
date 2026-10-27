package com.termux.app.archohall;

import android.content.Context;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.nio.file.attribute.PosixFilePermissions;
import java.security.MessageDigest;
import java.util.*;
import java.util.zip.*;
import org.json.JSONObject;

public final class OfflineRuntime {
    public interface Monitor { void phase(String name,long done,long total,String detail) throws IOException; void log(String line) throws IOException; boolean cancelled(); void process(Process process); }
    public static File prefix(Context c){return new File(c.getFilesDir(),"usr");}
    public static boolean ready(Context c){return new File(prefix(c),".archohall-runtime-001").isFile();}
    public static Map<String,String> environment(Context c){
        Map<String,String> env=new HashMap<>(System.getenv());
        String prefix=prefix(c).getAbsolutePath();
        env.put("PREFIX",prefix);env.put("HOME",new File(c.getFilesDir(),"home").getAbsolutePath());
        env.put("PATH",prefix+"/bin:/system/bin:/system/xbin");env.put("TMPDIR",prefix+"/tmp");
        env.put("LD_LIBRARY_PATH",prefix+"/lib");env.put("TERM","xterm-256color");env.put("LANG","en_US.UTF-8");env.put("SHELL",prefix+"/bin/bash");
        env.put("TERMUX_VERSION","0.118.3");env.put("TERMUX_APP__PACKAGE_NAME","com.archoh");env.put("TERMUX_APP__PREFIX",prefix);
        env.put("DEBIAN_FRONTEND","noninteractive");
        File exec=new File(prefix,"lib/libtermux-exec.so");
        if(exec.isFile())env.put("LD_PRELOAD",exec.getAbsolutePath());else env.remove("LD_PRELOAD");
        return env;
    }
    static byte[] readSmall(InputStream in,int limit) throws IOException {
        ByteArrayOutputStream out=new ByteArrayOutputStream();byte[] buffer=new byte[8192];int n;
        while((n=in.read(buffer))!=-1){if(out.size()+n>limit)throw new IOException("元数据过大");out.write(buffer,0,n);}return out.toByteArray();
    }
    static String hex(byte[] bytes){StringBuilder s=new StringBuilder();for(byte b:bytes)s.append(String.format(java.util.Locale.ROOT,"%02x",b&255));return s.toString();}
    static void permissions(Path path,int mode) throws IOException {
        StringBuilder s=new StringBuilder();for(int i=8;i>=0;i--)s.append((mode&(1<<i))==0?'-':"rwx".charAt((8-i)%3));
        Files.setPosixFilePermissions(path,PosixFilePermissions.fromString(s.toString()));
    }
    public static void ensure(Context c,Monitor monitor) throws Exception {
        if(android.os.Process.myUid()/100000!=0)throw new IOException("此版本请安装在安卓主用户中");
        if(ready(c)){TermuxMirror.apply(prefix(c));HostRuntimeFixes.apply(c);monitor.log("离线运行环境已就绪");return;}
        File files=c.getFilesDir(),prefix=prefix(c), stage=new File(files,"runtime-staging"), archive=new File(files,"runtime-payload.zip");
        JSONObject manifest;
        try(InputStream in=c.getAssets().open("runtime-manifest.json")){manifest=new JSONObject(new String(readSmall(in,1024*1024),StandardCharsets.UTF_8));}
        if(!prefix.isDirectory()){
            SafeTar.deleteTree(stage);
            MessageDigest digest=MessageDigest.getInstance("SHA-256");
            try(InputStream in=c.getAssets().open("bootstrap-relocated.zip");OutputStream out=new FileOutputStream(archive)){
                byte[] buffer=new byte[131072];long bytes=0;int n;
                while((n=in.read(buffer))!=-1){if(monitor.cancelled())throw new IOException("已取消");out.write(buffer,0,n);digest.update(buffer,0,n);bytes+=n;monitor.phase("读取内置环境",bytes,manifest.optLong("bootstrapBytes",-1),"完全离线");}
            }
            if(!hex(digest.digest()).equals(manifest.getString("bootstrapSha256")))throw new IOException("内置运行包校验失败");
            Files.createDirectory(stage.toPath());
            List<String[]> links=new ArrayList<>();long bytes=0;
            try(ZipFile zip=new ZipFile(archive)){
                Enumeration<? extends ZipEntry> entries=zip.entries();
                while(entries.hasMoreElements()){
                    ZipEntry entry=entries.nextElement();if(monitor.cancelled())throw new IOException("已取消");
                    Path path=SafeTar.resolve(stage.toPath(),entry.getName());
                    if(path.equals(stage.toPath()))continue;
                    SafeTar.parents(stage.toPath(),path);
                    if(entry.isDirectory()){Files.createDirectories(path);continue;}
                    if(entry.getName().equals("SYMLINKS.txt")){
                        try(InputStream in=zip.getInputStream(entry)){
                            String[] lines=new String(readSmall(in,8*1024*1024),StandardCharsets.UTF_8).split("\n");
                            for(String line:lines){if(line.isEmpty())continue;String[] parts=line.split("←",2);if(parts.length!=2)throw new IOException("无效的内置链接表");links.add(parts);}
                        }continue;
                    }
                    try(InputStream in=zip.getInputStream(entry);OutputStream out=Files.newOutputStream(path,StandardOpenOption.CREATE_NEW)){
                        byte[] buffer=new byte[131072];int n;
                        while((n=in.read(buffer))!=-1){if(monitor.cancelled())throw new IOException("已取消");out.write(buffer,0,n);bytes+=n;monitor.phase("展开内置环境",bytes,manifest.getLong("expandedBytes"),entry.getName());}
                    }
                    String name=entry.getName();
                    boolean executable=name.startsWith("bin/")||name.startsWith("libexec/")||name.startsWith("lib/apt/")||name.endsWith(".postinst")||name.endsWith(".preinst")||name.endsWith(".prerm")||name.endsWith(".postrm")||name.endsWith("termux-bootstrap-second-stage.sh");
                    permissions(path,executable?0700:0600);
                }
            }
            for(String[] link:links){
                Path path=SafeTar.resolve(stage.toPath(),link[1]);SafeTar.parents(stage.toPath(),path);
                Files.createSymbolicLink(path,Paths.get(link[0]));
            }
            if(!stage.renameTo(prefix))throw new IOException("无法启用内置环境");
            Files.deleteIfExists(archive.toPath());
        }
        new File(files,"home").mkdirs();new File(prefix,"tmp").mkdirs();
        monitor.phase("配置离线环境",0,-1,"配置内置软件包，不执行联网下载");
        ProcessBuilder builder=new ProcessBuilder(new File(prefix,"bin/dpkg").getAbsolutePath(),"--configure","--pending").redirectErrorStream(true);
        builder.environment().clear();builder.environment().putAll(environment(c));builder.directory(new File(files,"home"));
        Process process=builder.start();monitor.process(process);
        try(BufferedReader reader=new BufferedReader(new InputStreamReader(process.getInputStream(),StandardCharsets.UTF_8))){String line;while((line=reader.readLine())!=null){monitor.log(line);if(monitor.cancelled()){process.destroyForcibly();throw new IOException("已取消");}}}
        int result=process.waitFor();monitor.process(null);
        if(result!=0)throw new IOException("离线环境配置失败，退出码 "+result);
        for(String tool:new String[]{"bin/bash","bin/proot","bin/pulseaudio","bin/tar","bin/xz"})if(!new File(prefix,tool).canExecute())throw new IOException("缺少内置工具："+tool);
        TermuxMirror.apply(prefix);
        HostRuntimeFixes.apply(c);
        Files.write(new File(prefix,".archohall-runtime-001").toPath(),manifest.getString("bootstrapSha256").getBytes(StandardCharsets.US_ASCII));
        monitor.log("离线运行环境准备完成；无需外部 Termux 或 X11");
    }
}
