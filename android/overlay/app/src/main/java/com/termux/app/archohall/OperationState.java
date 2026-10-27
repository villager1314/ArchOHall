package com.termux.app.archohall;

import android.os.Handler;
import android.os.Looper;
import java.util.*;

public final class OperationState {
    public static final OperationState INSTANCE=new OperationState();
    public volatile boolean busy=false, runtimeReady=false, installed=false;
    public volatile int progress=-1;
    public volatile String phase="等待准备", detail="";
    private final LinkedList<String> lines=new LinkedList<>();
    private final List<Runnable> listeners=new ArrayList<>();
    private final Handler handler=new Handler(Looper.getMainLooper());
    private long lastUpdate;
    public synchronized void add(Runnable listener){listeners.add(listener);listener.run();}
    public synchronized void remove(Runnable listener){listeners.remove(listener);}
    public synchronized String logText(){return String.join("\n",lines);}
    public synchronized void log(String text){lines.add(text);while(lines.size()>120)lines.removeFirst();}
    public synchronized void changed(boolean force){
        long now=android.os.SystemClock.uptimeMillis();
        if(!force&&now-lastUpdate<180)return;
        lastUpdate=now;
        handler.post(()->{List<Runnable> copy; synchronized(this){copy=new ArrayList<>(listeners);}for(Runnable listener:copy)listener.run();});
    }
}
