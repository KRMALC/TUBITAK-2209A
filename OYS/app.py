import sys
import subprocess
from pathlib import Path
from typing import Optional, Tuple

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QHBoxLayout, QDialog,
    QLabel, QSplashScreen, QFrame, QSizePolicy, QLineEdit, QMessageBox
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap, QGuiApplication, QPainter, QPalette, QColor, QFont

from add_student_window import AddStudentWindow
from ai_chatbox import AIArayuz
from register_window import RegisterWindow
from forgot_password_window import ForgotPasswordWindow

LOGIN_BG = Path("/home/krm/Desktop/dlibenv/OYS/login.png")   # Login arkaplanı (gönderdiğin görsel)
APP_BG   = Path("/home/krm/Desktop/dlibenv/OYS/arka_tema.jpg")  # Uygulama arkaplanı (MainWindow)
APP_LOGO = Path("/home/krm/Desktop/dlibenv/OYS/logo.png")       # Uygulama logosu (opsiyonel)
USERS_TXT = Path(__file__).resolve().parent / "users.txt"       # kullanıcı:sifre satırları

def load_pixmap(path: Path) -> Optional[QPixmap]:
    if path.exists() and path.is_file():
        pm = QPixmap(str(path))
        if not pm.isNull():
            return pm
    return None

def read_users_from_file(fp: Path) -> dict:
    """Basit dosya formatı: her satır 'kullanici:sifre' (file-based auth)."""
    users = {}
    if not fp.exists():
        return users
    for line in fp.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        u, p = line.split(":", 1)
        users[u.strip()] = p.strip()
    return users

def check_credentials(username: str, password: str) -> bool:
    """Önce users.txt, yoksa hardcoded default (admin/1234)."""
    users = read_users_from_file(USERS_TXT)
    if users:
        return users.get(username, "") == password
    return username == "admin" and password == "1234"

