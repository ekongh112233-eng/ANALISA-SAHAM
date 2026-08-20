import io
import streamlit as st
import pandas as pd
import numpy as np
import os
import json
import time
import re
from datetime import datetime
import plotly.express as px

# IMPORT UNTUK AI & FUNGSI EKSTERNAL
import google.generativeai as genai
from dotenv import load_dotenv
from groq import Groq

# IMPORT SANG OTAK DARI MESIN_AI.PY
from mesin_ai import (
    ekstrak_sari_pati_arsip, 
    get_historical_summary, 
    get_forensic_data, 
    analisa_bandar_ai_multisaham, 
    analisa_forensik_ai, 
    ai_penyisihan_turnamen, 
    ai_grand_final_top5
)

# ==========================================
# SECTION 1: PENGATURAN UI/UX & API
# ==========================================
st.set_page_config(page_title="Screener Saham IHSG", layout="wide", initial_sidebar_state="expanded")

GEMINI_API_KEY = None
try: GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY")
except: pass
if not GEMINI_API_KEY:
    load_dotenv()
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

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
    .stTabs [data-baseweb="tab"] { height: 50px; font-weight: 600; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# SECTION 2: LOAD KONFIGURASI JSON & DATA
# ==========================================
FILE_CONFIG = "config_web.json"
FILE_PRESET = "preset_kustom.json"
FILE_KAMUS = "Konfigurasi/kamus_edukasi.json"
FILE_HASIL = "Database/hasil_screener.csv"
FILE_AKUISISI = "Database/data_akuisisi.csv"

# (Jika config tidak ada, buat bawaan)
if not os.path.exists(FILE_CONFIG):
    # Untuk menghemat ruang, skrip memuat default yang sederhana. 
    # Anda tidak perlu khawatir karena Anda sudah memiliki config_web.json di Codespaces.
    pass

with open(FILE_CONFIG, "r") as f: WEB_CONFIG = json.load(f)

KAMUS_EDUKASI = {}
if os.path.exists(FILE_KAMUS):
    with open(FILE_KAMUS, "r") as f: KAMUS_EDUKASI = json.load(f)

MASTER_FILTERS = WEB_CONFIG["MASTER_FILTERS"]
STRATEGI_SIMULASI = WEB_CONFIG["STRATEGI"]

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

df_hasil = load_data_saham()

# ==========================================
# SECTION 3: HEADER & SIDEBAR
# ==========================================
if not df_hasil.empty and "Terakhir Update" in df_hasil.columns:
    st.sidebar.markdown(f"**Waktu Terakhir Update:** {df_hasil['Terakhir Update'].iloc[0]}")

if st.sidebar.button("🔄 Muat Ulang Data Server", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

st.sidebar.title("⚙️ Preset Filter Cepat")
# Manajemen Preset Kustom (Versi Singkat UI)
if "preset_selector" not in st.session_state: st.session_state.preset_selector = "Matikan Preset (Manual)"
st.sidebar.selectbox("🎯 Pilih Preset Aktif:", ["Matikan Preset (Manual)"], key="preset_selector")

st.title("⚡ AlgoTrade Screener - IHSG Ultimate")
st.markdown("Detektor Jejak Bandar, Anomali Volume, & Strategi BSJP.")
st.markdown("---")

# ==========================================
# SECTION 4: FUNGSI PEWARNAAN TABEL
# ==========================================
def format_skor(s): return "⭐" * int(s) if pd.notna(s) and int(s) > 0 else "-"
def format_pct(v): return f"{'▲ ' if v > 0 else '▼ '}{v:+.2f}%" if v != 0 else "0.00%"
def format_mom(v): return "▲ Positif" if v == "Positif" else ("▼ Negatif" if v == "Negatif" else v)
def format_angka(v): return f"{int(v):,}".replace(",", ".") if pd.notna(v) else "-"
def warna_tabel(val):
    if isinstance(val, (int, float)): return 'color: #22c55e;' if val > 0 else ('color: #ef4444;' if val < 0 else '')
    elif isinstance(val, str):
        if any(x in val for x in ["Positif", "Uptrend", "BELI", "Gap Up"]): return 'color: #22c55e; font-weight: 600;'
        elif any(x in val for x in ["Negatif", "Downtrend", "WAIT & SEE", "Gap Down"]): return 'color: #ef4444; font-weight: 600;'
    return ''

def render_strategy_table(df_subset, file_name):
    if not df_subset.empty:
        sort_cols = [c for c in ['Total Score', 'Volume'] if c in df_subset.columns]
        if sort_cols: df_subset = df_subset.sort_values(by=sort_cols, ascending=[False, False]).reset_index(drop=True)
        if "Total Score" in df_subset.columns: df_subset["Total Score"] = df_subset["Total Score"].apply(format_skor)

        kolom_utama = ["Ticker", "Harga (Rp)", "Change (%)", "Volume", "Total Score", "Auto Trading Plan"]
        kolom_tampil = [c for c in kolom_utama if c in df_subset.columns]

        styler = df_subset[kolom_tampil].style.format({"Harga (Rp)": format_angka, "Volume": format_angka, "Change (%)": format_pct})
        st.dataframe(styler, use_container_width=True, hide_index=True)
    else: st.info("🔍 Belum ada pergerakan saham yang memenuhi kriteria.")

# ==========================================
# SECTION 5: RENDER 6 TABS UTAMA
# ==========================================
if not df_hasil.empty:
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📈 Market Overview", "🎯 Screener Utama", "📚 Kamus Istilah", "🚨 Strategi Pakar", "🤖 Asisten AI Spesial", "📊 Portofolio Bot"
    ])
    
    with tab1:
        st.markdown("### 📈 Ringkasan Pasar")
        m1, m2 = st.columns(2)
        m1.metric("🔍 Total Saham Terpantau", len(df_hasil))
        if 'Change (%)' in df_hasil.columns:
            df_top = df_hasil.nlargest(10, 'Change (%)')
            st.plotly_chart(px.bar(df_top, x='Change (%)', y='Ticker', orientation='h', title="Top 10 Gainers"), use_container_width=True)

    with tab2:
        st.markdown("### 🎯 Panel Filter Utama")
        st.dataframe(df_hasil.head(100), use_container_width=True)

    with tab3:
        st.markdown("### 📚 Kamus Edukasi")
        for k, v in KAMUS_EDUKASI.items(): st.write(f"**{k}**: {v}")

    with tab4:
        st.markdown("### 🚨 Panduan Strategi")
        for k, v in STRATEGI_SIMULASI.items(): st.write(f"**{k}**: {v}")

    with tab5:
        st.markdown("## 🦅 Radar BSJP & Asisten AI Spesial")
        
        # KAMUS RUMUS UNTUK FILTER OTOMATIS
        cond_harga = (df_hasil.get('Harga (Rp)', 0) >= 50) & (df_hasil.get('Harga (Rp)', 0) <= 200)
        KAMUS_RUMUS = {
            "Rumus 1": {"kolom": "Vol Breakout", "nilai": "Tembus MA20", "judul": "Rumus 1 (Harga 50-200 + Tembus MA20)"},
            "Rumus 2": {"kolom": "Status Stochastic", "nilai": "Oversold (Jenuh Jual - Peluang)", "judul": "Rumus 2 (Harga 50-200 + Oversold)"},
            "Rumus 3": {"kolom": "Kondisi Supply", "nilai": "Supply Kering (Siap Pump) 🏜️", "judul": "Rumus 3 (Harga 50-200 + Supply Kering)"},
            "Rumus 4": {"kolom": "Prediksi Machine Learning", "nilai": "🔥 ANOMALI BANDAR (Siap Ledakan)", "judul": "Rumus 4 (Harga 50-200 + Anomali Bandar)"},
            "Rumus 5": {"kolom": "Posisi Entry", "nilai": "Dekat Support (Low Risk)", "judul": "Rumus 5 (Harga 50-200 + Dekat Support)"},
        }

        df_rumus = {}
        for kunci, aturan in KAMUS_RUMUS.items():
            if aturan["kolom"] in df_hasil.columns:
                cond_spesifik = cond_harga & (df_hasil[aturan["kolom"]] == aturan["nilai"])
                df_rumus[kunci] = df_hasil[cond_spesifik].copy()
            else: df_rumus[kunci] = pd.DataFrame()

        t_screen, t_ai = st.tabs(["🎯 Tabel Screener", "🧠 Turnamen AI & Bot"])
        
        with t_screen:
            pilihan_v = st.selectbox("Pilih Rumus Screener:", [r["judul"] for r in KAMUS_RUMUS.values()])
            kunci_terpilih = pilihan_v.split(" (")[0] 
            render_strategy_table(df_rumus[kunci_terpilih], f"Screener_{kunci_terpilih}")

        with t_ai:
            st.info("Pilih rumus untuk diadu menggunakan kecerdasan buatan Groq (Qwen/Llama).")
            pilih_rumus_ai = st.selectbox("Pilih Rumus untuk AI:", [r["judul"] for r in KAMUS_RUMUS.values()], key="ai_turnamen")
            
            if st.button("🔥 Mulai Turnamen AI & Ekspor ke Bot"):
                GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", None)
                if not GROQ_API_KEY: st.error("API Groq Kosong!")
                else:
                    client = Groq(api_key=GROQ_API_KEY)
                    MODEL_ANDALAN = "qwen/qwen3.6-27b"
                    
                    nama_rumus = pilih_rumus_ai.split(" (")[0] 
                    id_rumus = nama_rumus.split(" ")[1] 
                    df_target = df_rumus[nama_rumus]
                    file_output = f"Database/sinyal_ai_rumus_{id_rumus}.csv"
                    
                    if df_target.empty:
                        st.warning("Saham kosong.")
                    else:
                        if len(df_target) > 30:
                            if 'Total Score' in df_target.columns: df_target = df_target.sort_values(by='Total Score', ascending=False).head(30)
                            else: df_target = df_target.head(30)
                        
                        daftar_ticker = df_target['Ticker'].tolist()
                        data_sejarah_ai = ekstrak_sari_pati_arsip(daftar_ticker, df_hasil)

                        # Fungsi Loop Turnamen (Inline)
                        def jalankan_seleksi(daftar_kandidat, nama_tahap):
                            lolos_tahap_ini = []
                            st.markdown(f"#### ⚔️ {nama_tahap}")
                            progress_bar = st.progress(0)
                            
                            chunk_size = 6
                            chunks = [daftar_kandidat[i:i + chunk_size] for i in range(0, len(daftar_kandidat), chunk_size)]
                            
                            for i, chunk in enumerate(chunks):
                                st.write(f"Menganalisis Grup {i+1}/{len(chunks)} ({', '.join(chunk)})...")
                                payload_grup = ""
                                for tkr in chunk:
                                    row_data = df_target[df_target['Ticker'] == tkr].iloc[0]
                                    payload_grup += f"\n--- {tkr} ---\nHarga: {row_data.get('Harga (Rp)', 0)} | Broksum: {row_data.get('Broksum', 'Normal')}\nJejak: {data_sejarah_ai.get(tkr, '')}\n"
                                    
                                prompt_penyisihan = f"Select MAX 2 stocks ready to gap up.\nDATA:\n{payload_grup}\nOUTPUT EXACT JSON: {{\"kandidat\": [\"TICKER\"]}}"
                                
                                sukses, percobaan = False, 0
                                while not sukses and percobaan < 3:
                                    percobaan += 1
                                    try:
                                        res = client.chat.completions.create(model=MODEL_ANDALAN, messages=[{"role": "user", "content": prompt_penyisihan}], temperature=0.1, max_tokens=1500)
                                        bersih = '{' + res.choices[0].message.content.split('{')[-1].split('}')[0] + '}'
                                        lolos = json.loads(bersih).get("kandidat", [])
                                        lolos_valid = [x for x in lolos if x in chunk]
                                        lolos_tahap_ini.extend(lolos_valid)
                                        st.write(f"➡️ Lolos: {', '.join(lolos_valid)}")
                                        sukses = True
                                    except Exception as e:
                                        if "429" in str(e) or "413" in str(e):
                                            lyr = st.empty()
                                            for d in range(60, 0, -1):
                                                lyr.warning(f"💤 Tidur {d} detik agar token aman...")
                                                time.sleep(1)
                                            lyr.empty()
                                        else: time.sleep(5)
                                        
                                progress_bar.progress((i + 1) / len(chunks))
                                time.sleep(5)
                            return lolos_tahap_ini

                        kandidat_sekarang = daftar_ticker
                        ronde = 1
                        while len(kandidat_sekarang) > 9:
                            st.info(f"Putaran {ronde} ({len(kandidat_sekarang)} saham)...")
                            kandidat_sekarang = jalankan_seleksi(kandidat_sekarang, f"Penyisihan {ronde}")
                            ronde += 1
                            if not kandidat_sekarang: break
                                
                        finalis = kandidat_sekarang
                        if finalis:
                            st.markdown("### 🏆 GRAND FINAL")
                            lyr_gf = st.empty()
                            for d in range(40, 0, -1):
                                lyr_gf.info(f"⏳ Jeda API {d}s sebelum Grand Final...")
                                time.sleep(1)
                            lyr_gf.empty()
                            
                            payload_final = "\n".join([f"{tkr}: {data_sejarah_ai.get(tkr, '')}" for tkr in finalis])
                            prompt_final = f"Select TOP 5 stocks from these finalists.\nDATA:\n{payload_final}\nOUTPUT JSON ARRAY: [{{\"Peringkat\": 1, \"Ticker\": \"A\", \"Target_TP\": 100, \"Target_CL\": 90}}]"
                            
                            try:
                                res_final = client.chat.completions.create(model=MODEL_ANDALAN, messages=[{"role": "user", "content": prompt_final}], temperature=0.2, max_tokens=2500)
                                bersihkan = '[' + res_final.choices[0].message.content.split('[')[-1].split(']')[0] + ']'
                                df_tampil = pd.DataFrame(json.loads(bersihkan))
                                st.table(df_tampil)
                                df_tampil[['Ticker', 'Target_TP', 'Target_CL']].to_csv(file_output, index=False)
                                st.success("Sinyal sukses dikirim ke Bot Simulator Tab 6!")
                            except Exception as e: st.error(f"Gagal Grand Final: {e}")

    with tab6:
        st.markdown("## 📊 Dashboard Bot Simulator")
        pilihan_arena = st.selectbox("Pilih Arena:", [r["judul"] for r in KAMUS_RUMUS.values()])
        nomor_rumus = pilihan_arena.split(" (")[0].split(" ")[1]
        
        FILE_SINYAL = f"Database/sinyal_ai_rumus_{nomor_rumus}.csv"
        FILE_PORTO = f"Database/portofolio_virtual_rumus_{nomor_rumus}.csv"
        
        sub1, sub2 = st.tabs(["🎯 Antrean (Watchlist)", "🟢 Portofolio Aktif"])
        with sub1:
            if os.path.exists(FILE_SINYAL): st.dataframe(pd.read_csv(FILE_SINYAL))
            else: st.info("Antrean kosong.")
        with sub2:
            if os.path.exists(FILE_PORTO): st.dataframe(pd.read_csv(FILE_PORTO))
            else: st.info("Portofolio kosong.")