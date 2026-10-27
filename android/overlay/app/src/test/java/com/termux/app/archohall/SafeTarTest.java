package com.termux.app.archohall;

import org.junit.*;
import static org.junit.Assert.*;
import org.apache.commons.compress.archivers.tar.*;
import org.tukaani.xz.*;
import java.io.*;
import java.nio.file.*;

public class SafeTarTest {
    private Path temp;
    @Before public void setup() throws Exception {temp=Files.createTempDirectory("archohall-test");}
    @After public void cleanup() throws Exception {SafeTar.deleteTree(temp.toFile());}
    interface Writer {void write(TarArchiveOutputStream out)throws Exception;}
    private File archive(Writer writer)throws Exception {
        File file=temp.resolve("rootfs.tar.xz").toFile();
        try(XZOutputStream xz=new XZOutputStream(new FileOutputStream(file),new LZMA2Options(1));TarArchiveOutputStream out=new TarArchiveOutputStream(xz)){writer.write(out);}return file;
    }
    private static void file(TarArchiveOutputStream out,String name,String value)throws Exception {byte[] b=value.getBytes(java.nio.charset.StandardCharsets.UTF_8);TarArchiveEntry e=new TarArchiveEntry(name);e.setSize(b.length);e.setMode(0755);out.putArchiveEntry(e);out.write(b);out.closeArchiveEntry();}
    private static void link(TarArchiveOutputStream out,String name,String target,boolean hard)throws Exception {TarArchiveEntry e=new TarArchiveEntry(name,hard?TarConstants.LF_LINK:TarConstants.LF_SYMLINK);e.setLinkName(target);out.putArchiveEntry(e);out.closeArchiveEntry();}
    private void extract(File archive)throws Exception {SafeTar.extract(archive,temp.resolve("stage").toFile(),(p,f,b,t)->assertTrue(b>=0&&t>0));}
    private static String read(Path p)throws IOException{return new String(Files.readAllBytes(p),java.nio.charset.StandardCharsets.UTF_8);}
    private static void write(Path p,String s)throws IOException{Files.write(p,s.getBytes(java.nio.charset.StandardCharsets.UTF_8));}
    @Test public void normalFileAndExecutable()throws Exception {extract(archive(out->file(out,"usr/bin/tool","ok")));assertEquals("ok",read(temp.resolve("stage/usr/bin/tool")));assertTrue(Files.isExecutable(temp.resolve("stage/usr/bin/tool")));}
    @Test public void traversalCannotEscape()throws Exception {File a=archive(out->file(out,"../escaped","bad"));assertThrows(IOException.class,()->extract(a));assertFalse(Files.exists(temp.resolve("escaped")));}
    @Test public void symlinkParentCannotEscape()throws Exception {Path outside=Files.createDirectory(temp.resolve("outside"));File a=archive(out->{link(out,"jump",outside.toString(),false);file(out,"jump/escaped","bad");});assertThrows(IOException.class,()->extract(a));assertFalse(Files.exists(outside.resolve("escaped")));}
    @Test public void leafSymlinkCannotBeOverwritten()throws Exception {Path victim=temp.resolve("victim");write(victim,"keep");File a=archive(out->{link(out,"file",victim.toString(),false);file(out,"file","bad");});assertThrows(IOException.class,()->extract(a));assertEquals("keep",read(victim));}
    @Test public void forwardHardlinkWorks()throws Exception {extract(archive(out->{link(out,"alias","target",true);file(out,"target","data");}));assertEquals("data",read(temp.resolve("stage/alias")));}
    @Test public void hardlinkCannotReadExternalSymlink()throws Exception {Path victim=temp.resolve("victim");write(victim,"keep");File a=archive(out->{link(out,"outside",victim.toString(),false);link(out,"copy","outside",true);});assertThrows(IOException.class,()->extract(a));assertFalse(Files.exists(temp.resolve("stage/copy")));}
    @Test public void cancellationKeepsExistingContainer()throws Exception {Path old=temp.resolve("old");write(old,"keep");File a=archive(out->file(out,"usr/bin/tool","ok"));assertThrows(IOException.class,()->SafeTar.extract(a,temp.resolve("stage").toFile(),(p,f,b,t)->{throw new IOException("cancelled");}));assertEquals("keep",read(old));}
}
