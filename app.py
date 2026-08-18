import io
import streamlit as st
import pandas as pd
import numpy as np
import os
import json
import glob
from datetime import datetime
import plotly.express as px

# IMPORT UNTUK AI GEMINI & GROQ
import google.generativeai as genai
from groq import Groq
from dotenv import load_dotenv

# ==========================================
# 🧠 SISTEM ARSIP CERDAS: GPS & PEMERAS DATA
# ==========================================
def ekstrak_sari_pati_arsip(daftar_ticker_terpilih, df_utama):
    """
    Fungsi ini mencari lokasi file arsip berdasarkan harga saham (GPS),
    lalu memeras ribuan baris data 5-menitan menjadi teks pendek untuk AI.
    """
    base_folder = "Arsip_Data_Saham"
    hasil_perasan_ai = {}

    for ticker in daftar_ticker_terpilih:
        # --- 1. SISTEM GPS (Mencari Lokasi Folder) ---
        try:
            # Mengambil harga acuan dari DataFrame utama web Anda
            harga = df_utama[df_utama['Ticker'] == ticker]['Harga (Rp)'].values[0]
        except:
            harga = 0

        # Penentuan Kamar (Folder)
        if 1 <= harga <= 200:
            nama_folder = "Kelas_1_Gorengan_50_200"
        elif 201 <= harga <= 1000:
            nama_folder = "Kelas_2_Midcap_201_1000"
        else:
            nama_folder = "Kelas_3_Bluechip_1001_Plus"

        # Membentuk rute persis di dalam Codespaces Anda
        jalur_file = os.path.join(base_folder, nama_folder, f"{ticker}_arsip.csv")

        # --- 2. MESIN PEMERAS SARI PATI ---
        if os.path.exists(jalur_file):
            try:
                # Membaca data arsip 5-menitan
                df_arsip = pd.read_csv(jalur_file)
                
                # Memastikan format waktu terbaca
                df_arsip['Waktu'] = pd.to_datetime(df_arsip['Waktu'])
                
                # BATES WAKTU EMAS: Potong ketat di jam 17:30
                batas_waktu = pd.to_datetime('17:30').time()
                df_arsip = df_arsip[df_arsip['Waktu'].dt.time <= batas_waktu]

                if not df_arsip.empty:
                    # Mengambil intisari pergerakan
                    harga_pagi = df_arsip['Harga'].iloc[0]
                    harga_sore = df_arsip['Harga'].iloc[-1]
                    total_vol = df_arsip['Volume'].sum()
                    
                    # Mencari jejak "Paus" (Ledakan volume terbesar di jam berapa?)
                    idx_ledakan = df_arsip['Volume'].idxmax()
                    jam_ledakan = df_arsip.loc[idx_ledakan, 'Waktu'].strftime('%H:%M')
                    vol_ledakan = df_arsip.loc[idx_ledakan, 'Volume']

                    status = "Uptrend" if harga_sore > harga_pagi else ("Downtrend" if harga_sore < harga_pagi else "Sideways")

                    # Merakit 1 kalimat super padat (Token AI sangat hemat!)
                    sari_pati = (
                        f"Tren {status} (Rp {harga_pagi} ke Rp {harga_sore}). "
                        f"Akumulasi agresif terdeteksi pada pukul {jam_ledakan} dengan guyuran volume {vol_ledakan} lot."
                    )
                    hasil_perasan_ai[ticker] = sari_pati
                else:
                    hasil_perasan_ai[ticker] = "Data transaksi kosong sebelum pukul 17:30."
            except Exception as e:
                hasil_perasan_ai[ticker] = f"Error kompresi data: {e}"
        else:
            hasil_perasan_ai[ticker] = "Arsip 5-menit belum terbentuk."

    return hasil_perasan_ai

# ==========================================
# SECTION 1: PENGATURAN UI/UX & API
# ==========================================
st.set_page_config(page_title="Screener Saham IHSG", layout="wide", initial_sidebar_state="expanded")

# Konfigurasi API Gemini
GEMINI_API_KEY = None
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    pass
if not GEMINI_API_KEY:
    try:
        load_dotenv()
        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    except:
        pass
if not GEMINI_API_KEY:
    GEMINI_API_KEY = None 
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

