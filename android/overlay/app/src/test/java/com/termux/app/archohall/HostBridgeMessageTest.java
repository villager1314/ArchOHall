package com.termux.app.archohall;
import org.junit.Test;
import static org.junit.Assert.*;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.Base64;
public class HostBridgeMessageTest {
    @Test public void unicodeClipboardRoundTrip() throws Exception {
        String value="中文 English\nsecond line\n";
        HostBridgeMessage m=HostBridgeMessage.parse("clipboard-set:"+Base64.getEncoder().encodeToString(value.getBytes(StandardCharsets.UTF_8)));
        assertEquals("clipboard-set",m.action);assertEquals(value,m.text);
    }
    @Test public void controlsAreBounded() throws Exception {
        assertEquals(0,HostBridgeMessage.parse("volume-set:0").value);
        assertEquals(100,HostBridgeMessage.parse("brightness-set:100").value);
        for(String s:new String[]{"volume-set:101","brightness-set:-1","volume-set:1;id","volume-set:NaN","shell","wifi extra","clipboard-set:%%","clipboard-set:/w=="})
            assertThrows(IOException.class,()->HostBridgeMessage.parse(s));
    }
    @Test public void largeClipboardRejected() {
        String payload="clipboard-set:"+Base64.getEncoder().encodeToString(new byte[262145]);
        assertThrows(IOException.class,()->HostBridgeMessage.parse(payload));
    }
    @Test public void ordinaryActionsRemainValid() throws Exception {
        assertEquals("wifi",HostBridgeMessage.parse("wifi").action);
        assertEquals("bluetooth",HostBridgeMessage.parse("bluetooth").action);
    }
}
