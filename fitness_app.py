import streamlit as st
import sqlite3
import datetime
import zoneinfo  # Saat dilimi ayarı için ekledik kanka
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
        CREATE TABLE IF NOT EXISTS supplements_v3 (
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

# --- TÜRKİYE SAAT AYARI (SORUNU ÇÖZEN KISIM) ---
tr_timezone = zoneinfo.ZoneInfo("Europe/Istanbul")
now = datetime.datetime.now(tr_timezone)
today = now.strftime("%Y-%m-%d")
current_time = now.strftime("%H:%M")

# --- VERİ TOPLAMA SİSTEMİ ---
conn = sqlite3.connect('fitness_tracker.db')
cursor = conn.cursor()
cursor.execute("SELECT SUM(calories), SUM(protein), SUM(carbs), SUM(fat) FROM nutrition WHERE date=?", (today,))
totals = cursor.fetchone()
cursor.execute("SELECT exercise_name, sets FROM workouts WHERE date=?", (today,))
today_workouts = cursor.fetchall()
cursor.execute("SELECT supp_name, amount FROM supplements_v3 WHERE date=? AND taken=1", (today,))
taken_supps = cursor.fetchall()

# Son girilen güncel kiloyu çekme
cursor.execute("SELECT weight FROM progress ORDER BY id DESC LIMIT 1")
last_weight_row = cursor.fetchone()
current_weight = last_weight_row[0] if last_weight_row else 79.95
conn.close()

cal, prot, carb, fat = (totals[0] or 0), (totals[1] or 0), (totals[2] or 0), (totals[3] or 0)
workout_str = ", ".join([f"{w[0]} ({w[1]})" for w in today_workouts]) if today_workouts else "Henüz idman girilmedi"
supp_str = ", ".join([f"{s[0]} ({s[1]})" for s in taken_supps]) if taken_supps else "Henüz supplement alınmadı"

# --- GELİŞMİŞ ANALİTİK MOTORU ---
bmr = 66.47 + (13.75 * current_weight) + (5.00 * 175) - (6.75 * 17)
tahmini_yakilan = bmr * 1.55

kalori_acigi = tahmini_yakilan - cal if cal > 0 else 0
tahmini_yag_yakimi_gr = (kalori_acigi / 7.7) if kalori_acigi > 0 else 0
tahmini_mevcut_yag_orani = 21.5 - ((cal / 5000) if cal > 0 else 0)

hedef_yag_orani = 14.0
yakilmasi_gereken_yag_kg = (current_weight * (tahmini_mevcut_yag_orani - hedef_yag_orani)) / 100
toplam_gereken_kalori_acigi = yakilmasi_gereken_yag_kg * 7700

if kalori_acigi > 100:
    gereken_gun_sayisi = int(toplam_gereken_kalori_acigi / kalori_acigi)
    hedef_tarih = (now + datetime.timedelta(days=gereken_gun_sayisi)).strftime("%d %B %Y")
    projeksiyon_str = f"Eğer her gün mevcut kalori açığını ({kalori_acigi:.0f} kcal) korursan, tam {gereken_gun_sayisi} gün sonra, yani {hedef_tarih} tarihinde %14 yağ oranına ve tahmini {current_weight - yakilmasi_gereken_yag_kg:.1f} kiloya düşeceksin."
else:
    projeksiyon_str = "Mevcut kalori alımınla yağ yakımı hedefi hesaplanamıyor. Kalori açığı yaratmadığın sürece yağ oranın düşmeyecek."

# KOÇUN SİSTEM BACKEND PROMPTI
system_context = f"""
Sen kullanıcının kişisel, profesyonel, son derece gerçekçi ve analitik fitness koçusun. Adın 'Koç AI'. Kullanıcıya 'kanka' diyorsun ama boş övgüler, sahte motivasyon cümleleri ASLA kurmuyorsun. Tamamen verilerle, sert gerçeklerle konuşuyorsun. 

Şu anki Zaman ve Tarih Bilgisi (Türkiye Saati):
- Bugünün Tarihi: {today}
- Şu Anki Saat: {current_time}

Kullanıcı Profili: Yaş: 17, Boy: 175 cm, Güncel Kilo: {current_weight:.2f} kg. Program: PPL (Haftada 6 Gün).

Bugünkü Gerçek Zamanlı Veriler:
- Alınan Kalori: {cal:.0f} kcal (Protein: {prot:.1f}g, Karbonhidrat: {carb:.1f}g, Yağ: {fat:.1f}g)
- Yapılan İdmanlar: {workout_str}
- Alınan Supplementler ve Miktarları: {supp_str}

Arka Plan Analiz Motoru Sonuçları:
- Günlük Bazal Metabolizma + İdman Harcaması (TDEE): {tahmini_yakilan:.0f} kcal
- Şu Anki Net Kalori Açığı: {kalori_acigi:.0f} kcal
- Bugün Yakılan Net Yağ: {tahmini_yag_yakimi_gr:.1f} gram
- Tahmini Mevcut Yağ Oranı: %{tahmini_mevcut_yag_orani:.1f}
- Gelecek Projeksiyonu: {projeksiyon_str}

Senden Beklenen Sert ve Gerçekçi Koçluk Kuralları:
1. Zamanın farkında ol! Saat şu an Türkiye saati ile tam olarak {current_time}. Eğer saat öğlen veya akşamsa ve hala 'Henüz idman girilmedi' yazıyorsa, hemen "Saat {current_time} oldu, idmana ne zaman gidiyorsun? Bugün PPL'in hangi günündesin, planda ne var?" diye hesap sor.
2. Kesinlikle boş yere övme. Protein eksikse "Bu proteinle kas kütleni koruyamazsın" de. Kalori fazlaysa ya da açık azsa "Böyle giderse yağ yakamazsın, hedefin hayal olur" de. 
3. Yağ oranı ve gelecek projeksiyonunu analiz et. Kullanıcıya net olarak: "Şu anki durumuna göre yağ oranın tahmini %{tahmini_mevcut_yag_orani:.1f}. Eğer bu disiplini bozmazsan şu günde %14'e düşeceksin, ama bozduğun an takvim patlar" şeklinde matematiksel konuş.
4. Supplement miktarlarına (örneğin 50g Cream of Rice, ZMA vb.) dikkat et. Alınmadıysa eksikliğini yüzüne vur.
"""

# ==================== 1. SAYFA: ÖZET & KOÇUN RAPORU ====================
if choice == "🔥 Koçun Günlük Raporu & Özet":
    st.header("📋 Gerçek Zamanlı Analiz Paneli")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Alınan Kalori", f"{cal:.0f} kcal")
    col2.metric("Protein", f"{prot:.1f} g")
    col3.metric("Tahmini Yağ Oranın", f"%{tahmini_mevcut_yag_orani:.1f}")
    col4.metric("Net Kalori Açığı", f"{kalori_acigi:.0f} kcal")

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
        with st.spinner("Koçun tüm verilerini ve zaman parametrelerini analiz ediyor..."):
            try:
                prompt = "Mevcut saate ve verilere bakarak bana hiç lafı dolandırmadan; 'Zamanlama ve İdman Kontrolü', 'Yağ Oranı ve Projeksiyon Değerlendirmesi', 'Gözümden Kaçmayan Eksikler' başlıklarıyla net, sert ve matematiksel bir karne çıkar."
                response = model.generate_content([system_context, prompt])
                st.write(response.text)
            except Exception as e:
                st.error(f"Hata: {e}")

# ==================== 2. SAYFA: SOHBET ====================
elif choice == "💬 Koçla Sohbet & Akıl Danışma":
    st.header("💬 Koç AI ile Canlı Dertleşme & Akıl Odası")
    st.caption(f"Koç şu an saatin {current_time} olduğunun bilincinde.")
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
                
        user_input = st.chat_input("İdman durumunu, beslenmeni yaz ya da soru sor...")
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
        
        cursor.execute("SELECT taken, amount FROM supplements_v3 WHERE date=? AND supp_name=?", (today, s_name))
        row = cursor.fetchone()
        
        db_taken = row[0] if row else 0
        db_amount = row[1] if row else ""
        
        is_taken = col1.checkbox("Aldım", value=True if db_taken == 1 else False, key=f"check_{s_name}")
        amount_input = col2.text_input("Ne kadar aldın?", value=db_amount, placeholder=placeholder, key=f"text_{s_name}")
        
        new_taken = 1 if is_taken else 0
        
        if row:
            cursor.execute("UPDATE supplements_v3 SET taken=?, amount=? WHERE date=? AND supp_name=?", (new_taken, amount_input, today, s_name))
        else:
            cursor.execute("INSERT INTO supplements_v3 (date, supp_name, amount, taken) VALUES (?, ?, ?, ?)", (today, s_name, amount_input, new_taken))
            
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
    current_w = st.number_input("Bugünkü Kilon (kg):", min_value=0.0, value=current_weight, step=0.05)
    note = st.text_area("Ekstra Notun:")
    if st.button("Kaydet"):
        conn = sqlite3.connect('fitness_tracker.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO progress (date, weight, note) VALUES (?, ?, ?)", (today, current_w, note))
        conn.commit()
        conn.close()
        st.success("Kilo kaydedildi!")
