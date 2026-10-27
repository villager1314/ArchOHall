package com.termux.app.archohall;

import android.app.*;
import android.content.*;
import android.media.AudioManager;
import android.net.*;
import android.net.wifi.WifiManager;
import android.bluetooth.BluetoothAdapter;
import android.os.*;
import android.provider.Settings;
import android.view.*;
import android.graphics.Color;
import org.json.JSONObject;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.concurrent.*;

/** Private, same-app bridge. No TCP listener, shell execution or privileged Android APIs. */
public final class AndroidHostBridge implements Application.ActivityLifecycleCallbacks {
    private static AndroidHostBridge instance;
    private final Application app;
    private final File dir, requests;
    private final Handler main = new Handler(Looper.getMainLooper());
    private volatile boolean keepAwake, nightTint;
    private volatile float brightness = -1;
    private Activity visible;
    private Activity desktop;
    private long lastSnapshot;

    public static synchronized AndroidHostBridge start(Application app) throws IOException {
        if (instance == null) instance = new AndroidHostBridge(app);
        return instance;
    }
    public static File directory(Context c) { return new File(c.getFilesDir(), "home/.archohall/host-bridge"); }
    private AndroidHostBridge(Application app) throws IOException {
        this.app = app; dir = directory(app); requests = new File(dir, "requests");
        if (!requests.mkdirs() && !requests.isDirectory()) throw new IOException("Cannot create Android bridge directory");
        dir.setReadable(false, false); dir.setReadable(true, true);
        dir.setWritable(false, false); dir.setWritable(true, true);
        app.registerActivityLifecycleCallbacks(this);
        ScheduledExecutorService worker = Executors.newSingleThreadScheduledExecutor(r -> {
            Thread t = new Thread(r, "archohall-host-bridge"); t.setDaemon(true); return t;
        });
        worker.scheduleWithFixedDelay(this::poll, 0, 250, TimeUnit.MILLISECONDS);
    }
    private static void write(File target, String value) throws IOException {
        File tmp = File.createTempFile(".bridge-", ".tmp", target.getParentFile());
        try {
            Files.write(tmp.toPath(), value.getBytes(StandardCharsets.UTF_8));
            Files.move(tmp.toPath(), target.toPath(), StandardCopyOption.REPLACE_EXISTING);
        } finally { tmp.delete(); }
    }
    private void poll() {
        try {
            File[] pending = requests.listFiles((d, n) -> n.matches("req-[A-Za-z0-9]+\\.request"));
            int processed = 0;
            if (pending != null) for (File f : pending) {
                if (++processed > 32) break;
                if (Files.isSymbolicLink(f.toPath()) || f.length() > 1024 || System.currentTimeMillis()-f.lastModified() > 30000) { f.delete(); continue; }
                String action = new String(Files.readAllBytes(f.toPath()), StandardCharsets.UTF_8).trim();
                f.delete();
                String id = f.getName().replace(".request", ".reply");
                main.post(() -> {
                    String result;
                    try { dispatch(action); result = "OK"; }
                    catch (Exception e) { result = "ERROR: " + e.getMessage(); android.widget.Toast.makeText(app,result,android.widget.Toast.LENGTH_LONG).show(); }
                    try { write(new File(requests,id),result+"\n"); } catch (IOException ignored) {}
                });
            }
            if (SystemClock.elapsedRealtime()-lastSnapshot > 1500) {
                write(new File(dir,"state.json"),snapshot().toString()); lastSnapshot=SystemClock.elapsedRealtime();
            }
            File[] replies=requests.listFiles((d,n)->n.endsWith(".reply"));
            if(replies!=null)for(File f:replies)if(System.currentTimeMillis()-f.lastModified()>30000)f.delete();
        } catch(Exception e) { android.util.Log.w("ArchOHall","Host bridge update failed",e); }
    }
    private JSONObject snapshot() throws Exception {
        JSONObject s=new JSONObject(); s.put("schema",1); s.put("timestamp",System.currentTimeMillis());
        Intent battery=app.registerReceiver(null,new IntentFilter(Intent.ACTION_BATTERY_CHANGED));
        if(battery!=null){
            int level=battery.getIntExtra(BatteryManager.EXTRA_LEVEL,-1), scale=battery.getIntExtra(BatteryManager.EXTRA_SCALE,0);
            s.put("battery",level>=0&&scale>0 ? Math.round(100.0*level/scale) : JSONObject.NULL);
            s.put("plugged",battery.getIntExtra(BatteryManager.EXTRA_PLUGGED,0)!=0);
            s.put("batteryStatus",battery.getIntExtra(BatteryManager.EXTRA_STATUS,1));
            s.put("batteryPresent",battery.getBooleanExtra(BatteryManager.EXTRA_PRESENT,true));
        }
        s.put("model",Build.MODEL);
        AudioManager audio=(AudioManager)app.getSystemService(Context.AUDIO_SERVICE);
        s.put("volume",audio.getStreamVolume(AudioManager.STREAM_MUSIC));
        s.put("volumeMax",audio.getStreamMaxVolume(AudioManager.STREAM_MUSIC));
        s.put("keepAwake",keepAwake); s.put("nightTint",nightTint);
        s.put("brightness",brightness);
        s.put("airplane",Settings.Global.getInt(app.getContentResolver(),Settings.Global.AIRPLANE_MODE_ON,0)!=0);
        try { s.put("wifi",((WifiManager)app.getApplicationContext().getSystemService(Context.WIFI_SERVICE)).isWifiEnabled()); } catch(Exception ignored){s.put("wifi",JSONObject.NULL);}
        try { BluetoothAdapter b=BluetoothAdapter.getDefaultAdapter();s.put("bluetooth",b==null?JSONObject.NULL:b.isEnabled()); } catch(Exception ignored){s.put("bluetooth",JSONObject.NULL);}
        try {
            ConnectivityManager cm=(ConnectivityManager)app.getSystemService(Context.CONNECTIVITY_SERVICE);
            NetworkCapabilities nc=cm.getNetworkCapabilities(cm.getActiveNetwork());
            s.put("network",nc==null?"none":nc.hasTransport(NetworkCapabilities.TRANSPORT_WIFI)?"wifi":nc.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR)?"mobile":"other");
        }catch(Exception ignored){s.put("network","unknown");}
        NotificationManager nm=(NotificationManager)app.getSystemService(Context.NOTIFICATION_SERVICE);
        s.put("dndGranted",nm.isNotificationPolicyAccessGranted());
        s.put("dnd",nm.getCurrentInterruptionFilter()!=NotificationManager.INTERRUPTION_FILTER_ALL);
        return s;
    }
    private void open(String action) {
        Intent intent=new Intent(action).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        if(intent.resolveActivity(app.getPackageManager())==null)intent=new Intent(Settings.ACTION_SETTINGS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        app.startActivity(intent);
    }
    private void dispatch(String action) throws Exception {
        switch(action){
            case "wifi": open(Build.VERSION.SDK_INT>=29?Settings.Panel.ACTION_WIFI:Settings.ACTION_WIFI_SETTINGS); break;
            case "mobiledata": open(Settings.ACTION_DATA_USAGE_SETTINGS); break;
            case "bluetooth": open(Settings.ACTION_BLUETOOTH_SETTINGS); break;
            case "airplane": open(Settings.ACTION_AIRPLANE_MODE_SETTINGS); break;
            case "hotspot": {
                Intent tether=new Intent("android.settings.TETHER_SETTINGS");
                open(tether.resolveActivity(app.getPackageManager())!=null?tether.getAction():Settings.ACTION_WIRELESS_SETTINGS);break;
            }
            case "settings": open(Settings.ACTION_SETTINGS); break;
            case "battery": open(Settings.ACTION_BATTERY_SAVER_SETTINGS); break;
            case "volume": case "brightness": case "power": case "apps":
                app.startActivity(new Intent(app,HostControlActivity.class).putExtra("control",action).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)); break;
            case "keepawake": keepAwake=!keepAwake; if(desktop!=null)apply(desktop); break;
            case "nightcolor": nightTint=!nightTint; if(desktop!=null)apply(desktop); break;
            case "dnd": {
                NotificationManager nm=(NotificationManager)app.getSystemService(Context.NOTIFICATION_SERVICE);
                if(!nm.isNotificationPolicyAccessGranted())open(Settings.ACTION_NOTIFICATION_POLICY_ACCESS_SETTINGS);
                else nm.setInterruptionFilter(nm.getCurrentInterruptionFilter()==NotificationManager.INTERRUPTION_FILTER_ALL?NotificationManager.INTERRUPTION_FILTER_PRIORITY:NotificationManager.INTERRUPTION_FILTER_ALL);
                break;
            }
            default: throw new IOException("Unknown host action");
        }
    }
    public static void setBrightness(float value){if(instance!=null){instance.brightness=Math.max(0.02f,Math.min(1f,value)); if(instance.desktop!=null)instance.apply(instance.desktop);}}
    private void apply(Activity a){
        // Controls are scoped to ArchOHall's desktop, never the Android system UI.
        if(!a.getClass().getName().equals("com.termux.x11.MainActivity"))return;
        Window w=a.getWindow(); WindowManager.LayoutParams p=w.getAttributes();p.screenBrightness=brightness;w.setAttributes(p);
        if(keepAwake)w.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);else w.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        ViewGroup decor=(ViewGroup)w.getDecorView(); View tint=decor.findViewWithTag("archohall-night-tint");
        if(nightTint&&tint==null){tint=new View(a);tint.setTag("archohall-night-tint");tint.setClickable(false);tint.setFocusable(false);tint.setImportantForAccessibility(View.IMPORTANT_FOR_ACCESSIBILITY_NO);tint.setBackgroundColor(Color.argb(32,255,140,0));decor.addView(tint,new ViewGroup.LayoutParams(-1,-1));}
        if(tint!=null)tint.setVisibility(nightTint?View.VISIBLE:View.GONE);
    }
    @Override public void onActivityResumed(Activity a){visible=a;if(a.getClass().getName().equals("com.termux.x11.MainActivity"))desktop=a;apply(a);}
    @Override public void onActivityPaused(Activity a){if(visible==a)visible=null;}
    @Override public void onActivityCreated(Activity a,Bundle b){}
    @Override public void onActivityStarted(Activity a){}
    @Override public void onActivityStopped(Activity a){}
    @Override public void onActivitySaveInstanceState(Activity a,Bundle b){}
    @Override public void onActivityDestroyed(Activity a){if(visible==a)visible=null;if(desktop==a)desktop=null;}
}
