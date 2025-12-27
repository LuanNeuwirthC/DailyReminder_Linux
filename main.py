import sys
import os
import platform
import sqlite3
import webbrowser
from pathlib import Path
from dataclasses import dataclass

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTimeEdit, QCheckBox, QPushButton, QFrame, QMainWindow,
    QSystemTrayIcon, QMenu, QAbstractSpinBox
)
from PyQt6.QtCore import (
    Qt, QTimer, QPoint, QTime, QLockFile, QStandardPaths
)
from PyQt6.QtGui import (
    QPainter, QBrush, QColor, QPen, QAction, QPixmap, QIcon
)

@dataclass
class AppConfig:
    target_time: str = "09:00"
    autostart_enabled: bool = False

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
            cursor.execute("SELECT value FROM config WHERE key='target_time'")
            row = cursor.fetchone()
            if row: config.target_time = row[0]
            cursor.execute("SELECT value FROM config WHERE key='autostart_enabled'")
            row = cursor.fetchone()
            if row: config.autostart_enabled = (row[0] == "1")
            conn.close()
        except: pass
        return config

    def save(self, config: AppConfig) -> None:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", ('target_time', config.target_time))
            val_bool = "1" if config.autostart_enabled else "0"
            cursor.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", ('autostart_enabled', val_bool))
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

class Colors:
    BG_MAIN = QColor(5, 15, 30, 240)
    ACCENT_BLUE = QColor(0, 210, 255)
    TEXT_WHITE = "#FFFFFF"
    TEXT_GREY = "#A0B0C0"

class CustomIcon(QWidget):
    def __init__(self, icon_type="clock", size=20, color=Colors.ACCENT_BLUE):
        super().__init__()
        self.setFixedSize(size, size)
        self.icon_type = icon_type
        self.color = color if isinstance(color, QColor) else QColor(color)
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

class VisualStyle:
    STYLESHEET = f"""
    QLabel {{ color: {Colors.TEXT_WHITE}; font-family: 'Segoe UI', sans-serif; border: none; background: transparent; }}
    QLabel#HeaderTitle {{ color: #00D2FF; font-size: 11px; letter-spacing: 1.5px; font-weight: bold; }}
    
    QTimeEdit {{
        background: rgba(20, 40, 70, 150); color: {Colors.TEXT_WHITE};
        font-size: 38px; border: 1px solid #1E3A5F; border-radius: 12px;
        selection-background-color: #00D2FF;
    }}
    QTimeEdit::up-button, QTimeEdit::down-button {{ width: 0px; border: none; }}

    QCheckBox {{ color: {Colors.TEXT_GREY}; spacing: 8px; font-size: 13px; background: transparent; }}
    QCheckBox::indicator {{ width: 14px; height: 14px; border: 2px solid #1E3A5F; border-radius: 4px; background: transparent; }}
    QCheckBox::indicator:checked {{ background-color: #00D2FF; border-color: #00D2FF; }}

    QPushButton#SaveButton {{
        background-color: rgba(30, 60, 100, 100); color: {Colors.TEXT_WHITE};
        border: 1px solid #1E3A5F; border-radius: 10px; font-size: 14px; font-weight: 600;
    }}
    QPushButton#SaveButton:hover {{ background-color: rgba(0, 210, 255, 30); border-color: #00D2FF; color: #00D2FF; }}
    """