# --- Login Window 
class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Giriş")
        self.setMinimumSize(520, 360)
        self._bg = load_pixmap(LOGIN_BG)
        self._login_logo = load_pixmap(APP_LOGO)

        pal = self.palette()
        pal.setColor(QPalette.Window, QColor(0, 0, 0))
        self.setAutoFillBackground(True)
        self.setPalette(pal)

        self._build_ui()

    def paintEvent(self, e):
        super().paintEvent(e)
        p = QPainter(self)
        if self._bg:
            bg = self._bg.scaled(self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            x = (self.width() - bg.width()) // 2
            y = (self.height() - bg.height()) // 2
            p.drawPixmap(x, y, bg.width(), bg.height(), bg)
        p.fillRect(self.rect(), QColor(0, 0, 0, 110))  # scrim/overlay

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(0)

        panel = QFrame()
        panel.setObjectName("panel")
        panel.setStyleSheet("""
            QFrame#panel {
                background: rgba(20, 25, 30, 0.35);
                border: 1px solid rgba(255,255,255,0.28);
                border-radius: 12px;
            }
            QLabel { color: rgba(255,255,255,0.96); font-size: 14px; }
            QLineEdit {
                color: #fff;
                background: rgba(0,0,0,0.35);
                border: 1px solid rgba(255,255,255,0.30);
                border-radius: 8px;
                padding: 8px 10px;
                font-size: 14px;
            }
            QPushButton {
                color: rgba(255,255,255,0.96);
                background: rgba(0,0,0,0.45);
                border: 1px solid rgba(255,255,255,0.34);
                border-radius: 10px;
                padding: 10px 14px;
                font-size: 15px;
                min-height: 40px;
            }
            QPushButton:hover { background: rgba(0,0,0,0.55); }
            QPushButton:pressed { background: rgba(0,0,0,0.65); }
        """)
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(20, 20, 20, 20)
        panel_layout.setSpacing(12)

        title = QLabel("Öğrenci Yönetim Sistemi — Giriş")

        # --- Top logo (optional) ---
        if self._login_logo:
            logo_label = QLabel()
            logo_label.setAlignment(Qt.AlignCenter)
            pm = self._login_logo
            # Küçük bir sınır: büyükse küçült (KeepAspectRatio)
            if pm.width() > 200 or pm.height() > 100:
                pm = pm.scaled(200, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_label.setPixmap(pm)
            panel_layout.addWidget(logo_label, 0, Qt.AlignCenter)

        title = QLabel("Öğrenci Yönetim Sistemi — Giriş")
        title.setStyleSheet("font-weight: bold; font-size: 18px;")

        self.ed_user = QLineEdit()
        self.ed_user.setPlaceholderText("Kullanıcı adı (username)")
        self.ed_pass = QLineEdit()
        self.ed_pass.setPlaceholderText("Şifre (password)")
        self.ed_pass.setEchoMode(QLineEdit.Password)

        self.btn_login = QPushButton("Giriş Yap")
        self.btn_login.clicked.connect(self._on_login_clicked)

        panel_layout.addWidget(title, 0, Qt.AlignCenter)
        panel_layout.addWidget(self.ed_user)
        panel_layout.addWidget(self.ed_pass)
        panel_layout.addWidget(self.btn_login)

        # Ek aksiyonlar: Kaydol / Şifremi Unuttum / Çıkış
        self.btn_register = QPushButton("Kaydol")
        self.btn_forgot   = QPushButton("Şifremi Unuttum")
        self.btn_exit     = QPushButton("Çıkış")
        
        # Basit yerleşim: alt alta

        panel_layout.addWidget(self.btn_register)
        panel_layout.addWidget(self.btn_forgot)
        panel_layout.addWidget(self.btn_exit)

        # Sinyaller
        self.btn_register.clicked.connect(self._on_register_clicked)
        self.btn_forgot.clicked.connect(self._on_forgot_clicked)
        self.btn_exit.clicked.connect(QApplication.instance().quit)

        # Ortala
        root.addStretch(1)
        h = QHBoxLayout()
        h.addStretch(1)
        h.addWidget(panel, 0, Qt.AlignCenter)
        h.addStretch(1)
        root.addLayout(h)
        root.addStretch(1)

    def _on_login_clicked(self):
        u = self.ed_user.text().strip()
        p = self.ed_pass.text()
        if check_credentials(u, p):
            self.accept_login()
        else:
            QMessageBox.warning(self, "Hatalı Giriş", "Kullanıcı adı veya şifre yanlış.")
    
    # Yeni butonlar için basit handler’lar (placeholder)
    def _on_register_clicked(self):
        self.reg = RegisterWindow()
        self.reg.show()

    def _on_forgot_clicked(self):
        self.fg = ForgotPasswordWindow()
        self.fg.show()

    def accept_login(self):
        # Neden: dışarıya basit bir sinyal yerine doğrudan kapatıyoruz; main akış gösterir.
        self.close()
        self.parent_open_main()  # main() içinde atanacak

# --- Main Window (senin işlevlerle, sadece görsel modern) --------------------
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Öğrenci Yönetim Sistemi")
        self.setMinimumSize(520, 720)
        self._bg_pixmap = load_pixmap(APP_BG)
        self._logo_pixmap = load_pixmap(APP_LOGO)

        pal = self.palette()
        pal.setColor(QPalette.Window, QColor(0, 0, 0))
        self.setAutoFillBackground(True)
        self.setPalette(pal)

        self._build_ui()

    def paintEvent(self, e):
        super().paintEvent(e)
        p = QPainter(self)
        if self._bg_pixmap:
            bg = self._bg_pixmap.scaled(self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            x = (self.width() - bg.width()) // 2
            y = (self.height() - bg.height()) // 2
            p.drawPixmap(x, y, bg.width(), bg.height(), bg)
        p.fillRect(self.rect(), QColor(0, 0, 0, 150))

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(0)

        card = QFrame()
        card.setObjectName("card")
        card.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        card.setMaximumWidth(420)
        card.setStyleSheet("""
            QFrame#card {
                background: rgba(20,25,30,0.34);
                border: 1px solid rgba(255,255,255,0.28);
                border-radius: 18px;
            }
            QLabel#title { color: rgba(255,255,255,0.96); }
            QPushButton {
                color: rgba(255,255,255,0.96);
                background: rgba(0,0,0,0.38);
                border: 1px solid rgba(255,255,255,0.34);
                border-radius: 14px;
                padding: 12px 16px;
                font-size: 15px;
                min-height: 54px;
            }
            QPushButton:hover { background: rgba(0,0,0,0.48); }
            QPushButton:pressed { background: rgba(0,0,0,0.56); }
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(16)

        # Logo (opsiyonel)
        if self._logo_pixmap:
            logo_plate = QFrame()
            logo_plate.setStyleSheet("""
                QFrame { background: rgba(255,255,255,0.18);
                         border: 1px solid rgba(255,255,255,0.28);
                         border-radius: 12px; }""")
            lp = QVBoxLayout(logo_plate); lp.setContentsMargins(12, 8, 12, 8)
            logo = QLabel(alignment=Qt.AlignCenter)
            pm = self._logo_pixmap
            if pm.width() > 220 or pm.height() > 120:
                pm = pm.scaled(220, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo.setPixmap(pm)
            lp.addWidget(logo)
            card_layout.addWidget(logo_plate, 0, Qt.AlignCenter)

        title = QLabel("Öğrenci Yönetim Sistemi")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-weight: bold; font-size: 22px;")
        card_layout.addWidget(title)

        # Butonlar (işlevler aynı)
        self.btn_add = QPushButton("Öğrenci Ekle")
        self.btn_add_db = QPushButton("Öğrenci Veritabanı")
        self.btn_add_ai = QPushButton("Yapay Zeka Asistanı")
        self.btn_add_hybrid = QPushButton("Öğrenci Dikkat Analiz Sistemi")

        self.btn_add.clicked.connect(self.open_add_window)
        self.btn_add_db.clicked.connect(self.open_student_list)
        self.btn_add_ai.clicked.connect(self.open_ai)
        self.btn_add_hybrid.clicked.connect(self.open_hybrid)

        card_layout.addWidget(self.btn_add)
        card_layout.addWidget(self.btn_add_db)
        card_layout.addWidget(self.btn_add_ai)
        card_layout.addWidget(self.btn_add_hybrid)

        root.addStretch(1)
        h = QHBoxLayout()
        h.addStretch(1)
        h.addWidget(card, 0, Qt.AlignCenter)
        h.addStretch(1)
        root.addLayout(h)
        root.addStretch(1)

    def open_add_window(self):
        self.add_window = AddStudentWindow()
        self.add_window.show()

    def open_student_list(self):
        db_path = "/home/krm/Desktop/dlibenv/OYS/ogrenciler.db"
        subprocess.Popen(["xdg-open", db_path])

    def open_ai(self):
        self.ai_arayuz = AIArayuz()
        self.ai_arayuz.show()

    def open_hybrid(self):
        self.popup = LoadingPopup(
            message="Sistem başlatılıyor,ilk açılışta biraz uzun sürebilir.Lütfen Bekleyiniz...",
            timeout=3000
        )
        self.popup.show()
        subprocess.Popen(["/home/krm/Desktop/detectenv/hybrid/run_app.sh"])

class LoadingPopup(QDialog):
    def __init__(self, message="Sistem başlatılıyor,\n"
                 "ilk açılışta biraz uzun sürebilir.\n"
                 "Lütfen Bekleyiniz...", timeout=3000):
        super().__init__()
        self.setWindowTitle("Bilgi")
        self.setModal(False)
        self.setFixedSize(350, 180)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.Dialog)

        layout = QVBoxLayout()
        label = QLabel(message)
        label.setStyleSheet("font-size: 15px; font-weight: bold;")
        label.setAlignment(Qt.AlignCenter)
        label.setWordWrap(True)
        layout.addWidget(label)
        self.setLayout(layout)
        QTimer.singleShot(timeout, self.close)

# --- Uygulama akışı (splash -> login -> main) --------------------------------
def main():
    app = QApplication(sys.argv)

    # 1) Login
    login = LoginWindow()

    # Login başarı akışı: basit bağlama
    def open_main_after_login():
        w = MainWindow()
        w.show()
        # MainWindow referansını sakla ki GC olmasın
        app._main_ref = w  # minimal hack; why: scope dışına çıkınca kapanmasın

    login.parent_open_main = open_main_after_login  # LoginWindow.accept_login içinde çağrılır
    login.show()

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
