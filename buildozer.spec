[app]
title = Saldaterra Impressora
package.name = saldaterra_impressora
package.domain = com.saldaterra
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
version = 1.0
requirements = python3,kivy,jnius,android
orientation = portrait
android.minapi = 21
android.api = 33
android.ndk = 25b
android.archs = arm64-v8a,armeabi-v7a
android.permissions = INTERNET,ACCESS_NETWORK_STATE,BLUETOOTH,BLUETOOTH_ADMIN,BLUETOOTH_CONNECT,BLUETOOTH_SCAN,WAKE_LOCK,FOREGROUND_SERVICE,RECEIVE_BOOT_COMPLETED,REQUEST_INSTALL_PACKAGES
android.wakelock = True
p4a.branch = release-2024.01.21
android.features = android.hardware.bluetooth
android.allow_backup = True

[buildozer]
log_level = 2
warn_on_root = 1
