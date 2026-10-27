package com.termux.termuxam;
public final class Am {
    public static String[] args; public static String caller;
    public static void main(String[] input) {
        caller=FakeContext.PACKAGE_NAME;args=input;
        if(input.length>0&&input[0].equals("throw"))throw new IllegalStateException("sentinel");
    }
}
