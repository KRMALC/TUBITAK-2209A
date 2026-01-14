# modern_ai_chat.py
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QScrollArea, QApplication
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap, QFont
from ai_engine import chate_sor

TUBITAK_LOGO_PATH = "/home/krm/Desktop/dlibenv/OYS/sss.png"   # LOGO YOLUNU BURAYA KOY


CHAT_STYLES = """
QLabel#assistantBubble {
    background: #ffffff;
    border-radius: 18px;
    padding: 14px;
    border: 1px solid #dcdcdc;
    font-size: 14px;
    color: #222;
    max-width: 420px;
}

QLabel#userBubble {
    background: #4e8cff;
    color: white;
    border-radius: 18px;
    padding: 14px;
    font-size: 14px;
    max-width: 420px;
}

QLabel#typing {
    background: #ffffff;
    border: 1px solid #dcdcdc;
    border-radius: 18px;
    padding: 12px;
    font-size: 14px;
    color: #222;
    max-width: 60px;
    font-style: italic;
}
"""


class AIArayuz(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Yapay Zeka Asistanı")
        self.setMinimumSize(750, 500)

        self.setStyleSheet(CHAT_STYLES)

        main = QVBoxLayout(self)

        # ------- LOGO + CHAT ---------
        top_area = QHBoxLayout()
        main.addLayout(top_area)

        # Sol logo alanı
        self.logo_label = QLabel()
        pix = QPixmap(TUBITAK_LOGO_PATH).scaled(90, 90, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.logo_label.setPixmap(pix)
        self.logo_label.setAlignment(Qt.AlignTop)
        top_area.addWidget(self.logo_label)

        # Scroll chat alanı
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)

        self.chat_container = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setAlignment(Qt.AlignTop)

        self.scroll.setWidget(self.chat_container)
        top_area.addWidget(self.scroll, stretch=1)

        # ------- INPUT ---------
        bottom = QHBoxLayout()
        bottom.addSpacing(95)
        self.input = QLineEdit()
        self.input.setPlaceholderText("Mesajınızı yazınız...")
        send_btn = QPushButton("Gönder")
        send_btn.clicked.connect(self.send_message)
        bottom.addWidget(self.input)
        bottom.addWidget(send_btn)
        main.addLayout(bottom)

        # typing animasyonu
        self.typing_label = None
        self.dot_state = 0
        self.typing_timer = QTimer()
        self.typing_timer.timeout.connect(self.animate_typing)

    # ---------------- BALON FONKSİYONLARI ----------------------

    def add_assistant_bubble(self, text):
        row = QHBoxLayout()

    # Sol panelde zaten logo var, burada eklemiyoruz
        bubble = QLabel(text)
        bubble.setObjectName("assistantBubble")
        bubble.setWordWrap(True)

        row.addSpacing(10)  # sol logonun hizasına boşluk
        row.addWidget(bubble)
        row.addStretch()

        self.chat_layout.addLayout(row)
        self.scroll_to_bottom()

    def add_user_bubble(self, text):
        row = QHBoxLayout()

        bubble = QLabel(text)
        bubble.setObjectName("userBubble")
        bubble.setWordWrap(True)

        row.addStretch()
        row.addWidget(bubble)

        self.chat_layout.addLayout(row)
        self.scroll_to_bottom()

    # ---------------- TYPING INDICATOR ----------------------

    def start_typing_indicator(self):
        row = QHBoxLayout()

        # Sol panelde logo olduğu için burada logo EKLEMİYORUZ.
        # Sadece logonun kapladığı alan kadar boşluk bırakıyoruz.
        row.addSpacing(70)   # 70 px → paneldeki logonun genişliği kadar

        lbl = QLabel("∙")
        lbl.setObjectName("typing")

        row.addWidget(lbl)
        row.addStretch()

        self.typing_label = lbl
        self.typing_timer.start(300)

        self.chat_layout.addLayout(row)
        self.scroll_to_bottom()


    def stop_typing_indicator(self):
        if self.typing_label:
            self.typing_label.deleteLater()
            self.typing_label = None
        self.typing_timer.stop()

    def animate_typing(self):
        if not self.typing_label:
            return
        dots = ["∙", "∙∙", "∙∙∙"]
        self.typing_label.setText(dots[self.dot_state])
        self.dot_state = (self.dot_state + 1) % 3

    # ---------------- GÖNDERME - DEMO ------------------------

    def send_message(self):
        txt = self.input.text().strip()
        if not txt:
            return
        
        self.add_user_bubble(txt)
        self.input.clear()

        self.start_typing_indicator()

        QTimer.singleShot(800, lambda: self.cevap_al(txt))

    def cevap_al(self,user_text):
        cevap=chate_sor(user_text)
        self.stop_typing_indicator()
        self.add_assistant_bubble(cevap)

    # --------------------------------------------------------
    def scroll_to_bottom(self):
        self.scroll.verticalScrollBar().setValue(
            self.scroll.verticalScrollBar().maximum()
        )


if __name__ == "__main__":
    app = QApplication([])
    ui = AIArayuz()
    ui.show()
    app.exec_()
