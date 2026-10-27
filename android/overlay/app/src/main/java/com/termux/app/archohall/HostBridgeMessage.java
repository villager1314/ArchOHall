package com.termux.app.archohall;

import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;
import java.util.Base64;
import java.util.Set;

/** Bounded data-only messages; no command strings or arbitrary intents. */
public final class HostBridgeMessage {
    private static final Set<String> ACTIONS=Set.of("wifi","mobiledata","bluetooth","airplane","hotspot","settings","battery","volume","brightness","power","apps","keepawake","nightcolor","dnd");
    public final String action,text;
    public final int value;
    private HostBridgeMessage(String action,int value,String text){this.action=action;this.value=value;this.text=text;}
    public static HostBridgeMessage parse(String raw) throws IOException {
        if(raw==null||raw.length()>350000)throw new IOException("Invalid host message size");
        if(ACTIONS.contains(raw))return new HostBridgeMessage(raw,-1,null);
        if(raw.matches("(?:brightness|volume)-set:[0-9]{1,3}")) {
            int split=raw.indexOf(':');int value=Integer.parseInt(raw.substring(split+1));
            if(value>100)throw new IOException("Invalid control value");
            return new HostBridgeMessage(raw.substring(0,split),value,null);
        }
        if(raw.startsWith("clipboard-set:")) {
            try {
                byte[] bytes=Base64.getDecoder().decode(raw.substring(14));
                if(bytes.length>262144)throw new IOException("Clipboard text exceeds 256 KiB");
                String text=StandardCharsets.UTF_8.newDecoder().onMalformedInput(CodingErrorAction.REPORT)
                    .onUnmappableCharacter(CodingErrorAction.REPORT).decode(ByteBuffer.wrap(bytes)).toString();
                return new HostBridgeMessage("clipboard-set",-1,text);
            } catch(IllegalArgumentException e){throw new IOException("Invalid clipboard encoding",e);}
        }
        throw new IOException("Unknown host action");
    }
}
