package com.termux.app.archohall;

import org.junit.*;
import static org.junit.Assert.*;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;

public class TermuxMirrorTest {
    private Path root;
    @Before public void setup() throws Exception {root=Files.createTempDirectory("archohall-mirror");}
    @After public void cleanup() throws Exception {SafeTar.deleteTree(root.toFile());}
    private String read(String name)throws Exception{return new String(Files.readAllBytes(root.resolve(name)),StandardCharsets.UTF_8);}
    private void write(String name,String text)throws Exception {Path p=root.resolve(name);Files.createDirectories(p.getParent());Files.write(p,text.getBytes(StandardCharsets.UTF_8));}
    @Test public void freshEnvironmentSelectsTunaForAptAndPkg()throws Exception {
        assertTrue(TermuxMirror.apply(root.toFile()));
        assertEquals(TermuxMirror.MAIN,read("etc/apt/sources.list"));
        assertEquals(TermuxMirror.X11,read("etc/apt/sources.list.d/x11.list"));
        Path chosen=root.resolve("etc/termux/chosen_mirrors");
        assertEquals(TermuxMirror.MIRROR,Files.readSymbolicLink(chosen).toString());
        assertTrue(Files.isRegularFile(chosen));
    }
    @Test public void upgradeBacksUpSourcesAndMirrorGroup()throws Exception {
        write("etc/apt/sources.list","old-main");write("etc/apt/sources.list.d/x11.list","old-x11");
        write("etc/termux/chosen_mirrors/old-mirror","keep");
        TermuxMirror.apply(root.toFile());
        assertEquals("old-main",read("etc/termux/archohall-before-003/sources.list"));
        assertEquals("old-x11",read("etc/termux/archohall-before-003/x11.list"));
        assertEquals("keep",read("etc/termux/archohall-before-003/chosen_mirrors/old-mirror"));
    }
    @Test public void laterUserChoicesAreNotOverwritten()throws Exception {
        TermuxMirror.apply(root.toFile());
        write("etc/apt/sources.list","user-main");
        Files.delete(root.resolve("etc/termux/chosen_mirrors"));
        write("etc/termux/chosen_mirrors","user-mirror");
        assertFalse(TermuxMirror.apply(root.toFile()));
        assertEquals("user-main",read("etc/apt/sources.list"));
        assertEquals("user-mirror",read("etc/termux/chosen_mirrors"));
    }
}
