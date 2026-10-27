#!/usr/bin/env python3
"""Compose a reproducible Android source project from pinned public GPL sources."""
import json
from pathlib import Path
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET

REPO = Path(__file__).resolve().parent.parent
WORK = REPO / '.android-build'
PROJECT = WORK / 'project'
LOCK = json.loads((REPO / 'android/source-lock.json').read_text())

def git_source(name, url, revision):
    dest = WORK / name
    if not dest.exists():
        subprocess.run(['git', 'clone', '--filter=blob:none', url, str(dest)], check=True)
    subprocess.run(['git', '-C', str(dest), 'checkout', '--detach', revision], check=True)
    return dest

def write(path, text):
    dest = PROJECT / path
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text)

def main():
    WORK.mkdir(exist_ok=True)
    termux = git_source('termux', 'https://github.com/termux/termux-app.git', LOCK['termux'])
    x11 = git_source('x11', 'https://github.com/termux/termux-x11.git', LOCK['x11'])
    if PROJECT.exists():
        shutil.rmtree(PROJECT)
    PROJECT.mkdir()
    for name in ('app', 'termux-shared', 'terminal-emulator', 'terminal-view', 'gradle'):
        shutil.copytree(termux / name, PROJECT / name)
    for name in ('gradlew', 'gradlew.bat', 'LICENSE.md'):
        shutil.copy2(termux / name, PROJECT / name)
    shutil.copytree(x11 / 'lorie', PROJECT / 'lorie', ignore=shutil.ignore_patterns('cpp'))
    shutil.copytree(x11 / 'shell-loader/stub', PROJECT / 'x11-stub')
    # Equal-length package relocation affects filesystem paths and IPC identifiers,
    # never Java/JNI namespaces.
    pairs = [('data/data/com.termux', 'data/data/com.archoh'),
             ('data/user/0/com.termux', 'data/user/0/com.archoh'),
             ('"com.termux"', '"com.archoh"'), ("'com.termux'", "'com.archoh'"),
             ('com.termux.service_', 'com.archoh.service_')]
    for p in PROJECT.rglob('*'):
        if not p.is_file() or p.suffix not in ('.java', '.xml', '.gradle', '.properties', '.sh'):
            continue
        text = p.read_text()
        for old, new in pairs:
            text = text.replace(old, new)
        if 'lorie' in p.relative_to(PROJECT).parts:
            text = text.replace('"com.termux.x11.ACTION_', '"com.archoh.x11.ACTION_')
            text = text.replace('"com.termux.x11.CmdEntryPoint.ACTION_START"', '"com.archoh.x11.CmdEntryPoint.ACTION_START"')
        p.write_text(text)
    # Native terminal JNI is shipped from the matching official APK, not rebuilt.
    write('settings.gradle', "include ':app', ':termux-shared', ':terminal-emulator', ':terminal-view', ':lorie', ':x11-stub'\n")
    write('build.gradle', '''buildscript {
 repositories { google(); mavenCentral() }
 dependencies { classpath 'com.android.tools.build:gradle:8.13.2' }
}
allprojects { repositories { google(); mavenCentral() } }
tasks.register('clean', Delete) { delete rootProject.layout.buildDirectory }
''')
    write('gradle.properties', '''org.gradle.jvmargs=-Xmx4096M
android.useAndroidX=true
android.nonFinalResIds=false
android.nonTransitiveRClass=false
minSdkVersion=26
targetSdkVersion=28
compileSdkVersion=36
markwonVersion=4.6.2
''')
    write('gradle/wrapper/gradle-wrapper.properties', '''distributionBase=GRADLE_USER_HOME
distributionPath=wrapper/dists
distributionUrl=https\\://services.gradle.org/distributions/gradle-8.13-bin.zip
zipStoreBase=GRADLE_USER_HOME
zipStorePath=wrapper/dists
''')
    write('app/build.gradle', '''plugins { id 'com.android.application' }
android {
 namespace 'com.termux'
 compileSdk 36
 defaultConfig {
  applicationId 'com.archoh'
  minSdk 26
  targetSdk 28
  versionCode 4
  versionName '0.02'
  manifestPlaceholders = [TERMUX_PACKAGE_NAME:'com.archoh', TERMUX_APP_NAME:'ArchOHall', TERMUX_API_APP_NAME:'Termux:API', TERMUX_BOOT_APP_NAME:'Termux:Boot', TERMUX_FLOAT_APP_NAME:'Termux:Float', TERMUX_STYLING_APP_NAME:'Termux:Styling', TERMUX_TASKER_APP_NAME:'Termux:Tasker', TERMUX_WIDGET_APP_NAME:'Termux:Widget']
  ndk { abiFilters 'arm64-v8a' }
 }
 buildFeatures { buildConfig true }
 compileOptions { sourceCompatibility JavaVersion.VERSION_17; targetCompatibility JavaVersion.VERSION_17; coreLibraryDesugaringEnabled true }
 buildTypes { release { minifyEnabled false }; debug { } }
 packagingOptions { jniLibs { useLegacyPackaging false } }
 androidResources { noCompress += ['zip'] }
 testOptions { unitTests.includeAndroidResources = true }
}
dependencies {
 implementation project(':lorie')
 implementation project(':terminal-view')
 implementation project(':termux-shared')
 implementation 'androidx.annotation:annotation:1.9.1'
 implementation 'androidx.core:core:1.16.0'
 implementation 'androidx.appcompat:appcompat:1.7.1'
 implementation 'androidx.drawerlayout:drawerlayout:1.2.0'
 implementation 'androidx.preference:preference:1.2.1'
 implementation 'androidx.viewpager:viewpager:1.0.0'
 implementation 'com.google.android.material:material:1.12.0'
 implementation 'com.google.guava:guava:24.1-jre'
 implementation 'com.google.guava:listenablefuture:9999.0-empty-to-avoid-conflict-with-guava'
 implementation 'io.noties.markwon:core:4.6.2'
 implementation 'io.noties.markwon:ext-strikethrough:4.6.2'
 implementation 'io.noties.markwon:linkify:4.6.2'
 implementation 'io.noties.markwon:recycler:4.6.2'
 implementation 'org.apache.commons:commons-compress:1.27.1'
 implementation 'org.tukaani:xz:1.10'
 coreLibraryDesugaring 'com.android.tools:desugar_jdk_libs:2.1.5'
 testImplementation 'junit:junit:4.13.2'
 testImplementation 'org.robolectric:robolectric:4.14.1'
}
''')
    for name, ns in [('terminal-emulator', 'com.termux.terminal'), ('terminal-view', 'com.termux.view'), ('termux-shared', 'com.termux.shared')]:
        text = f"plugins {{ id 'com.android.library' }}\nandroid {{ namespace '{ns}'; compileSdk 36; defaultConfig {{ minSdk 26 }}; buildFeatures {{ buildConfig true }}; compileOptions {{ sourceCompatibility JavaVersion.VERSION_17; targetCompatibility JavaVersion.VERSION_17; coreLibraryDesugaringEnabled true }} }}\n"
        deps = ["coreLibraryDesugaring 'com.android.tools:desugar_jdk_libs:2.1.5'", "implementation 'androidx.annotation:annotation:1.9.1'"]
        if name == 'terminal-view':
            deps += ["api project(':terminal-emulator')"]
        if name == 'termux-shared':
            deps += ["implementation project(':terminal-view')", "implementation 'androidx.appcompat:appcompat:1.7.1'", "implementation 'androidx.core:core:1.16.0'", "implementation 'com.google.android.material:material:1.12.0'", "implementation 'com.google.guava:guava:24.1-jre'", "implementation 'org.lsposed.hiddenapibypass:hiddenapibypass:6.1'", "implementation 'commons-io:commons-io:2.16.1'"]
            deps += [f"implementation 'io.noties.markwon:{n}:4.6.2'" for n in ('core', 'ext-strikethrough', 'linkify', 'recycler')]
        write(f'{name}/build.gradle', text + 'dependencies {\n' + '\n'.join(deps) + '\n}\n')
    lorie = (PROJECT / 'lorie/build.gradle').read_text()
    start = lorie.index('rootProject.subprojects.each')
    end = lorie.index('\nandroid {', start)
    lorie = lorie[:start] + "def hostApplicationId = 'com.archoh'\n" + lorie[end:]
    lorie = lorie.replace('compileSdkVersion 34', 'compileSdkVersion 36')
    lorie = re.sub(r'\s*ndkVersion termuxX11NdkVersion', '', lorie)
    lorie = re.sub(r'\s*externalNativeBuild.cmake.path.*', '', lorie)
    lorie = lorie.replace("project(':shell-loader:stub')", "project(':x11-stub')")
    lorie = lorie.replace('compileOptions.sourceCompatibility JavaVersion.VERSION_1_9', 'compileOptions.sourceCompatibility JavaVersion.VERSION_17')
    lorie = lorie.replace('compileOptions.targetCompatibility JavaVersion.VERSION_1_9', 'compileOptions.targetCompatibility JavaVersion.VERSION_17\n    compileOptions.coreLibraryDesugaringEnabled true')
    lorie = lorie.replace('dependencies {', "dependencies {\n    coreLibraryDesugaring 'com.android.tools:desugar_jdk_libs:2.1.5'", 1)
    write('lorie/build.gradle', lorie)
    stub = (PROJECT / 'x11-stub/build.gradle').read_text().replace('compileSdkVersion 34', 'compileSdkVersion 36')
    write('x11-stub/build.gradle', stub)
    # Remove historical androidx.window alpha API, incompatible with newer lifecycle.
    path = PROJECT / 'termux-shared/src/main/java/com/termux/shared/view/ViewUtils.java'
    text = path.read_text()
    start = text.index('        androidx.window.WindowManager windowManager')
    end = text.index('\n    }', start)
    text = text[:start] + '''        android.view.WindowManager wm = (android.view.WindowManager)context.getSystemService(Context.WINDOW_SERVICE);
        if (android.os.Build.VERSION.SDK_INT >= 30) {
            android.graphics.Rect bounds = (activitySize ? wm.getCurrentWindowMetrics() : wm.getMaximumWindowMetrics()).getBounds();
            return new Point(bounds.width(), bounds.height());
        }
        Point size = new Point();
        if (activitySize) wm.getDefaultDisplay().getSize(size); else wm.getDefaultDisplay().getRealSize(size);
        return size;''' + text[end:]
    path.write_text(text)
    application_path = PROJECT/'app/src/main/java/com/termux/app/TermuxApplication.java'
    application_path.write_text(application_path.read_text().replace('extends Application', 'extends com.termux.x11.LorieApp'))
    help_path=PROJECT/'app/src/main/java/com/termux/app/activities/HelpActivity.java'
    help_path.write_text(help_path.read_text().replace('settings.setAppCacheEnabled(false);','// Application Cache API was removed from the Android SDK.'))
    constants = PROJECT/'termux-shared/src/main/java/com/termux/shared/termux/TermuxConstants.java'
    constants.write_text(re.sub(r'(public static final String [A-Z_]+_NAME = )TERMUX_PACKAGE_NAME \+ "(\.app[^"]*)"',r'\1"com.termux\2"',constants.read_text()))
    # Fallback used by the built-in terminal after the foreground importer prepares assets.
    path = PROJECT / 'app/src/main/java/com/termux/app/TermuxInstaller.java'
    text = path.read_text().replace('final byte[] zipBytes = loadZipBytes();', 'final byte[] zipBytes = loadZipBytes(activity);')
    start = text.index('    public static byte[] loadZipBytes()')
    text = text[:start] + '''    public static byte[] loadZipBytes(Context context) throws java.io.IOException {
        try (java.io.InputStream in = context.getAssets().open("bootstrap-relocated.zip");
             java.io.ByteArrayOutputStream out = new java.io.ByteArrayOutputStream()) {
            byte[] buffer = new byte[65536]; int n;
            while ((n = in.read(buffer)) != -1) out.write(buffer, 0, n);
            return out.toByteArray();
        }
    }
}
'''
    path.write_text(text)
    # New activities, services, theme, and app manifest replace upstream app wiring.
    shutil.copytree(REPO / 'android/overlay', PROJECT, dirs_exist_ok=True)
    android_ns = 'http://schemas.android.com/apk/res/android'
    tools_ns = 'http://schemas.android.com/tools'
    ET.register_namespace('android', android_ns)
    ET.register_namespace('tools', tools_ns)
    attr = lambda name: '{' + android_ns + '}' + name
    for manifest, main_app in [(PROJECT/'app/src/main/AndroidManifest.xml', True), (PROJECT/'lorie/src/main/AndroidManifest.xml', False)]:
        tree = ET.parse(manifest)
        root = tree.getroot()
        application = root.find('application')
        for component in application:
            namespace = 'com.termux' if main_app else 'com.termux.x11'
            for key in ('name','targetActivity','parentActivityName'):
                value=component.get(attr(key),'')
                if value.startswith('.'):
                    component.set(attr(key),namespace+value)
            for intent_filter in list(component.findall('intent-filter')):
                if any(e.get(attr('name')) == 'android.intent.action.MAIN' for e in intent_filter.findall('action')):
                    component.remove(intent_filter)
        if main_app:
            # app_process loads libXlorie directly from base.apk. Compressed JNI
            # entries cannot be dlopen'ed, even though the installed Activity works.
            application.set(attr('extractNativeLibs'), 'false')
            application.set(attr('name'), 'com.termux.app.archohall.ArchApplication')
            application.set('{' + tools_ns + '}replace', 'android:name')
            application.set(attr('label'), 'ArchOHall')
            application.set(attr('icon'), '@drawable/archohall_icon')
            application.set(attr('roundIcon'), '@drawable/archohall_icon')
            activity = ET.SubElement(application, 'activity', {attr('name'):'com.termux.app.archohall.ArchActivity', attr('exported'):'true', attr('theme'):'@style/Theme.ArchOHall', attr('label'):'ArchOHall'})
            intent_filter = ET.SubElement(activity, 'intent-filter')
            ET.SubElement(intent_filter, 'action', {attr('name'):'android.intent.action.MAIN'})
            ET.SubElement(intent_filter, 'category', {attr('name'):'android.intent.category.LAUNCHER'})
            ET.SubElement(application, 'service', {attr('name'):'com.termux.app.archohall.ImportService', attr('exported'):'false'})
            ET.SubElement(root, 'uses-permission', {attr('name'):'android.permission.POST_NOTIFICATIONS'})
            for permission in list(root.findall('uses-permission')):
                if permission.get(attr('name')) in ['android.permission.MANAGE_EXTERNAL_STORAGE', 'android.permission.WRITE_EXTERNAL_STORAGE']:
                    root.remove(permission)
        else:
            for component in application:
                if component.tag in ('activity', 'receiver'):
                    component.set(attr('exported'), 'false')
        tree.write(manifest, encoding='unicode', xml_declaration=True)
    for p in PROJECT.rglob('AndroidManifest.xml'):
        text = re.sub(r'\s+package="[^"]+"', '', p.read_text(), count=1)
        p.write_text(text)
    (PROJECT / 'gradlew').chmod(0o755)
    print(PROJECT)

if __name__ == '__main__':
    main()
