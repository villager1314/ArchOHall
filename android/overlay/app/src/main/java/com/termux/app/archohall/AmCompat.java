package com.termux.app.archohall;

import java.lang.reflect.InvocationTargetException;

/** Entry point used by the bundled am script; upstream Java names stay intact. */
public final class AmCompat {
    public static void main(String[] args) throws Throwable {
        Class.forName("com.termux.termuxam.FakeContext").getField("PACKAGE_NAME").set(null, "com.archoh");
        try {
            Class.forName("com.termux.termuxam.Am").getMethod("main", String[].class).invoke(null, (Object) args);
        } catch (InvocationTargetException error) { throw error.getCause(); }
    }
}
