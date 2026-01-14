# ============================================
# file: veritabani.py
# ============================================

import sqlite3
import numpy as np
from typing import List, Tuple, Optional

DB_PATH = "/home/krm/Desktop/dlibenv/OYS/ogrenciler.db"


def get_connection() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def tablo_olustur() -> None:
    """
    Veritabanı ilk kez oluşturulurken tabloyu oluşturur.
    Bu sürümde dikkat_orani sütunu doğrudan eklenmiştir.
    """
    con = get_connection()
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ogrenciler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ad TEXT NOT NULL,
            soyad TEXT NOT NULL,
            okul_numarasi TEXT NOT NULL UNIQUE,
            yuz_vektoru BLOB NOT NULL,
            yoklama TEXT DEFAULT 'yok',
            dikkat_orani REAL DEFAULT 0
        );
    """)
    con.commit()
    con.close()


def _vec_to_blob(vec: np.ndarray) -> bytes:
    """
    Numpy 128-float32 vektörü → bytes.
    """
    v = np.asarray(vec, dtype=np.float32).reshape(128)
    return v.tobytes()


def _blob_to_vec(blob: bytes) -> Optional[np.ndarray]:
    """
    Veritabanındaki BLOB → numpy 128-float32 vektörü.
    """
    b = bytes(blob)

    if len(b) == 512:  # float32 * 128
        v = np.frombuffer(b, dtype=np.float32)
    elif len(b) == 1024:  # float64 * 128
        v = np.frombuffer(b, dtype=np.float64).astype(np.float32)
    else:
        return None

    return v if v.size == 128 and np.isfinite(v).all() else None


def ogrenci_ekle(ad: str, soyad: str, okul_numarasi: str, yuz_vektoru: np.ndarray) -> bool:
    """
    Yeni öğrenci ekler.
    yoklama = 'yok', dikkat_orani = 0 olarak başlar.
    """
    try:
        tablo_olustur()
        blob = _vec_to_blob(yuz_vektoru)

        con = get_connection()
        cur = con.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO ogrenciler
            (ad, soyad, okul_numarasi, yuz_vektoru, yoklama, dikkat_orani)
            VALUES(?,?,?,?,?,?)
        """, (ad, soyad, okul_numarasi, sqlite3.Binary(blob), "yok", 0.0))

        con.commit()
        con.close()
        return True

    except Exception as e:
        print("DB Hata:", e)
        return False


def yoklama_guncelle(okul_numarasi: str, durum: str) -> None:
    """
    durum: 'var' veya 'yok'
    """
    con = get_connection()
    cur = con.cursor()
    cur.execute(
        "UPDATE ogrenciler SET yoklama=? WHERE okul_numarasi=?",
        (durum, okul_numarasi)
    )
    con.commit()
    con.close()


def dikkat_orani_guncelle(okul_numarasi: str, oran: float) -> None:
    """
    Öğrencinin dikkat oranını (0–100) günceller.
    """
    con = get_connection()
    cur = con.cursor()
    cur.execute(
        "UPDATE ogrenciler SET dikkat_orani=? WHERE okul_numarasi=?",
        (float(oran), okul_numarasi)
    )
    con.commit()
    con.close()


def ogrencileri_cek() -> List[Tuple[str, str, str, np.ndarray, str, float]]:
    """
    Tüm öğrencileri çeker:
    (ad, soyad, okul_no, yüz vektörü, yoklama, dikkat_orani)
    """
    con = get_connection()
    cur = con.cursor()
    cur.execute("""
        SELECT ad, soyad, okul_numarasi, yuz_vektoru, yoklama, dikkat_orani
        FROM ogrenciler
    """)

    rows = cur.fetchall()
    con.close()

    out = []
    for ad, soyad, no, blob, yoklama, dikkat in rows:
        if isinstance(blob, (bytes, bytearray, memoryview)):
            v = _blob_to_vec(blob)
            if v is not None:
                out.append((ad, soyad, no, v, yoklama, float(dikkat)))

    return out


# Veritabanı oluşturulsun
tablo_olustur()

