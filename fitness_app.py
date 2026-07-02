import streamlit as st
import sqlite3
import datetime
import google.generativeai as genai

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
        CREATE TABLE IF NOT EXISTS supplements (
            id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, supp_name TEXT, taken INTEGER
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# --- GEMINI API AYARI ---
st.sidebar.title("🔑 Yapay Zeka Ayarı")
api_key = st.sidebar.text_input("Gemini API Key Girin:", type="password")

def get_gemini_model():
    if not api_key:
        return None
    genai.configure(api_key=api_key)
    return genai.GenerativeModel("gemini-2.5-flash")

# --- ARAYÜZ BAŞLANGIÇ ---
st.set_page_config(page_title="Gelişim Paneli", layout="wide")
st.title("🚀 Kişisel Yapay Zeka Fitness Koçu")

st.info("📋 **Profil Özeti:** Yaş: 17 | Boy: 175 cm | Güncel Kilo: 79.95 kg | Program: PPL (Haftada 6 Gün)")

menu = ["🔥 Koçun Günlük Raporu & Özet", "💬 Koçla Sohbet & Akıl Danışma", "🥗 Yemek & Makro Takibi", "💊 Supplement Günlüğü", "🏋️‍♂️ PPL Antrenman Günlüğü", "📉 Haftalık Form & Kilo"]
choice = st.sidebar.selectbox("Gitmek İstediğin Sayfa", menu)
today = datetime.date.today().strftime("%Y-%m-%d")

# --- VERİ TOPLAMA SİSTEMİ ---
conn = sqlite3.connect('fitness_tracker.db')
cursor = conn.cursor()
cursor.execute("SELECT SUM(calories), SUM(protein), SUM(carbs), SUM(fat) FROM nutrition WHERE date=?", (today,))
totals = cursor.fetchone()
cursor.execute("SELECT exercise_name, sets FROM workouts WHERE date=?", (today,))
today_workouts = cursor.fetchall()
cursor.execute("SELECT supp_name FROM supplements WHERE date=? AND taken=1", (today,))
taken_supps = cursor.fetchall()
conn.close()

cal, prot, carb, fat = (totals[0] or 0), (totals[1] or 0), (totals[2] or 0), (totals[3] or 0)
workout_str = ", ".join([f"{w[0]} ({w[1]})" for w in today_workouts]) if today_workouts else "Henüz idman girilmedi"
supp_str = ", ".join([s[0] for s in taken_supps]) if taken_supps else "Henüz supplement alınmadı"

# Matematiksel Hesaplamalar (Arkada çalışan mantık)
# Bazal Metabolizma ~1750 kcal + Günlük Aktivite/İdman ~600 kcal = Toplam Yakılan ~2350 kcal tahmini
tahmini_yakilan = 2350
net_kalori_alimi = cal
kalori_acigi = tahmini_yakilan - net_kalori_alimi
tahmini_yag_yakimi_gr = (kalori_acigi / 7.7) if kalori_acigi > 0 else 0

# KOÇUN SİSTEM BACKEND PROMPTI
system_context = f"""
Sen kullanıcının 7/24 yanında olan profesyonel, samimi, gerektiğinde sert ama her zaman gaza getiren fitness koçusun (Adın Koç AI, kullanıcıya hep 'kanka' diyorsun).
Kullanıcı Profili: Yaş: 17, Boy: 175 cm, Kilo: 79.95 kg. Hedef: Yağ yakarken kas kütlesini korumak/artırmak. Program: PPL.

Bugünkü Mevcut Durum Verileri:
- Alınan Kalori: {cal:.0f} kcal (Protein: {prot:.1f}g, Karbonhidrat: {carb:.1f}g, Yağ: {fat:.1f}g)
- Yapılan İdmanlar: {workout_str}
- Alınan Supplementler: {supp_str}
- Arkada Hesaplanan Tahmini Yağ Yakımı: {tahmini_yag_yakimi_gr:.1f} gram.

Senden istenen: Bu verilere göre kullanıcıya net, nokta atışı bir koçluk raporu veya sohbet cevabı vermen. Eğer karbonhidrat/kalori çok yüksekse 'kanka bugün sınırı aşmışız, hemen idman sonuna 25 dakika tempolu kardiyo ekle' gibi pratik ödevler ver. Supplementleri eksikse (örn: kreatin almadıysa) uyar. Jargona (pump, progressive overload, makro, bulk, kardiyo vb.) hakim bir salon kankası gibi konuş.
"""

# ==================== 1. SAYFA: ÖZET & KOÇUN RAPORU ====================
if choice == "🔥 Koçun Günlük Raporu & Özet":
    st.header("📋 Bugünün Durum Özeti")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Alınan Kalori", f"{cal:.0f} kcal")
    col2.metric("Protein", f"{prot:.1f} g")
    col3.metric("Karbonhidrat", f"{carb:.1f} g")
    col4.metric("Tahmini Yağ Yakımı", f"{tahmini_yag_yakimi_gr:.1f} gr")

    st.markdown("---")
    st.header("🧠 Koç AI'ın Bugün Klasörünü İnceleme Raporu")
    
    model = get_gemini_model()
    if not model:
        st.warning("Kanka koçunun rapor yazabilmesi için sol menüden Gemini API Key'ini girmen lazım.")
    else:
        with st.spinner("Koçun tüm verilerini, idmanını ve supplementlerini analiz ediyor..."):
            try:
                prompt = "Bütün bugünkü verileri incele ve bana 'Bugünkü Değerlendirmem', 'Bugün Hesapladığım Yağ Yakımı' ve en önemlisi 'Şu An Yapman Gereken Net Ödev/Tavsiye (Kardiyo vb.)' şeklinde maddeler halinde direktiflerini ver."
                response = model.generate_content([system_context, prompt])
                st.write(response.text)
            except Exception as e:
                st.error(f"Hata: {e}")

# ==================== 2. SAYFA: SOHBET ====================
elif choice == "💬 Koçla Sohbet & Akıl Danışma":
    st.header("💬 Koç AI ile Canlı Dertleşme & Akıl Odası")
    model = get_gemini_model()
    
    if not model:
        st.error("API Key gir kanka!")
    else:
        conn = sqlite3.connect('fitness_tracker.db')
        cursor = conn.cursor()
        cursor.execute("SELECT role, message FROM chat_history ORDER BY id ASC")
        db_history = cursor.fetchall()
        conn.close()
        
        for role, msg in db_history:
            with st.chat_message("user" if role == "user" else "assistant"):
                st.write(msg)
                
        user_input = st.chat_input("Diyeti mi bozdun? Yaz koçuna...")
        if user_input:
            with st.chat_message("user"):
                st.write(user_input)
            
            conn = sqlite3.connect('fitness_tracker.db')
            cursor = conn.cursor()
            cursor.execute("INSERT INTO chat_history (role, message) VALUES (?, ?)", ("user", user_input))
            conn.commit()
            
            chat_session_messages = [{"role": "user", "parts": [system_context]}]
            for r, m in db_history:
                chat_session_messages.append({"role": "user" if r == "user" else "model", "parts": [m]})
            chat_session_messages.append({"role": "user", "parts": [user_input]})
            
            with st.chat_message("assistant"):
                try:
                    response = model.generate_content(chat_session_messages)
                    reply = response.text
                    st.write(reply)
                    cursor.execute("INSERT INTO chat_history (role, message) VALUES (?, ?)", ("assistant", reply))
                    conn.commit()
                except Exception as e:
                    st.error(f"Hata: {e}")
            conn.close()
            st.rerun()

# ==================== 3. SAYFA: BESLENME ====================
elif choice == "🥗 Yemek & Makro Takibi":
    st.header("🥗 Bugün Ne Gömdün?")
    f_name = st.text_input("Yemek Adı")
    col1, col2, col3, col4 = st.columns(4)
    f_cal = col1.number_input("Kalori (kcal)", min_value=0.0, step=10.0)
    f_prot = col2.number_input("Protein (g)", min_value=0.0, step=1.0)
    f_carb = col3.number_input("Karbonhidrat (g)", min_value=0.0, step=1.0)
    f_fat = col4.number_input("Yağ (g)", min_value=0.0, step=1.0)
    
    if st.button("Öğünü Koça Bildir"):
        conn = sqlite3.connect('fitness_tracker.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO nutrition (date, food_name, calories, protein, carbs, fat) VALUES (?, ?, ?, ?, ?, ?)", (today, f_name, f_cal, f_prot, f_carb, f_fat))
        conn.commit()
        conn.close()
        st.success(f"{f_name} hafızaya alındı kanka!")

# ==================== 4. SAYFA: SUPPLEMENTLER ====================
elif choice == "💊 Supplement Günlüğü":
    st.header("💊 Bugün Hangi Supplementleri Attın?")
    supps = ["Creatine", "Whey Protein", "ZMA", "Magnesium", "Cream of Rice"]
    
    conn = sqlite3.connect('fitness_tracker.db')
    cursor = conn.cursor()
    
    for s in supps:
        cursor.execute("SELECT id FROM supplements WHERE date=? AND supp_name=?", (today, s))
        exists = cursor.fetchone()
        if not exists:
            cursor.execute("INSERT INTO supplements (date, supp_name, taken) VALUES (?, ?, 0)", (today, s))
    conn.commit()
    
    for s in supps:
        cursor.execute("SELECT taken FROM supplements WHERE date=? AND supp_name=?", (today, s))
        status = cursor.fetchone()[0]
        checked = st.checkbox(s, value=True if status == 1 else False)
        new_status = 1 if checked else 0
        cursor.execute("INSERT OR REPLACE INTO supplements (id, date, supp_name, taken) VALUES ((SELECT id FROM supplements WHERE date=? AND supp_name=?), ?, ?, ?)", (today, s, today, s, new_status))
    
    conn.commit()
    conn.close()
    st.info("İçtiğin supplementleri işaretle, koçun ana sayfada raporunu yazarken bunlara da bakacak!")

# ==================== DİĞER SAYFALAR ====================
elif choice == "🏋️‍♂️ PPL Antrenman Günlüğü":
    st.header("🏋️‍♂️ Bugün Demirleri Nasıl Ağlattın?")
    ppl_type = st.selectbox("Bugün Hangi Gün?", ["Push (İtiş)", "Pull (Çekiş)", "Legs (Bacak)"])
    ex_name = st.text_input("Hareket Adı")
    sets_input = st.text_input("Setler ve Tekrarlar (Örn: 4x12 60kg)")
    if st.button("Hareketi Veritabanına İşle"):
        conn = sqlite3.connect('fitness_tracker.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO workouts (date, routine_type, exercise_name, sets) VALUES (?, ?, ?, ?)", (today, ppl_type, ex_name, sets_input))
        conn.commit()
        conn.close()
        st.success(f"{ex_name} koçun defterine kaydedildi.")

elif choice == "📉 Haftalık Form & Kilo":
    st.header("📉 Kilo ve Form Kontrolü")
    current_w = st.number_input("Bugünkü Kilon (kg):", min_value=0.0, value=79.95, step=0.05)
    note = st.text_area("Ekstra Notun:")
    if st.button("Kaydet"):
        conn = sqlite3.connect('fitness_tracker.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO progress (date, weight, note) VALUES (?, ?, ?)", (today, current_w, note))
        conn.commit()
        conn.close()
        st.success("Kilo kaydedildi!")
