package com.termux.app.archohall;

import java.io.*;
import java.nio.file.*;
import java.nio.file.attribute.PosixFilePermissions;
import java.util.*;
import org.apache.commons.compress.archivers.tar.*;
import org.tukaani.xz.*;

/** Extracts into a fresh staging directory without following archive-created links. */
public final class SafeTar {
    public interface Progress { void update(String path, long files, long bytes, long total) throws IOException; }
    public static final long LIMIT = 16L * 1024 * 1024 * 1024;
    private static final int XZ_MEMORY_KIB = 256 * 1024; // XZ Java accepts KiB, not MiB.
    private record Link(Path path, Path target, int mode) {}
    private record Mode(Path path, int mode) {}
    public static Path resolve(Path root, String name) throws IOException {
        if (name.indexOf('\0') >= 0 || name.startsWith("/") || name.contains("\\")) throw new IOException("非法归档路径：" + name);
        Path path = root.resolve(name).normalize();
        if (!path.startsWith(root)) throw new IOException("归档路径越界：" + name);
        return path;
    }
    public static void parents(Path root, Path file) throws IOException {
        Path parent = file.getParent();
        if (parent == null || !parent.startsWith(root)) throw new IOException("非法父目录");
        Path current = root;
        for (Path part : root.relativize(parent)) {
            current = current.resolve(part);
            if (Files.isSymbolicLink(current)) throw new IOException("拒绝通过符号链接写入：" + current.getFileName());
            if (Files.exists(current, LinkOption.NOFOLLOW_LINKS) && !Files.isDirectory(current, LinkOption.NOFOLLOW_LINKS)) throw new IOException("父路径不是目录");
            Files.createDirectories(current);
        }
    }
    private static void mode(Path p, int mode) throws IOException {
        // Android's app UID owns all entries; retain executable bits, drop setuid/setgid.
        StringBuilder permissions = new StringBuilder();
        for (int i=8;i>=0;i--) permissions.append((mode & (1<<i)) == 0 ? '-' : "rwx".charAt((8-i)%3));
        Files.setPosixFilePermissions(p, PosixFilePermissions.fromString(permissions.toString()));
    }
    public static long expandedSize(File archive) throws IOException {
        try (SeekableXZInputStream in = new SeekableXZInputStream(new SeekableFileInputStream(archive), XZ_MEMORY_KIB)) {
            long length = in.length();
            if (length <= 0 || length > LIMIT) throw new IOException("解压大小不在允许范围内（最多 16 GiB）");
            return length;
        }
    }
    public static void extract(File archive, File directory, Progress listener) throws IOException {
        Path root = directory.toPath().toAbsolutePath().normalize();
        Files.createDirectory(root);
        long total = expandedSize(archive), count=0, written=0;
        List<Link> links = new ArrayList<>();
        List<Mode> dirs = new ArrayList<>();
        byte[] buffer = new byte[131072];
        try (InputStream file = new BufferedInputStream(new FileInputStream(archive));
             XZInputStream xz = new XZInputStream(file, XZ_MEMORY_KIB);
             TarArchiveInputStream tar = new TarArchiveInputStream(xz)) {
            TarArchiveEntry entry;
            while ((entry = tar.getNextTarEntry()) != null) {
                if (++count > 250000) throw new IOException("归档文件数量过多");
                String name = entry.getName();
                Path path = resolve(root, name);
                listener.update(name, count, tar.getBytesRead(), total);
                if (path.equals(root)) continue;
                parents(root, path);
                if (entry.isDirectory()) {
                    if (Files.isSymbolicLink(path)) throw new IOException("目录与链接冲突："+name);
                    Files.createDirectories(path);
                    dirs.add(new Mode(path, entry.getMode() & 0777));
                } else if (entry.isSymbolicLink()) {
                    // Absolute link targets have container semantics, and are NEVER followed here.
                    String target = entry.getLinkName();
                    if (target.indexOf('\0') >= 0) throw new IOException("非法链接");
                    Files.createSymbolicLink(path, Paths.get(target));
                } else if (entry.isLink()) {
                    String target = entry.getLinkName();
                    if (target.startsWith("/")) target = target.substring(1);
                    links.add(new Link(path, resolve(root, target), entry.getMode() & 0777));
                } else if (entry.isFile() && !entry.isSparse()) {
                    if (entry.getSize() < 0 || entry.getSize() > LIMIT-written) throw new IOException("归档展开大小超限");
                    try (OutputStream out = Files.newOutputStream(path, StandardOpenOption.CREATE_NEW, StandardOpenOption.WRITE)) {
                        int n;
                        while ((n = tar.read(buffer)) != -1) {
                            out.write(buffer,0,n); written += n;
                            if (written > LIMIT) throw new IOException("归档展开大小超限");
                            listener.update(name,count,tar.getBytesRead(),total);
                        }
                    }
                    mode(path, entry.getMode() & 0777);
                } else if (entry.isSparse()) {
                    throw new IOException("0.01 暂不支持稀疏归档条目");
                }
                // Device nodes and FIFOs have no useful meaning in an unprivileged Android rootfs.
            }
        }
        while (!links.isEmpty()) {
            boolean advanced = false;
            for (Iterator<Link> it=links.iterator();it.hasNext();) {
                Link link=it.next();
                parents(root,link.path); parents(root,link.target);
                if (!Files.isRegularFile(link.target,LinkOption.NOFOLLOW_LINKS)) continue;
                try { Files.createLink(link.path,link.target); }
                catch (FileSystemException e) { Files.copy(link.target,link.path); }
                mode(link.path,link.mode); it.remove(); advanced=true;
            }
            if (!advanced) throw new IOException("硬链接目标缺失或不安全");
        }
        dirs.sort((a,b)->Integer.compare(b.path.getNameCount(),a.path.getNameCount()));
        for (Mode dir:dirs) mode(dir.path,dir.mode);
        mode(root,0700);
        listener.update("解压完成",count,total,total);
    }
    public static void deleteTree(File directory) throws IOException {
        if (!directory.exists() && !Files.isSymbolicLink(directory.toPath())) return;
        Files.walkFileTree(directory.toPath(),new SimpleFileVisitor<>() {
            @Override public FileVisitResult visitFile(Path file, java.nio.file.attribute.BasicFileAttributes attrs) throws IOException { Files.delete(file);return FileVisitResult.CONTINUE; }
            @Override public FileVisitResult postVisitDirectory(Path dir,IOException error) throws IOException { if(error!=null)throw error;Files.delete(dir);return FileVisitResult.CONTINUE; }
        });
    }
    public static void validate(File directory) throws IOException {
        Path root=directory.toPath().toAbsolutePath().normalize();
        for(String name:new String[]{"usr/bin/kwin_wayland","usr/bin/plasmashell","usr/local/bin/archohall-mobile","usr/local/bin/archohall-init","etc/passwd"}) {
            Path p=resolve(root,name);parents(root,p);
            if(!Files.isRegularFile(p,LinkOption.NOFOLLOW_LINKS))throw new IOException("缺少必需文件："+name);
        }
        String passwd=new String(Files.readAllBytes(root.resolve("etc/passwd")),java.nio.charset.StandardCharsets.UTF_8);
        if(!passwd.contains("\narch:")&&!passwd.startsWith("arch:"))throw new IOException("镜像缺少 arch 用户");
        try(InputStream in=Files.newInputStream(root.resolve("usr/bin/kwin_wayland"))){byte[] head=new byte[20];if(in.read(head)!=20||head[0]!=0x7f||head[1]!='E'||head[2]!='L'||head[3]!='F'||(head[18]&255)!=183||head[19]!=0)throw new IOException("此导入包不是 ARM64 桌面镜像");}
    }
}
