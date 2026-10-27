package com.termux.app.archohall;

import android.content.Intent;
import com.termux.app.TermuxApplication;
import com.google.android.material.color.DynamicColors;
import java.io.*;
import java.nio.charset.StandardCharsets;

public class ArchApplication extends TermuxApplication {
    @Override public void onCreate(){
        super.onCreate();
        DynamicColors.applyToActivitiesIfAvailable(this);
        try(FileOutputStream out=new FileOutputStream(new File(getFilesDir(),"apk-path"))){out.write((getApplicationInfo().sourceDir+"\n").getBytes(StandardCharsets.UTF_8));}
        catch(IOException e){android.util.Log.e("ArchOHall","Cannot record APK path",e);}
        OperationState.INSTANCE.runtimeReady=new File(getFilesDir(),"usr/.archohall-runtime-001").isFile();
        OperationState.INSTANCE.installed=new File(getFilesDir(),"containers/archohall/.archohall-installed").isFile();
        if(OperationState.INSTANCE.runtimeReady){OperationState.INSTANCE.phase="离线环境已就绪";OperationState.INSTANCE.detail=OperationState.INSTANCE.installed?"可以启动 Plasma Mobile":"请选择本地导入包";}
        File log=new File(getFilesDir(),"import.log");
        try(FileInputStream input=new FileInputStream(log)){
            long offset=Math.max(0,log.length()-65536);input.getChannel().position(offset);
            java.io.BufferedReader reader=new java.io.BufferedReader(new java.io.InputStreamReader(input,StandardCharsets.UTF_8));
            if(offset>0)reader.readLine();String line;while((line=reader.readLine())!=null)OperationState.INSTANCE.log(line);
        }catch(IOException ignored){}
        if(OperationState.INSTANCE.runtimeReady){
            try{if(TermuxMirror.apply(OfflineRuntime.prefix(this)))OperationState.INSTANCE.log("Termux 主仓库和 X11 仓库已切换至清华源，旧配置已备份");}
            catch(IOException e){OperationState.INSTANCE.log("清华源配置未完成："+e.getMessage());}
        }
    }
}
