package com.termux.app.archohall;
import org.junit.*;
import static org.junit.Assert.*;
public class AmCompatTest {
    @Test public void suppliesOwnPackageBeforeEnteringAmAndPreservesArguments()throws Throwable {
        com.termux.termuxam.FakeContext.PACKAGE_NAME="com.termux";
        String[] args={"broadcast","--user","0"};AmCompat.main(args);
        assertEquals("com.archoh",com.termux.termuxam.Am.caller);assertSame(args,com.termux.termuxam.Am.args);
    }
    @Test public void preservesUnderlyingException() {
        assertEquals("sentinel",assertThrows(IllegalStateException.class,()->AmCompat.main(new String[]{"throw"})).getMessage());
    }
}
