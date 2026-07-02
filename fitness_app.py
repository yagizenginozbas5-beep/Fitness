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

# --- GEMINI API AYARI (SECRETS OTOMASYONU) ---
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
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
cursor.execute("SELECT SUM(calories), SUM(protein), SUM(carbs), SUM(fat) FROM nutrition WHERE date=?", (today,))
totals = cursor.fetchone()
cursor.execute("SELECT exercise_name, sets FROM workouts WHERE date=?", (today,))
today_workouts = cursor.fetchall()
cursor.execute("SELECT supp_name, amount FROM supplements_v3 WHERE date=? AND taken=1", (today,))
taken_supps = cursor.fetchall()

# Kardiyo Verilerini Çekme
cursor.execute("SELECT cardio_type, duration_min, intensity FROM cardio WHERE date=?", (today,))
today_cardio = cursor.fetchall()

# Gelişim Kıyaslama Motoru İçin Veri Çekme
cursor.execute("SELECT weight, date FROM progress ORDER BY id ASC LIMIT 1")
first_weight_row = cursor.fetchone()

cursor.execute("SELECT weight, date FROM progress ORDER BY id DESC LIMIT 1")
last_weight_row = cursor.fetchone()
conn.close()

# Başlangıç ve Güncel Kilo Atamaları
baslangic_kilosu = 79.95
baslangic_tarihi = "2026-06-20"

if first_weight_row:
    baslangic_kilosu = first_weight_row[0]
    baslangic_tarihi = first_weight_row[1]

current_weight = last_weight_row[0] if last_weight_row else baslangic_kilosu
current_weight_date = last_weight_row[1] if last_weight_row else today

# Değişim Analitiği Hesaplamaları
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
tahmini_yag_yakimi_gr = (kalori_acigi / 7.7) if kalori_acigi > 0 else 0

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

Gelişim ve Kamp Kıyaslama Analizi:
- Başlangıç Kilon ({baslangic_tarihi}): {baslangic_kilosu:.2f} kg
- Güncel Kilon ({current_weight_date}): {current_weight:.2f} kg
- Toplam Değişim: {toplam_kilo_degisimi:.2f} kg
- Tahmini Başlangıç Yağ Oranın: %{baslangic_yag_orani:.1f}
- Tahmini Güncel Yağ Oranın: %{tahmini_mevcut_yag_orani:.1f}

Bugünkü Gerçek Zamanlı Veriler:
- Alınan Kalori: {cal:.0f} kcal (Protein: {prot:.1f}g, Karbonhidrat: {carb:.1f}g, Yağ: {fat:.1f}g)
- Yapılan İdmanlar: {workout_str}
- Yapılan Kardiyolar: {cardio_str}
- Alınan Supplementler ve Miktarları: {supp_str}

Arka Plan Analiz Motoru Sonuçları:
- Günlük Bazal Metabolizma + İdman Harcaması (TDEE): {tahmini_yakilan:.0f} kcal
- Şu Anki Net Kalori Açığı: {kalori_acigi:.0f} kcal
- Bugün Yakılan Net Yağ: {tahmini_yag_yakimi_gr:.1f} gram
- Gelecek Projeksiyonu: {projeksiyon_str}

