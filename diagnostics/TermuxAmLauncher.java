// SPDX-License-Identifier: MIT
package com.archoh.compat;

import java.lang.reflect.InvocationTargetException;

/** Set the caller identity before entering the unmodified TermuxAm classes. */
public final class TermuxAmLauncher {
    public static void main(String[] args) throws Throwable {
        String prefix = System.getenv("PREFIX");
        if (!"/data/data/com.archoh/files/usr".equals(prefix)
                && !"/data/user/0/com.archoh/files/usr".equals(prefix)) {
            throw new IllegalStateException("Run this launcher in the ArchOHall terminal");
        }
        Class<?> context = Class.forName("com.termux.termuxam.FakeContext");
        context.getField("PACKAGE_NAME").set(null, "com.archoh");
        try {
            Class.forName("com.termux.termuxam.Am")
                .getMethod("main", String[].class).invoke(null, (Object) args);
        } catch (InvocationTargetException exception) {
            throw exception.getCause();
        }
    }
}
