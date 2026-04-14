[app]

title = Saldaterra Impressora
package.name = saldaterra_impressora
package.domain = com.saldaterra

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json

version = 1.0

# Dependencias — jnius e android sao para APIs nativas do Android
requirements = python3,kivy,jnius,android

orientation = portrait

# Icone e splash (opcional — coloque icone.png na raiz se quiser)
# icon.filename = %(source.dir)s/icone.png

# Android SDK
android.minapi = 21
android.api = 33
android.ndk = 25b

# Arquitetura — arm64-v8a para celulares modernos, armeabi-v7a para antigos
android.archs = arm64-v8a,armeabi-v7a

# Permissoes necessarias para Bluetooth + Internet + Background
android.permissions = \
    INTERNET, \
    ACCESS_NETWORK_STATE, \
    BLUETOOTH, \
    BLUETOOTH_ADMIN, \
    BLUETOOTH_CONNECT, \
    BLUETOOTH_SCAN, \
    WAKE_LOCK, \
    FOREGROUND_SERVICE, \
    RECEIVE_BOOT_COMPLETED, \
    REQUEST_INSTALL_PACKAGES

# Permite app continuar em segundo plano
android.wakelock = True

# Branch estavel do python-for-android
p4a.branch = release-2024.01.21

# Features do Android (necessario para Bluetooth)
android.features = android.hardware.bluetooth

# Nao fechar app quando minimizado
android.allow_backup = True

[buildozer]
log_level = 2
warn_on_root = 1
