[app]
title = 中医诊所处方系统
package.name = chufangxitong
package.domain = org.example
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
source.exclude_dirs =
source.exclude_exts = spec
version = 0.1
requirements = python3,kivy,sqlite3
orientation = landscape
osx.python_version = 3
osx.kivy_version = 2.0.0
audio = True
video = True
p4a.source_dir = 
p4a.local_recipes = 
p4a.libSDL2_ttf = True
p4a.libSDL2_image = True
p4a.libSDL2_mixer = True
p4a.android_api = 27
p4a.sdk = 24
p4a.ndk_api = 21
p4a.arch = armeabi-v7a
p4a.build_dir = ./build
p4a.dist_dir = ./dist
p4a.requirements = python3,kivy,sqlite3
p4a.private_storage = True
p4a.system_packages = libssl-dev
main = main_kivy.py

[buildozer]
log_level = 2
warn_on_root = 1

[app:android]
android.api = 27
android.sdk = 24
android.ndk = 21
android.arch = armeabi-v7a
android.buildtools = 28.0.3
android.use_aapt2 = True
android.allow_backup = True
android.icon = %(source.dir)s/系统图标.png
android.presplash = %(source.dir)s/系统图标.png
android.presplash_color = #FFFFFF
android.adaptive_icon_foreground = %(source.dir)s/系统图标.png
android.adaptive_icon_background = %(source.dir)s/系统图标.png
android.permissions = INTERNET

[app:ios]
ios.codesign.allowed = false

[app:linux]

[app:macosx]

[app:windows]
