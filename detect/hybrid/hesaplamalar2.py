# ============================================
# file: hesaplamalar2.py
# Öğrenci bazlı süre ve dikkat oranı hesaplama (30 sn kaybolma toleransı ile)
# ============================================

from __future__ import annotations

import time
from typing import Dict, Set, Optional
import sqlite3

# Varsayılan DB yolu (gerekirse hybrid.py'den parametre olarak da geliyor)
DB_PATH = "/home/krm/Desktop/dlibenv/OYS/ogrenciler.db"

# ---- Genel prensip ----
# 1) Öğrenci görünüyorsa -> geçen süre "visible_total"e eklenir.
# 2) Öğrenci kaybolduğunda -> her kaybolma serisi için en fazla 30 sn "grace_total"e eklenir.
#    30 saniyeyi aşan kaybolma süresi artık dikkat süresine eklenmez.
# 3) Öğrenci geri döndüğünde -> yeni görünme süresi kaldığı yerden eklenmeye devam eder.
# 4) Dikkat süresi = visible_total + grace_total
# 5) Dikkat oranı = (visible_total + grace_total) / (ilk_görülme_anından_itibaren_geçen_süre)

# ---- İç veri yapısı ----
# tracking[okul_no] = {
#     "first_seen": float,
#     "state": "visible" | "invisible",
#     "state_since": float,
#     "visible_total": float,
#     "grace_total": float,
#     "grace_in_streak": float,  # o anki kaybolma serisi içinde kullanılan tolerans
# }
tracking: Dict[str, Dict[str, float | str]] = {}

# Sabit tolerans (saniye)
MISSING_TOLERANCE_SECONDS = 30.0


def _ensure_student(okul_no: str, now: Optional[float] = None) -> None:
    """Öğrenciyi takipte başlatır; ilk görünme anını işaretler (neden: oran paydasını doğru tutmak)."""
    if okul_no in tracking:
        return
    ts = time.time() if now is None else now
    tracking[okul_no] = {
        "first_seen": ts,
        "state": "visible",
        "state_since": ts,
        "visible_total": 0.0,
        "grace_total": 0.0,
        "grace_in_streak": 0.0,
    }


def reset_tracking() -> None:
    """Ders başlangıcında çağrılır; tüm RAM takibini sıfırlar."""
    tracking.clear()


def mark_seen(okul_no: str, now: Optional[float] = None) -> None:
    """
    Bu frame'de öğrenciyi gördüğümüzü bildirir.
    Neden sadece başlatıyoruz: süre birikimi tek noktadan (update_missing) yönetilsin, çifte sayım olmasın.
    """
    _ensure_student(okul_no, now=now)


def update_missing(recognized_ids: Set[str], now: Optional[float] = None, timeout: float = MISSING_TOLERANCE_SECONDS) -> None:
    """
    Bu frame için görünür/görünmez öğrencilerin sürelerini günceller.
    - recognized_ids: Bu frame'de tanınan okul numaraları.
    - now: Zaman damgası. None ise time.time().
    - timeout: Kaybolma başına en fazla eklenecek tolerans (varsayılan 30 sn).
    """
    ts = time.time() if now is None else now

    # Takipte olup bu frame'de de görünenlerin görünür sürelerini güncelle
    for okul_no, st in list(tracking.items()):
        state = st["state"]
        state_since = float(st["state_since"])

        if okul_no in recognized_ids:
            # Görünüyor
            if state == "visible":
                dt = ts - state_since
                if dt > 0:
                    st["visible_total"] = float(st["visible_total"]) + dt
                    st["state_since"] = ts
            else:
                # invisible -> visible
                st["state"] = "visible"
                st["state_since"] = ts
                st["grace_in_streak"] = 0.0
        else:
            # Görünmüyor
            if state == "visible":
                # visible -> invisible
                dt = ts - state_since
                if dt > 0:
                    st["visible_total"] = float(st["visible_total"]) + dt
                st["state"] = "invisible"
                st["state_since"] = ts
                st["grace_in_streak"] = 0.0
            else:
                # invisible serisinde tolerans ekle (maks. timeout)
                dt = ts - state_since
                if dt > 0:
                    used = float(st["grace_in_streak"])
                    can_add = max(0.0, timeout - used)
                    add_grace = min(dt, can_add)
                    if add_grace > 0:
                        st["grace_total"] = float(st["grace_total"]) + add_grace
                    st["grace_in_streak"] = used + dt
                    st["state_since"] = ts

    # Bu frame'de yeni görünen öğrenciler varsa başlat
    for okul_no in recognized_ids:
        if okul_no not in tracking:
            _ensure_student(okul_no, now=ts)


