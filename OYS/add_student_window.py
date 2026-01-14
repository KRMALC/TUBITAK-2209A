from PyQt5.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QMessageBox, QFileDialog
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal

from veritabani import ogrenci_ekle
import numpy as np
import face_recognition
import cv2
from ultralytics import YOLO

# ============================================================
# === BİRDEN FAZLA FOTOĞRAFTAN EMBEDDING ÇIKARAN THREAD ===
# ============================================================

class MultiEmbeddingWorker(QThread):
    finished = pyqtSignal(np.ndarray)
    error = pyqtSignal(str)

    def __init__(self, file_paths):
        super().__init__()
        self.file_paths = file_paths

    def run(self):
        try:
            embeddings = []

            for path in self.file_paths:
                img = cv2.imread(path)
                if img is None:
                    continue

                rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                boxes = face_recognition.face_locations(rgb)

                if len(boxes) == 0:
                    continue  # yüz yoksa fotoğrafı atla

                encs = face_recognition.face_encodings(rgb, boxes,model="large")
                if len(encs) == 0:
                    continue

                embeddings.append(encs[0])

            if len(embeddings) == 0:
                self.error.emit("Hiçbir fotoğraftan yüz çıkarılamadı.")
                return

            # ORTALAMA EMBEDDING (daha stabil tanıma sağlar)
            final_emb = np.mean(np.array(embeddings), axis=0)

            self.finished.emit(final_emb)

        except Exception as e:
            self.error.emit(str(e))



# ============================================================
# === ÖĞRENCİ EKLEME PENCERESİ ===
# ============================================================

class AddStudentWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Öğrenci Ekle")
        self.setGeometry(550, 350, 400, 300)

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignTop)

        # Form alanları
        self.ad_input = QLineEdit()
        self.ad_input.setPlaceholderText("Ad")

        self.soyad_input = QLineEdit()
        self.soyad_input.setPlaceholderText("Soyad")

        self.okul_no_input = QLineEdit()
        self.okul_no_input.setPlaceholderText("Okul Numarası")

        layout.addWidget(QLabel("Ad:"))
        layout.addWidget(self.ad_input)

        layout.addWidget(QLabel("Soyad:"))
        layout.addWidget(self.soyad_input)

        layout.addWidget(QLabel("Okul Numarası:"))
        layout.addWidget(self.okul_no_input)

        # Çoklu fotoğraf seçme butonu
        self.vector_btn = QPushButton("Yüz Vektörü Al (25–40 Fotoğraf)")
        self.vector_btn.clicked.connect(self.select_photos)
        layout.addWidget(self.vector_btn)

        # Kaydet butonu
        self.save_btn = QPushButton("Kaydet")
        self.save_btn.clicked.connect(self.kaydet)
        layout.addWidget(self.save_btn)

        self.setLayout(layout)

        # Embedding burada tutulacak
        self.embedding_vector = None



    # ============================================================
    # === ÖĞRENCİYİ KAYDET ===
    # ============================================================

    def kaydet(self):
        ad = self.ad_input.text().strip()
        soyad = self.soyad_input.text().strip()
        okul_no = self.okul_no_input.text().strip()

        if ad == "" or soyad == "" or okul_no == "":
            QMessageBox.warning(self, "Uyarı", "Lütfen tüm alanları doldurun.")
            return

        if self.embedding_vector is None:
            QMessageBox.warning(self, "Uyarı", "Lütfen yüz vektörü alın.")
            return

        basarili = ogrenci_ekle(ad, soyad, okul_no, self.embedding_vector)

        if basarili:
            QMessageBox.information(self, "Başarılı", "Öğrenci kaydı oluşturuldu.")
            self.close()
        else:
            QMessageBox.critical(self, "Hata", "Kayıt sırasında bir hata oluştu.")



    # ============================================================
    # === ÇOKLU FOTOĞRAF SEÇME ===
    # ============================================================

    def select_photos(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "25–40 Yüz Fotoğrafı Seçin",
            "",
            "Image Files (*.jpg *.jpeg *.png)"
        )

        if not file_paths:
            return

        if len(file_paths) < 3:
            QMessageBox.warning(self, "Uyarı", "En az 3 fotoğraf seçmelisiniz (Önerilen: 25–40).")
            return

        QMessageBox.information(
            self,
            "Bekleyin",
            f"{len(file_paths)} fotoğraftan embedding çıkarılıyor. Lütfen bekleyin…"
        )

        # Thread başlat
        self.worker = MultiEmbeddingWorker(file_paths)
        self.worker.finished.connect(self.embedding_alindi)
        self.worker.error.connect(self.embedding_hatasi)
        self.worker.start()



    # ============================================================
    # === EMBEDDING ALINDI ===
    # ============================================================

    def embedding_alindi(self, vector):
        self.embedding_vector = vector
        QMessageBox.information(self, "Başarılı", "Tüm fotoğraflardan ortalama yüz vektörü çıkarıldı.")

    def embedding_hatasi(self, hata):
        QMessageBox.warning(self, "Hata", hata)