Senden Beklenen Sert ve Gerçekçi Koçluk Kuralları:
1. Zamanın farkında ol! Saat şu an Türkiye saati ile tam olarak {current_time}. Eğer saat öğlen veya akşamsa ve hala 'Henüz idman girilmedi' yazıyorsa, hemen "Saat {current_time} oldu, idmana ne zaman gidiyorsun? Bugün PPL'in hangi günündesin, planda ne var?" diye hesap sor.
2. Analiz yaparken mutlaka başlangıç verileri ile şimdiki verileri kıyasla! Gelişimi yüzüne vur ya da gidişat kötüyse uyar.
3. Bugün yapılan kardiyo bilgisini kontrol et. Eğer kullanıcı çok kalori aldıysa veya kalori açığı azsa ve 'Henüz kardiyo girilmedi' yazıyorsa, kesinlikle sert bir şekilde kardiyo yapmasını söyle, uyar.
4. Kesinlikle boş yere övme. Protein eksikse "Bu proteinle kas kütleni koruyamazsın" de. Kalori fazlaysa ya da açık azsa "Böyle giderse yağ yakamazsın, hedefin hayal olur" de. 
5. Yağ oranı ve gelecek projeksiyonunu analiz et. Kullanıcıya net olarak: "Şu anki durumuna göre yağ oranın tahmini %{tahmini_mevcut_yag_orani:.1f}. Eğer bu disiplini bozmazsan şu günde %14'e düşeceksin, ama bozduğun an takvim patlar" şeklinde matematiksel konuş.
6. Supplement miktarlarına (örneğin 50g Cream of Rice, ZMA vb.) dikkat et. Alınmadıysa eksikliğini yüzüne vur.
"""

# ==================== 1. SAYFA: ÖZET & KOÇUN RAPORU ====================
# 🔥 Koçun Günlük Raporu & Özet sayfası için:
if choice == "🔥 Koçun Günlük Raporu & Özet":
    # ... (metriklerin burada kalsın) ...

    # ANALİZİ BUTONA BAĞLIYORUZ:
    if st.button("Koçtan Yeni Analiz İste 🧠"):
        model = get_gemini_model()
        if model:
            with st.spinner("Analiz ediliyor..."):
                try:
                    response = model.generate_content([system_context, prompt])
                    st.session_state["rapor_hafiza"] = response.text
                except Exception as e:
                    st.error(f"Hata: {e}")
    
    # Raporu butona basınca hafızadan göster:
    if "rapor_hafiza" in st.session_state:
        st.write(st.session_state["rapor_hafiza"])
    st.header("📋 Gerçek Zamanlı Analiz Paneli")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Alınan Kalori", f"{cal:.0f} kcal")
    col2.metric("Protein", f"{prot:.1f} g")
    col3.metric("Tahmini Yağ Oranın", f"%{tahmini_mevcut_yag_orani:.1f}")
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
        with st.spinner("Koçun tüm verilerini ve zaman parametrelerini analiz ediyor..."):
            try:
                prompt = "Mevcut saate, başlangıç/güncel kilo değişimlerine ve bugünkü verilere bakarak bana hiç lafı dolandırmadan; 'Kamp Gelişim / Değişim Değerlendirmesi', 'Zamanlama, İdman ve Kardiyo Kontrolü', 'Yağ Oranı ve Projeksiyon Değerlendirmesi' başlıklarıyla net, sert ve matematiksel bir karne çıkar."
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
elif choice == "🥗 Yemek & Otomatik Makro":
    st.header("🥗 Bugün Ne Gömdün?")
    st.subheader("Makroları Sen Değil, Koç Hesaplasın")
    
    user_food_input = st.text_area("Ne yediğini gramajıyla veya porsiyonuyla serbestçe yaz kanka:", 
                                   placeholder="Örn: 300 gram pirinç pilavı ve 200 gram tavuk göğsü")
    
    model = get_gemini_model()
    
    if st.button("Öğünü Çözümle ve Sisteme İşle"):
        if not model:
            st.error("Kanka sol menüden Gemini API Key girmen lazım, yoksa yapay zeka yemeği hesaplayamaz!")
        elif not user_food_input.strip():
            st.warning("Lütfen boş bırakma, ne yediğini yaz.")
        else:
            with st.spinner("Yapay zeka besin değerlerini ve makroları çıkartıyor..."):
                try:
                    macro_prompt = f"""
                    Kullanıcı şunu yedi: "{user_food_input}"
                    Bu yemeğin/öğünün kalori ve makro değerlerini (karbonhidrat, protein, yağ) profesyonel bir fitness veritabanı hassasiyetinde tahmin et.
                    Sadece ve sadece aşağıdaki JSON formatında çıktı ver, başka hiçbir yazı, açıklama veya markdown kesmesi ekleme:
                    {{"calories": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0, "summary": "Kısa yemek adı veya özeti"}}
                    """
                    response = model.generate_content(macro_prompt)
                    
                   # 260. satıra bunu yapıştır:
                    raw_text = response.text.strip()
                    clean_text = raw_text.replace("```json", "").replace("```", "").strip()
                    data = json.loads(clean_text)
                    
                    
                    conn = sqlite3.connect('fitness_tracker.db')
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO nutrition (date, food_name, calories, protein, carbs, fat) 
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (today, data["summary"], data["calories"], data["protein"], data["carbs"], data["fat"]))
                    conn.commit()
                    conn.close()
                    
                    st.success(f"✔️ Başarıyla İşlendi: **{data['summary']}**")
                    st.markdown(f"""
                    - **Tahmini Kalori:** {data['calories']:.0f} kcal
                    - **Protein:** {data['protein']:.1f} g
                    - **Karbonhidrat:** {data['carbs']:.1f} g
                    - **Yağ:** {data['fat']:.1f} g
                    """)
                    st.info("Değerler doğrudan bugünün toplam gelişim paneline eklendi!")
                except Exception as e:
                    st.error(f"Yemek çözümlenirken bir hata oluştu: {e}. Lütfen girdiyi net yazıp tekrar dene.")

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

# ==================== 5. SAYFA: ANTRENMAN & KARDİYO ====================
elif choice == "🏋️‍♂️ PPL Antrenman Günlüğü":
    st.header("🏋️‍♂️ Bugün Demirleri Nasıl Ağlattın?")
    
    st.subheader("💪 Ağırlık Antrenmanı Gir")
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

    st.markdown("---")
    
    st.subheader("🏃‍♂️ Kardiyo Ekle")
    cardio_type = st.selectbox("Kardiyo Tipi", ["Eğimli Yürüyüş (Incline Treadmill)", "Koşu", "Bisiklet", "Merdiven (Stairmaster)", "HIIT Kardiyo"])
    duration = st.number_input("Kaç Dakika Yaptın?", min_value=1, value=20, step=5)
    intensity = st.selectbox("Tempo / Yoğunluk", ["Düşük Tempo (LISS)", "Orta Tempo", "Yüksek Tempo (HIIT)"])
    
    if st.button("Kardiyoyu Kaydet"):
        conn = sqlite3.connect('fitness_tracker.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO cardio (date, cardio_type, duration_min, intensity) VALUES (?, ?, ?, ?)", (today, cardio_type, duration, intensity))
        conn.commit()
        conn.close()
        st.success(f"{duration} dakikalık {cardio_type} koçun defterine işlendi!")

# ==================== 6. SAYFA: KİLO KAYDI ====================
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