@st.cache_data
def ambil_daftar_ai():
    if not GEMINI_API_KEY:
        return ['❌ API Key Belum Terbaca!']
    return ['gemma-4-26b-a4b-it']

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stDataFrame { border-radius: 12px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.15); }
    h1 { font-weight: 800; background: -webkit-linear-gradient(#38bdf8, #3b82f6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; padding-bottom: 10px; }
    .metric-container { border-radius: 10px; padding: 15px; text-align: center; border: 1px solid #334155; background-color: #1e293b; color: #f8fafc; margin-bottom: 20px; }
    .bandar-box { border-left: 5px solid #ef4444; background-color: #2a1111; padding: 15px; border-radius: 8px; margin-bottom: 15px; }
    .bandar-box-green { border-left: 5px solid #22c55e; background-color: #0f291e; padding: 15px; border-radius: 8px; margin-bottom: 15px; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: transparent; border-radius: 4px 4px 0px 0px; padding: 10px 16px; font-weight: 600; }
    .view-mode-container { background-color: #0f172a; padding: 10px 20px; border-radius: 8px; margin-bottom: 15px; border: 1px solid #334155; }
    
    div[data-baseweb="select"] > div { height: auto; min-height: 38px; }
    div[data-baseweb="select"] span { white-space: normal !important; word-break: break-word !important; line-height: 1.4 !important; }
    ul[data-baseweb="menu"] li { white-space: normal !important; word-break: break-word !important; padding-top: 8px !important; padding-bottom: 8px !important; line-height: 1.4 !important; }
    li[role="option"] { white-space: normal !important; word-wrap: break-word !important; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# SECTION 2: LOAD KONFIGURASI JSON
# ==========================================
FILE_CONFIG = "config_web.json"
FILE_PRESET = "preset_kustom.json"
FILE_KAMUS = "kamus_edukasi.json"
FILE_HASIL = "hasil_screener.csv"
FILE_AKUISISI = "data_akuisisi.csv"

DEFAULT_CONFIG = {
    "MASTER_FILTERS": {
        "Kategori": {"label": "🏢 Kategori Saham", "options": ["Semua", "Big Cap (Lapis 1)", "Mid Cap (Lapis 2)", "Small Cap (Lapis 3)"]},
        "Status Open": {"label": "🌅 Sinyal Open", "options": ["Semua", "Open = Low (Bullish Kuat)", "Open = High (Tekanan Jual)", "Normal"]},
        "Risk/Reward Ratio": {"label": "⚖️ Risk/Reward", "options": ["Semua", "Sangat Menarik (> 1:3)", "Ideal (1:2)", "Menengah (1:1)", "Tidak Ideal (< 1:1)", "Di Area Support"]},
        "Kelas Transaksi": {"label": "💸 Kelas Transaksi", "options": ["Semua", "Sultan (> 50M/hari)", "Ritel Aktif (5M - 50M)", "Gorengan Sepi (< 5M)"]},
        "Sinyal Cuci Barang": {"label": "🧹 Sinyal Shakeout", "options": ["Semua", "Jarum Bawah (Sinyal Pantulan Kuat)", "Normal"]},
        "Valuasi": {"label": "💎 Valuasi Fundamental", "options": ["Semua", "Undervalued (Murah)", "Fair Value (Wajar)", "Overvalued (Mahal)"]},
        "Posisi VWAP": {"label": "⚖️ Posisi thd VWAP", "options": ["Semua", "Di Atas VWAP (Kuat)", "Di Bawah VWAP (Lemah)", "Persis di VWAP"]},
        "Fase Siklus Bandar": {"label": "🔄 Siklus Wyckoff", "options": ["Semua", "Accumulation (Kumpul Barang)", "Mark-Up (Fase Pesta)", "Distribution (Fase Jualan)", "Mark-Down (Fase Runtuh)", "Sideways"]},
        "RVOL (Anomali Vol)": {"label": "🌋 Ledakan Volume", "options": ["Semua", "Ledakan Ekstrem (> 300%)", "Anomali Tinggi (150-300%)", "Normal (50-150%)", "Sepi (< 50%)"]},
        "Karakter Gorengan": {"label": "🕵️ Karakter Saham", "options": ["Semua", "Spesialis Tiang Jemuran (Banting Pucuk)", "Solid (Jarang Dibanting)", "Normal"]},
        "Status Bandar": {"label": "🕵️ Status Bandar", "options": ["Semua", "Akumulasi Kuat", "Distribusi Kuat", "Normal"]},
        "Tekanan Bandar": {"label": "⚔️ Tekanan Harian", "options": ["Semua", "Dominan Beli (Hajar Kanan)", "Dominan Jual (Guyur)", "Seimbang / Adu Mekanik"]},
        "Kekuatan A/D": {"label": "🧠 Smart Money (A/D)", "options": ["Semua", "Akumulasi Pro (Smart Money)", "Distribusi Pro (Guyuran)", "Netral"]},
        "OBV Trend": {"label": "🌊 Tren Uang (OBV)", "options": ["Semua", "Akumulasi (Naik)", "Distribusi (Turun)", "Netral"]},
        "Pola Candle": {"label": "🕯️ Price Action", "options": ["Semua", "Marubozu (Strong Bullish)", "Hammer (Potensi Reversal)", "Doji (Ragu-ragu)", "Normal"]},
        "Posisi Entry": {"label": "🎯 Jarak ke Support", "options": ["Semua", "Dekat Support (Low Risk)", "Area Tengah", "Rawan Pucuk (High Risk)"]},
        "Vol Breakout": {"label": "🔊 Volume", "options": ["Semua", "Tembus MA20", "Normal"]},
        "RSI (14D)": {"label": "📊 RSI (14D)", "options": ["Semua", "> 50 (Bullish)", "<= 50 (Bearish)"]},
        "MA Signal": {"label": "📈 Tren (MA20)", "options": ["Semua", "Uptrend", "Downtrend"]},
        "Momentum": {"label": "⚡ Momentum", "options": ["Semua", "Positif", "Negatif"]},
        "Total Score": {"label": "⭐ Total Score", "options": ["Semua", 10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0]},
        "Rekomendasi": {"label": "🎯 Rekomendasi", "options": ["Semua", "BELI", "WAIT & SEE"]},
        "Likuiditas": {"label": "💧 Likuiditas", "options": ["Semua", "> 1 Miliar", "< 1 Miliar"]},
        "Status BB": {"label": "🌐 Bollinger Bands", "options": ["Semua", "Squeeze", "Bottom Rebound", "Breakout Upper", "Normal"]},
        "MA Cross": {"label": "🔀 MA Cross (5/20)", "options": ["Semua", "Golden Cross", "Bullish", "Death Cross", "Bearish"]},
        "Risiko": {"label": "⚠️ Risiko Volatilitas", "options": ["Semua", "Tinggi", "Sedang", "Rendah"]},
        "Status Akuisisi": {"label": "🤝 Sentimen Akuisisi", "options": ["Semua", "TIDAK ADA", "RENCANA AKUISISI", "DALAM AKUISISI"]},
        "MACD": {"label": "📈 MACD", "options": ["Semua", "Strong Bullish", "Bullish MACD", "Strong Bearish", "Bearish MACD"]},
        "Status Stochastic": {"label": "🌊 Stochastic", "options": ["Semua", "Oversold (Jenuh Jual - Peluang)", "Golden Cross (Awal Bullish)", "Overbought (Jenuh Beli - Rawan)", "Death Cross (Awal Bearish)", "Netral / Sideways"]},
        "Status Sentimen": {"label": "📰 Sentimen Berita", "options": ["Semua", "Sentimen Positif 📰", "Sentimen Negatif ⚠️", "Netral / Sepi Berita"]},
        "Prediksi Machine Learning": {"label": "🧠 AI Machine Learning", "options": ["Semua", "🔥 ANOMALI BANDAR (Siap Ledakan)", "⚠️ Anomali (Sudah Terbang)", "Biasa / Mengikuti Pasar"]},
        "Kondisi Supply": {"label": "🏜️ Supply & Demand", "options": ["Semua", "Supply Kering (Siap Pump) 🏜️", "Supply Banjir (Distribusi) 🌊", "Normal / Sedang Transisi"]},
        "Status Fibonacci": {"label": "📏 Level Fibonacci", "options": ["Semua", "Golden Rebound Fibo 61.8% (Golden Ratio) 🎯", "Dekat Support Fibo 61.8% (Golden Ratio)", "Golden Rebound Fibo 50.0% 🎯", "Golden Rebound Fibo 38.2% 🎯", "Mengambang (Jauh dari Fibo)"]}
    },
    "STRATEGI": {
        "1. BSJP (Beli Sore Jual Pagi) ⏰ 15:30": "Aturan: 1) Eksekusi HANYA jam 15:30 - 15:45. 2) Pilih preset 'BSJP' di sidebar kiri. 3) Beli di sore hari, set Take Profit otomatis 3-5% untuk esok pagi saat market buka.",
        "2. HAKA Pagi (Open = Low) ⏰ 09:05": "Aturan: 1) Buka screener pukul 09:05. 2) Filter: Status Open = 'Open = Low', RVOL = 'Ledakan Ekstrem (> 300%)'. 3) Cocokkan Target TP di kolom Auto Trading Plan.",
        "3. Buy on Weakness (Tangkap Pisau Jatuh)": "Filter: Streak Harian = 'Turun Beruntun', Sinyal Cuci Barang = 'Jarum Bawah', Kekuatan A/D = 'Akumulasi Pro'. Momen ritel panik tapi bandar memborong.",
        "4. Menghindari Guyuran Bandar": "Jika saham naik kencang TAPI Tekanan Bandar 'Dominan Jual', bandar sedang take profit perlahan."
    }
}

if not os.path.exists(FILE_CONFIG):
    with open(FILE_CONFIG, "w") as f: json.dump(DEFAULT_CONFIG, f, indent=4)
else:
    with open(FILE_CONFIG, "r") as f: cek_config = json.load(f)
    if "Status Fibonacci" not in cek_config.get("MASTER_FILTERS", {}):
        with open(FILE_CONFIG, "w") as f: json.dump(DEFAULT_CONFIG, f, indent=4)

with open(FILE_CONFIG, "r") as f: WEB_CONFIG = json.load(f)

KAMUS_EDUKASI = {}
if os.path.exists(FILE_KAMUS):
    with open(FILE_KAMUS, "r") as f: KAMUS_EDUKASI = json.load(f)

MASTER_FILTERS = WEB_CONFIG["MASTER_FILTERS"]
STRATEGI_SIMULASI = WEB_CONFIG["STRATEGI"]

# ==========================================
# SECTION 3: DATABASE PRESET & LOAD DATA
# ==========================================
def muat_preset():
    preset_bawaan = {
        "🌙 BSJP (Beli Sore 15:30)": {k: "Semua" for k in MASTER_FILTERS},
        "⚡ HAKA Sesi Pagi (Open=Low)": {k: "Semua" for k in MASTER_FILTERS},
        "🚀 Gorengan Aktif (High Risk)": {k: "Semua" for k in MASTER_FILTERS},
        "🎣 Pantulan Reversal Emas": {k: "Semua" for k in MASTER_FILTERS},
        "🔥 Bluechip Terakumulasi": {k: "Semua" for k in MASTER_FILTERS}
    }
    preset_bawaan["🌙 BSJP (Beli Sore 15:30)"].update({"Tekanan Bandar": "Dominan Beli (Hajar Kanan)", "Karakter Gorengan": "Solid (Jarang Dibanting)", "Status Bandar": "Akumulasi Kuat", "MA Signal": "Uptrend", "Rekomendasi": "BELI"})
    preset_bawaan["⚡ HAKA Sesi Pagi (Open=Low)"].update({"Status Open": "Open = Low (Bullish Kuat)", "Risk/Reward Ratio": "Sangat Menarik (> 1:3)"})
    preset_bawaan["🚀 Gorengan Aktif (High Risk)"].update({"Kategori": "Small Cap (Lapis 3)", "RVOL (Anomali Vol)": "Ledakan Ekstrem (> 300%)", "Posisi VWAP": "Di Atas VWAP (Kuat)"})
    preset_bawaan["🎣 Pantulan Reversal Emas"].update({"Sinyal Cuci Barang": "Jarum Bawah (Sinyal Pantulan Kuat)", "Kekuatan A/D": "Akumulasi Pro (Smart Money)"})
    preset_bawaan["🔥 Bluechip Terakumulasi"].update({"Status Bandar": "Akumulasi Kuat", "Kategori": "Big Cap (Lapis 1)", "MA Signal": "Uptrend"})

    if os.path.exists(FILE_PRESET):
        try:
            with open(FILE_PRESET, "r") as f: preset_bawaan.update(json.load(f))
        except: pass
    return preset_bawaan

daftar_preset_aktif = muat_preset()
if "preset_selector" not in st.session_state: st.session_state.preset_selector = "Matikan Preset (Manual)"

def apply_preset():
    if st.session_state.preset_selector != "Matikan Preset (Manual)":
        for k, v in daftar_preset_aktif[st.session_state.preset_selector].items():
            if k in MASTER_FILTERS: st.session_state[f"main_{k}"] = v

def manual_override(): st.session_state.preset_selector = "Matikan Preset (Manual)"

@st.cache_data(ttl=10)
def load_data_saham():
    if not os.path.exists(FILE_HASIL): return pd.DataFrame()
    df = pd.read_csv(FILE_HASIL)
    if os.path.exists(FILE_AKUISISI):
        df_akuisisi = pd.read_csv(FILE_AKUISISI)
        if "Status Akuisisi" in df.columns: df = df.drop(columns=["Status Akuisisi"])
        df = pd.merge(df, df_akuisisi, on="Ticker", how="left")
        df["Status Akuisisi"] = df["Status Akuisisi"].fillna("TIDAK ADA")
    else: df["Status Akuisisi"] = "TIDAK ADA"
    return df

# ==========================================
# SECTION 3.5: LOGIKA AI & COMPRESSOR ARSIP
# ==========================================
def get_historical_summary(ticker):
    arsip_files = glob.glob("Arsip_Data_Harian/screener_*.csv")
    if not arsip_files: return None
    arsip_files.sort(reverse=True)
    arsip_files = arsip_files[:5]
    
    df_list = []
    for file in arsip_files:
        try:
            cols = ["Waktu Update", "Ticker", "Harga (Rp)", "Volume", "Posisi VWAP", "OBV Trend", "Tekanan Bandar", "Fase Siklus Bandar", "Trend MA (5,20,50)"]
            temp_df = pd.read_csv(file, usecols=lambda c: c in cols)
            temp_df = temp_df[temp_df["Ticker"] == ticker]
            if not temp_df.empty:
                date_str = file.split("_")[-1].replace(".csv", "")
                temp_df["Tanggal"] = date_str
                df_list.append(temp_df)
        except: pass
    
    if not df_list: return None
    df_history = pd.concat(df_list, ignore_index=True)
    df_history = df_history.sort_values(by=["Tanggal", "Waktu Update"])
    
    summary_text = f"REKAM JEJAK ARSIP INTRADAY SAHAM {ticker}:\n\n"
    for date, group in df_history.groupby("Tanggal"):
        open_price = group.iloc[0]["Harga (Rp)"]
        close_price = group.iloc[-1]["Harga (Rp)"]
        max_vol = group["Volume"].max()
        tekanan_akhir = group.iloc[-1]["Tekanan Bandar"]
        siklus = group.iloc[-1]["Fase Siklus Bandar"]
        summary_text += f"📅 {date} | Buka: {open_price} | Tutup: {close_price} | Max Vol Harian: {max_vol} | Tekanan Akhir: {tekanan_akhir} | Siklus Wyckoff: {siklus}\n"
    return summary_text

def get_forensic_data(ticker):
    arsip_files = glob.glob("Arsip_Data_Harian/screener_*.csv")
    if not arsip_files: return None
    arsip_files.sort(reverse=True)
    arsip_files = arsip_files[:5] 
    
    df_list = []
    for file in arsip_files:
        try:
            cols = ["Waktu Update", "Ticker", "Harga (Rp)", "Volume", "Posisi VWAP", "OBV Trend", "Tekanan Bandar", "Fase Siklus Bandar", "Trend MA (5,20,50)", "Status BB", "RVOL (Anomali Vol)"]
            temp_df = pd.read_csv(file, usecols=lambda c: c in cols)
            temp_df = temp_df[temp_df["Ticker"] == ticker]
            if not temp_df.empty:
                date_str = file.split("_")[-1].replace(".csv", "")
                temp_df["Tanggal"] = date_str
                df_list.append(temp_df)
        except: pass
    
    if not df_list: return None
    df_history = pd.concat(df_list, ignore_index=True)
    df_history = df_history.sort_values(by=["Tanggal", "Waktu Update"])
    
    tanggal_unik = sorted(df_history["Tanggal"].unique())
    if len(tanggal_unik) > 1:
        tanggal_unik = tanggal_unik[:-1] 
        tanggal_unik = tanggal_unik[-3:] 
    else:
        return "Data historis sebelum hari ini belum tersedia di arsip."
        
    df_history = df_history[df_history["Tanggal"].isin(tanggal_unik)]
    
    summary_text = f"REKAM JEJAK H-3 SEBELUM MELEDAK SAHAM {ticker}:\n"
    for date, group in df_history.groupby("Tanggal"):
        close_price = group.iloc[-1]["Harga (Rp)"]
        max_vol = group["Volume"].max()
        tekanan_akhir = group.iloc[-1]["Tekanan Bandar"]
        siklus = group.iloc[-1]["Fase Siklus Bandar"]
        obv = group.iloc[-1]["OBV Trend"] if "OBV Trend" in group.columns else "N/A"
        rvol = group.iloc[-1]["RVOL (Anomali Vol)"] if "RVOL (Anomali Vol)" in group.columns else "N/A"
        bb = group.iloc[-1]["Status BB"] if "Status BB" in group.columns else "N/A"
        
        summary_text += f"📅 {date} | Tutup: {close_price} | Vol: {max_vol} | Tekanan: {tekanan_akhir} | Siklus: {siklus} | OBV: {obv} | RVOL: {rvol} | BB: {bb}\n"
    return summary_text

# AI BANDAR (V6)
def analisa_bandar_ai_multisaham(data_saham_dict, pilihan_ai):
    try:
        GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
    except:
        GROQ_API_KEY = None
    if not GROQ_API_KEY: return "❌ Kunci API Groq belum dipasang!"

    try:
        client = Groq(api_key=GROQ_API_KEY)
        model_andalan = "llama-3.1-70b-versatile" 
        try:
            daftar_model = client.models.list()
            semua_model = [m.id for m in daftar_model.data]
            model_70b = [m for m in semua_model if '70b' in m.lower()]
            if model_70b: model_andalan = model_70b[0] 
            else:
                model_llama = [m for m in semua_model if 'llama' in m.lower()]
                if model_llama: model_andalan = model_llama[0]
        except: pass 

        payload_text = ""
        for ticker, data in data_saham_dict.items():
            payload_text += f"\n--- STOCK: {ticker} ---\n"
            payload_text += f"Current Price: Rp {data['harga']}\n"
            payload_text += f"Today's Change: {data['change']}%\n"
            payload_text += f"Broker Summary: {data['broksum']}\n"
            payload_text += f"Wyckoff Phase: {data['status']}\n"
            payload_text += f"Technical Score: {data['skor']}/10\n"
            payload_text += f"Historical Trace (Intraday):\n{data['histori']}\n"

        prompt = f"""
        You are the mastermind of an elite Indonesian stock market syndicate (Mega Bandar). 
        Your specialty is 'Gorengan' (highly volatile) stocks. You DO NOT buy stocks that have already pumped today. You look for "Stealth Accumulation"—stocks that are currently sideways or slightly up (Change is <= 5%), but have massive hidden accumulation in the historical intraday data, indicating they are ready to EXPLODE to top gainers tomorrow.

        I have filtered and provided {len(data_saham_dict)} candidate stocks that haven't pumped yet today.

        YOUR TASK:
        Analyze the 'Historical Trace' and 'Broker Summary' carefully. Select ONLY THE TOP 5 STOCKS that have completed their stealth accumulation phase today (by 15:00) and are 100% ready for a massive Mark-Up tomorrow morning (BSJP strategy).

        STOCK DATA TO ANALYZE:
        {payload_text}

        STRICT RULES:
        1. OUTPUT LANGUAGE: MUST be in Indonesian.
        2. DO NOT list all stocks. ONLY output your Top 5 selections.
        3. Create a Markdown table: [Peringkat, Ticker, Skor Ledakan (0-100%), Status Saat Ini].
        4. Below the table, provide a brutally analytical explanation for each stock. Prove why the pump is imminent by citing specific anomalies from the 'Historical Trace' and 'Broker Summary'.
        5. Provide a realistic Trading Plan (Buy Area near Current Price, Target Price for a massive pump >10%, and a tight Cut Loss). 
        6. Act like a ruthless market maker. No pleasantries. Start immediately with the table.
        """
        completion = client.chat.completions.create(
            model=model_andalan, messages=[{"role": "user", "content": prompt}],
            temperature=0.3, max_tokens=3000, top_p=1, stream=False,
        )
        return completion.choices[0].message.content + f"\n\n---\n⚡ *Dianalisa menggunakan mesin: **{model_andalan}** via Groq*"
    except Exception as e: return f"❌ Gagal memproses data dengan Groq. Error: {e}"

# AI FORENSIK BANDAR (V7)
def analisa_forensik_ai(data_saham_dict, master_filters_keys):
    try:
        GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
    except:
        GROQ_API_KEY = None
    if not GROQ_API_KEY: return "❌ Kunci API Groq belum dipasang!"

    try:
        client = Groq(api_key=GROQ_API_KEY)
        model_andalan = "llama-3.1-70b-versatile" 
        try:
            daftar_model = client.models.list()
            semua_model = [m.id for m in daftar_model.data]
            model_70b = [m for m in semua_model if '70b' in m.lower()]
            if model_70b: model_andalan = model_70b[0] 
            else:
                model_llama = [m for m in semua_model if 'llama' in m.lower()]
                if model_llama: model_andalan = model_llama[0]
        except: pass 

        payload_text = ""
        for ticker, data in data_saham_dict.items():
            payload_text += f"\n--- STOCK: {ticker} ---\n"
            payload_text += f"Broker Summary (Hari H): {data['broksum']}\n"
            payload_text += f"{data['histori']}\n"

        prompt = f"""
        You are a legendary Quantitative Analyst and Stock Market Forensic Expert in Indonesia.
        I am giving you the historical data of {len(data_saham_dict)} stocks from EXACTLY 1 TO 3 DAYS BEFORE they skyrocketed to Top Gainers / ARA (>10%). This is their condition BEFORE the pump.

        YOUR OBJECTIVE:
        1. Reverse engineer the 'Bandar' strategy. Find the exact common "DNA" or hidden patterns that occurred in these stocks during the 3 days BEFORE they exploded, including their Broker Summary activity.
        2. Cross-reference your findings with the EXISTING WEB FILTERS in my application.
        3. Suggest new metrics if my existing filters are missing the secret sauce.

        DATA STOCKS (H-3 to H-1 before pump):
        {payload_text}

        MY EXISTING WEB FILTERS (Categories you can use):
        {master_filters_keys}

        STRICT RULES:
        1. OUTPUT LANGUAGE: MUST be in Indonesian.
        2. Format your response into 3 sections using Markdown:
           - "### 🧬 DNA & Pola Tersembunyi Sebelum Ledakan": Explain exactly what similarities these stocks shared (e.g., "Ketiga saham ini mengalami penurunan harga, namun OBV terus naik dan volume ditahan...").
           - "### 🎛️ Resep Filter Web Saat Ini": Tell me EXACTLY how to set my existing filters (based on the provided list) to catch this pattern tomorrow.
           - "### 💡 Rekomendasi Rumus/Kategori Baru": If there is a pattern not covered by my filters, explicitly suggest what new filter/indicator I should code into my web application.
        3. Be highly analytical, specific, and brutally honest. Do not hallucinate.
        """
        completion = client.chat.completions.create(
            model=model_andalan, messages=[{"role": "user", "content": prompt}],
            temperature=0.2, max_tokens=3000, top_p=1, stream=False,
        )
        return completion.choices[0].message.content + f"\n\n---\n🔬 *Lab Forensik AI: **{model_andalan}** via Groq*"
    except Exception as e: return f"❌ Gagal memproses data dengan Groq. Error: {e}"

# ==========================================
# FUNGSI 1: AI PENYISIHAN (TETAP MENGGUNAKAN LLAMA 3.3)
# Alasan: Sangat cepat, stabil, dan patuh pada format koma tanpa basa-basi.
# ==========================================
def ai_penyisihan_turnamen(data_saham_dict, api_key):
    try:
        client = Groq(api_key=api_key)
        model_andalan = "llama-3.3-70b-versatile"
        try:
            daftar_model = client.models.list()
            semua_model = [m.id for m in daftar_model.data]
            model_70b = [m for m in semua_model if '70b' in m.lower() and '3.1' not in m.lower() and 'deepseek' not in m.lower()]
            if model_70b: model_andalan = model_70b[0] 
        except: pass

        payload_text = ""
        for ticker, data in data_saham_dict.items():
            payload_text += f"\n[{ticker}] Price:{data['harga']} | Vol:{data['volume']} | Broksum:{data['broksum']} | MM:{data['tekanan_bandar']} | Supply:{data['supply']} | OBV:{data['obv']} | Fibo:{data['fibo']}"

        prompt = f"""
        You are a Strict Quantitative Filter for an Indonesian Hedge Fund. 
        Evaluate these {len(data_saham_dict)} candidate stocks.
        {payload_text}

        SLIGHTLY BRUTAL ELIMINATION RULES:
        1. ELIMINATE stocks if Volume is extremely low or dead (Illiquid).
        2. ELIMINATE stocks if Broksum clearly indicates massive Distribution (Dist / Guyuran) without any redeeming technical factors.
        3. KEEP the stock ONLY if it shows "Stealth Accumulation" clues: Broksum is (Acc), OR Supply is drying up (Supply Kering), OR OBV is trending Up, OR it is bouncing off a strong Fibonacci support.
        
        OUTPUT INSTRUCTION:
        Do NOT provide any analysis, tables, or conversational text. 
        ONLY return a comma-separated list of the Ticker symbols that SURVIVE this elimination. 
        If absolutely NO stock survives, output exactly the word: SKIP_GRUP
        Example output: BBCA, ASII, GOTO
        """
        
        completion = client.chat.completions.create(
            model=model_andalan, messages=[{"role": "user", "content": prompt}],
            temperature=0.1, max_tokens=100, top_p=1, stream=False,
        )
        return completion.choices[0].message.content
    except Exception as e:
        return "ERROR"

# ==========================================
# FUNGSI 2: AI GRAND FINAL (HYBRID / AUTO-FALLBACK)
# ==========================================
def ai_grand_final_top5(data_saham_dict, api_key):
    import re
    try:
        client = Groq(api_key=api_key)
        
        # 1. Jadikan Llama 3.3 sebagai cadangan utama yang PASTI JALAN
        model_andalan = "llama-3.3-70b-versatile"
        
        # 2. Radar pelacak otomatis: Cari DeepSeek yang masih aktif di server
        try:
            daftar_model = client.models.list()
            semua_model = [m.id for m in daftar_model.data]
            
            # Cari nama model yang mengandung kata 'deepseek'
            model_deepseek = [m for m in semua_model if 'deepseek' in m.lower()]
            if model_deepseek:
                # Prioritaskan yang versi 70b jika ada
                ds_70b = [m for m in model_deepseek if '70b' in m.lower()]
                model_andalan = ds_70b[0] if ds_70b else model_deepseek[0]
        except: 
            pass

        payload_text = ""
        for ticker, data in data_saham_dict.items():
            payload_text += f"\n--- {ticker} ---\n"
            payload_text += f"Harga: Rp {data['harga']} | Vol: {data['volume']}\n"
            payload_text += f"Broksum: {data['broksum']} | Tekanan: {data['tekanan_bandar']} | Supply: {data['supply']}\n"
            payload_text += f"Teknikal: OBV: {data['obv']} | Fibo: {data['fibo']} | VWAP: {data['vwap']} | Candle: {data['pola_candle']}\n"

        prompt = f"""
        You are the Chief Investment Officer of a Top-Tier Indonesian Hedge Fund.
        I am giving you {len(data_saham_dict)} Elite Semi-Finalist stocks. They have all survived a strict elimination phase and possess signs of stealth accumulation.
        
        DATA SEMI-FINALIS:
        {payload_text}

        YOUR GRAND FINALE MISSION:
        1. Deeply compare and contrast all these surviving stocks.
        2. Rank and select EXACTLY the TOP 5 BEST STOCKS with the absolute highest probability of exploding tomorrow (Gap Up/ARA). (If there are fewer than 5 stocks provided, rank all of them).
        
        STRICT OUTPUT RULES:
        - YOU MUST WRITE YOUR ENTIRE RESPONSE IN INDONESIAN (BAHASA INDONESIA).
        - Start directly with a Markdown table: [Peringkat, Ticker, Skor Potensi (0-100%), Trigger Utama Ledakan].
        - Below the table, provide a brutally honest, highly detailed explanation of WHY these stocks made it to the Top 5. Detail the specific broker activities (Broksum) and technical confluences (Fibo, Supply).
        - Provide a concise Trading Plan (Buy Area, Target Price, Cut Loss) for the Top 3 stocks on your list.
        """
        
        completion = client.chat.completions.create(
            model=model_andalan, messages=[{"role": "user", "content": prompt}],
            temperature=0.3, max_tokens=4000, top_p=1, stream=False,
        )
        
        raw_content = completion.choices[0].message.content
        
        # PEMBERSIHAN OUTPUT DEEPSEEK (Membungkam proses berpikirnya agar UI bersih)
        clean_content = re.sub(r'<think>.*?</think>', '', raw_content, flags=re.DOTALL).strip()
        
        return clean_content + f"\n\n---\n🏆 *Grand Final AI: **{model_andalan}** via Groq*"
    except Exception as e:
        return f"❌ Gagal memproses Grand Final. Error: {e}"


# ==========================================
# FUNGSI 2: ALGO MASTER (GRAND FINAL TOP 5)
# ==========================================
def ai_grand_final(data_saham_dict, api_key):
    try:
        client = Groq(api_key=api_key)
        model_andalan = "llama-3.1-70b-versatile"
        
        payload_text = ""
        for ticker, data in data_saham_dict.items():
            payload_text += f"\n--- STOCK TICKER: {ticker} ---\n"
            payload_text += f"Price: Rp {data['harga']} (Change: {data['change']}%, Volume: {data['volume']})\n"
            payload_text += f"Order Flow: Broksum: {data['broksum']} | MM Pressure: {data['tekanan_bandar']} | Smart Money A/D: {data['ad']} | OBV Trend: {data['obv']}\n"
            payload_text += f"Supply & Anomalies: Supply Condition: {data['supply']} | RVOL: {data['rvol']} | Shakeout Signal: {data['shakeout']}\n"
            payload_text += f"Technical: Fibonacci: {data['fibo']} | VWAP: {data['vwap']} | RSI: {data['rsi']} | Stoch: {data['stochastic']} | MACD: {data['macd']} | BB: {data['bb']} | MA Cross: {data['ma_cross']}\n"
            payload_text += f"Profile: Wyckoff Phase: {data['siklus']} | Candlestick: {data['pola_candle']} | Market Cap: {data['kategori']}\n"

        prompt = f"""
        You are the Chief Quantitative Strategist for a Top-Tier Indonesian Hedge Fund.
        I am handing you a highly curated list of {len(data_saham_dict)} elite candidate stocks. These stocks have already survived a brutal algorithmic elimination process. They are confirmed to be undergoing "Stealth Accumulation" (flat price, hidden massive buying).

        Data for the elite candidates:
        {payload_text}

        YOUR FINAL DIRECTIVE (GRAND FINALE):
        1. Deep Confluence Analysis: Synthesize all variables. Look for the ultimate setup: Smart Money Accumulation (A/D) + Bullish Technicals (Fibo bounces, Golden Crosses, or Squeeze) + Dry Supply.
        2. Select EXACTLY the TOP 5 stocks with the absolute highest, most explosive probability of a massive breakout (Gap Up / ARA) tomorrow. 
        3. If there are fewer than 5 stocks provided, analyze all of them.

        STRICT OUTPUT RULES:
        - YOU MUST WRITE YOUR ENTIRE RESPONSE IN INDONESIAN (BAHASA INDONESIA).
        - Start with a Markdown table: [Peringkat, Ticker, Skor Ledakan (0-100%), Trigger Utama Ledakan].
        - Below the table, provide a brutally honest, highly detailed explanation of WHY these Top 5 were chosen over the others. Detail the specific broker activities and technical confluences.
        - Conclude with a strict, realistic Trading Plan (Buy Area, Target Price > 10%, Cut Loss).
        """
        
        completion = client.chat.completions.create(
            model=model_andalan, messages=[{"role": "user", "content": prompt}],
            temperature=0.2, max_tokens=3000, top_p=1, stream=False,
        )
        return completion.choices[0].message.content + f"\n\n---\n🏆 *AI Grand Final (Top 5): **{model_andalan}** via Groq*"
    except Exception as e:
        return f"❌ Gagal memproses Grand Final. Error: {e}"

# ==========================================
# SECTION 4: HEADER & SIDEBAR
# ==========================================
df_hasil = load_data_saham()

if not df_hasil.empty and "Terakhir Update" in df_hasil.columns:
    waktu_update = df_hasil["Terakhir Update"].iloc[0]
    st.sidebar.markdown(f"""
        <div style="border: 2px solid #06b6d4; padding: 10px; border-radius: 4px; text-align: center; margin-bottom: 15px; background-color: #0f172a; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
            <span style="font-size: 12px; color: #94a3b8; font-weight: 600;">Waktu Terakhir Update:</span><br>
            <strong style="color: #06b6d4; font-size: 14px;">{waktu_update}</strong>
        </div>
    """, unsafe_allow_html=True)

if st.sidebar.button("🔄 Muat Ulang Data Server", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

st.sidebar.title("⚙️ Preset Filter Cepat")
st.sidebar.info("Gunakan **'BSJP (Beli Sore 15:30)'** untuk mencari saham yang mantap dibeli sebelum penutupan bursa!")
opsi_preset = ["Matikan Preset (Manual)"] + list(daftar_preset_aktif.keys())
idx_default = opsi_preset.index(st.session_state.preset_selector) if st.session_state.preset_selector in opsi_preset else 0
st.sidebar.selectbox("🎯 Pilih Preset Aktif:", opsi_preset, index=idx_default, key="preset_selector", on_change=apply_preset)

kustom_presets = {}
if os.path.exists(FILE_PRESET):
    try:
        with open(FILE_PRESET, "r") as f: kustom_presets = json.load(f)
    except: pass

with st.sidebar.expander("🛠️ Manajemen Preset Kustom"):
    tab_edit, tab_hapus = st.tabs(["📝 Buat/Edit", "🗑️ Hapus"])
    with tab_edit:
        opsi_edit = ["-- Buat Baru --"] + list(kustom_presets.keys())
        pilih_edit = st.selectbox("Pilih Preset:", opsi_edit, key="select_edit")
        if pilih_edit == "-- Buat Baru --":
            nama_preset_baru = st.text_input("Nama Preset Baru:", placeholder="Contoh: Strategi X", key="nama_baru")
            nilai_awal = {k: info['options'][0] for k, info in MASTER_FILTERS.items()}
        else:
            nama_preset_baru = st.text_input("Simpan sebagai:", value=pilih_edit, key="nama_edit")
            nilai_awal = kustom_presets[pilih_edit]

        kustom_input = {}
        for k, info in MASTER_FILTERS.items():
            val_awal = nilai_awal.get(k, info['options'][0])
            idx_awal = info['options'].index(val_awal) if val_awal in info['options'] else 0
            kustom_input[k] = st.selectbox(f"P-{info['label']}", info['options'], index=idx_awal, key=f"edit_{k}")

        if st.button("💾 Simpan Preset"):
            if nama_preset_baru.strip():
                if pilih_edit != "-- Buat Baru --" and pilih_edit != nama_preset_baru.strip(): del kustom_presets[pilih_edit]
                kustom_presets[nama_preset_baru.strip()] = kustom_input
                with open(FILE_PRESET, "w") as f: json.dump(kustom_presets, f, indent=4)
                st.session_state.preset_selector = nama_preset_baru.strip()
                st.success("Preset berhasil disimpan!")
                st.rerun()
    with tab_hapus:
        if kustom_presets:
            pilih_hapus = st.selectbox("Pilih Preset untuk Dihapus:", list(kustom_presets.keys()))
            if st.button("🗑️ Hapus Preset"):
                del kustom_presets[pilih_hapus]
                with open(FILE_PRESET, "w") as f: json.dump(kustom_presets, f, indent=4)
                if st.session_state.preset_selector == pilih_hapus: st.session_state.preset_selector = "Matikan Preset (Manual)"
                st.success("Preset dihapus!")
                st.rerun()
        else: st.info("Belum ada preset kustom.")

st.sidebar.markdown("---")
st.title("⚡ AlgoTrade Screener - IHSG Ultimate")
st.markdown("Detektor Jejak Bandar, Anomali Volume, & Strategi BSJP.")
st.markdown("---")

# ==========================================
# SECTION 5: FUNGSI PEWARNAAN
# ==========================================
def format_skor(s): return "⭐" * int(s) if pd.notna(s) and int(s) > 0 else "-"
def format_pct(v): return f"{'▲ ' if v > 0 else '▼ '}{v:+.2f}%" if v != 0 else "0.00%"
def format_mom(v): return "▲ Positif" if v == "Positif" else ("▼ Negatif" if v == "Negatif" else v)
def format_desimal(v): return f"{v:.2f}" if pd.notna(v) and v != 0 else "-"
def format_angka(v): return f"{int(v):,}".replace(",", ".") if pd.notna(v) else "-"
def warna_tabel(val):
    if isinstance(val, (int, float)): 
        return 'color: #22c55e; font-weight: 600;' if val > 0 else ('color: #ef4444; font-weight: 600;' if val < 0 else '')
    elif isinstance(val, str):
        if any(x in val for x in ["Positif", "Uptrend", "BELI", "Breakout Upper", "Bottom Rebound", "DALAM AKUISISI", "Rendah", "▲", "Golden Cross", "Bullish", "Tembus MA20", "Akumulasi", "Big Cap", "Gap Up", "Dominan Beli", "Undervalued", "Marubozu", "Dekat Support", "Hammer", "Di Atas VWAP", "Sultan", "Ledakan Ekstrem", "Solid", "Mark-Up", "Jarum Bawah", "Naik", "Open = Low", "Sangat Menarik", "Perfect Uptrend", "Awal Reversal", "Acc"]): return 'color: #22c55e; font-weight: 600;'
        elif any(x in val for x in ["Negatif", "Downtrend", "WAIT & SEE", "Tinggi", "▼", "Death Cross", "Bearish", "Distribusi", "Small Cap", "Gap Down", "Dominan Jual", "Overvalued", "Rawan Pucuk", "Di Bawah VWAP", "Gorengan Sepi", "Sepi", "Tiang Jemuran", "Mark-Down", "Turun", "Open = High", "Tidak Ideal", "Strong Downtrend", "Dist", "Token Mati", "Gagal", "Timeout"]): return 'color: #ef4444; font-weight: 600;'
        elif val == "> 1 Miliar": return 'color: #3b82f6; font-weight: 600;'
        elif any(x in val for x in ["Squeeze", "RENCANA AKUISISI", "Sedang", "Mid Cap", "Seimbang", "Fair Value", "Area Tengah", "Doji", "Ritel Aktif", "Anomali", "Accumulation", "Sideways", "Ideal", "Menengah", "Konsolidasi / Transisi", "Neutral"]): return 'color: #eab308; font-weight: 600;'
        elif "⭐" in val: return 'color: #22c55e;' if len(val) >= 6 else 'color: #ef4444;'
    return ''

def render_strategy_table(df_subset, file_name):
    if not df_subset.empty:
        sort_cols = [c for c in ['Total Score', 'Volume'] if c in df_subset.columns]
        if sort_cols: df_subset = df_subset.sort_values(by=sort_cols, ascending=[False, False]).reset_index(drop=True)
        if "Total Score" in df_subset.columns: df_subset["Total Score"] = df_subset["Total Score"].apply(format_skor)

        kolom_utama = ["Ticker", "Harga (Rp)", "Change (%)", "Volume", "Total Score", "Auto Trading Plan"]
        kolom_tambahan = ["Broksum", "Trend MA (5,20,50)", "RVOL (Anomali Vol)", "Tekanan Bandar", "Status Bandar", "Kekuatan A/D", "Sinyal Cuci Barang", "Status BB", "MA Signal"]
        kolom_tampil = [c for c in kolom_utama + kolom_tambahan if c in df_subset.columns]

        styler = df_subset[kolom_tampil].style.format({"Harga (Rp)": format_angka, "Volume": format_angka, "Change (%)": format_pct})
        subset_warna = [c for c in kolom_tampil if c not in ["Ticker", "Auto Trading Plan"]]
        tabel_jadi = styler.map(warna_tabel, subset=subset_warna) if hasattr(styler, 'map') else styler.applymap(warna_tabel, subset=subset_warna)

        st.dataframe(tabel_jadi, use_container_width=True, hide_index=True)

        c1, c2 = st.columns([1, 1])
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer: tabel_jadi.to_excel(writer, index=False, sheet_name='Screener')
        c1.download_button(label=f"📥 Download {file_name} (Excel)", data=buffer.getvalue(), file_name=f"{file_name}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=f"dl_{file_name}")
        with c2:
            st.markdown("**📋 Salin Daftar Saham:**")
            st.code("\n".join(df_subset["Ticker"].tolist()), language="text")
            st.caption("Klik icon 'Copy' untuk paste ke Tab AI.")
    else: st.info("🔍 Belum ada pergerakan saham yang memenuhi kriteria strategi ini pada sesi saat ini.")

# ==========================================
# SECTION 6: RENDER TABS
# ==========================================
if not df_hasil.empty:
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📈 Market Overview", 
    "🎯 Screener Utama", 
    "🔎 Cek Saham Spesifik", 
    "🚨 Radar Bandar", 
    "🤖 Screener Spesial", 
    "📊 Portofolio AI"
])
    
    with tab1:
        total = len(df_hasil)
        beli = len(df_hasil[df_hasil['Rekomendasi'] == 'BELI']) if 'Rekomendasi' in df_hasil.columns else 0
        uptrend = len(df_hasil[df_hasil['MA Signal'] == 'Uptrend']) if 'MA Signal' in df_hasil.columns else 0
        m1, m2, m3 = st.columns(3)
        m1.markdown(f"<div class='metric-container'><h3>🔍 Total Saham</h3><h2>{total}</h2></div>", unsafe_allow_html=True)
        m2.markdown(f"<div class='metric-container'><h3>🎯 Sinyal BELI</h3><h2 style='color: #4ade80;'>{beli}</h2></div>", unsafe_allow_html=True)
        m3.markdown(f"<div class='metric-container'><h3>📈 Fase Uptrend</h3><h2 style='color: #60a5fa;'>{uptrend}</h2></div>", unsafe_allow_html=True)
        st.markdown("---")
        c1, c2 = st.columns([1, 2])
        with c1:
            if 'Rekomendasi' in df_hasil.columns:
                df_rek = df_hasil['Rekomendasi'].value_counts().reset_index()
                df_rek.columns = ['Rekomendasi', 'Jumlah']
                st.plotly_chart(px.pie(df_rek, names='Rekomendasi', values='Jumlah', hole=0.5, color='Rekomendasi', color_discrete_map={'BELI': '#22c55e', 'WAIT & SEE': '#ef4444'}), use_container_width=True)
        with c2:
            if 'Change (%)' in df_hasil.columns:
                df_top = df_hasil.nlargest(15, 'Change (%)').iloc[::-1]
                fig_bar = px.bar(df_top, x='Change (%)', y='Ticker', orientation='h', color='Change (%)', color_continuous_scale=['#86efac', '#22c55e', '#166534'])
                fig_bar.update_traces(texttemplate='%{x:.0f}%', textposition='outside')
                st.plotly_chart(fig_bar, use_container_width=True)

    with tab2:
        with st.expander("🎛️ Buka Panel Filter Lengkap", expanded=False):
            col_f1, col_f2, col_f3, col_f4 = st.columns(4)
            filter_terpilih = {}
            for idx, (db_key, info) in enumerate(MASTER_FILTERS.items()):
                target_col = col_f1 if idx % 4 == 0 else (col_f2 if idx % 4 == 1 else (col_f3 if idx % 4 == 2 else col_f4))
                with target_col:
                    val_sekarang = st.session_state.get(f"main_{db_key}", info["options"][0])
                    idx_opsi = info["options"].index(val_sekarang) if val_sekarang in info["options"] else 0
                    filter_terpilih[db_key] = st.selectbox(info["label"], info["options"], index=idx_opsi, key=f"main_{db_key}", on_change=manual_override)

        # Membagi layout menjadi 4 kolom yang proporsional dan rapi
        col_search, col_broker, col_min, col_max = st.columns([1.5, 1.5, 1, 1])
        with col_search: 
            search_ticker = st.text_input("🔍 Cari Kode Saham", "", placeholder="Contoh: BBCA")
        with col_broker: 
            search_broker = st.text_input("🕵️ Cari Kode Broker", "", placeholder="Contoh: MG / YP")
        with col_min: 
            min_price = st.number_input("⬇️ Harga Minimal (Rp)", min_value=0, value=0, step=10)
        with col_max: 
            max_price = st.number_input("⬆️ Harga Maksimal (Rp)", min_value=0, value=0, step=10)

        # 1. AMBIL DATA UTAMA 
        df_filtered = df_hasil.copy()
        
        # 2. EKSEKUSI FILTER PENCARIAN (Ticker & Broker)
        if search_ticker: 
            df_filtered = df_filtered[df_filtered["Ticker"].astype(str).str.contains(search_ticker.upper(), na=False)]
            
        if search_broker and "Broksum" in df_filtered.columns: 
            # Menggunakan astype(str) agar kebal terhadap data kosong (NaN)
            df_filtered = df_filtered[df_filtered["Broksum"].astype(str).str.contains(search_broker.upper(), na=False)]
            
        # 3. EKSEKUSI FILTER HARGA
        if min_price > 0:
            df_filtered = df_filtered[df_filtered["Harga (Rp)"] >= min_price]
        if max_price > 0:
            df_filtered = df_filtered[df_filtered["Harga (Rp)"] <= max_price]
        
        for db_key, nilai in filter_terpilih.items():
            if nilai != "Semua":
                if db_key == "RSI (14D)":
                    if "RSI (14D)" in df_filtered.columns: df_filtered = df_filtered[df_filtered["RSI (14D)"] > 50] if "Bullish" in nilai else df_filtered[df_filtered["RSI (14D)"] <= 50]
                elif db_key == "Total Score":
                    if "Total Score" in df_filtered.columns: df_filtered = df_filtered[df_filtered["Total Score"] == int(nilai)]
                elif db_key in df_filtered.columns: df_filtered = df_filtered[df_filtered[db_key] == nilai]

        if not df_filtered.empty:
            st.caption(f"Menampilkan **{len(df_filtered)}** saham yang lolos filter dari total **{len(df_hasil)}** saham.")
            st.markdown("<div class='view-mode-container'>", unsafe_allow_html=True)
            mode_tampilan = st.radio("👁️ Pilih Mode Tampilan Tabel:", ["🚀 Ringkasan Cepat", "🕵️ Bandarmologi & Wyckoff", "📈 Teknikal & Support", "💎 Fundamental & Likuiditas", "🌌 Tampilkan Semua Kolom"], horizontal=True)
            st.markdown("</div>", unsafe_allow_html=True)
            
            cp1, cp2, cp3 = st.columns([1, 1, 2])
            with cp1: per_hal = st.selectbox("Tampilkan baris:", [20, 50, 100])
            tot_hal = int(np.ceil(len(df_filtered) / per_hal))
            with cp2: hal_aktif = st.selectbox("Halaman:", range(1, tot_hal + 1)) if tot_hal > 0 else 1
                    
            idx_awal = (hal_aktif - 1) * per_hal
            df_tampil = df_filtered.iloc[idx_awal : idx_awal + per_hal].copy()
            if "Total Score" in df_tampil.columns: df_tampil["Total Score"] = df_tampil["Total Score"].apply(format_skor)
            
            kolom_ringkasan = ["Ticker", "Harga (Rp)", "Change (%)", "Broksum", "Rekomendasi", "Status Open", "Posisi VWAP", "Total Score", "Volume", "Auto Trading Plan"]
            kolom_bandar = ["Ticker", "Harga (Rp)", "Change (%)", "Broksum", "Fase Siklus Bandar", "Kekuatan A/D", "Status Bandar", "RVOL (Anomali Vol)", "Karakter Gorengan", "Tekanan Bandar", "OBV Trend", "Kondisi Supply", "Prediksi Machine Learning"]
            kolom_teknikal = ["Ticker", "Harga (Rp)", "Change (%)", "Auto Trading Plan", "Risk/Reward Ratio", "Status Fibonacci", "Sinyal Cuci Barang", "Posisi Entry", "Pola Candle", "Trend MA (5,20,50)", "MA Signal", "Status BB", "RSI (14D)", "MACD", "Status Stochastic"]
            kolom_fundamental = ["Ticker", "Harga (Rp)", "Kategori", "Valuasi", "PER (x)", "PBV (x)", "Kelas Transaksi", "Likuiditas", "Status Sentimen"]
            kolom_semua = ["Ticker", "Broksum", "Status Open", "Risk/Reward Ratio", "Status Fibonacci", "Auto Trading Plan", "Streak Harian", "Sinyal Cuci Barang", "Kategori", "Kelas Transaksi", "Valuasi", "Harga (Rp)", "PER (x)", "PBV (x)", "Harga MA20", "Posisi VWAP", "Support", "Resistance", "Posisi Entry", "Pola Candle", "Change (%)", "Volume", "RVOL (Anomali Vol)", "Vol Breakout", "Status Gap", "Fase Siklus Bandar", "Karakter Gorengan", "Tekanan Bandar", "Kekuatan A/D", "Status Bandar", "OBV Trend", "RSI (14D)", "Momentum", "Trend MA (5,20,50)", "MA Signal", "MA Cross", "MACD", "Status Stochastic", "Status BB", "Risiko", "Likuiditas", "Status Sentimen", "Prediksi Machine Learning", "Kondisi Supply", "Total Score", "Rekomendasi"]
            
            if "Ringkasan" in mode_tampilan: kolom_pilih = kolom_ringkasan
            elif "Bandarmologi" in mode_tampilan: kolom_pilih = kolom_bandar
            elif "Teknikal" in mode_tampilan: kolom_pilih = kolom_teknikal
            elif "Fundamental" in mode_tampilan: kolom_pilih = kolom_fundamental
            else: kolom_pilih = kolom_semua

            kolom_ada = [c for c in kolom_pilih if c in df_tampil.columns]
            format_dict = {}
            for col in ["Harga (Rp)", "Harga MA20", "Support", "Resistance", "Volume"]:
                if col in df_tampil.columns: format_dict[col] = format_angka
            if "Change (%)" in df_tampil.columns: format_dict["Change (%)"] = format_pct
            if "Momentum" in df_tampil.columns: format_dict["Momentum"] = format_mom
            for col in ["PER (x)", "PBV (x)"]:
                if col in df_tampil.columns: format_dict[col] = format_desimal
            if "RSI (14D)" in df_tampil.columns: format_dict["RSI (14D)"] = "{:.0f}"

            styler_obj = df_tampil[kolom_ada].style.format(format_dict)
            subset_warna = [c for c in kolom_ada if c not in ["Ticker", "Auto Trading Plan"]]
            tabel_akhir = styler_obj.map(warna_tabel, subset=subset_warna) if hasattr(styler_obj, 'map') else styler_obj.applymap(warna_tabel, subset=subset_warna)
            st.dataframe(tabel_akhir, use_container_width=True, hide_index=True)
            
            st.markdown("---")
            col_dl, col_wl = st.columns([1, 1])
            with col_dl:
                csv_filter = df_filtered[kolom_ada].to_csv(index=False).encode('utf-8')
                st.download_button(label=f"📥 Download Data Tabel CSV", data=csv_filter, file_name=f"Screener_View_{datetime.now().strftime('%Y%m%d_%H%M')}.csv", mime="text/csv", key="dl_tab2")
            with col_wl:
                st.markdown("**📋 Salin Daftar Saham:**")
                st.code("\n".join(df_filtered["Ticker"].tolist()), language="text")
                st.caption("Klik icon 'Copy' untuk paste massal ke Tab V6/V7.")
        else: st.warning("Tidak ada data sesuai filter.")

    with tab3:
        st.markdown("### 📚 Kamus Istilah Kolom")
        if not KAMUS_EDUKASI: st.warning(f"⚠️ File '{FILE_KAMUS}' tidak ditemukan.")
        else:
            st.info("Berikut adalah penjelasan untuk membaca semua metrik di Tab Screener:")
            for kolom_nama, penjelasan in KAMUS_EDUKASI.items(): st.markdown(f"🔹 **{kolom_nama}**: {penjelasan}")

    with tab4:
        st.markdown("### 📈 Strategi & Simulasi Trading Profesional (Termasuk BSJP)")
        st.success("Terapkan kombinasi filter Screener Anda menggunakan pendekatan para ahli di bawah ini.")
        for judul, deskripsi in STRATEGI_SIMULASI.items():
            with st.expander(f"💼 {judul}", expanded=False): st.write(deskripsi)
        st.markdown("---")
        if 'Status Bandar' in df_hasil.columns:
            dominasi_bandar = len(df_hasil[df_hasil['Status Bandar'] == 'Akumulasi Kuat'])
            if dominasi_bandar > (len(df_hasil) * 0.1): st.info("🔥 **SIMULASI:** Saat ini banyak saham (>10% pasar) sedang diakumulasi bandar. Fokus pada strategi **BSJP**.")
            else: st.warning("⚖️ **SIMULASI:** Pasar sedang sepi dari pergerakan bandar masif. Gunakan strategi **Buy on Weakness**.")

    with tab5:
        st.markdown("## 🦅 Radar BSJP & Laboratorium Forensik AI")
        st.markdown("<div class='bandar-box-green'><b>💡 INFO:</b> Gunakan kotak pilihan (Dropdown) di bawah ini untuk beralih antar strategi atau mode AI agar tampilan lebih rapi.</div>", unsafe_allow_html=True)
        
        if 'Tekanan Bandar' not in df_hasil.columns:
            st.warning("⏳ **Fitur Radar belum menerima data terbaru.** Harap jalankan 'update_data.py'.")
        else:
            # ===============================================
            # KALKULASI RUMUS 1 - 9 (STRATEGI HARGA 50-200)
            # ===============================================
            # Kondisi Dasar: Harga wajib antara 50 sampai 200
            cond_harga = (df_hasil.get('Harga (Rp)', 0) >= 50) & (df_hasil.get('Harga (Rp)', 0) <= 200)

            cond_v1 = (cond_harga & (df_hasil.get('Vol Breakout', '') == 'Tembus MA20'))
            df_v1 = df_hasil[cond_v1].copy() if not df_hasil.empty else pd.DataFrame()

            cond_v2 = (cond_harga & (df_hasil.get('Status Stochastic', '') == 'Oversold (Jenuh Jual - Peluang)'))
            df_v2 = df_hasil[cond_v2].copy() if not df_hasil.empty else pd.DataFrame()

            cond_v3 = (cond_harga & (df_hasil.get('Kondisi Supply', '') == 'Supply Kering (Siap Pump) 🏜️'))
            df_v3 = df_hasil[cond_v3].copy() if not df_hasil.empty else pd.DataFrame()

            cond_v4 = (cond_harga & (df_hasil.get('Status Fibonacci', '') == 'Golden Rebound Fibo 61.8% (Golden Ratio) 🎯'))
            df_v4 = df_hasil[cond_v4].copy() if not df_hasil.empty else pd.DataFrame()

            cond_v5 = (cond_harga & (df_hasil.get('Prediksi Machine Learning', '') == '🔥 ANOMALI BANDAR (Siap Ledakan)'))
            df_v5 = df_hasil[cond_v5].copy() if not df_hasil.empty else pd.DataFrame()

            cond_v6 = (cond_harga & (df_hasil.get('Posisi Entry', '') == 'Dekat Support (Low Risk)'))
            df_v6 = df_hasil[cond_v6].copy() if not df_hasil.empty else pd.DataFrame()

            cond_v7 = (cond_harga & (df_hasil.get('Kekuatan A/D', '') == 'Akumulasi Pro (Smart Money)'))
            df_v7 = df_hasil[cond_v7].copy() if not df_hasil.empty else pd.DataFrame()

            cond_v8 = (cond_harga & (df_hasil.get('Fase Siklus Bandar', '') == 'Accumulation (Kumpul Barang)'))
            df_v8 = df_hasil[cond_v8].copy() if not df_hasil.empty else pd.DataFrame()

            cond_v9 = (cond_harga & (df_hasil.get('Valuasi', '') == 'Undervalued (Murah)'))
            df_v9 = df_hasil[cond_v9].copy() if not df_hasil.empty else pd.DataFrame()

            # MEMBAGI MENJADI 2 TAB UTAMA YANG RAPI
            tab_screener, tab_ai = st.tabs(["🎯 Screener Spesial", "🧠 Asisten AI"])
            
            # ===============================================
            # AREA SCREENER OTOMATIS
            # ===============================================
            with tab_screener:
                pilihan_v = st.selectbox(
                    "Pilih Rumus Screener:",
                    [
                        "Rumus 1 (Harga 50-200 + Tembus MA20)", 
                        "Rumus 2 (Harga 50-200 + Oversold)", 
                        "Rumus 3 (Harga 50-200 + Supply Kering)", 
                        "Rumus 4 (Harga 50-200 + Golden Fibo 61.8%)", 
                        "Rumus 5 (Harga 50-200 + Anomali Bandar)",
                        "Rumus 6 (Harga 50-200 + Dekat Support)",
                        "Rumus 7 (Harga 50-200 + Akumulasi Pro)",
                        "Rumus 8 (Harga 50-200 + Accumulation Wyckoff)",
                        "Rumus 9 (Harga 50-200 + Undervalued)"
                    ]
                )
                
                st.markdown("---")
                if "Rumus 1" in pilihan_v:
                    render_strategy_table(df_v1, "Screener_Rumus_1")
                elif "Rumus 2" in pilihan_v:
                    render_strategy_table(df_v2, "Screener_Rumus_2")
                elif "Rumus 3" in pilihan_v:
                    render_strategy_table(df_v3, "Screener_Rumus_3")
                elif "Rumus 4" in pilihan_v:
                    render_strategy_table(df_v4, "Screener_Rumus_4")
                elif "Rumus 5" in pilihan_v:
                    render_strategy_table(df_v5, "Screener_Rumus_5")
                elif "Rumus 6" in pilihan_v:
                    render_strategy_table(df_v6, "Screener_Rumus_6")
                elif "Rumus 7" in pilihan_v:
                    render_strategy_table(df_v7, "Screener_Rumus_7")
                elif "Rumus 8" in pilihan_v:
                    render_strategy_table(df_v8, "Screener_Rumus_8")
                elif "Rumus 9" in pilihan_v:
                    render_strategy_table(df_v9, "Screener_Rumus_9")

            # ===============================================
            # AREA KECERDASAN BUATAN (AI)
            # ===============================================
            with tab_ai:
                pilihan_ai = st.selectbox(
                    "Pilih Mode Analisis AI:",
                    [
                        "🤖 AI Bandar (Persiapan BSJP)", 
                        "🔎 Forensik Bandar (Bongkar DNA ARA)", 
                        "🎯 Pemburu ARA (Spesialis DNA Ledakan)"
                    ]
                )
                st.markdown("---")
                
                # --- LOGIKA AI BANDAR ---
                if "AI Bandar" in pilihan_ai:
                    st.subheader("🤖 AI Bandar (Persiapan BSJP Besok)")
                    st.markdown("Paste saham yang MASIH MERAH / SIDEWAYS. AI akan mencari siapa yang siap terbang besok.")
                    input_saham_massal = st.text_area("📋 Paste Daftar Saham (Pisahkan dengan Enter/Spasi):", placeholder="Contoh:\nDMAS\nINDF", height=200, key="input_ai_bandar")
                    
                    if st.button("🔮 Mulai Eksekusi AI Bandar"):
                        import re
                        saham_bersih = [s.strip().upper() for s in re.split(r'[,\s\n]+', input_saham_massal) if s.strip()]
                        saham_unik = list(dict.fromkeys(saham_bersih))
                        saham_valid = [s for s in saham_unik if s in df_hasil['Ticker'].values]
                        
                        df_valid = df_hasil[df_hasil['Ticker'].isin(saham_valid)].copy()
                        if 'Change (%)' in df_valid.columns:
                            df_valid = df_valid[df_valid['Change (%)'] <= 5.0]
                            saham_valid = df_valid['Ticker'].tolist()

                        if not saham_valid:
                            st.error("❌ Saham yang Anda masukkan sudah terbang terlalu tinggi (>5%). Gunakan AI Bandar untuk mencari saham yang masih di bawah!")
                        else:
                            if len(saham_valid) > 19:
                                st.info("🤖 Menyaring 19 saham terbaik untuk mencegah limit AI...")
                                df_valid = df_valid.sort_values(by=['Total Score', 'Volume'], ascending=[False, False])
                                saham_valid = df_valid['Ticker'].head(19).tolist()
                            
                            with st.spinner(f"Menganalisa {len(saham_valid)} saham untuk BSJP besok..."):
                                data_kompilasi = {}
                                for ticker in saham_valid:
                                    data_saham = df_hasil[df_hasil['Ticker'] == ticker].iloc[0]
                                    teks_ringkasan = get_historical_summary(ticker)
                                    data_kompilasi[ticker] = {
                                        'harga': data_saham.get('Harga (Rp)', 0),
                                        'change': data_saham.get('Change (%)', 0), 
                                        'broksum': data_saham.get('Broksum', 'Tidak Ada'),
                                        'status': data_saham.get('Fase Siklus Bandar', 'Normal'),
                                        'skor': data_saham.get('Total Score', 0),
                                        'histori': teks_ringkasan if teks_ringkasan else "Arsip belum tersedia."
                                    }
                                hasil_ai = analisa_bandar_ai_multisaham(data_kompilasi, 'gemma-4-26b-a4b-it')
                                st.info(hasil_ai)

                # --- LOGIKA FORENSIK BANDAR ---
                elif "Forensik Bandar" in pilihan_ai:
                    st.subheader("🔎 Forensik Bandar (Bongkar DNA Top Gainer)")
                    st.markdown("Paste saham-saham yang **HARI INI ARA ATAU NAIK >10%**. AI akan memutar mundur waktu ke H-3, membongkar polanya, dan menciptakan racikan *Screener* untuk Anda!")
                    input_forensik = st.text_area("📋 Paste Daftar Saham ARA/Top Gainer Hari Ini:", placeholder="Contoh:\nVISI\nBBHI\nPANI", height=200, key="input_forensik")
                    
                    if st.button("🔬 Mulai Proses Forensik"):
                        import re
                        saham_bersih = [s.strip().upper() for s in re.split(r'[,\s\n]+', input_forensik) if s.strip()]
                        saham_unik = list(dict.fromkeys(saham_bersih))
                        saham_valid = [s for s in saham_unik if s in df_hasil['Ticker'].values]
                        
                        if not saham_valid:
                            st.error("❌ Kode saham tidak ditemukan di database hari ini.")
                        else:
                            if len(saham_valid) > 15:
                                st.warning("⚠️ Untuk analisa mendalam H-3, kami membatasi max 15 saham agar AI lebih fokus.")
                                saham_valid = saham_valid[:15]
                                
                            with st.spinner(f"Memutar mesin waktu ke H-3 untuk {len(saham_valid)} saham. Mencari DNA Bandar..."):
                                data_kompilasi = {}
                                for ticker in saham_valid:
                                    data_saham = df_hasil[df_hasil['Ticker'] == ticker].iloc[0]
                                    teks_histori = get_forensic_data(ticker)
                                    if teks_histori and "belum tersedia" not in teks_histori:
                                        data_kompilasi[ticker] = {
                                            'broksum': data_saham.get('Broksum', 'Tidak Ada'),
                                            'histori': teks_histori
                                        }
                                
                                if not data_kompilasi:
                                    st.error("❌ Data arsip masa lalu (H-3) tidak ditemukan untuk saham-saham ini.")
                                else:
                                    daftar_kategori_web = ", ".join(MASTER_FILTERS.keys())
                                    hasil_ai = analisa_forensik_ai(data_kompilasi, daftar_kategori_web)
                                    st.success("✅ DNA Berhasil Dibongkar!")
                                    st.info(hasil_ai)

                # --- LOGIKA PEMBURU ARA (TURNAMEN ESTAFET ANTI-MACET) ---
                elif "Pemburu ARA" in pilihan_ai:
                    import re
                    import time
                    
                    st.subheader("🎯 Turnamen AI (Spesialis Akumulasi Siluman)")
                    st.markdown("Paste ratusan (bahkan 900+) saham di sini. Mesin akan melakukan kualifikasi brutal (5 saham/menit) secara estafet. Saham yang lolos akan dikumpulkan untuk diadu di **Grand Final Top 5** pada akhir putaran.")
                    
                    # 1. SETUP MEMORI WEB (SESSION STATE)
                    if 'radar_aktif' not in st.session_state:
                        st.session_state.radar_aktif = False
                        st.session_state.radar_tahap = 1 # 1: Penyisihan, 2: Grand Final
                        st.session_state.radar_antrean = []
                        st.session_state.radar_index = 0
                        st.session_state.total_grup = 0
                        st.session_state.semi_finalists = []

                    GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", None)
                    
                    # ==========================================
                    # MODE STANDBY (MENUNGGU INPUT)
                    # ==========================================
                    if not st.session_state.radar_aktif:
                        input_v8 = st.text_area("📋 Paste Daftar Saham (Pisahkan dengan Enter/Spasi):", placeholder="Contoh:\nVISI\nPANI\nDMAS", height=200, key="input_pemburu_ara")
                        
                        if st.button("🚀 Mulai Turnamen Otomatis"):
                            if not GROQ_API_KEY:
                                st.error("❌ Kunci API Groq belum dipasang!")
                            else:
                                saham_bersih = [s.strip().upper() for s in re.split(r'[,\s\n]+', input_v8) if s.strip()]
                                saham_unik = list(dict.fromkeys(saham_bersih))
                                saham_valid = [s for s in saham_unik if s in df_hasil['Ticker'].values]
                                
                                if not saham_valid:
                                    st.error("❌ Kode saham tidak valid atau tidak ada di database.")
                                else:
                                    batch_size = 10
                                    groups = [saham_valid[i:i + batch_size] for i in range(0, len(saham_valid), batch_size)]
                                    
                                    st.session_state.radar_antrean = groups
                                    st.session_state.total_grup = len(groups)
                                    st.session_state.radar_index = 0
                                    st.session_state.semi_finalists = []
                                    st.session_state.radar_tahap = 1
                                    st.session_state.radar_aktif = True
                                    
                                    st.rerun()

                    # ==========================================
                    # MODE EKSEKUSI (MESIN MENYALA)
                    # ==========================================
                    else:
                        st.warning("⚠️ **JANGAN ME-REFRESH BROWSER!** Mesin sedang menjalankan turnamen.")
                        if st.button("🛑 Hentikan Turnamen Darurat"):
                            st.session_state.radar_aktif = False
                            st.rerun()

                        # --- TAHAP 1: PENYISIHAN ESTAFET ---
                        if st.session_state.radar_tahap == 1:
                            idx = st.session_state.radar_index
                            total = st.session_state.total_grup
                            
                            st.info(f"⚔️ **Babak Penyisihan: Membedah Grup {idx + 1} dari {total}**...")
                            st.progress((idx) / total if total > 0 else 0)

                            group_sekarang = st.session_state.radar_antrean[idx]
                            
                            data_grup = {}
                            for ticker in group_sekarang:
                                data_saham = df_hasil[df_hasil['Ticker'] == ticker].iloc[0]
                                data_grup[ticker] = {
                                    'harga': data_saham.get('Harga (Rp)', 0),
                                    'volume': data_saham.get('Volume', 0),
                                    'broksum': data_saham.get('Broksum', 'Tidak Ada'),
                                    'tekanan_bandar': data_saham.get('Tekanan Bandar', 'Normal'),
                                    'supply': data_saham.get('Kondisi Supply', 'Normal'),
                                    'obv': data_saham.get('OBV Trend', 'Normal'),
                                    'fibo': data_saham.get('Status Fibonacci', 'Normal')
                                }
                                
                            hasil_kualifikasi = ai_penyisihan_turnamen(data_grup, GROQ_API_KEY)
                            
                            if "SKIP_GRUP" not in hasil_kualifikasi and "ERROR" not in hasil_kualifikasi:
                                # Ekstrak Ticker yang lolos
                                lolos = [s.strip().upper() for s in hasil_kualifikasi.replace('`', '').split(',')]
                                lolos_valid = [s for s in lolos if s in group_sekarang] 
                                st.session_state.semi_finalists.extend(lolos_valid)

                            st.session_state.radar_index += 1

                            # Tampilkan Daftar Sementara
                            st.markdown("### 🏆 Daftar Semi-Finalis Sementara")
                            if not st.session_state.semi_finalists:
                                st.info("Belum ada yang lolos kualifikasi brutal...")
                            else:
                                st.success(f"Berhasil mengumpulkan **{len(st.session_state.semi_finalists)} saham** unggulan: {', '.join(st.session_state.semi_finalists)}")

                            if st.session_state.radar_index < total:
                                placeholder_timer = st.empty()
                                for i in range(60, 0, -1):
                                    placeholder_timer.warning(f"⏳ Jeda API (Rate Limit): Lanjut ke Grup {idx + 2} dalam **{i} detik**.")
                                    time.sleep(1)
                                st.rerun()
                            else:
                                # Semua grup selesai, lanjut ke Grand Final
                                st.session_state.radar_tahap = 2
                                st.rerun()

                        # --- TAHAP 2: GRAND FINAL ---
                        elif st.session_state.radar_tahap == 2:
                            st.markdown("### 🏟️ MEMULAI GRAND FINAL")
                            st.progress(1.0)
                            
                            semi_finalists = st.session_state.semi_finalists
                            
                            if not semi_finalists:
                                st.error("💀 Sangat brutal! Tidak ada satu pun saham yang lolos dari babak kualifikasi hari ini.")
                                st.session_state.radar_aktif = False
                                if st.button("🔄 Reset"): st.rerun()
                            else:
                                # Jaga-jaga jika saham lolos terlalu banyak (Max 30 untuk Grand Final agar token aman)
                                if len(semi_finalists) > 35:
                                    st.warning("⚠️ Saham yang lolos terlalu banyak. AI akan memilih 35 terbaik berdasarkan skor sistem sebelum masuk Grand Final.")
                                    df_semi = df_hasil[df_hasil['Ticker'].isin(semi_finalists)].sort_values(by=['Total Score', 'Volume'], ascending=[False, False])
                                    semi_finalists = df_semi['Ticker'].head(35).tolist()

                                with st.spinner(f"🧠 AI Master sedang meracik Grand Final TOP 5 dari {len(semi_finalists)} saham Semi-Finalis..."):
                                    data_final = {}
                                    for ticker in semi_finalists:
                                        data_saham = df_hasil[df_hasil['Ticker'] == ticker].iloc[0]
                                        data_final[ticker] = {
                                            'harga': data_saham.get('Harga (Rp)', 0),
                                            'volume': data_saham.get('Volume', 0),
                                            'broksum': data_saham.get('Broksum', 'Tidak Ada'),
                                            'tekanan_bandar': data_saham.get('Tekanan Bandar', 'Normal'),
                                            'supply': data_saham.get('Kondisi Supply', 'Normal'),
                                            'obv': data_saham.get('OBV Trend', 'Normal'),
                                            'fibo': data_saham.get('Status Fibonacci', 'Normal'),
                                            'vwap': data_saham.get('Posisi VWAP', 'Normal'),
                                            'pola_candle': data_saham.get('Pola Candle', 'Normal')
                                        }
                                        
                                    hasil_grand_final = ai_grand_final_top5(data_final, GROQ_API_KEY)
                                    
                                    st.success("🎉 **TURNAMEN SELESAI!**")
                                    st.balloons()
                                    
                                    # Menggunakan container bawaan Streamlit agar tabel Markdown terbaca sempurna
                                    with st.container():
                                        st.markdown("---")
                                        st.markdown(hasil_grand_final)
                                        st.markdown("---")
                                    
                                    st.session_state.radar_aktif = False
                                    if st.button("🔄 Mulai Turnamen Baru"):
                                        st.rerun()

            # ===============================================
            # AREA ASISTEN AI (SISTEM TURNAMEN LAMBAT & AMAN)
            # ===============================================
            with tab_ai:
                st.markdown("### 🤖 Analisis AI Spesial (Sistem Turnamen & Distribusi Bot)")
                st.info("Pilih satu rumus untuk dianalisis. Mesin menggunakan mode lambat (jeda 60 detik) agar tidak terkena blokir limit API Groq.")
                
                pilih_rumus_ai = st.selectbox(
                    "Pilih Rumus yang akan dianalisis oleh AI:",
                    [
                        "Rumus 1 (Harga 50-200 + Tembus MA20)", 
                        "Rumus 2 (Harga 50-200 + Oversold)", 
                        "Rumus 3 (Harga 50-200 + Supply Kering)", 
                        "Rumus 4 (Harga 50-200 + Golden Fibo 61.8%)", 
                        "Rumus 5 (Harga 50-200 + Anomali Bandar)",
                        "Rumus 6 (Harga 50-200 + Dekat Support)",
                        "Rumus 7 (Harga 50-200 + Akumulasi Pro)",
                        "Rumus 8 (Harga 50-200 + Accumulation Wyckoff)",
                        "Rumus 9 (Harga 50-200 + Undervalued)"
                    ], key="pilihan_ai_spesial"
                )
                
                if st.button("🔥 Mulai Turnamen AI & Ekspor ke Bot"):
                    GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", None)
                    if not GROQ_API_KEY:
                        st.error("Kunci API Groq belum dipasang!")
                    else:
                        import time
                        import json
                        import os
                        from groq import Groq
                        
                        client = Groq(api_key=GROQ_API_KEY)
                        
                        # ==========================================
                        # MEMBACA AMUNISI MODEL DARI FILE EKSTERNAL
                        # ==========================================
                        FILE_MODEL = "versigroq.txt"
                        daftar_model_groq = []
                        
                        if os.path.exists(FILE_MODEL):
                            with open(FILE_MODEL, "r") as f:
                                # Membaca setiap baris, membuang spasi, dan mengabaikan baris kosong
                                daftar_model_groq = [line.strip() for line in f if line.strip()]
                        
                        # Jika file versigroq.txt terhapus atau kosong, gunakan model cadangan darurat
                        if not daftar_model_groq:
                            st.warning(f"⚠️ File {FILE_MODEL} tidak ditemukan atau kosong. Menggunakan model bawaan.")
                            daftar_model_groq = ["llama3-8b-8192", "mixtral-8x7b-32768"]
                        else:
                            st.info(f"✅ Berhasil memuat {len(daftar_model_groq)} amunisi model dari {FILE_MODEL}.")
                        
                        # 1. Tentukan Dataframe dan Nama File Output
                        df_target = pd.DataFrame()
                        file_output = ""
                        nama_rumus = ""
                        
                        if "Rumus 1" in pilih_rumus_ai: df_target, file_output, nama_rumus = df_v1, "sinyal_ai_rumus_1.csv", "Rumus 1"
                        elif "Rumus 2" in pilih_rumus_ai: df_target, file_output, nama_rumus = df_v2, "sinyal_ai_rumus_2.csv", "Rumus 2"
                        elif "Rumus 3" in pilih_rumus_ai: df_target, file_output, nama_rumus = df_v3, "sinyal_ai_rumus_3.csv", "Rumus 3"
                        elif "Rumus 4" in pilih_rumus_ai: df_target, file_output, nama_rumus = df_v4, "sinyal_ai_rumus_4.csv", "Rumus 4"
                        elif "Rumus 5" in pilih_rumus_ai: df_target, file_output, nama_rumus = df_v5, "sinyal_ai_rumus_5.csv", "Rumus 5"
                        elif "Rumus 6" in pilih_rumus_ai: df_target, file_output, nama_rumus = df_v6, "sinyal_ai_rumus_6.csv", "Rumus 6"
                        elif "Rumus 7" in pilih_rumus_ai: df_target, file_output, nama_rumus = df_v7, "sinyal_ai_rumus_7.csv", "Rumus 7"
                        elif "Rumus 8" in pilih_rumus_ai: df_target, file_output, nama_rumus = df_v8, "sinyal_ai_rumus_8.csv", "Rumus 8"
                        elif "Rumus 9" in pilih_rumus_ai: df_target, file_output, nama_rumus = df_v9, "sinyal_ai_rumus_9.csv", "Rumus 9"
                        
                        if df_target.empty:
                            st.warning(f"⚠️ Belum ada saham yang lolos di {nama_rumus} hari ini.")
                        else:
                            daftar_ticker = df_target['Ticker'].tolist()
                            st.success(f"Ditemukan {len(daftar_ticker)} saham. Memulai ekstraksi data historis untuk {nama_rumus}...")
                            
                            data_sejarah_ai = ekstrak_sari_pati_arsip(daftar_ticker, df_hasil)
                            finalis = []
                            
                            # ==========================================
                            # FASE 1: BABAK PENYISIHAN (AUTO-HUNTING MODEL)
                            # ==========================================
                            if len(daftar_ticker) <= 5:
                                st.info("Jumlah kandidat sedikit. Langsung menuju Grand Final!")
                                finalis = daftar_ticker
                            else:
                                st.markdown("#### ⚔️ Babak Penyisihan Dimulai")
                                progress_bar = st.progress(0)
                                
                                chunk_size = 10
                                chunks = [daftar_ticker[i:i + chunk_size] for i in range(0, len(daftar_ticker), chunk_size)]
                                
                                for i, chunk in enumerate(chunks):
                                    st.write(f"Menganalisis Grup {i+1}/{len(chunks)} ({', '.join(chunk)})...")
                                    
                                    payload_grup = ""
                                    for tkr in chunk:
                                        row_data = df_target[df_target['Ticker'] == tkr].iloc[0]
                                        payload_grup += f"\n--- {tkr} ---\n"
                                        payload_grup += f"Harga: {row_data.get('Harga (Rp)', 0)} | Vol: {row_data.get('Volume', 0)}\n"
                                        payload_grup += f"Broksum: {row_data.get('Broksum', 'Normal')} | Supply: {row_data.get('Kondisi Supply', 'Normal')}\n"
                                        payload_grup += f"Jejak Historis: {data_sejarah_ai.get(tkr, 'Tidak ada data')}\n"
                                        
                                    prompt_penyisihan = f"""
                                    From the following list of stocks and their historical data:
                                    {payload_grup}
                                    
                                    YOUR MISSION:
                                    Select a MAXIMUM of 3 BEST STOCKS that show the strongest accumulation footprint (Golden Time) for Day Trading tomorrow.
                                    Reply ONLY with the Tickers of the selected stocks, separated by commas. Do not write any explanations, introductory text, or markdown.
                                    Example reply: VISI, PANI, GOTO
                                    If none of the stocks are good, reply EXACTLY with the word: KOSONG
                                    """
                                    
                                    sukses = False
                                    for model_tes in daftar_model_groq:
                                        if sukses: break
                                        
                                        try:
                                            res = client.chat.completions.create(
                                                model=model_tes,
                                                messages=[{"role": "user", "content": prompt_penyisihan}],
                                                temperature=0.2, max_tokens=50
                                            )
                                            jawaban = res.choices[0].message.content.strip().upper()
                                            
                                            if "KOSONG" not in jawaban:
                                                lolos = [x.strip() for x in jawaban.split(',') if x.strip() in chunk]
                                                finalis.extend(lolos)
                                                st.write(f"➡️ Lolos ke Final: **{', '.join(lolos)}** *(via {model_tes})*")
                                            else:
                                                st.write(f"➡️ Tidak ada yang lolos dari grup ini. *(via {model_tes})*")
                                                
                                            sukses = True
                                            
                                        except Exception as e:
                                            pesan_error = str(e)
                                            if "404" in pesan_error or "model_not_found" in pesan_error:
                                                st.warning(f"⚠️ Model `{model_tes}` tidak aktif (404). Melompat...")
                                                time.sleep(1)
                                            elif "429" in pesan_error:
                                                st.warning(f"⚠️ Kuota limit di `{model_tes}` (429). Beralih ke model lain...")
                                                time.sleep(2)
                                            else:
                                                st.warning(f"⚠️ Error tak terduga di `{model_tes}`. Mencoba model lain...")
                                                time.sleep(1)
                                                
                                    if not sukses:
                                        st.error("🚨 Semua senjata model di versigroq.txt gagal atau limit habis! Grup ini dilewati.")
                                        
                                    progress_bar.progress((i + 1) / len(chunks))
                                    
                                    if i < len(chunks) - 1:
                                        with st.spinner("⏳ Mendinginkan mesin (Jeda 60 detik)..."):
                                            time.sleep(60)
                                    
                            # ==========================================
                            # FASE 2: GRAND FINAL (AUTO-HUNTING MODEL)
                            # ==========================================
                            st.markdown(f"#### 🏆 Grand Final {nama_rumus} (Mencetak Sinyal Auto-Trade)")
                            if not finalis:
                                st.warning("Tidak ada saham yang lolos ke Grand Final. Pasar mungkin sedang buruk.")
                            else:
                                st.write(f"Kandidat Final: {', '.join(finalis)}")
                                
                                with st.spinner("⏳ Persiapan masuk Grand Final (Jeda 30 detik)..."):
                                    time.sleep(30)
                                
                                payload_final = ""
                                for tkr in finalis:
                                    try:
                                        row_data = df_target[df_target['Ticker'] == tkr].iloc[0]
                                        payload_final += f"\n--- {tkr} ---\n"
                                        payload_final += f"Harga: {row_data.get('Harga (Rp)', 0)} | Vol: {row_data.get('Volume', 0)}\n"
                                        payload_final += f"Broksum: {row_data.get('Broksum', 'Normal')} | Supply: {row_data.get('Kondisi Supply', 'Normal')}\n"
                                        payload_final += f"Jejak Historis: {data_sejarah_ai.get(tkr, 'Tidak ada data')}\n"
                                    except:
                                        pass
                                        
                                prompt_final = f"""
                                You are an Elite Indonesian Stock Analyst. You have {len(finalis)} finalists:
                                {payload_final}
                                
                                YOUR MISSION:
                                1. Pick EXACTLY the TOP 5 stocks with the highest probability of Gap Up / ARA tomorrow (If less than 5, pick all).
                                2. Determine Target_TP and Target_CL. They MUST be integer numbers.
                                3. You MUST output ONLY a valid JSON array of objects.
                                
                                Format exactly like this:
                                [
                                  {{"Peringkat": 1, "Ticker": "GOTO", "Alasan": "Akumulasi siluman", "Target_TP": 60, "Target_CL": 50}}
                                ]
                                """
                                
                                with st.spinner(f"AI sedang menyusun JSON untuk Bot {nama_rumus}..."):
                                    sukses_final = False
                                    
                                    for model_tes in daftar_model_groq:
                                        if sukses_final: break
                                        
                                        try:
                                            res_final = client.chat.completions.create(
                                                model=model_tes,
                                                messages=[{"role": "user", "content": prompt_final}],
                                                temperature=0.3, max_tokens=1000
                                            )
                                            
                                            jawaban_raw = res_final.choices[0].message.content
                                            bersih = jawaban_raw.replace('```json', '').replace('```', '').strip()
                                            
                                            hasil_json = json.loads(bersih)
                                            df_tampil = pd.DataFrame(hasil_json)
                                            
                                            with st.container():
                                                st.markdown("---")
                                                st.success(f"🎉 **Sinyal {nama_rumus} Berhasil Dicetak!** *(Model Pekerja: {model_tes})*")
                                                st.table(df_tampil)
                                                st.markdown("---")
                                                
                                            df_sinyal = df_tampil[['Ticker', 'Target_TP', 'Target_CL']]
                                            df_sinyal.to_csv(file_output, index=False)
                                            
                                            st.info(f"🤖 **Sinyal dikirim ke Bot Simulator!** Silakan cek Tab 6 ({nama_rumus}) besok pagi.")
                                            sukses_final = True
                                            
                                        except Exception as e:
                                            pesan_error = str(e)
                                            if "404" in pesan_error or "model_not_found" in pesan_error:
                                                st.warning(f"⚠️ Model `{model_tes}` tidak aktif (404). Melompat...")
                                                time.sleep(1)
                                            elif "429" in pesan_error:
                                                st.warning(f"⚠️ Kuota limit di `{model_tes}` (429). Mencoba model lain...")
                                                time.sleep(2)
                                                
                                    if not sukses_final:
                                        st.error("❌ Terjadi kesalahan mencetak JSON di Grand Final. Semua model di versigroq.txt gagal/limit.")

        # ===============================================
        # TAB 6: DASHBOARD PORTOFOLIO SIMULASI AI
        # ===============================================
        with tab6:
            st.markdown("## 📊 Dashboard Simulasi Auto-Trading (9 Arena)")
            st.markdown("Pantau performa eksekusi bot dari masing-masing rumus secara terpisah (Modal awal Rp 100 Juta per arena).")
            st.markdown("---")

            # MENU DROPDOWN UNTUK MEMILIH ARENA RUMUS
            pilihan_arena = st.selectbox(
                "Pilih Portofolio Arena yang Ingin Dilihat:",
                [f"Rumus {i}" for i in range(1, 10)]
            )
            
            # Ekstrak angka rumus (1-9) dari pilihan dropdown
            nomor_rumus = pilihan_arena.split(" ")[1]
            
            # 1. BACA DATA DARI DATABASE VIRTUAL SPESIFIK RUMUS
            FILE_PORTO = f"portofolio_virtual_rumus_{nomor_rumus}.csv"
            FILE_HIST = f"history_trade_rumus_{nomor_rumus}.csv"
            MODAL_AWAL = 100000000.0

            df_porto = pd.read_csv(FILE_PORTO) if os.path.exists(FILE_PORTO) else pd.DataFrame()
            df_hist = pd.read_csv(FILE_HIST) if os.path.exists(FILE_HIST) else pd.DataFrame()

            # 2. KALKULASI METRIK UTAMA (KPI)
            modal_terpakai = df_porto['Total_Modal'].sum() if not df_porto.empty else 0
            saldo_kas = MODAL_AWAL - modal_terpakai
            
            total_realized_profit = df_hist['Total_Return_Rp'].sum() if not df_hist.empty else 0
            total_aset = saldo_kas + modal_terpakai + total_realized_profit
            
            total_trade = len(df_hist)
            if total_trade > 0:
                win_count = len(df_hist[df_hist['Return_%'] > 0])
                win_rate = (win_count / total_trade) * 100
            else:
                win_rate = 0.0

            # 3. TAMPILAN KARTU METRIK
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric(label="💰 Total Aset (Rp)", value=f"{total_aset:,.0f}".replace(",", "."))
            with col2:
                st.metric(label="💵 Kas Tersedia (Rp)", value=f"{saldo_kas:,.0f}".replace(",", "."))
            with col3:
                st.metric(label="📈 Realized Profit (Rp)", value=f"{total_realized_profit:,.0f}".replace(",", "."), delta=f"{total_realized_profit:,.0f}")
            with col4:
                st.metric(label="🎯 Win Rate AI", value=f"{win_rate:.1f}%", delta=f"{total_trade} Transaksi Selesai", delta_color="off")

            st.markdown("---")

            # 4. SUB-TAB UNTUK TABEL DETAIL
            sub_aktif, sub_riwayat = st.tabs(["🟢 Posisi Aktif (Hold)", "📚 Riwayat Transaksi (Closed)"])

            with sub_aktif:
                if not df_porto.empty:
                    df_porto_tampil = df_porto.copy()
                    df_porto_tampil['Harga_Beli'] = df_porto_tampil['Harga_Beli'].apply(lambda x: f"Rp {x:,.0f}")
                    df_porto_tampil['Target_TP'] = df_porto_tampil['Target_TP'].apply(lambda x: f"Rp {x:,.0f}")
                    df_porto_tampil['Target_CL'] = df_porto_tampil['Target_CL'].apply(lambda x: f"Rp {x:,.0f}")
                    df_porto_tampil['Total_Modal'] = df_porto_tampil['Total_Modal'].apply(lambda x: f"Rp {x:,.0f}".replace(",", "."))
                    
                    st.dataframe(df_porto_tampil, use_container_width=True, hide_index=True)
                else:
                    st.info(f"Buku portofolio {pilihan_arena} kosong.")

            with sub_riwayat:
                if not df_hist.empty:
                    def warnai_profit(val):
                        if isinstance(val, (int, float)):
                            color = '#166534' if val > 0 else '#991b1b' if val < 0 else ''
                            return f'background-color: {color}'
                        return ''

                    df_hist_tampil = df_hist.sort_values(by='Tanggal_Jual', ascending=False).reset_index(drop=True)
                    
                    st.dataframe(
                        df_hist_tampil.style.applymap(warnai_profit, subset=['Total_Return_Rp', 'Return_%']).format({
                            'Harga_Beli': "Rp {:,.0f}",
                            'Harga_Jual': "Rp {:,.0f}",
                            'Total_Return_Rp': "Rp {:,.0f}",
                            'Return_%': "{:.2f}%"
                        }),
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.info(f"Belum ada riwayat penjualan saham untuk {pilihan_arena}.")