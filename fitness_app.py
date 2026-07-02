import streamlit as st
import sqlite3
import datetime
import google.generativeai as genai
from PIL import Image
import io

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
    conn.commit()
    conn.close()

init_db()

st.sidebar.title("🔑 Yapay Zeka Ayarı")
api_key = st.sidebar.text_input("Gemini API Key Girin:", type="password")

def analyze_image_with_gemini(image, prompt_text):
    if not api_key:
        st.error("Lütfen sol menüden Gemini API Key gir kanka!")
        return None
    try:
        genai.configure(api_key=api_key)
        model = genai.get_model("gemini-2.5-flash")
        response = model.generate_content([prompt_text, image])
        return response.text
    except Exception as e:
        st.error(f"API Hatası: {e}")
        return None

st.set_page_config(page_title="Gelişim Paneli", layout="wide")
st.title("🚀 Kişisel Yapay Zeka Fitness Koçu")
st.subheader("Hoş geldin kanka! Bugün PPL döngüsünü patlatma zamanı.")
st.info("📋 **Profil Özeti:** Yaş: 17 | Boy: 175 cm | Başlangıç Kilosu: 79.95 kg | Program: PPL (Haftada 6 Gün)")

menu = ["Özet Dashboard", "Yemek & Makro Takibi", "PPL Antrenman Günlüğü", "Haftalık Form & Kilo"]
choice = st.sidebar.selectbox("Gitmek İstediğin Sayfa", menu)
today = datetime.date.today().strftime("%Y-%m-%d")

if choice == "Özet Dashboard":
    st.header("📊 Günlük Durum Analizi")
    conn = sqlite3.connect('fitness_tracker.db')
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(calories), SUM(protein), SUM(carbs), SUM(fat) FROM nutrition WHERE date=?", (today,))
    totals = cursor.fetchone()
    conn.close()
    
    cal = totals[0] if totals[0] else 0
    prot = totals[1] if totals[1] else 0
    carb = totals[2] if totals[2] else 0
    fat = totals[3] if totals[3] else 0
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Alınan Kalori", f"{cal:.0f} kcal")
    col2.metric("Protein", f"{prot:.1f} g")
    col3.metric("Karbonhidrat", f"{carb:.1f} g")
    col4.metric("Yağ", f"{fat:.1f} g")
    
    st.markdown("---")
    st.subheader("💡 Koçun Tavsiyesi")
    if prot < 140:
        st.warning(f"Kanka kas kütleni korumak/artırmak için proteine yüklen. En az bir {140 - prot:.0f}g daha protein lazım!")
    else:
        st.success("Harika! Protein hedefini bugün canavar gibi yakaladın.")

elif choice == "Yemek & Makro Takibi":
    st.header("🥗 Beslenme ve Fotoğraftan Makro Analizi")
    upload_option = st.radio("Yemek Giriş Türü", ["Fotoğraf Yükle (AI Analizi)", "Manuel Gramaj Gir"])
    
    if upload_option == "Fotoğraf Yükle (AI Analizi)":
        uploaded_file = st.file_uploader("Yemeğin fotoğrafını çekip yükle kanka:", type=["jpg", "jpeg", "png"])
        if uploaded_file is not None:
            image = Image.open(uploaded_file)
            st.image(image, caption="Yüklenen Yemek", width=300)
            if st.button("Fotoğrafı Analiz Et"):
                with st.spinner("Yapay zekâ tabağı inceliyor..."):
                    prompt = 'Sen profesyonel bir fitness koçusun. Bu fotoğraftaki yemeği analiz et. Tahmini gramajlarını çıkar ve şu formata BİREBİR uygun bir JSON yanıtı ver (Başka hiçbir metin yazma, sadece JSON olsun): {"food_name": "Yemek Adı", "calories": 450, "protein": 35, "carbs": 50, "fat": 12}'
                    result_text = analyze_image_with_gemini(image, prompt)
                    if result_text:
                        st.subheader("AI Analiz Sonucu:")
                        st.code(result_text, language="json")

    st.subheader("✍️ Öğün Kaydet")
    f_name = st.text_input("Yemek Adı")
    f_cal = st.number_input("Kalori (kcal)", min_value=0.0, step=10.0)
    f_prot = st.number_input("Protein (g)", min_value=0.0, step=1.0)
    f_carb = st.number_input("Karbonhidrat (g)", min_value=0.0, step=1.0)
    f_fat = st.number_input("Yağ (g)", min_value=0.0, step=1.0)
    
    if st.button("Öğünü Hafızaya Ekle"):
        conn = sqlite3.connect('fitness_tracker.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO nutrition (date, food_name, calories, protein, carbs, fat) VALUES (?, ?, ?, ?, ?, ?)", (today, f_name, f_cal, f_prot, f_carb, f_fat))
        conn.commit()
        conn.close()
        st.success(f"{f_name} başarıyla günlüğe eklendi unutmuyorum!")

elif choice == "PPL Antrenman Günlüğü":
    st.header("🏋️‍♂️ PPL Antrenman Günlüğü")
    ppl_type = st.selectbox("Bugün Hangi Gün?", ["Push (İtiş)", "Pull (Çekiş)", "Legs (Bacak)"])
    
    conn = sqlite3.connect('fitness_tracker.db')
    cursor = conn.cursor()
    cursor.execute("SELECT date, exercise_name, sets FROM workouts WHERE routine_type=? ORDER BY id DESC LIMIT 5", (ppl_type,))
    past_workouts = cursor.fetchall()
    conn.close()
    
    if past_workouts:
        for row in past_workouts:
            st.text(f"📅 {row[0]} | 💪 {row[1]} | 🔢 Setler: {row[2]}")
    
    ex_name = st.text_input("Hareket Adı")
    sets_input = st.text_input("Setler ve Tekrarlar (Örn: 4x12 60kg)")
    if st.button("Hareketi Kaydet"):
        conn = sqlite3.connect('fitness_tracker.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO workouts (date, routine_type, exercise_name, sets) VALUES (?, ?, ?, ?)", (today, ppl_type, ex_name, sets_input))
        conn.commit()
        conn.close()
        st.success(f"{ex_name} veritabanına işlendi.")

elif choice == "Haftalık Form & Kilo":
    st.header("📉 Haftalık Form ve Kilo Değişim Analizi")
    current_w = st.number_input("Bugünkü Kilon (kg):", min_value=0.0, value=79.95, step=0.05)
    note = st.text_area("Form Durumu Notu:")
    if st.button("Haftalık Durumu Kaydet"):
        conn = sqlite3.connect('fitness_tracker.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO progress (date, weight, note) VALUES (?, ?, ?)", (today, current_w, note))
        conn.commit()
        conn.close()
        st.success("Kilo kaydedildi!")