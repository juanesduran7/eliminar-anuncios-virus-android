import sys
import re
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QPushButton, 
                            QTextEdit, QWidget, QMessageBox)
from PyQt5.QtCore import QThread, pyqtSignal, QTimer  
from ppadb.client import Client as AdbClient


class LogcatThread(QThread):
    new_log = pyqtSignal(str)

    def __init__(self, device):
        super().__init__()
        self.device = device
        self._running = True
        self._logcat_stream = None  

    def run(self):
        try:
            self.device.shell("logcat -c")
            self._logcat_stream = self.device.shell("logcat -v brief", stream=True)

            while self._running:
                line = self._logcat_stream.readline()
                if line:
                    self.new_log.emit(line.strip())
        except Exception as e:
            self.new_log.emit(f"❌ Error en logcat: {str(e)}")

    def stop(self):
        self._running = False
        if self._logcat_stream:
            self._logcat_stream.close() 
        self.wait()  


class ForegroundAppMonitor(QThread):
    suspicious_app_detected = pyqtSignal(str)

    def __init__(self, device, safe_apps):
        super().__init__()
        self.device = device
        self.safe_apps = safe_apps
        self._running = True

    def run(self):
        recent_apps = {}
        while self._running:
            try:
                output = self.device.shell("dumpsys activity activities | grep mResumedActivity")
                match = re.search(r'([a-zA-Z0-9_.]+)/(.*?) ', output)
                if match:
                    package = match.group(1)
                    if not any(package.startswith(p) for p in self.safe_apps):
                        recent_apps[package] = recent_apps.get(package, 0) + 1
                        if recent_apps[package] >= 3:
                            self.suspicious_app_detected.emit(package)
                            recent_apps[package] = 0
            except Exception as e:
                pass
            self.msleep(2000)

    def stop(self):
        self._running = False
        self.wait()

from PyQt5.QtGui import QDesktopServices
from PyQt5.QtCore import QUrl

class AndroidCleanerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BLACK BOX DELETE VIRUS ADDS")
        self.setGeometry(100, 100, 800, 600)
        self.adb_client = AdbClient(host="127.0.0.1", port=5037)
        self.device = None
        self.logcat_thread = None
        
        self.init_ui()
        self.init_adb()
        self.suspicious_packages = set()
        
      
        self.device_check_timer = QTimer(self)
        self.device_check_timer.timeout.connect(self.check_connected_devices)
        self.device_check_timer.start(5000)
        
        self.safe_apps = [
            "com.whatsapp", "org.telegram", "com.facebook",
            "com.google", "com.android", "com.motorola", "android",
            "com.sec.android", "com.samsung.android", "com.miui.gallery"
        ]
        self.foreground_monitor = None

    def init_ui(self):
        """Este método debe estar dentro de la clase, asegurándote de que la indentación es correcta"""
        central_widget = QWidget()
        layout = QVBoxLayout()
        
        self.text_output = QTextEdit()
        self.text_output.setReadOnly(True)
        
        self.btn_remove_junk = QPushButton("Eliminar Apps Basura")
        self.btn_remove_junk.clicked.connect(self.remove_junk_apps)
        
        self.btn_monitor_ads = QPushButton("Monitorear Anuncios (logcat)")
        self.btn_monitor_ads.clicked.connect(self.toggle_monitor_ads)
        
        self.btn_whatsapp = QPushButton("MY WHATSAPP - MY CONTACT")
        self.btn_whatsapp.clicked.connect(self.open_whatsapp)
        
        layout.addWidget(self.text_output)
        layout.addWidget(self.btn_remove_junk)
        layout.addWidget(self.btn_monitor_ads)
        layout.addWidget(self.btn_whatsapp) 
        
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

    def open_whatsapp(self):
       
        whatsapp_url = "https://api.whatsapp.com/send?phone=573169441188" 
      
      
        QDesktopServices.openUrl(QUrl(whatsapp_url))

  


    def init_adb(self):
        try:
            self.adb_client = AdbClient(host="127.0.0.1", port=5037)
            version = self.adb_client.version()
            self.append_text(f"✅ Servidor ADB (versión: {version})")
            self.check_connected_devices()
        except Exception as e:
            self.append_text(f"❌ Error ADB: {str(e)}")

    def check_connected_devices(self):
        try:
            devices = self.adb_client.devices()
            
            if not devices:
                self.device = None
                self.append_text("🔌 Esperando dispositivo...")
            else:
                new_device = devices[0]
                if self.device is None or self.device.serial != new_device.serial:
                    self.device = new_device
                    self.append_text(f"✅ Dispositivo: {self.device.serial}")
                    try:
                        model = self.device.shell("getprop ro.product.model").strip()
                        brand = self.device.shell("getprop ro.product.brand").strip()
                        self.append_text(f"📱 Modelo: {brand} {model}")
                    except:
                        pass
        except Exception as e:
            self.append_text(f"⚠️ Error dispositivos: {str(e)}")

    def append_text(self, text):
        self.text_output.append(text)
        self.text_output.ensureCursorVisible()

    def handle_suspicious_app(self, package):
        if package not in self.suspicious_packages:
            self.suspicious_packages.add(package)
        
        self.append_text(f"🚨 App sospechosa activa detectada: {package}")
        try:
            self.device.shell(f"am force-stop {package}")
            self.append_text(f"✅ App cerrada: {package}")
        except Exception as e:
            self.append_text(f"⚠️ Error al cerrar {package}: {str(e)}")

    def start_monitoring(self): 
        if not self.device:
            self.append_text("⚠️ Conecta un dispositivo primero")
            return

        self.append_text("🛰️ Monitoreando apps activas y anuncios...")
        self.btn_monitor_ads.setText("Detener Monitoreo")

     
        self.logcat_thread = LogcatThread(self.device)
        self.logcat_thread.new_log.connect(self.process_log_line)
        self.logcat_thread.start()

       
        self.foreground_monitor = ForegroundAppMonitor(self.device, self.safe_apps)
        self.foreground_monitor.suspicious_app_detected.connect(self.handle_suspicious_app)
        self.foreground_monitor.start()

    def stop_monitoring(self):
        if self.logcat_thread:
            self.logcat_thread.stop()
        if self.foreground_monitor:
            self.foreground_monitor.stop()
        self.append_text("🛑 Monitoreo detenido")
        self.btn_monitor_ads.setText("Monitorear Anuncios")

    def process_log_line(self, line):
        patterns = [
            "ads", "admob", "fullscreen", "overlay", "popup",
            "airpush", "startapp", "adview", "showAd", "Interstitial",
            "RewardedAd", "banner", "exoplayer", "activity", "launch"
        ]
        
        if any(p.lower() in line.lower() for p in patterns):
            package = self.extract_package_from_log(line)
            if package and self.is_removable_package(package):
                self.append_text(f"🚨 Anuncio detectado: {package}\n{line}")
                self.try_remove_package(package)

    def extract_package_from_log(self, line):
        match = re.search(r'([a-zA-Z0-9_.]+)(?=:\s|\s)', line)
        if match:
            return match.group(1)
        return None

    def is_removable_package(self, package):
        protected = [
               # Aplicaciones populares de mensajería
        "com.whatsapp", "org.telegram", "com.facebook", "com.instagram", "com.snapchat",
        
        # Aplicaciones de Google (esenciales para el sistema y servicios)
        "com.google", "com.android", "com.google.android", "com.google.android.gms",  # Servicios de Google
        "com.google.android.apps", "com.google.android.youtube", "com.google.android.maps",
        
        # Aplicaciones del sistema Android
        "com.android", "com.android.providers", "com.android.systemui", "com.android.settings",
        "android", "com.android.phone", "com.android.contacts", "com.android.mms",
        "com.android.messaging", "com.android.dialer", "com.android.browser",
        "com.android.camera", "com.android.gallery3d", "com.android.documentsui",
        
        # Aplicaciones del fabricante del dispositivo (como Samsung, Xiaomi, etc.)
        "com.samsung", "com.samsung.android", "com.samsung.android.app", "com.samsung.android.contacts",
        "com.samsung.android.messaging", "com.samsung.android.camera", "com.samsung.android.gallery",
        "com.samsung.android.email", "com.samsung.android.bixby", "com.samsung.android.locksettings",
        "com.sec.android", "com.sec.android.app", "com.sec.android.provider", "com.sec.android.gallery3d",

        # Aplicaciones relacionadas con la seguridad y actualizaciones
        "com.android.vending",  # Google Play Store
        "com.google.android.play", "com.android.packageinstaller",  # Instalar aplicaciones y seguridad
        "com.google.android.apps.docs",  # Google Drive
        "com.google.android.gms",  # Google Play Services
        "com.google.android.gsf",  # Google Services Framework
        "com.google.android.gsf.login",  # Framework de inicio de sesión de Google
        
        # Otras aplicaciones importantes del sistema y del dispositivo
        "com.motorola", "com.htc", "com.sonyericsson", "com.lge",  # Paquetes de otros fabricantes como Motorola, HTC, LG
        "com.miui", "com.xiaomi", "com.oneplus",  # Xiaomi y OnePlus
        "com.oppo", "com.vivo",  # Oppo y Vivo

        # Aplicaciones bancarias y de pago (por ejemplo, las de bancos populares)
        "com.bbva", "com.santander", "com.amex", "com.paypal", "com.google.pay",
        "com.mastercard", "com.visa", "com.paypal.android.p2pmobile", "com.banco",
        
        # Servicios de streaming y multimedia
        "com.netflix", "com.spotify", "com.pandora", "com.spotify.music", "com.amazon.music", "com.hulu.plus", "com.disney.disneyplus",
        
        # Otros servicios comunes
        "com.dropbox", "com.box.android", "com.amazon.mShop.android", "com.evernote",
        
        # Otras aplicaciones importantes del sistema operativo
        "com.android.providers.telephony", "com.android.providers.contacts", "com.android.providers.media",
        "com.android.providers.downloads", "com.android.providers.applications", "com.android.providers.settings",
        ]
        return not any(package.startswith(p) for p in protected)

    def try_remove_package(self, package):
        try:
            result = self.device.shell(f"pm uninstall --user 0 {package}")
            if "Success" in result:
                self.append_text(f"✅ Eliminado: {package}")
            else:
                self.append_text(f"❌ No se pudo eliminar: {package}")
        except Exception as e:
            self.append_text(f"⚠️ Error eliminando {package}: {str(e)}")

    def remove_junk_apps(self):
        predefined_packages = [
            "com.clarocolombia.miclaro",
            "com.clarodrive.android",
            "com.amazon.appmanager",
        ]

        all_packages = list(set(predefined_packages).union(self.suspicious_packages))

        if not all_packages:
            self.append_text("✅ No hay apps basura ni sospechosas para eliminar.")
            return

        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("Advertencia")
        msg.setText("Se eliminarán las siguientes apps sospechosas:")
        msg.setInformativeText("\n".join(all_packages))
        msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        result = msg.exec_()

        if result == QMessageBox.Ok:
            for package in all_packages:
                self.append_text(f"🚫 Eliminando: {package}")
                try:
                    result = self.device.shell(f"pm uninstall --user 0 {package}")
                    if "Success" in result:
                        self.append_text(f"✅ Eliminado: {package}")
                    else:
                        self.append_text(f"❌ Falló: {package}")
                except Exception as e:
                    self.append_text(f"⚠️ Error: {str(e)}")

            self.suspicious_packages.clear()
        else:
            self.append_text("❌ Eliminación cancelada por el usuario.")

    def toggle_monitor_ads(self):
        if self.logcat_thread and self.logcat_thread.isRunning():
            self.stop_monitoring()
        else:
            self.start_monitoring()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AndroidCleanerApp()
    window.show()
    sys.exit(app.exec_())
