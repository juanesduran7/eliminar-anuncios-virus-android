import sys
import re
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QPushButton, 
                            QTextEdit, QWidget, QMessageBox, QLabel, QScrollArea)
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
        central_widget = QWidget()
        layout = QVBoxLayout()
        
        self.text_output = QTextEdit()
        self.text_output.setReadOnly(True)
        
        self.btn_remove_junk = QPushButton("Eliminar Apps Basura")
        self.btn_remove_junk.clicked.connect(self.remove_junk_apps)
        
        self.btn_monitor_ads = QPushButton("Monitorear Anuncios (logcat)")
        self.btn_monitor_ads.clicked.connect(self.toggle_monitor_ads)
        
        self.btn_read_fake_apps = QPushButton("Leer Apps Falsas o paquetes extraños")
        self.btn_read_fake_apps.clicked.connect(self.read_fake_apps)
        
        self.btn_whatsapp = QPushButton("MY WHATSAPP - MY CONTACT")
        self.btn_whatsapp.clicked.connect(self.open_whatsapp)
        
        layout.addWidget(self.text_output)
        layout.addWidget(self.btn_remove_junk)
        layout.addWidget(self.btn_monitor_ads)
        layout.addWidget(self.btn_read_fake_apps)
        layout.addWidget(self.btn_whatsapp)
        
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

    def toggle_monitor_ads(self):
        """Alterna el monitoreo de anuncios"""
        if self.logcat_thread and self.logcat_thread.isRunning():
            self.stop_monitoring()
        else:
            self.start_monitoring()

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

    def remove_junk_apps(self):
        """Función para eliminar apps basura"""
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

    def read_fake_apps(self):
        if not self.device:
            self.append_text("⚠️ Conecta un dispositivo primero")
            return
            
        try:
            # Obtener solo paquetes instalados por el usuario
            output = self.device.shell("pm list packages -3")
            packages = [line.split(":")[1] for line in output.splitlines() if line.startswith("package:")]
            
            # Filtrar paquetes sospechosos
            suspicious = []
            for package in packages:
                if not self.is_safe_package(package):
                    suspicious.append(package)
            
            if not suspicious:
                QMessageBox.information(self, "Resultado", "No se encontraron apps falsas o paquetes extraños instalados por el usuario.")
                return
                
            # Crear el diálogo personalizado
            dialog = QMessageBox()
            dialog.setWindowTitle("Apps Falsas o Paquetes Extraños (Usuario)")
            dialog.setText(f"Se encontraron {len(suspicious)} apps instaladas por el usuario:")
            
            # Añadir área de scroll con los paquetes
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            content = QWidget()
            layout = QVBoxLayout(content)
            
            for package in suspicious:
                label = QLabel(package)
                layout.addWidget(label)
                
            scroll.setWidget(content)
            
            # Añadir botón personalizado para eliminar
            dialog.addButton("Eliminar Apps", QMessageBox.ActionRole)
            dialog.addButton(QMessageBox.Ok)
            
            # Añadir el scroll al diálogo
            dialog.layout().addWidget(scroll, 0, 0, 1, dialog.layout().columnCount())
            
            # Mostrar el diálogo y esperar respuesta
            result = dialog.exec_()
            
            # Si se presionó "Eliminar Apps"
            if result == 0:  # 0 es el índice del botón personalizado
                self.remove_selected_apps(suspicious)
                
        except Exception as e:
            self.append_text(f"❌ Error al leer apps de usuario: {str(e)}")

    def remove_selected_apps(self, packages):
        """Elimina las apps seleccionadas"""
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("Confirmar Eliminación")
        msg.setText(f"¿Estás seguro de que deseas eliminar {len(packages)} apps?")
        msg.setInformativeText("Esta acción no se puede deshacer.")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        
        if msg.exec_() == QMessageBox.Yes:
            for package in packages:
                self.append_text(f"🚫 Intentando eliminar: {package}")
                try:
                    result = self.device.shell(f"pm uninstall --user 0 {package}")
                    if "Success" in result:
                        self.append_text(f"✅ Eliminado: {package}")
                    else:
                        self.append_text(f"❌ No se pudo eliminar: {package}")
                except Exception as e:
                    self.append_text(f"⚠️ Error eliminando {package}: {str(e)}")
        else:
            self.append_text("❌ Eliminación cancelada por el usuario.")

    def is_safe_package(self, package):
        safe_prefixes = [
            "com.whatsapp", "org.telegram", "com.facebook", "com.instagram",
            "com.google", "com.android", "com.samsung", "com.motorola",
            "android", "com.sec", "com.miui", "com.xiaomi", "com.oneplus",
            "com.oppo", "com.vivo", "com.lge", "com.htc", "com.sony",
            "com.amazon", "com.netflix", "com.spotify", "com.microsoft",
            "com.spotify",
            "com.paypal", "com.bank", "com.bbva",
            "com.santander", "com.davivienda", "com.bancolombia"
        ]
        return any(package.startswith(prefix) for prefix in safe_prefixes)

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
            "com.whatsapp", "org.telegram", "com.facebook", "com.instagram", "com.android", "com.google.android", "com.google.android.gms",
            "com.google.android.apps", "com.google.android.youtube", "com.google.android.maps",
            "com.android", "com.android.providers", "com.android.systemui", "com.android.settings",
            "android", "com.android.phone", "com.android.contacts", "com.android.mms",
            "com.samsung", "com.samsung.android", "com.sec.android", "com.motorola",
            "com.miui", "com.xiaomi", "com.bbva", "com.santander", "com.paypal"
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


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AndroidCleanerApp()
    window.show()
    sys.exit(app.exec_())
