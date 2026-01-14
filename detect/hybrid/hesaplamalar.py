# file: /mnt/data/hesaplamalar.py
"""
Katılım oranı hesaplama ve durum dosyası yardımcıları.
Tek sorumluluk: current/max/percent hesaplamak ve JSON dosyasını (atomic) yazıp/okumak.
"""
from __future__ import annotations
import json
import os
import tempfile
from typing import Optional, Dict

# Ortak yol: GUI ve Hybrid aynı dosyayı paylaşır
STATS_PATH = os.environ.get("ATTENDANCE_STATS_PATH", "/tmp/attendance_stats.json")

def compute_percent(current: int, max_seen: int) -> int:
    """max 0 ise 0 döner; aksi halde yuvarlanmış yüzde."""
    return int(round((current / max_seen) * 100)) if max_seen > 0 else 0

def update_max(max_seen: int, current: int) -> int:
    """Yeni maksimumu döndürür."""
    return current if current > max_seen else max_seen

def _atomic_write_json(path: str, payload: Dict) -> None:
    """Yarım yazımı engellemek için atomic yazım."""
    d = os.path.dirname(path) or "."
    fd, tmp = tempfile.mkstemp(prefix=".tmp_stats_", dir=d, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
        os.replace(tmp, path)
    finally:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass

def write_stats(current: int, max_seen: int, path: str = STATS_PATH) -> None:
    """current, max ve percent alanlarını birlikte yazar."""
    _atomic_write_json(path, {
        "current": int(current),
        "max": int(max_seen),
        "percent": compute_percent(int(current), int(max_seen))
    })

def read_stats(path: str = STATS_PATH) -> Optional[Dict]:
    """Yoksa None döner; varsa sözlük döner."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def format_ratio(stats: Dict) -> str:
    """GUI üzerinde gösterim metni."""
    cur = int(stats.get("current", 0))
    mx = int(stats.get("max", 0))
    pct = int(stats.get("percent", 0))
    return f"Anlık Katılım Oranı: %{pct}  (Şimdi: {cur} / Maks: {mx})"
