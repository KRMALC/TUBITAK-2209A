# file: /mnt/data/gui_app.py
import json
import os
import subprocess
import sys
import tkinter as tk
from typing import Optional
import signal

# Ortak yardımcılar
from hesaplamalar import read_stats, format_ratio, STATS_PATH

PROCESS: Optional[subprocess.Popen] = None
PYTHON = sys.executable

# hybrid.py bu klasörde
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HYBRID_SCRIPT = os.path.join(BASE_DIR, "hybrid.py")

def start_record() -> None:
    global PROCESS
    if PROCESS is None:
        try:
            env = os.environ.copy()
            env.setdefault("ATTENDANCE_STATS_PATH", STATS_PATH)
            PROCESS = subprocess.Popen([PYTHON, HYBRID_SCRIPT], env=env)
            status_var.set("Kayıt başlatıldı.")
        except Exception as e:
            status_var.set(f"Başlatılamadı: {e}")
    else:
        status_var.set("Zaten çalışıyor.")

def stop_record() -> None:
    global PROCESS
    if PROCESS is not None:
        try:
            # Hybrid.py'ye SIGINT gönder → finally bloğu düzgün çalışır.
            PROCESS.send_signal(signal.SIGINT)
        except Exception:
            PROCESS.terminate()  # yedek olarak
        PROCESS = None
        status_var.set("Kayıt durduruldu.")
    else:
        status_var.set("Çalışan kayıt yok.")
    live_var.set("Anlık Katılım Oranı: ---")

def _poll_stats() -> None:
    stats = read_stats()
    if stats:
        live_var.set(format_ratio(stats))
    root.after(500, _poll_stats)

def exit_app() -> None:
    try:
        stop_record()
    finally:
        root.destroy()

# --- UI ---
root = tk.Tk()
root.title("Öğrenci Dikkat Analiz Sistemi")
root.geometry("640x460")
root.configure(bg="#d9f2f7")

title_label = tk.Label(
    root,
    text="Öğrenci Dikkat Analiz Sistemine Hoş geldiniz",
    bg="#d9f2f7",
    fg="black",
    font=("Arial", 18, "bold")
)
title_label.pack(pady=20)

frame_buttons = tk.Frame(root, bg="#d9f2f7")
frame_buttons.pack(pady=10)

btn_start = tk.Button(
    frame_buttons,
    text="KAYDI BAŞLAT",
    bg="#4CAF50",
    fg="white",
    width=20,
    height=2,
    font=("Arial", 12, "bold"),
    command=start_record
)
btn_start.grid(row=0, column=0, padx=10)

btn_stop = tk.Button(
    frame_buttons,
    text="KAYDI DURDUR",
    bg="#f44336",
    fg="white",
    width=20,
    height=2,
    font=("Arial", 12, "bold"),
    command=stop_record
)
btn_stop.grid(row=0, column=1, padx=10)

live_var = tk.StringVar(value="Anlık Katılım Oranı: ---")
live_label = tk.Label(
    root,
    textvariable=live_var,
    bg="#d9f2f7",
    fg="blue",
    font=("Arial", 16, "bold")
)
live_label.pack(pady=20)

frame_bottom = tk.Frame(root, bg="#d9f2f7")
frame_bottom.pack(side="bottom", fill="x", pady=25)

btn_exit = tk.Button(
    frame_bottom,
    text="ÇIKIŞ",
    bg="#bdbdbd",
    fg="black",
    width=12,
    height=2,
    font=("Arial", 11, "bold"),
    command=exit_app
)
btn_exit.pack(side="right", padx=40)

status_var = tk.StringVar(value="")
status_label = tk.Label(
    root,
    textvariable=status_var,
    bg="#d9f2f7",
    fg="black",
    font=("Arial", 11)
)
status_label.pack(pady=5)

root.after(500, _poll_stats)
root.mainloop()
