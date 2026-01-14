# file: forgot_password_window.py

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
)
from PyQt5.QtCore import Qt
from pathlib import Path

USERS_TXT = Path(__file__).resolve().parent / "users.txt"


class ForgotPasswordWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Şifremi Unuttum")
        self.setFixedSize(350, 150)

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignTop)

        self.ed_user = QLineEdit()
        self.ed_user.setPlaceholderText("Kullanıcı adı")

        self.ed_new = QLineEdit()
        self.ed_new.setPlaceholderText("Yeni şifre")
        self.ed_new.setEchoMode(QLineEdit.Password)

        btn = QPushButton("Şifreyi Güncelle")
        btn.clicked.connect(self.reset_password)

        layout.addWidget(QLabel("Şifre Sıfırlama"),alignment=Qt.AlignCenter)
        layout.addWidget(self.ed_user)
        layout.addWidget(self.ed_new)
        layout.addWidget(btn)

        self.setLayout(layout)

    def reset_password(self):
        u = self.ed_user.text().strip()
        new_pass = self.ed_new.text().strip()

        if not u or not new_pass:
            QMessageBox.warning(self, "Hata", "Tüm alanları doldurun.")
            return

        # Kullanıcıları oku
        if not USERS_TXT.exists():
            QMessageBox.warning(self, "Hata", "Hiç kullanıcı kayıtlı değil.")
            return

        lines = USERS_TXT.read_text().splitlines()
        updated = False
        new_lines = []

        for line in lines:
            if ":" not in line:
                continue
            name, pwd = line.split(":", 1)
            if name.strip() == u:
                new_lines.append(f"{u}:{new_pass}")
                updated = True
            else:
                new_lines.append(line)

        if not updated:
            QMessageBox.warning(self, "Hata", "Bu kullanıcı bulunamadı.")
            return

        USERS_TXT.write_text("\n".join(new_lines), encoding="utf-8")
        QMessageBox.information(self, "Başarılı", "Şifre güncellendi.")
        self.close()
