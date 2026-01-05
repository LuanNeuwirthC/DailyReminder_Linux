import sys
import os
import platform
import sqlite3
import webbrowser
import subprocess
import json
import urllib.request
from pathlib import Path
from dataclasses import dataclass

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTimeEdit, QCheckBox, QPushButton, QFrame, QMainWindow,
    QSystemTrayIcon, QMenu, QAbstractSpinBox, QMessageBox
)
from PyQt6.QtCore import (
    Qt, QTimer, QPoint, QTime, QDate, QLockFile, QStandardPaths, 
    QUrl, QPropertyAnimation, QEasingCurve, QThread, pyqtSignal
)
from PyQt6.QtGui import (
    QPainter, QBrush, QColor, QPen, QAction, QPixmap, QIcon, QActionGroup
)

APP_VERSION = "1.0.8"
GITHUB_REPO = "LuanNeuwirthC/DailyReminder_Linux" 

@dataclass
class AppConfig:
    target_time: str = "09:00"
    autostart_enabled: bool = False
    last_run_date: str = ""
    theme_mode: str = "dark"
    accent_color: str = "blue"

class ThemeColors:
    PALETTES = {
        "dark": {
            "bg": QColor(5, 15, 30, 240),
            "panel": "rgba(20, 40, 70, 150)",
            "text": "#FFFFFF",
            "text_sec": "#A0B0C0",
            "border": "#1E3A5F",
            "hover": "rgba(255, 255, 255, 10)"
        },
        "light": {
            "bg": QColor(240, 242, 245, 240),
            "panel": "rgba(255, 255, 255, 180)",
            "text": "#1A1A1A",
            "text_sec": "#505050",
            "border": "#D0D0D0",
            "hover": "rgba(0, 0, 0, 10)"
        },
        "contrast": {
            "bg": QColor(0, 0, 0, 255),
            "panel": "#000000",
            "text": "#FFFFFF",
            "text_sec": "#FFFFFF",
            "border": "#FFFFFF",
            "hover": "#333333"
        }
    }

    ACCENTS = {
        "blue": {"name": "Azul Original", "color": "#00D2FF"},
        "gray": {"name": "Cinza", "color": "#A0B0C0"},
        "green": {"name": "Verde", "color": "#00E070"},
        "purple": {"name": "Roxo", "color": "#BD00FF"},
        "pink": {"name": "Rosa", "color": "#FF007F"},
        "red": {"name": "Vermelho", "color": "#FF0000"},
        "orange": {"name": "Laranja", "color": "#FF5C00"},
    }

    @staticmethod
    def get_color(mode, accent_key):
        return ThemeColors.ACCENTS.get(accent_key, ThemeColors.ACCENTS["blue"])["color"]

class UpdateWorker(QThread):
    update_available = pyqtSignal(str, str) 

    def run(self):
        try:
            url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
            with urllib.request.urlopen(url) as response:
                data = json.loads(response.read().decode())
                latest_tag = data.get("tag_name", "").replace("v", "")
                html_url = data.get("html_url", "")
                
                if self.is_newer(latest_tag, APP_VERSION):
                    self.update_available.emit(latest_tag, html_url)
        except:
            pass

    def is_newer(self, latest, current):
        try:
            l_parts = [int(x) for x in latest.split('.')]
            c_parts = [int(x) for x in current.split('.')]
            return l_parts > c_parts
        except:
            return False

class DatabaseManager:
    def __init__(self):
        app_data_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
        self.db_dir = Path(app_data_path) / "DailyReminder"
        self.db_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.db_dir / "settings.db"
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT)")
        conn.commit()
        conn.close()

    def load(self) -> AppConfig:
        config = AppConfig()
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            data = dict(cursor.execute("SELECT key, value FROM config").fetchall())
            
            if "target_time" in data: config.target_time = data["target_time"]
            if "autostart_enabled" in data: config.autostart_enabled = (data["autostart_enabled"] == "1")
            if "last_run_date" in data: config.last_run_date = data["last_run_date"]
            if "theme_mode" in data: config.theme_mode = data["theme_mode"]
            if "accent_color" in data: config.accent_color = data["accent_color"]
            conn.close()
        except: pass
        return config

    def save(self, config: AppConfig) -> None:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", ('target_time', config.target_time))
            cursor.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", ('autostart_enabled', "1" if config.autostart_enabled else "0"))
            cursor.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", ('last_run_date', config.last_run_date))
            cursor.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", ('theme_mode', config.theme_mode))
            cursor.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", ('accent_color', config.accent_color))
            conn.commit()
            conn.close()
        except: pass