class DaemonApp(DraggableWindow):
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        self.autostart_manager = AutoStartManager()
        self.config = self.db_manager.load()
        self.scheduler_timer = QTimer(self)
        self.scheduler_timer.setSingleShot(True)
        self.scheduler_timer.timeout.connect(self.trigger_alert)
        self.tray_icon = None
        self.confirm_window = None 
        self.init_ui()
        self.setup_tray()
        self.apply_config_to_ui()
        self.schedule_next_run()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QBrush(Colors.BG_MAIN))
        painter.setPen(QPen(Colors.ACCENT_BLUE))
        rect = self.rect().adjusted(1, 1, -1, -1)
        painter.drawRoundedRect(rect, 15, 15)

    def setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QBrush(Colors.ACCENT_BLUE))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(4, 4, 24, 24)
        painter.setBrush(QBrush(QColor("black")))
        painter.drawEllipse(14, 14, 4, 4)
        painter.end()
        self.tray_icon.setIcon(QIcon(pixmap))
        menu = QMenu()
        menu.addAction("Abrir Configuração", self.show_normal)
        menu.addSeparator()
        menu.addAction("Sair Totalmente", QApplication.instance().quit)
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self.on_tray_click)
        self.tray_icon.show()

    def on_tray_click(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick: self.show_normal()

    def show_normal(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def init_ui(self):
        self.setFixedSize(340, 320)
        self.setStyleSheet(VisualStyle.STYLESHEET)
        central = QWidget()
        central.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("DAILY REMINDER")
        title.setObjectName("HeaderTitle")
        close_btn = QPushButton()
        close_btn.setFixedSize(30, 30)
        close_btn.setStyleSheet("background: transparent; border: none;")
        close_icon = CustomIcon("close", 14, Colors.ACCENT_BLUE)
        l_btn = QVBoxLayout(close_btn)
        l_btn.setContentsMargins(0,0,0,0)
        l_btn.addWidget(close_icon)
        close_btn.clicked.connect(self.hide_and_save)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(close_btn)
        
        lbl_info = QLabel("Horário do aviso")
        lbl_info.setStyleSheet("font-weight: bold; font-size: 13px; margin-top: 10px;")

        h_time = QHBoxLayout()
        self.time_input = QTimeEdit()
        self.time_input.setDisplayFormat("HH:mm")
        self.time_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_input.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.time_input.setFixedHeight(60)
        h_time.addWidget(self.time_input)

        self.chk_auto = QCheckBox("Iniciar com o Sistema")
        self.chk_auto.setCursor(Qt.CursorShape.PointingHandCursor)
        
        btn_save = QPushButton("Salvar e Ativar")
        btn_save.setObjectName("SaveButton")
        btn_save.setFixedHeight(40)
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.clicked.connect(self.hide_and_save)

        main_layout.addLayout(header)
        main_layout.addWidget(lbl_info)
        main_layout.addLayout(h_time)
        main_layout.addStretch()
        main_layout.addWidget(self.chk_auto)
        main_layout.addWidget(btn_save)

    def apply_config_to_ui(self):
        t = QTime.fromString(self.config.target_time, "HH:mm")
        self.time_input.setTime(t)
        self.chk_auto.setChecked(self.config.autostart_enabled)

    def schedule_next_run(self):
        target_time = QTime.fromString(self.config.target_time, "HH:mm")
        now = QTime.currentTime()
        msecs = now.msecsTo(target_time)
        if msecs <= 0: msecs += 24 * 3600 * 1000
        self.scheduler_timer.start(msecs)

    def hide_and_save(self):
        self.config.target_time = self.time_input.time().toString("HH:mm")
        self.config.autostart_enabled = self.chk_auto.isChecked()
        self.db_manager.save(self.config)
        self.autostart_manager.set_autostart(self.config.autostart_enabled)
        self.schedule_next_run()
        self.hide()
        self.tray_icon.showMessage("Daily Reminder", f"Agendado para {self.config.target_time}", QSystemTrayIcon.MessageIcon.Information, 2000)

    def trigger_alert(self):
        self.alert_window = NotificationWindow(on_register_callback=self.start_confirmation_timer)
        self.alert_window.show()

    def start_confirmation_timer(self):
        QTimer.singleShot(600000, self.show_confirmation_window)

    def show_confirmation_window(self):
        self.confirm_window = ConfirmationWindow(
            on_yes=self.schedule_next_run,
            on_no=self.reopen_link
        )
        self.confirm_window.show()

    def reopen_link(self):
        webbrowser.open("https://rifyt.com/login")
        self.schedule_next_run()

class NotificationWindow(DraggableWindow): 
    def __init__(self, on_register_callback):
        super().__init__()
        self.on_register = on_register_callback
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(320, 110)
        screen_geo = QApplication.primaryScreen().availableGeometry()
        self.move(screen_geo.x() + 20, screen_geo.y() + 50) 
        central = QWidget()
        central.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(5, 5, 5, 5)
        self.card = QFrame()
        self.card.setStyleSheet(f"background-color: #050F1E; border: 2px solid #00D2FF; border-radius: 12px;")
        card_layout = QVBoxLayout(self.card)
        lbl_title = QLabel("⏰ HORA DA DAILY")
        lbl_title.setStyleSheet("color: #00D2FF; font-weight: bold; font-size: 14px; border: none;")
        btn_action = QPushButton("REGISTRAR AGORA")
        btn_action.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_action.setStyleSheet("background-color: rgba(30, 60, 100, 200); color: white; border: 1px solid #1E3A5F; border-radius: 6px; padding: 8px; font-weight: bold;")
        btn_action.clicked.connect(self._handle_click)
        card_layout.addWidget(lbl_title)
        card_layout.addWidget(btn_action)
        layout.addWidget(self.card)

    def _handle_click(self):
        self.hide()
        webbrowser.open("https://rifyt.com/login")
        self.on_register()
        self.close()

class ConfirmationWindow(DraggableWindow):
    def __init__(self, on_yes, on_no):
        super().__init__()
        self.on_yes = on_yes
        self.on_no = on_no
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(320, 130)
        screen_geo = QApplication.primaryScreen().availableGeometry()
        x_pos = screen_geo.width() - 340 
        self.move(x_pos, screen_geo.y() + 50) 
        central = QWidget()
        central.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(5, 5, 5, 5)
        self.card = QFrame()
        self.card.setStyleSheet(f"background-color: #050F1E; border: 2px solid #00D2FF; border-radius: 12px;")
        card_layout = QVBoxLayout(self.card)
        lbl = QLabel("Você registrou a Daily?")
        lbl.setStyleSheet("color: white; font-size: 14px; font-weight: bold; border: none;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn_layout = QHBoxLayout()
        btn_no = QPushButton("Não")
        btn_no.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_no.setStyleSheet("background-color: rgba(60, 20, 20, 200); color: #FF4444; border: 1px solid #FF4444; border-radius: 6px; padding: 8px; font-weight: bold;")
        btn_no.clicked.connect(self._handle_no)
        btn_yes = QPushButton("Sim")
        btn_yes.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_yes.setStyleSheet("background-color: rgba(20, 60, 20, 200); color: #00FF88; border: 1px solid #00FF88; border-radius: 6px; padding: 8px; font-weight: bold;")
        btn_yes.clicked.connect(self._handle_yes)
        btn_layout.addWidget(btn_no)
        btn_layout.addWidget(btn_yes)
        card_layout.addWidget(lbl)
        card_layout.addLayout(btn_layout)
        layout.addWidget(self.card)

    def _handle_yes(self):
        self.hide()
        self.on_yes()
        self.close()

    def _handle_no(self):
        self.hide()
        self.on_no()
        self.close()

if __name__ == "__main__":
    lock_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.TempLocation) + "/daily_reminder_v12.lock"
    lock = QLockFile(lock_path)
    lock.setStaleLockTime(3000)
    if not lock.tryLock(): sys.exit(0)

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    
    window = DaemonApp()
    if "--minimized" not in sys.argv: window.show()
    sys.exit(app.exec())
