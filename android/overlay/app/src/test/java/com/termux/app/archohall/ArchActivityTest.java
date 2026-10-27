package com.termux.app.archohall;
import org.junit.*;
import static org.junit.Assert.*;
import org.junit.runner.RunWith;
import org.robolectric.*;
import org.robolectric.annotation.Config;
import android.app.Application;
import android.content.Intent;
import org.robolectric.annotation.GraphicsMode;

@RunWith(RobolectricTestRunner.class)
@Config(sdk=34,application=Application.class)
public class ArchActivityTest {
    @Test public void safUsesLocalOpenDocument(){Intent i=ArchActivity.importIntent();assertEquals(Intent.ACTION_OPEN_DOCUMENT,i.getAction());assertTrue(i.hasCategory(Intent.CATEGORY_OPENABLE));assertTrue(i.getBooleanExtra(Intent.EXTRA_LOCAL_ONLY,false));assertTrue((i.getFlags()&Intent.FLAG_GRANT_READ_URI_PERMISSION)!=0);}
    @Test @GraphicsMode(GraphicsMode.Mode.NATIVE) public void materialScreenCanBeCreated() throws Exception {
        org.robolectric.util.ReflectionHelpers.setStaticField(android.os.Build.class,"SUPPORTED_ABIS",new String[]{"arm64-v8a"});
        OperationState.INSTANCE.runtimeReady=true;OperationState.INSTANCE.installed=true;OperationState.INSTANCE.phase="离线环境已就绪";OperationState.INSTANCE.detail="选择本地导入包或启动桌面";
        try(var controller=Robolectric.buildActivity(ArchActivity.class).setup()){
            android.view.View view=controller.get().getWindow().getDecorView();assertNotNull(view);
            view.measure(android.view.View.MeasureSpec.makeMeasureSpec(1080,android.view.View.MeasureSpec.EXACTLY),android.view.View.MeasureSpec.makeMeasureSpec(2400,android.view.View.MeasureSpec.EXACTLY));view.layout(0,0,1080,2400);
            android.graphics.Bitmap bitmap=android.graphics.Bitmap.createBitmap(1080,2400,android.graphics.Bitmap.Config.ARGB_8888);view.draw(new android.graphics.Canvas(bitmap));
            java.io.File directory=new java.io.File("build/screenshots");directory.mkdirs();
            try(java.io.FileOutputStream out=new java.io.FileOutputStream(new java.io.File(directory,"archohall-0.01.png"))){assertTrue(bitmap.compress(android.graphics.Bitmap.CompressFormat.PNG,100,out));}bitmap.recycle();
        }
    }
}