class AutoStartManager:
    APP_NAME = "DailyReminderApp"
    def get_exec_path(self) -> str:
        if getattr(sys, 'frozen', False): return sys.executable
        return f'"{sys.executable}" "{os.path.abspath(sys.argv[0])}"'
    def set_autostart(self, enable: bool):
        if platform.system() == "Linux":
            autostart_dir = Path.home() / ".config" / "autostart"
            autostart_dir.mkdir(parents=True, exist_ok=True)
            desktop_file = autostart_dir / f"{self.APP_NAME.lower()}.desktop"
            if enable:
                content = f"[Desktop Entry]\nType=Application\nName={self.APP_NAME}\nExec={self.get_exec_path()} --minimized\nHidden=false\nNoDisplay=false\nX-GNOME-Autostart-enabled=true\n"
                with open(desktop_file, 'w') as f: f.write(content)
                desktop_file.chmod(0o755)
            else:
                if desktop_file.exists(): desktop_file.unlink()

class CustomIcon(QWidget):
    def __init__(self, icon_type="clock", size=20, color="#00D2FF"):
        super().__init__()
        self.setFixedSize(size, size)
        self.icon_type = icon_type
        self.color = QColor(color)
    
    def set_color(self, color_str):
        self.color = QColor(color_str)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(self.color)
        pen.setWidth(2)
        painter.setPen(pen)
        rect = self.rect()
        c = rect.center()
        if self.icon_type == "clock":
            painter.drawEllipse(c, 8, 8)
            painter.drawLine(c, c + QPoint(0, -4))
            painter.drawLine(c, c + QPoint(3, 0))
        elif self.icon_type == "close":
            painter.drawLine(rect.left()+4, rect.top()+4, rect.right()-4, rect.bottom()-4)
            painter.drawLine(rect.right()-4, rect.top()+4, rect.left()+4, rect.bottom()-4)
        elif self.icon_type == "palette":
            painter.setBrush(QBrush(self.color))
            painter.drawEllipse(c, 7, 7)

class DraggableWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.drag_pos = None
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self.drag_pos:
            self.move(event.globalPosition().toPoint() - self.drag_pos)
            event.accept()