def _compute_final_stats_for(okul_no: str, at_time: float, timeout: float = MISSING_TOLERANCE_SECONDS) -> tuple[float, float, float]:
    """
    Bir öğrenci için (at_time anında) nihai görünür, tolerans ve toplam geçen süreyi döndürür.
    Dönüş: (visible_total_final, grace_total_final, elapsed_total)
    """
    st = tracking[okul_no]
    first_seen = float(st["first_seen"])
    visible_total = float(st["visible_total"])
    grace_total = float(st["grace_total"])
    state = st["state"]
    state_since = float(st["state_since"])

    if state == "visible":
        # Son görünür dilimi de ekle
        dt = at_time - state_since
        if dt > 0:
            visible_total += dt
    else:
        # Son kaybolma dilimi için kalan toleransı ekle
        dt = at_time - state_since
        if dt > 0:
            used = float(st["grace_in_streak"])
            can_add = max(0.0, timeout - used)
            add_grace = min(dt, can_add)
            if add_grace > 0:
                grace_total += add_grace

    elapsed = max(0.0, at_time - first_seen)
    return visible_total, grace_total, elapsed


def write_attentions_to_db(record_start_time: float, db_path: str = DB_PATH) -> None:
    """
    Ders sonunda çağrılır. Her öğrenci için dikkat oranını DB'ye yazar.
    Not: Bu sürüm yüzde (0–100) olarak kaydeder.
    """
    now = time.time()

    try:
        con = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES, check_same_thread=False)
        cur = con.cursor()

        for okul_no in list(tracking.keys()):
            vis, grace, elapsed = _compute_final_stats_for(okul_no, at_time=now, timeout=MISSING_TOLERANCE_SECONDS)
            attention_seconds = vis + grace

            # 0–1 oran -> yüzde (0–100)
            if elapsed > 0.0:
                ratio_0_1 = attention_seconds / elapsed
            else:
                ratio_0_1 = 0.0

            percent = max(0.0, min(100.0, ratio_0_1 * 100.0))  # uç değerler için kırp
            # İsterseniz yuvarlama: percent = round(percent, 2)

            # Şema farklılıklarına toleranslı güncelleme (dikkat_sure saniye cinsinden kalır)

            #ondaliklari kaldirdik.
            percent=int(percent)

            try:
                cur.execute(
                    "UPDATE ogrenciler SET dikkat_orani=?, dikkat_sure=? WHERE okul_numarasi=?",
                    (percent, attention_seconds, okul_no),
                )
            except sqlite3.OperationalError:
                cur.execute(
                    "UPDATE ogrenciler SET dikkat_orani=? WHERE okul_numarasi=?",
                    (percent, okul_no),
                )

        con.commit()
    finally:
        try:
            con.close()
        except Exception:
            pass


def mark_present(okul_no: str, db_path: str = DB_PATH) -> None:
    """Yoklamayı 'var' yapar (idempotent; tekrar çalışsa da sorun olmaz)."""
    try:
        con = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES, check_same_thread=False)
        cur = con.cursor()
        cur.execute(
            "UPDATE ogrenciler SET yoklama='var' WHERE okul_numarasi=?",
            (okul_no,),
        )
        con.commit()
    finally:
        try:
            con.close()
        except Exception:
            pass
