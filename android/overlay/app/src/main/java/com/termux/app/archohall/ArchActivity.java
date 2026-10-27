package com.termux.app.archohall;

import android.app.*;
import android.content.*;
import android.net.Uri;
import android.os.*;
import android.view.*;
import android.widget.*;
import android.graphics.Typeface;
import androidx.appcompat.app.AppCompatActivity;
import com.google.android.material.button.MaterialButton;
import com.google.android.material.card.MaterialCardView;
import com.google.android.material.chip.Chip;
import com.google.android.material.dialog.MaterialAlertDialogBuilder;
import com.google.android.material.progressindicator.LinearProgressIndicator;
import com.google.android.material.textfield.*;
import com.google.android.material.appbar.MaterialToolbar;
import com.termux.app.TermuxActivity;
import com.termux.app.HostPermissions;
import com.termux.R;
import java.io.*;
import java.util.Locale;

public final class ArchActivity extends AppCompatActivity {
    private final OperationState state=OperationState.INSTANCE;
    private final Handler handler=new Handler(Looper.getMainLooper());
    private TextView phase,detail,logs,status;
    private LinearProgressIndicator progress;
    private MaterialButton importButton,startButton,cancelButton,terminalButton,compatButton;
    private TextInputEditText resolution;
    private final Runnable listener=this::render;
    private final Runnable refresh=new Runnable(){public void run(){render();handler.postDelayed(this,1500);}};
    private int dp(int n){return Math.round(n*getResources().getDisplayMetrics().density);}
    private boolean supported(){for(String abi:Build.SUPPORTED_ABIS)if(abi.equals("arm64-v8a"))return true;return false;}
    @Override public void onCreate(Bundle saved){
        super.onCreate(saved);
        LinearLayout page=new LinearLayout(this);page.setOrientation(LinearLayout.VERTICAL);
        MaterialToolbar toolbar=new MaterialToolbar(this);toolbar.setTitle("ArchOHall");toolbar.setSubtitle("你的掌上 Linux 工作空间");page.addView(toolbar,new LinearLayout.LayoutParams(-1,dp(80)));
        ScrollView scroll=new ScrollView(this);scroll.setFillViewport(true);page.addView(scroll,new LinearLayout.LayoutParams(-1,0,1));
        LinearLayout content=new LinearLayout(this);content.setOrientation(1);content.setPadding(dp(20),dp(8),dp(20),dp(28));scroll.addView(content);
        LinearLayout badges=new LinearLayout(this);Chip version=new Chip(this);version.setText("0.04 · ARM64");version.setCheckable(false);badges.addView(version);Chip offline=new Chip(this);offline.setText("离线导入");offline.setCheckable(false);badges.addView(offline);content.addView(badges);
        LinearLayout overview=card(content);text(overview,"Arch + Plasma Mobile",26);text(overview,"选择已经下载的 ArchOHall 导入包，展开后即可尝试启动桌面。",15);
        status=text(overview,"正在检查运行环境",14);
        LinearLayout controls=card(content);text(controls,"容器",20);
        importButton=button(controls,"选择本地导入包",v->{if(state.installed)new MaterialAlertDialogBuilder(this).setTitle("导入新的容器？").setMessage("新容器校验成功后才会替换当前容器，原容器会保留为备份并继续占用空间。").setNegativeButton("取消",null).setPositiveButton("选择文件",(d,w)->choose()).show();else choose();});
        TextView types=text(controls,"支持 tar.xz 和 Actions ZIP · 建议预留 12 GB",13);
        TextInputLayout field=new TextInputLayout(this);field.setHint("桌面分辨率");resolution=new TextInputEditText(field.getContext());resolution.setSingleLine(true);resolution.setText(getPreferences(0).getString("resolution","720x1280"));field.addView(resolution);controls.addView(field,new LinearLayout.LayoutParams(-1,-2));
        startButton=button(controls,"启动 Plasma Mobile",v->launch());
        LinearLayout tools=new LinearLayout(this);tools.setOrientation(LinearLayout.HORIZONTAL);controls.addView(tools);
        MaterialButton display=button(tools,"打开桌面",v->openDisplay());display.setLayoutParams(new LinearLayout.LayoutParams(0,-2,1));
        MaterialButton stop=button(tools,"停止桌面",v->{try{SessionController.stop(this);}catch(Exception e){error(e);}});stop.setLayoutParams(new LinearLayout.LayoutParams(0,-2,1));
        terminalButton=button(controls,"内置终端",v->startActivity(new Intent(this,TermuxActivity.class)));
        button(controls,"显示设置",v->startActivity(new Intent(this,com.termux.x11.LoriePreferences.class)));
        compatButton=button(controls,"安装软件兼容组件",v->ImportService.start(this,ImportService.COMPAT,null));
        text(controls,"桌面启动崩溃时可尝试软件兼容模式。原启动脚本会备份，部分桌面功能暂不可用。",13);
        LinearLayout permissions=card(content);text(permissions,"权限与文件",20);
        button(permissions,"共享存储访问",v->{try{HostPermissions.requestStorage(this);}catch(Exception e){error(e);}});
        button(permissions,"通知设置",v->{try{HostPermissions.notificationSettings(this);}catch(Exception e){error(e);}});
        button(permissions,"导入终端文件",v->startActivityForResult(importIntent(),13));
        text(permissions,"通过文件选择器复制到终端 downloads，单个文件上限 64 MiB。无需开放整个存储空间。",13);
        LinearLayout operation=card(content);phase=text(operation,"等待准备",20);progress=new LinearProgressIndicator(this);progress.setMax(1000);operation.addView(progress,new LinearLayout.LayoutParams(-1,dp(12)));detail=text(operation,"",14);
        cancelButton=button(operation,"取消当前操作",v->startService(new Intent(this,ImportService.class).setAction(ImportService.CANCEL)));
        detail.setMaxLines(3);detail.setEllipsize(android.text.TextUtils.TruncateAt.END);
        View progressCard=(View)operation.getParent();content.removeView(progressCard);content.addView(progressCard,2);
        LinearLayout logging=card(content);text(logging,"操作日志",20);ScrollView logScroll=new ScrollView(this);logs=new TextView(this);logs.setTextSize(12);logs.setTypeface(Typeface.MONOSPACE);logs.setTextIsSelectable(true);logs.setPadding(dp(8),dp(8),dp(8),dp(8));logScroll.addView(logs);logging.addView(logScroll,new LinearLayout.LayoutParams(-1,dp(240)));
        button(logging,"导出导入日志",v->startActivityForResult(new Intent(Intent.ACTION_CREATE_DOCUMENT).addCategory(Intent.CATEGORY_OPENABLE).setType("text/plain").putExtra(Intent.EXTRA_TITLE,"archohall-import.log"),12));
        button(logging,"查看桌面日志",v->{File log=new File(getFilesDir(),"home/.archohall/session.log");try{String s=log.isFile()?new String(java.nio.file.Files.readAllBytes(log.toPath()),java.nio.charset.StandardCharsets.UTF_8):"尚无桌面日志";if(s.length()>30000)s=s.substring(s.length()-30000);new MaterialAlertDialogBuilder(this).setTitle("桌面日志（末尾）").setMessage(s).setPositiveButton("关闭",null).show();}catch(Exception e){error(e);}});
        text(content,"首次先使用软件渲染验证桌面。此版本为实验版，GPU 加速与安卓系统控制将在后续适配。",13);
        setContentView(page);
        if(!supported()){state.phase="设备架构不支持";state.detail="0.04 需要 ARM64 安卓设备";}
        else if(!state.runtimeReady&&!state.busy)ImportService.start(this,ImportService.PREPARE,null);
    }
    private LinearLayout card(LinearLayout parent){MaterialCardView card=new MaterialCardView(this);card.setRadius(dp(24));card.setCardElevation(0);card.setStrokeWidth(dp(1));LinearLayout.LayoutParams params=new LinearLayout.LayoutParams(-1,-2);params.topMargin=dp(16);parent.addView(card,params);LinearLayout body=new LinearLayout(this);body.setOrientation(1);body.setPadding(dp(20),dp(16),dp(20),dp(16));card.addView(body);return body;}
    private TextView text(LinearLayout p,String value,int size){TextView t=new TextView(this);t.setText(value);t.setTextSize(size);t.setPadding(0,dp(6),0,dp(6));p.addView(t);return t;}
    private MaterialButton button(LinearLayout p,String value,View.OnClickListener action){MaterialButton b=new MaterialButton(this);b.setText(value);b.setAllCaps(false);b.setCornerRadius(dp(22));b.setOnClickListener(action);LinearLayout.LayoutParams params=new LinearLayout.LayoutParams(-1,dp(56));params.topMargin=dp(6);p.addView(b,params);return b;}
    public static Intent importIntent(){return new Intent(Intent.ACTION_OPEN_DOCUMENT).addCategory(Intent.CATEGORY_OPENABLE).setType("*/*").putExtra(Intent.EXTRA_LOCAL_ONLY,true).addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION|Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION);}
    private void choose(){startActivityForResult(importIntent(),11);}
    private void launch(){try{HostRuntimeFixes.apply(this);String value=resolution.getText().toString().trim();if(!value.matches("[0-9]{3,4}x[0-9]{3,4}"))throw new IOException("分辨率示例：720x1280");String[] parts=value.split("x");int w=Integer.parseInt(parts[0]),h=Integer.parseInt(parts[1]);if(w>4096||h>4096)throw new IOException("单边分辨率不能超过 4096");getPreferences(0).edit().putString("resolution",value).apply();SessionController.start(this,w,h);openDisplay();render();}catch(Exception e){error(e);}}
    private void openDisplay(){try{startActivity(new Intent(this,com.termux.x11.MainActivity.class).addFlags(Intent.FLAG_ACTIVITY_REORDER_TO_FRONT));}catch(Exception e){error(e);}}
    @Override protected void onResume(){super.onResume();HostPermissions.finishStorageRequest(this);render();}
    @Override public void onRequestPermissionsResult(int request,String[] permissions,int[] grants){super.onRequestPermissionsResult(request,permissions,grants);if(request==HostPermissions.STORAGE){HostPermissions.finishStorageRequest(this);render();}}
    private void error(Exception e){new MaterialAlertDialogBuilder(this).setTitle("操作未完成").setMessage(e.getMessage()).setPositiveButton("确定",null).show();}
    @Override protected void onStart(){super.onStart();state.add(listener);handler.post(refresh);}
    @Override protected void onStop(){state.remove(listener);handler.removeCallbacks(refresh);super.onStop();}
    private void render(){if(phase==null)return;boolean running=SessionController.running(this);status.setText("运行环境："+(state.runtimeReady?"已就绪":"准备中")+"\n容器："+(state.installed?"已导入":"尚未导入")+"\n桌面："+(running?"运行中":"未运行")+"\n共享存储："+(HostPermissions.storageGranted(this)?"已授权":"未授权，可使用文件选择器"));phase.setText(state.phase);detail.setText(state.detail+(state.progress>=0?"\n"+String.format(Locale.ROOT,"%.1f%%",state.progress/10.0):""));progress.setIndeterminate(state.progress<0);if(state.progress>=0)progress.setProgressCompat(state.progress,false);logs.setText(state.logText());importButton.setEnabled(supported()&&!state.busy&&state.runtimeReady&&!running);startButton.setEnabled(supported()&&!state.busy&&state.runtimeReady&&state.installed&&!running);terminalButton.setEnabled(state.runtimeReady&&!state.busy);compatButton.setEnabled(state.runtimeReady&&state.installed&&!state.busy&&!running);cancelButton.setVisibility(state.busy?View.VISIBLE:View.GONE);}
    @Override protected void onActivityResult(int request,int result,Intent data){super.onActivityResult(request,result,data);if(result!=RESULT_OK||data==null||data.getData()==null)return;Uri uri=data.getData();if(request==11||request==13){try{getContentResolver().takePersistableUriPermission(uri,Intent.FLAG_GRANT_READ_URI_PERMISSION);}catch(SecurityException ignored){}ImportService.start(this,request==13?ImportService.FILE:ImportService.IMPORT,uri);}else if(request==12){new Thread(()->{try(InputStream in=new FileInputStream(new File(getFilesDir(),"import.log"));OutputStream out=getContentResolver().openOutputStream(uri)){if(out==null)throw new IOException("无法写入文件");byte[] b=new byte[65536];int n;while((n=in.read(b))!=-1)out.write(b,0,n);runOnUiThread(()->Toast.makeText(this,"日志已导出",Toast.LENGTH_SHORT).show());}catch(Exception e){runOnUiThread(()->error(e));}},"export-log").start();}}
}