class DaemonApp(DraggableWindow):
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        self.autostart_manager = AutoStartManager()
        self.config = self.db_manager.load()
        self.check_timer = QTimer(self)
        self.check_timer.timeout.connect(self.check_schedule)
        self.check_timer.start(5000)
        self.tray_icon = None
        self.confirm_window = None 
        self.init_ui()
        self.setup_tray()
        self.apply_theme()
        self.apply_config_to_ui()
        
        self.update_worker = UpdateWorker()
        self.update_worker.update_available.connect(self.show_update_dialog)
        self.update_worker.start()

    def show_update_dialog(self, version, url):
        msg = QMessageBox()
        msg.setWindowTitle("Atualização Disponível")
        msg.setText(f"Uma nova versão ({version}) está disponível!")
        msg.setInformativeText("Deseja baixar e instalar agora?")
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg.setDefaultButton(QMessageBox.StandardButton.Yes)
        
        # Estilo escuro básico para o dialog não ficar branco demais
        msg.setStyleSheet("QMessageBox { background-color: #1a1a1a; color: white; } QLabel { color: white; } QPushButton { background-color: #333; color: white; padding: 5px; }")
        
        if msg.exec() == QMessageBox.StandardButton.Yes:
            webbrowser.open(url)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        mode = self.get_current_mode()
        bg_color = ThemeColors.PALETTES[mode]["bg"]
        accent = ThemeColors.get_color(mode, self.config.accent_color)
        
        painter.setBrush(QBrush(bg_color))
        painter.setPen(QPen(QColor(accent)))
        rect = self.rect().adjusted(1, 1, -1, -1)
        painter.drawRoundedRect(rect, 15, 15)

    def get_current_mode(self):
        if self.config.theme_mode not in ["dark", "light", "contrast"]:
            return "dark"
        return self.config.theme_mode

    def setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.update_tray_icon()
        menu = QMenu()
        menu.addAction("Abrir Configuração", self.show_normal)
        menu.addSeparator()
        menu.addAction("Sair Totalmente", QApplication.instance().quit)
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self.on_tray_click)
        self.tray_icon.show()

    def update_tray_icon(self):
        accent = ThemeColors.get_color(self.get_current_mode(), self.config.accent_color)
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QBrush(QColor(accent)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(4, 4, 24, 24)
        painter.setBrush(QBrush(QColor("black")))
        painter.drawEllipse(14, 14, 4, 4)
        painter.end()
        self.tray_icon.setIcon(QIcon(pixmap))

    def on_tray_click(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick: self.show_normal()

    def show_normal(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def init_ui(self):
        self.setFixedSize(340, 340)
        central = QWidget()
        central.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(10)

        header = QHBoxLayout()
        self.title_lbl = QLabel(f"DAILY REMINDER v{APP_VERSION}")
        self.title_lbl.setObjectName("HeaderTitle")
        
        self.btn_theme = QPushButton()
        self.btn_theme.setFixedSize(30, 30)
        self.btn_theme.setStyleSheet("background: transparent; border: none;")
        self.theme_icon = CustomIcon("palette", 14, "#00D2FF")
        l_t = QVBoxLayout(self.btn_theme)
        l_t.setContentsMargins(0,0,0,0)
        l_t.addWidget(self.theme_icon)
        self.btn_theme.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_theme.clicked.connect(self.show_theme_menu)

        close_btn = QPushButton()
        close_btn.setFixedSize(30, 30)
        close_btn.setStyleSheet("background: transparent; border: none;")
        self.close_icon = CustomIcon("close", 14, "#00D2FF")
        l_btn = QVBoxLayout(close_btn)
        l_btn.setContentsMargins(0,0,0,0)
        l_btn.addWidget(self.close_icon)
        close_btn.clicked.connect(self.hide_and_save)
        
        header.addWidget(self.title_lbl)
        header.addStretch()
        header.addWidget(self.btn_theme)
        header.addWidget(close_btn)
        
        self.lbl_info = QLabel("Horário do aviso")
        self.lbl_info.setStyleSheet("font-weight: bold; font-size: 13px; margin-top: 10px;")

        h_time = QHBoxLayout()
        self.time_input = QTimeEdit()
        self.time_input.setDisplayFormat("HH:mm")
        self.time_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_input.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.time_input.setFixedHeight(60)
        h_time.addWidget(self.time_input)

        self.chk_auto = QCheckBox("Iniciar com o Sistema")
        self.chk_auto.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.btn_save = QPushButton("Salvar e Ativar")
        self.btn_save.setObjectName("SaveButton")
        self.btn_save.setFixedHeight(40)
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.clicked.connect(self.hide_and_save)

        main_layout.addLayout(header)
        main_layout.addWidget(self.lbl_info)
        main_layout.addLayout(h_time)
        main_layout.addStretch()
        main_layout.addWidget(self.chk_auto)
        main_layout.addWidget(self.btn_save)

    def show_theme_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet(self.styleSheet()) 
        
        mode_menu = menu.addMenu("Modo de Fundo")
        g = QActionGroup(self)
        for mode, name in [("dark", "Escuro"), ("light", "Claro"), ("contrast", "Alto Contraste")]:
            act = QAction(name, self, checkable=True)
            act.setChecked(self.config.theme_mode == mode)
            act.triggered.connect(lambda _, m=mode: self.set_theme_mode(m))
            g.addAction(act)
            mode_menu.addAction(act)

        menu.addSeparator()
        
        color_menu = menu.addMenu("Cor de Destaque")
        g2 = QActionGroup(self)
        for key, val in ThemeColors.ACCENTS.items():
            act = QAction(val["name"], self, checkable=True)
            act.setChecked(self.config.accent_color == key)
            act.triggered.connect(lambda _, c=key: self.set_accent_color(c))
            g2.addAction(act)
            color_menu.addAction(act)

        menu.exec(self.btn_theme.mapToGlobal(QPoint(0, 30)))

    def set_theme_mode(self, mode):
        self.config.theme_mode = mode
        self.apply_theme()

    def set_accent_color(self, color_key):
        self.config.accent_color = color_key
        self.apply_theme()

    def apply_theme(self):
        mode = self.get_current_mode()
        p = ThemeColors.PALETTES[mode]
        accent = ThemeColors.get_color(mode, self.config.accent_color)
        
        ss = f"""
        QWidget {{ color: {p['text']}; font-family: 'Segoe UI', sans-serif; }}
        QMenu {{ background-color: {p['bg'].name()}; border: 1px solid {p['border']}; }}
        QMenu::item {{ padding: 5px 20px; }}
        QMenu::item:selected {{ background-color: {accent}; color: #000000; }}
        
        QLabel#HeaderTitle {{ color: {accent}; font-size: 11px; letter-spacing: 1.5px; font-weight: bold; }}
        
        QTimeEdit {{
            background: {p['panel']}; color: {p['text']};
            font-size: 38px; border: 1px solid {p['border']}; border-radius: 12px;
            selection-background-color: {accent}; selection-color: #000000;
        }}
        
        QCheckBox {{ color: {p['text_sec']}; spacing: 8px; font-size: 13px; background: transparent; }}
        QCheckBox::indicator {{ width: 14px; height: 14px; border: 2px solid {p['border']}; border-radius: 4px; background: transparent; }}
        QCheckBox::indicator:checked {{ background-color: {accent}; border-color: {accent}; }}
        
        QPushButton#SaveButton {{
            background-color: {p['panel']}; color: {p['text']};
            border: 1px solid {p['border']}; border-radius: 10px; font-size: 14px; font-weight: 600;
        }}
        QPushButton#SaveButton:hover {{ background-color: {p['hover']}; border-color: {accent}; color: {accent}; }}
        """
        self.setStyleSheet(ss)
        self.theme_icon.set_color(accent)
        self.close_icon.set_color(accent)
        self.update() 
        self.update_tray_icon()

    def apply_config_to_ui(self):
        t = QTime.fromString(self.config.target_time, "HH:mm")
        self.time_input.setTime(t)
        self.chk_auto.setChecked(self.config.autostart_enabled)

    def check_schedule(self):
        now = QTime.currentTime()
        today_str = QDate.currentDate().toString("yyyy-MM-dd")
        target = QTime.fromString(self.config.target_time, "HH:mm")
        
        if self.config.last_run_date != today_str:
            if now >= target:
                self.trigger_alert()
                self.config.last_run_date = today_str
                self.db_manager.save(self.config)

    def hide_and_save(self):
        new_time_str = self.time_input.time().toString("HH:mm")
        
        if new_time_str != self.config.target_time:
            current_time = QTime.currentTime()
            new_target_time = QTime.fromString(new_time_str, "HH:mm")
            
            if new_target_time <= current_time:
                self.config.last_run_date = QDate.currentDate().toString("yyyy-MM-dd")
            else:
                self.config.last_run_date = ""
        
        self.config.target_time = new_time_str
        self.config.autostart_enabled = self.chk_auto.isChecked()
        self.db_manager.save(self.config)
        self.autostart_manager.set_autostart(self.config.autostart_enabled)
        self.hide()
        self.tray_icon.showMessage("Daily Reminder", f"Monitorando para {self.config.target_time}", QSystemTrayIcon.MessageIcon.Information, 2000)

    def trigger_alert(self):
        self.alert_window = NotificationWindow(
            self.get_current_mode(), self.config.accent_color,
            on_register_callback=self.start_confirmation_timer
        )
        self.alert_window.show()

    def start_confirmation_timer(self):
        QTimer.singleShot(600000, self.show_confirmation_window)

    def show_confirmation_window(self):
        self.confirm_window = ConfirmationWindow(
            self.get_current_mode(), self.config.accent_color,
            on_yes=self.dummy_callback,
            on_no=self.reopen_link
        )
        self.confirm_window.show()

    def dummy_callback(self): pass

    def reopen_link(self):
        webbrowser.open("https://rifyt.com/login")

class NotificationWindow(DraggableWindow): 
    def __init__(self, mode, accent_key, on_register_callback):
        super().__init__()
        self.on_register = on_register_callback
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(320, 110)
        screen_geo = QApplication.primaryScreen().availableGeometry()
        self.move(screen_geo.x() + 20, screen_geo.y() + 50) 
        
        if mode not in ThemeColors.PALETTES: mode = "dark"
        
        self.p = ThemeColors.PALETTES[mode]
        self.accent = ThemeColors.get_color(mode, accent_key)
        self.bg_color = self.p['bg']
        
        central = QWidget()
        layout = QHBoxLayout(central)
        layout.setContentsMargins(5, 5, 5, 5)
        self.card = QFrame()
        
        css_bg = f"rgba({self.bg_color.red()}, {self.bg_color.green()}, {self.bg_color.blue()}, {self.bg_color.alpha()})"
        self.card.setStyleSheet(f"background-color: {css_bg}; border: 2px solid {self.accent}; border-radius: 12px;")
        
        card_layout = QVBoxLayout(self.card)
        lbl_title = QLabel("⏰ HORA DA DAILY")
        lbl_title.setStyleSheet(f"color: {self.accent}; font-weight: bold; font-size: 14px; border: none; font-family: 'Segoe UI', sans-serif;")
        
        btn_action = QPushButton("REGISTRAR AGORA")
        btn_action.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_action.setStyleSheet(f"""
            QPushButton {{ background-color: {self.p['panel']}; color: {self.p['text']}; border: 1px solid {self.p['border']}; border-radius: 6px; padding: 8px; font-weight: bold; font-family: 'Segoe UI'; }}
            QPushButton:hover {{ background-color: {self.accent}; color: black; }}
        """)
        btn_action.clicked.connect(self._handle_click)
        
        card_layout.addWidget(lbl_title)
        card_layout.addWidget(btn_action)
        layout.addWidget(self.card)
        self.setCentralWidget(central)

        self.setWindowOpacity(0.0)
        self.anim = QPropertyAnimation(self, b"windowOpacity")
        self.anim.setDuration(500)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        self.anim.start()

        sound_files = [
            "/usr/share/sounds/freedesktop/stereo/message.oga",
            "/usr/share/sounds/Yaru/stereo/message.oga",
            "/usr/share/sounds/gnome/default/alerts/glass.ogg"
        ]
        
        for s in sound_files:
            if os.path.exists(s):
                try:
                    subprocess.Popen(["paplay", s], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
                except:
                    try:
                        subprocess.Popen(["aplay", s], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
                    except:
                        pass
                break

    def _handle_click(self):
        self.hide()
        webbrowser.open("https://rifyt.com/login")
        self.on_register()
        self.close()

class ConfirmationWindow(DraggableWindow):
    def __init__(self, mode, accent_key, on_yes, on_no):
        super().__init__()
        self.on_yes = on_yes
        self.on_no = on_no
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(320, 130)
        
        screen_geo = QApplication.primaryScreen().availableGeometry()
        x_pos = screen_geo.width() - 340 
        self.move(x_pos, screen_geo.y() + 50) 
        
        if mode not in ThemeColors.PALETTES: mode = "dark"
        p = ThemeColors.PALETTES[mode]
        accent = ThemeColors.get_color(mode, accent_key)
        bg_color = p['bg']

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(5, 5, 5, 5)
        self.card = QFrame()
        
        css_bg = f"rgba({bg_color.red()}, {bg_color.green()}, {bg_color.blue()}, {bg_color.alpha()})"
        self.card.setStyleSheet(f"background-color: {css_bg}; border: 2px solid {accent}; border-radius: 12px;")
        
        card_layout = QVBoxLayout(self.card)
        lbl = QLabel("Você registrou a Daily?")
        lbl.setStyleSheet(f"color: {p['text']}; font-size: 14px; font-weight: bold; border: none; font-family: 'Segoe UI';")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        btn_layout = QHBoxLayout()
        btn_no = QPushButton("Não")
        btn_no.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_no.setStyleSheet(f"background-color: {p['panel']}; color: #FF4444; border: 1px solid #FF4444; border-radius: 6px; padding: 8px; font-weight: bold;")
        btn_no.clicked.connect(self._handle_no)
        
        btn_yes = QPushButton("Sim")
        btn_yes.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_yes.setStyleSheet(f"background-color: {p['panel']}; color: #00E070; border: 1px solid #00E070; border-radius: 6px; padding: 8px; font-weight: bold;")
        btn_yes.clicked.connect(self._handle_yes)
        
        btn_layout.addWidget(btn_no)
        btn_layout.addWidget(btn_yes)
        card_layout.addWidget(lbl)
        card_layout.addLayout(btn_layout)
        layout.addWidget(self.card)
        self.setCentralWidget(central)

    def _handle_yes(self):
        self.hide()
        self.on_yes()
        self.close()

    def _handle_no(self):
        self.hide()
        self.on_no()
        self.close()

if __name__ == "__main__":
    lock_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.TempLocation) + "/daily_reminder_v22.lock"
    lock = QLockFile(lock_path)
    lock.setStaleLockTime(3000)
    if not lock.tryLock(): sys.exit(0)

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    
    window = DaemonApp()
    if "--minimized" not in sys.argv: window.show()
    sys.exit(app.exec())