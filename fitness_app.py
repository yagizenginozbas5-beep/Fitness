import streamlit as st
import sqlite3
import datetime
import zoneinfo
import google.generativeai as genai
import json

# --- VERİTABANI AYARLARI ---
def init_db():
    conn = sqlite3.connect('fitness_tracker.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS nutrition (
            id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, food_name TEXT, calories REAL, protein REAL, carbs REAL, fat REAL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS workouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, routine_type TEXT, exercise_name TEXT, sets TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, weight REAL, note TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT, role TEXT, message TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS supplements_v3 (
            id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, supp_name TEXT, amount TEXT, taken INTEGER
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cardio (
            id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, cardio_type TEXT, duration_min INTEGER, intensity TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# --- GEMINI API AYARI ---
# --- GEMINI API AYARI ---
# Eğer Streamlit Secrets'a 'GEMINI_API_KEY' olarak eklediysen otomatik okur kanka
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    # Eğer secrets'ta bulamazsa yedek olarak yine sol menüde kutu açar
    st.sidebar.title("🔑 Yapay Zeka Ayarı")
    api_key = st.sidebar.text_input("Gemini API Key Girin:", type="password")

def get_gemini_model():
    if not api_key:
        return None
    genai.configure(api_key=api_key)
    return genai.GenerativeModel("gemini-2.5-flash")

def get_gemini_model():
    if not api_key:
        return None
    genai.configure(api_key=api_key)
    return genai.GenerativeModel("gemini-2.5-flash")

# --- ARAYÜZ BAŞLANGIÇ ---
st.set_page_config(page_title="Gelişim Paneli", layout="wide")
st.title("🚀 Kişisel Yapay Zeka Fitness Koçu")

st.info("📋 **Profil Özeti:** Yaş: 17 | Boy: 175 cm | Başlangıç Kilosu: 79.95 kg | Program: PPL (Haftada 6 Gün)")

menu = ["🔥 Koçun Günlük Raporu & Özet", "💬 Koçla Sohbet & Akıl Danışma", "🥗 Yemek & Otomatik Makro", "💊 Supplement Günlüğü", "🏋️‍♂️ PPL Antrenman Günlüğü", "📉 Haftalık Form & Kilo"]
choice = st.sidebar.selectbox("Gitmek İstediğin Sayfa", menu)

# --- TÜRKİYE SAAT AYARI ---
tr_timezone = zoneinfo.ZoneInfo("Europe/Istanbul")
now = datetime.datetime.now(tr_timezone)
today = now.strftime("%Y-%m-%d")
current_time = now.strftime("%H:%M")

# --- VERİ TOPLAMA SİSTEMİ ---
conn = sqlite3.connect('fitness_tracker.db')
cursor = conn.cursor()

# Bugünkü beslenme
cursor.execute("SELECT SUM(calories), SUM(protein), SUM(carbs), SUM(fat) FROM nutrition WHERE date=?", (today,))
totals = cursor.fetchone()

# Bugünkü idman, supplement ve kardiyo
cursor.execute("SELECT exercise_name, sets FROM workouts WHERE date=?", (today,))
today_workouts = cursor.fetchall()

# Hata veren kısım burasıydı, tablo ismi supplements_v3 olarak düzeltildi kanka
cursor.execute("SELECT supp_name, amount FROM supplements_v3 WHERE date=? AND taken=1", (today,))
taken_supps = cursor.fetchall()

cursor.execute("SELECT cardio_type, duration_min, intensity FROM cardio WHERE date=?", (today,))
today_cardio = cursor.fetchall()

# Gelişim Kıyaslama Motoru İçin Veri Çekme
cursor.execute("SELECT weight, date FROM progress ORDER BY id ASC LIMIT 1")
first_weight_row = cursor.fetchone()

cursor.execute("SELECT weight, date FROM progress ORDER BY id DESC LIMIT 1")
last_weight_row = cursor.fetchone()

conn.close()

# Başlangıç ve Güncel Kilo Analizi
baslangic_kilosu = 79.95
baslangic_tarihi = "2026-06-20"

if first_weight_row:
    baslangic_kilosu = first_weight_row[0]
    baslangic_tarihi = first_weight_row[1]

current_weight = last_weight_row[0] if last_weight_row else baslangic_kilosu
current_weight_date = last_weight_row[1] if last_weight_row else today

# Değişim Değerleri
toplam_kilo_degisimi = current_weight - baslangic_kilosu
baslangic_yag_orani = 21.5
tahmini_mevcut_yag_orani = baslangic_yag_orani - ((baslangic_kilosu - current_weight) * 0.7)

cal, prot, carb, fat = (totals[0] or 0), (totals[1] or 0), (totals[2] or 0), (totals[3] or 0)
workout_str = ", ".join([f"{w[0]} ({w[1]})" for w in today_workouts]) if today_workouts else "Henüz idman girilmedi"
supp_str = ", ".join([f"{s[0]} ({s[1]})" for s in taken_supps]) if taken_supps else "Henüz supplement alınmadı"
cardio_str = ", ".join([f"{c[0]} ({c[1]} dk - {c[2]})" for c in today_cardio]) if today_cardio else "Henüz kardiyo girilmedi"

# --- GELİŞMİŞ ANALİTİK MOTORU ---
bmr = 66.47 + (13.75 * current_weight) + (5.00 * 175) - (6.75 * 17)
tahmini_yakilan = bmr * 1.55
kalori_acigi = tahmini_yakilan - cal if cal > 0 else 0

hedef_yag_orani = 14.0
yakilmasi_gereken_yag_kg = (current_weight * (tahmini_mevcut_yag_orani - hedef_yag_orani)) / 100
toplam_gereken_kalori_acigi = yakilmasi_gereken_yag_kg * 7700

if kalori_acigi > 100:
    gereken_gun_sayisi = int(toplam_gereken_kalori_acigi / kalori_acigi)
    hedef_tarih = (now + datetime.timedelta(days=gereken_gun_sayisi)).strftime("%d %B %Y")
    projeksiyon_str = f"Eğer her gün mevcut kalori açığını ({kalori_acigi:.0f} kcal) korursan, tam {gereken_gun_sayisi} gün sonra, yani {hedef_tarih} tarihinde %14 yağ oranına düşeceksin."
else:
    projeksiyon_str = "Mevcut kalori alımınla yağ yakımı hedefi hesaplanamıyor. Kalori açığı yaratmadığın sürece yağ oranın düşmeyecek."

# KOÇUN SİSTEM BACKEND PROMPTI
system_context = f"""
Sen kullanıcının kişisel, profesyonel, son derece gerçekçi ve analitik fitness koçusun. Adın 'Koç AI'. Kullanıcıya 'kanka' diyorsun.

Kullanıcı Profili: Yaş: 17, Boy: 175 cm.
Gelişim ve Kıyaslama Verileri:
- Başlangıç Kilosu ({baslangic_tarihi}): {baslangic_kilosu:.2f} kg
- Güncel Kilo ({current_weight_date}): {current_weight:.2f} kg
- Toplam Fark: {toplam_kilo_degisimi:.2f} kg
- Başlangıç Tahmini Yağ Oranı: %{baslangic_yag_orani:.1f}
- Güncel Tahmini Yağ Orani: %{tahmini_mevcut_yag_orani:.1f}

Bugünkü Veriler:
- Alınan Kalori: {cal:.0f} kcal (Protein: {prot:.1f}g, Karbonhidrat: {carb:.1f}g, Yağ: {fat:.1f}g)
- Yapılan İdmanlar: {workout_str}
- Yapılan Kardiyolar: {cardio_str}

Senden Beklenen Sert ve Gerçekçi Koçluk Kuralları:
1. Analiz yaparken mutlaka başlangıç verileri ile şimdiki verileri kıyasla! Gelişimi yüzüne vur.
2. Bugün yapılan kardiyo bilgisini kontrol et. Eğer kullanıcı çok kalori aldıysa veya kalori açığı azsa ve 'Henüz kardiyo girilmedi' yazıyorsa, kesinlikle sert bir şekilde kardiyo yapmasını söyle, uyar.
3. Asla boş yere övme. Matematiksel konuş.
"""

# ==================== 1. SAYFA: ÖZET & KOÇUN RAPORU ====================
if choice == "🔥 Koçun Günlük Raporu & Özet":
    st.header("📋 Gerçek Zamanlı Analiz Paneli")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Alınan Kalori", f"{cal:.0f} kcal")
    col2.metric("Protein", f"{prot:.1f} g")
    col3.metric("Tahmini Güncel Yağ Oranın", f"%{tahmini_mevcut_yag_orani:.1f}")
    col4.metric("Net Kalori Açığı", f"{kalori_acigi:.0f} kcal")

    st.markdown("---")
    st.subheader("📉 Kamp Gelişim ve Değişim Kıyaslaması")
    col_k1, col_k2, col_k3 = st.columns(3)
    col_k1.metric("Başlangıç Kilon", f"{baslangic_kilosu:.2f} kg", help=f"Kayıt Tarihi: {baslangic_tarihi}")
    col_k2.metric("Güncel Kilon", f"{current_weight:.2f} kg", help=f"Son Kayıt: {current_weight_date}")
    col_k3.metric("Toplam Değişim", f"{toplam_kilo_degisimi:.2f} kg", delta=f"{toplam_kilo_degisimi:.2f} kg", delta_color="inverse")

    st.markdown("---")
    st.subheader("📊 Matematiksel Projeksiyon")
    st.info(projeksiyon_str)

    st.markdown("---")
    st.header("🧠 Koç AI'ın Gerçekçi & Net Durum Analizi")
    st.caption(f"Sistem Saati (TR): {current_time} | Tarih: {today}")
    
    model = get_gemini_model()
    if not model:
        st.warning("Kanka koçunun rapor yazabilmesi için sol menüden Gemini API Key'ini girmen lazım.")
    else:
        if st.button("🔄 Koçun Analizini Tetikle / Yenile"):
            with st.spinner("Koçun tüm verilerini ve zaman parametrelerini analiz ediyor..."):
                try:
                    prompt = "Başlangıç verilerimle şu anki verilerimi ve bugünkü kardiyo durumumu kıyaslayarak; 'Gelişim / Değişim Değerlendirmesi', 'Kardiyo ve İdman Kontrolü' başlıklarıyla sert, gerçekçi ve matematiksel bir karne çıkar."
                    response = model.generate_content([system_context, prompt])
                    st.write(response.text)
                except Exception as e:
                    st.error(f"Hata: {e}")

# =================
