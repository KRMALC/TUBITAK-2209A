# ai_engine.py

import json
import sqlite3
from openai import OpenAI


API_KEY = "apiKey"   # <-- API key buraya
MODEL_ADI = "gpt-4o-mini"        # en ekonomik ve güçlü model
DB_YOLU = "/home/krm/Desktop/dlibenv/OYS/ogrenciler.db"

client = OpenAI(api_key=API_KEY)


def ogrencileri_al_dbden():
    try:
        conn = sqlite3.connect(DB_YOLU)
        cursor = conn.cursor()

        cursor.execute("SELECT ad, soyad, okul_numarasi, dikkat_orani, yoklama FROM ogrenciler")
        rows = cursor.fetchall()
        conn.close()

        ogrenciler = []

        for ad, soyad, okul_numarasi, dikkat_orani, yoklama in rows:
            ogrenciler.append({
                "ad": ad,
                "soyad": soyad,
                "okul_numarasi": okul_numarasi,
                "dikkat_orani": dikkat_orani,
                "yoklama": yoklama
            })

        return ogrenciler

    except Exception as e:
        return {"error": str(e)}


def chate_sor(user_text):

    ogrenciler = ogrencileri_al_dbden()

    prompt = f"""
Sen bir öğrenci analiz asistanısın.

Eğer kullanıcı öğrenci, dikkat analizi, başarı durumu veya veritabanı ile ilgili bir şey sormazsa:
- Sadece normal sohbet eden, yardımsever bir asistan gibi davran.

Eğer kullanıcı öğrenciler hakkında sorarsa:
- Aşağıdaki öğrenci listesini analiz et:

{json.dumps(ogrenciler, indent=2, ensure_ascii=False)}

Kullanıcı sorusu: "{user_text}"

Kurallar:
- Kullanıcı ne istiyorsa sadece ona göre cevap ver
- Gereksiz analiz yapma
- Gereksiz uzun yazma
- Türkçe konuş
"""

    try:
        response = client.responses.create(
            model=MODEL_ADI,
            input=prompt,
            max_output_tokens=180  # ekonomik kullanım için
        )

        return response.output_text

    except Exception as e:
        return f"HATA: {e}"
