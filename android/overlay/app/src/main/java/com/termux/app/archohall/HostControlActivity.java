package com.termux.app.archohall;

import android.app.*;
import android.os.Bundle;
import android.content.*;
import android.media.AudioManager;
import android.widget.*;

/** Explicit host controls opened by a user action in the Linux quick settings. */
public final class HostControlActivity extends Activity {
    @Override public void onCreate(Bundle b){
        super.onCreate(b);
        String control=getIntent().getStringExtra("control");
        if("apps".equals(control)){
            android.content.pm.PackageManager pm=getPackageManager();
            java.util.List<android.content.pm.ResolveInfo> entries=pm.queryIntentActivities(new Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_LAUNCHER),0);
            entries.sort((a,c)->a.loadLabel(pm).toString().compareToIgnoreCase(c.loadLabel(pm).toString()));
            String[] labels=new String[entries.size()];for(int i=0;i<labels.length;i++)labels[i]=entries.get(i).loadLabel(pm).toString();
            new AlertDialog.Builder(this).setTitle("Android 应用")
                .setItems(labels,(d,w)->{android.content.pm.ActivityInfo a=entries.get(w).activityInfo;try{startActivity(new Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_LAUNCHER).setComponent(new ComponentName(a.packageName,a.name)));}catch(Exception e){Toast.makeText(this,e.getMessage(),Toast.LENGTH_LONG).show();}finish();})
                .setNegativeButton("关闭",(d,w)->finish()).setOnCancelListener(d->finish()).show();return;
        }
        if("power".equals(control)){
            new AlertDialog.Builder(this).setTitle("ArchOHall 桌面")
                .setMessage("停止 Linux 桌面，保留容器和应用数据。手机不会关机。")
                .setNegativeButton("取消",(d,w)->finish())
                .setPositiveButton("停止桌面",(d,w)->{try{SessionController.stop(this);}catch(Exception e){Toast.makeText(this,e.getMessage(),Toast.LENGTH_LONG).show();}finish();})
                .setOnCancelListener(d->finish()).show();return;
        }
        boolean volume="volume".equals(control);
        if(!volume&&!"brightness".equals(control)){finish();return;}
        AudioManager audio=(AudioManager)getSystemService(AUDIO_SERVICE);
        SeekBar slider=new SeekBar(this);
        slider.setMax(volume?audio.getStreamMaxVolume(AudioManager.STREAM_MUSIC):100);
        slider.setProgress(volume?audio.getStreamVolume(AudioManager.STREAM_MUSIC):50);
        slider.setOnSeekBarChangeListener(new SeekBar.OnSeekBarChangeListener(){
            public void onProgressChanged(SeekBar s,int p,boolean user){if(!user)return;if(volume)audio.setStreamVolume(AudioManager.STREAM_MUSIC,p,0);else AndroidHostBridge.setBrightness(p/100f);}
            public void onStartTrackingTouch(SeekBar s){} public void onStopTrackingTouch(SeekBar s){}
        });
        LinearLayout body=new LinearLayout(this);body.setPadding(32,24,32,24);body.addView(slider,new LinearLayout.LayoutParams(-1,-2));
        new AlertDialog.Builder(this).setTitle(volume?"Android 媒体音量":"ArchOHall 窗口亮度")
            .setView(body).setPositiveButton("完成",(d,w)->finish()).setOnCancelListener(d->finish()).show();
    }
}
