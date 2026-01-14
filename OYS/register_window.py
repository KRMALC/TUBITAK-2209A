from pathlib import Path
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
from PyQt5.QtCore import Qt

USERS_TXT = Path(__file__).resolve().parent / "users.txt"


class RegisterWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kaydol")
        self.setFixedSize(350, 180)

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignTop)

        self.ed_user = QLineEdit()
        self.ed_user.setPlaceholderText("Kullanıcı adı")

        self.ed_pass = QLineEdit()
        self.ed_pass.setPlaceholderText("Şifre")
        self.ed_pass.setEchoMode(QLineEdit.Password)

        self.ed_pass2 = QLineEdit()
        self.ed_pass2.setPlaceholderText("Şifre (tekrar)")
        self.ed_pass2.setEchoMode(QLineEdit.Password)

        btn = QPushButton("Kaydol")
        btn.clicked.connect(self.register_user)

        layout.addWidget(QLabel("Yeni Kullanıcı Kaydı"),alignment=Qt.AlignCenter)
        layout.addWidget(self.ed_user)
        layout.addWidget(self.ed_pass)
        layout.addWidget(self.ed_pass2)
        layout.addWidget(btn)

        self.setLayout(layout)

    def register_user(self):
        u = self.ed_user.text().strip()
        p1 = self.ed_pass.text()
        p2 = self.ed_pass2.text()

        if not u or not p1 or not p2:
            QMessageBox.warning(self, "Hata", "Tüm alanları doldurun.")
            return

        if p1 != p2:
            QMessageBox.warning(self, "Hata", "Şifreler aynı değil.")
            return

        # Var olan kullanıcıları oku
        users = {}
        if USERS_TXT.exists():
            for line in USERS_TXT.read_text(encoding="utf-8").splitlines():
                if ":" in line:
                    name, pwd = line.split(":", 1)
                    users[name.strip()] = pwd.strip()

        if u in users:
            QMessageBox.warning(self, "Hata", "Bu kullanıcı adı zaten kayıtlı.")
            return

        # Yeni satır için prefix (dosya boş değilse ve zaten düzgün satırlar varsa)
        prefix = ""
        if USERS_TXT.exists():
            content = USERS_TXT.read_text(encoding="utf-8")
            if content.strip() != "" and not content.endswith("\n"):
                prefix = "\n"

        # Yeni kullanıcıyı ekle
        with open(USERS_TXT, "a", encoding="utf-8") as f:
            f.write(f"{prefix}{u}:{p1}\n")

        QMessageBox.information(self, "Başarılı", "Kullanıcı kaydedildi.")
        self.close()
