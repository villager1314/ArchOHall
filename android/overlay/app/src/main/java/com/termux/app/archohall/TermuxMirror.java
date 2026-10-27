package com.termux.app.archohall;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;

/** One-time offline migration; later user mirror choices are left alone. */
public final class TermuxMirror {
    static final String MAIN = "deb https://mirrors.tuna.tsinghua.edu.cn/termux/apt/termux-main stable main\n";
    static final String X11 = "deb https://mirrors.tuna.tsinghua.edu.cn/termux/apt/termux-x11 x11 main\n";
    static final String MIRROR = "mirrors/chinese_mainland/mirrors.tuna.tsinghua.edu.cn";
    private static void replace(Path path, String text) throws IOException {
        Files.createDirectories(path.getParent());
        Path temporary = path.resolveSibling(path.getFileName()+".archohall-tmp");
        Files.write(temporary, text.getBytes(StandardCharsets.UTF_8));
        Files.move(temporary, path, StandardCopyOption.REPLACE_EXISTING);
    }
    private static void backup(Path source, Path dest) throws IOException {
        if(Files.exists(source,LinkOption.NOFOLLOW_LINKS) && !Files.exists(dest,LinkOption.NOFOLLOW_LINKS))
            Files.copy(source,dest,LinkOption.NOFOLLOW_LINKS);
    }
    public static synchronized boolean apply(File prefix) throws IOException {
        Path root=prefix.toPath(), marker=root.resolve(".archohall-tuna-003");
        if(Files.exists(marker))return false;
        Path termux=root.resolve("etc/termux"), saved=termux.resolve("archohall-before-003");
        Files.createDirectories(saved);
        Path main=root.resolve("etc/apt/sources.list"), x11=root.resolve("etc/apt/sources.list.d/x11.list");
        backup(main,saved.resolve("sources.list"));backup(x11,saved.resolve("x11.list"));
        Path chosen=termux.resolve("chosen_mirrors"), old=saved.resolve("chosen_mirrors");
        if(Files.exists(chosen,LinkOption.NOFOLLOW_LINKS)) {
            if(!Files.exists(old,LinkOption.NOFOLLOW_LINKS))Files.move(chosen,old);
            else if(Files.isDirectory(chosen,LinkOption.NOFOLLOW_LINKS))throw new IOException("镜像选择目录冲突，原配置已保留");
            else Files.delete(chosen);
        }
        // A concrete mirror definition also keeps `pkg` from choosing another mirror.
        replace(termux.resolve(MIRROR),"WEIGHT=1\nMAIN=\"https://mirrors.tuna.tsinghua.edu.cn/termux/apt/termux-main\"\nX11=\"https://mirrors.tuna.tsinghua.edu.cn/termux/apt/termux-x11\"\nROOT=\"https://mirrors.tuna.tsinghua.edu.cn/termux/apt/termux-root\"\n");
        replace(main,MAIN);replace(x11,X11);
        Files.createSymbolicLink(chosen,Paths.get(MIRROR));
        Files.write(marker,"0.03\n".getBytes(StandardCharsets.US_ASCII));
        return true;
    }
}
