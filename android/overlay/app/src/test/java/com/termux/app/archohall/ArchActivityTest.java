package com.termux.app.archohall;
import org.junit.*;
import static org.junit.Assert.*;
import org.junit.runner.RunWith;
import org.robolectric.*;
import org.robolectric.annotation.Config;
import android.app.Application;
import android.content.Intent;

@RunWith(RobolectricTestRunner.class)
@Config(sdk=34,application=Application.class)
public class ArchActivityTest {
    @Test public void safUsesLocalOpenDocument(){Intent i=ArchActivity.importIntent();assertEquals(Intent.ACTION_OPEN_DOCUMENT,i.getAction());assertTrue(i.hasCategory(Intent.CATEGORY_OPENABLE));assertTrue(i.getBooleanExtra(Intent.EXTRA_LOCAL_ONLY,false));assertTrue((i.getFlags()&Intent.FLAG_GRANT_READ_URI_PERMISSION)!=0);}
    @Test public void materialScreenCanBeCreated(){try(var controller=Robolectric.buildActivity(ArchActivity.class).setup()){assertNotNull(controller.get().findViewById(android.R.id.content));}}
}
