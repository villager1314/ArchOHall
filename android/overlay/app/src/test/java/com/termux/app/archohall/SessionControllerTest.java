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
public class SessionControllerTest {
    @Test public void desktopCommandRunsWithoutOpeningTerminalFromService() {
        Intent i=SessionController.executionIntent(RuntimeEnvironment.getApplication(),"/private/launch.sh","desktop");
        assertTrue(i.getBooleanExtra("com.archoh.execute.background",false));
        assertEquals("2",i.getStringExtra("com.archoh.execute.session_action"));
        assertEquals("com.termux.app.TermuxService",i.getComponent().getClassName());
        assertArrayEquals(new String[]{"--noprofile","--norc","/private/launch.sh"},i.getStringArrayExtra("com.archoh.execute.arguments"));
    }
}
