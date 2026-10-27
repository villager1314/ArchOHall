package com.termux.app.archohall;

import org.junit.*;
import static org.junit.Assert.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;

public class HostRuntimeFixesTest {
    private Path root;
    @Before public void setup() throws Exception {root=Files.createTempDirectory("archohall-hostfix");}
    @After public void cleanup() throws Exception {SafeTar.deleteTree(root.toFile());}
    private void write(String name,String value)throws Exception {Path p=root.resolve(name);Files.createDirectories(p.getParent());Files.write(p,value.getBytes(StandardCharsets.UTF_8));}
    private String read(String name)throws Exception{return new String(Files.readAllBytes(root.resolve(name)),StandardCharsets.UTF_8);}
    @Test public void upgradePreservesOriginalToolsAndUsesCurrentApkPointer()throws Exception {
        String old="#!/bin/sh\nAM_APK_PATH=/prefix/am.apk\nexport CLASSPATH=\"$AM_APK_PATH\"\nexec /system/bin/app_process / com.termux.termuxam.Am \"$@\"\n";
        write("bin/am",old);write("bin/termux-x11","original-loader");write("libexec/termux-am/am.apk","unchanged-dex");
        File pointer=root.resolve("../apk-path").toFile();
        HostRuntimeFixes.apply(root.toFile(),pointer);
        assertEquals(old,read("bin/am.before-004"));
        assertEquals("original-loader",read("bin/termux-x11.before-004"));
        assertEquals("unchanged-dex",read("libexec/termux-am/am.apk"));
        assertTrue(read("bin/am").contains("com.termux.app.archohall.AmCompat \"$@\""));
        assertTrue(read("bin/am").contains(pointer.getAbsolutePath()));
        assertTrue(read("bin/termux-x11").contains("com.termux.x11.CmdEntryPoint \"$@\""));
        assertTrue(read("etc/apt/apt.conf.d/99archohall-hostfix").contains("DPkg::Post-Invoke"));
        String first=read("bin/am");HostRuntimeFixes.apply(root.toFile(),pointer);
        assertEquals(first,read("bin/am"));assertEquals(old,read("bin/am.before-004"));
    }
    @Test public void recognizesEarlierHotfix()throws Exception {
        String old="export CLASSPATH=\"$AM_APK_PATH:/old/helper.zip\"\nexec /system/bin/app_process / com.archoh.compat.TermuxAmLauncher \"$@\"\n";
        String fixed=HostRuntimeFixes.wrapAm(old,"/prefix","/apk-path");
        assertTrue(fixed.contains("com.termux.app.archohall.AmCompat"));assertFalse(fixed.contains("/old/helper.zip"));
    }
    @Test public void unknownWrapperIsPreserved()throws Exception {
        write("bin/am","custom script");
        assertThrows(IOException.class,()->HostRuntimeFixes.apply(root.toFile(),new File("/apk-path")));
        assertEquals("custom script",read("bin/am"));
    }
}
