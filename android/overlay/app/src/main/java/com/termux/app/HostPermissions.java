package com.termux.app;

import android.Manifest;
import android.app.Activity;
import android.content.*;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Build;
import android.os.Environment;
import android.provider.Settings;
import android.widget.Toast;
import java.io.File;
import java.nio.file.Files;
import java.nio.file.LinkOption;

public final class HostPermissions {
    public static final int STORAGE = 4401;
    public static boolean storageGranted(Context c) {
        if (Build.VERSION.SDK_INT >= 30) {
            try {return Environment.isExternalStorageManager();}
            catch (RuntimeException error) {android.util.Log.w("ArchOHall","Shared storage status is unavailable",error);return false;}
        }
        return c.checkSelfPermission(Manifest.permission.WRITE_EXTERNAL_STORAGE) == PackageManager.PERMISSION_GRANTED;
    }
    public static void requestStorage(Activity a) {
        if (storageGranted(a)) { setupLinks(a); return; }
        a.getSharedPreferences("host-permissions", 0).edit().putBoolean("storage-pending", true).apply();
        try {
            if (Build.VERSION.SDK_INT >= 30) a.startActivity(new Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION, Uri.parse("package:" + a.getPackageName())));
            else a.requestPermissions(new String[]{Manifest.permission.READ_EXTERNAL_STORAGE, Manifest.permission.WRITE_EXTERNAL_STORAGE}, STORAGE);
        } catch (ActivityNotFoundException error) {
            a.startActivity(new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.parse("package:" + a.getPackageName())));
        }
    }
    public static void finishStorageRequest(Context c) {
        android.content.SharedPreferences p = c.getSharedPreferences("host-permissions", 0);
        if (!p.getBoolean("storage-pending", false)) return;
        p.edit().remove("storage-pending").apply();
        if (storageGranted(c)) {
            setupLinks(c);
        } else Toast.makeText(c, "未授予共享存储访问，仍可通过文件选择器导入", Toast.LENGTH_LONG).show();
    }
    public static void notificationSettings(Activity a) {
        a.startActivity(new Intent(Settings.ACTION_APP_NOTIFICATION_SETTINGS).putExtra(Settings.EXTRA_APP_PACKAGE, a.getPackageName()));
    }
    private static void setupLinks(Context c) {
        try {
            File directory = new File(c.getFilesDir(), "home/storage");
            if (Files.isSymbolicLink(directory.toPath())) throw new java.io.IOException("storage 目录是符号链接，已保留原配置");
            Files.createDirectories(directory.toPath());
            String[] names={"shared","downloads","dcim","pictures","music","movies"};
            File[] targets={Environment.getExternalStorageDirectory(),Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS),Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DCIM),Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_PICTURES),Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_MUSIC),Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_MOVIES)};
            for(int i=0;i<names.length;i++) {
                File link=new File(directory,names[i]);
                if(!Files.exists(link.toPath(),LinkOption.NOFOLLOW_LINKS)) android.system.Os.symlink(targets[i].getAbsolutePath(),link.getAbsolutePath());
            }
            Toast.makeText(c,"存储访问已授权，终端 storage 目录已配置；已有文件已保留",Toast.LENGTH_LONG).show();
        } catch(Exception error) {Toast.makeText(c,"已授权，但终端目录配置未完成："+error.getMessage(),Toast.LENGTH_LONG).show();}
    }
}
