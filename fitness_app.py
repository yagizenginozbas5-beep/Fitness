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
    # Tablo ismini v2 yaparak eski çakışmayı kökten çözüyoruz kanka
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS supplements_v2 (
            id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, supp_name TEXT, amount TEXT, taken INTEGER
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
# Güncellenmiş tablo isminden veriyi çekiyoruz
cursor.execute("SELECT supp_name, amount FROM supplements_v2 WHERE date=? AND taken=1", (today,))
taken_supps = cursor.fetchall()
conn.close()

cal, prot, carb, fat = (totals[0] or 0), (totals[1] or 0), (totals[2] or 0), (totals[3] or 0)
workout_str = ", ".join([f"{w[0]} ({w[1]})" for w in today_workouts]) if today_workouts else "Henüz idman girilmedi"
supp_str = ", ".join([f"{s[0]} ({s[1]})" for s in taken_supps]) if taken_supps else "Henüz supplement alınmadı"

# Matematiksel Hesaplamalar
tahmini_yakilan = 2350
net_kalori_alimi = cal
kalori_acigi = tahmini_yakilan - net_kalori_alimi
tahmini_yag_yakimi_gr = (kalori_acigi / 7.7) if kalori_acigi > 0 else 0

# KOÇUN SİSTEM BACKEND PROMPTI
system_context = f"""
Sen kullanıcının 7/24 yanında olan profesyonel, samimi, gerektiğinde sert ama her zaman gaza getiren fitness koçusun. Adın 'Koç AI'. Kullanıcıya hep 'kanka' diyorsun.
Kullanıcı Profili: Yaş: 17, Boy: 175 cm, Kilo: 79.95 kg. Hedef: Yağ yakarken kas kütlesini korumak/artırmak. Program: PPL.

Bugünkü Mevcut Durum Verileri:
- Alınan Kalori: {cal:.0f} kcal (Protein: {prot:.1f}g, Karbonhidrat: {carb:.1f}g, Yağ: {fat:.1f}g)
- Yapılan İdmanlar: {workout_str}
- Alınan Supplementler ve Miktarları: {supp_str}
- Arkada Hesaplanan Tahmini Yağ Yakımı: {tahmini_yag_yakimi_gr:.1f} gram.

Senden istenen: Bu verilere göre kullanıcıya net, nokta atışı bir koçluk raporu veya sohbet cevabı vermen.
Supplement miktarlarına (örneğin 50g Cream of Rice, 1 adet ZMA, Pre-Workout vb.) dikkat et. Eğer Pre-Workout alındıysa antrenman odağını yorumla, Magnezyum Bisglisinat ve ZMA alındıysa uyku kalitesini ve kas toparlanmasını öv. Eksik supplement varsa uyar. Jargona (pump, progressive overload, makro, bulk, kardiyo, recovery vb.) hakim bir salon kankası gibi konuş.
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
                prompt = "Bütün bugünkü verileri incele ve bana 'Bugünkü Değerlendirmem', 'Supplement & Reçete Yorumum' ve en önemlisi 'Şu An Yapman Gereken Net Ödev/Tavsiye (Kardiyo, beslenme, supplement vb.)' şeklinde maddeler halinde direktiflerini ver."
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
    st.header("💊 Gelişmiş Supplement Deposu")
    st.subheader("Bugün Vücuda Neler Girdi?")
    
    supp_list = {
        "Creatine Monohydrate": "Örn: 5 gram veya 1 ölçek",
        "Whey Protein": "Örn: 30 gram veya 1 ölçek",
        "ZMA": "Örn: 1 adet veya 2 kapsül",
        "Magnezyum Bisglisinat": "Örn: 1 tablet veya 200 mg",
        "Cream of Rice": "Örn: 50 gram",
        "D3 Vitamini": "Örn: 1 damla veya 2000 IU",
        "Omega-3 Balık Yağı": "Örn: 1 kapsül veya 1000 mg",
        "Pre-Workout": "Örn: 1 ölçek veya 10 gram",
        "Elektrolit Tozu": "Örn: 1 paket veya 5 gram",
        "Milk Thistle (Deve Dikeni - Karaciğer Destek)": "Örn: 1 kapsül"
    }
    
    conn = sqlite3.connect('fitness_tracker.db')
    cursor = conn.cursor()
    
    for s_name, placeholder in supp_list.items():
        st.markdown(f"**🔹 {s_name}**")
        col1, col2 = st.columns([1, 3])
        
        cursor.execute("SELECT taken, amount FROM supplements_v2 WHERE date=? AND supp_name=?", (today, s_name))
        row = cursor.fetchone()
        
        db_taken = row[0] if row else 0
        db_amount = row[1] if row else ""
        
        is_taken = col1.checkbox("Aldım", value=True if db_taken == 1 else False, key=f"check_{s_name}")
        amount_input = col2.text_input("Ne kadar aldın?", value=db_amount, placeholder=placeholder, key=f"text_{s_name}")
        
        new_taken = 1 if is_taken else 0
        
        if row:
            cursor.execute("UPDATE supplements_v2 SET taken=?, amount=? WHERE date=? AND supp_name=?", (new_taken, amount_input, today, s_name))
        else:
            cursor.execute("INSERT INTO supplements_v2 (date, supp_name, amount, taken) VALUES (?, ?, ?, ?)", (today, s_name, amount_input, new_taken))
            
    conn.commit()
    conn.close()
    st.success("Supplement deposu güncellendi kanka!")

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
