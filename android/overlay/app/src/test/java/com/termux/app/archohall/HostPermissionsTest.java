package com.termux.app.archohall;
import org.junit.*;
import static org.junit.Assert.*;
import org.junit.runner.RunWith;
import org.robolectric.*;
import org.robolectric.annotation.Config;
import org.robolectric.shadows.ShadowEnvironment;
import android.app.*;
import android.content.Intent;
import android.Manifest;
import android.provider.Settings;
import com.termux.app.HostPermissions;

@RunWith(RobolectricTestRunner.class)
@Config(sdk=34,application=Application.class,shadows=HostPermissionsTest.StorageEnvironment.class)
public class HostPermissionsTest {
    @org.robolectric.annotation.Implements(android.os.Environment.class)
    public static class StorageEnvironment extends ShadowEnvironment {
        @org.robolectric.annotation.Implementation(minSdk=30)
        protected static boolean isExternalStorageManager() {return false;}
    }
    @Test public void storageOpensSettingsForThisPackage() {
        Shadows.shadowOf(RuntimeEnvironment.getApplication()).denyPermissions(Manifest.permission.WRITE_EXTERNAL_STORAGE);
        try(var controller=Robolectric.buildActivity(Activity.class).setup()) {
            Activity a=controller.get();HostPermissions.requestStorage(a);
            Intent i=Shadows.shadowOf(a).getNextStartedActivity();
            assertEquals(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION,i.getAction());
            assertEquals("package:"+a.getPackageName(),i.getDataString());
        }
    }
    @Test public void notificationEntryOpensOwnSettings() {
        try(var controller=Robolectric.buildActivity(Activity.class).setup()) {
            Activity a=controller.get();HostPermissions.notificationSettings(a);
            Intent i=Shadows.shadowOf(a).getNextStartedActivity();
            assertEquals(Settings.ACTION_APP_NOTIFICATION_SETTINGS,i.getAction());
            assertEquals(a.getPackageName(),i.getStringExtra(Settings.EXTRA_APP_PACKAGE));
        }
    }
    @Test public void legacyWriteGrantDoesNotHideAllFilesAuthorizationOnModernAndroid() {
        Shadows.shadowOf(RuntimeEnvironment.getApplication()).grantPermissions(Manifest.permission.WRITE_EXTERNAL_STORAGE);
        assertFalse(HostPermissions.storageGranted(RuntimeEnvironment.getApplication()));
    }
}
