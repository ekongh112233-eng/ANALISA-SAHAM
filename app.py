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
# PENGATURAN UI/UX & API
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
    .view-mode-container { background-color: #0f172a; padding: 10px 20px; border-radius: 8px; margin-bottom: 15px; border: 1px solid #334155; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# LOAD KONFIGURASI JSON & DATA
# ==========================================
FILE_CONFIG = "config_web.json"
FILE_PRESET = "preset_kustom.json"
FILE_KAMUS = "Konfigurasi/kamus_edukasi.json"
FILE_HASIL = "Database/hasil_screener.csv"
FILE_AKUISISI = "Database/data_akuisisi.csv"

if not os.path.exists(FILE_CONFIG): pass 

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
# HEADER & SIDEBAR
# ==========================================
if not df_hasil.empty and "Terakhir Update" in df_hasil.columns:
    waktu_update = df_hasil["Terakhir Update"].iloc[0]
    st.sidebar.markdown(f"""
        <div style="border: 2px solid #06b6d4; padding: 10px; border-radius: 4px; text-align: center; margin-bottom: 15px; background-color: #0f172a; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
            <span style="font-size: 12px; color: #94a3b8; font-weight: 600;">Waktu Terakhir Update:</span><br>
            <strong style="color: #06b6d4; font-size: 14px;">{waktu_update}</strong>
        </div>
    """, unsafe_allow_html=True)

if st.sidebar.button("🔃 Muat Ulang Data Server", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

st.sidebar.title("⚙️ Preset Filter Cepat")
st.sidebar.info("Gunakan **'BSJP (Beli Sore 15:30)'** untuk mencari saham yang mantap dibeli sebelum penutupan bursa!")

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

opsi_preset = ["Matikan Preset (Manual)"] + list(daftar_preset_aktif.keys())
idx_default = opsi_preset.index(st.session_state.preset_selector) if st.session_state.preset_selector in opsi_preset else 0
st.sidebar.selectbox("📌 Pilih Preset Aktif:", opsi_preset, index=idx_default, key="preset_selector", on_change=apply_preset)

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

st.title("⚡ AlgoTrade Screener - IHSG Ultimate")
st.markdown("Detektor Jejak Bandar, Anomali Volume, & Strategi BSJP.")
st.markdown("---")

# ==========================================
# FUNGSI PEWARNAAN & FORMATTER TABEL
# ==========================================
def format_skor(s): return "⭐" * int(s) if pd.notna(s) and int(s) > 0 else "-"
def format_pct(v): return f"{'▲ ' if v > 0 else '▼ '}{v:+.2f}%" if pd.notna(v) and v != 0 else "0.00%"
def format_mom(v): return "▲ Positif" if v == "Positif" else ("▼ Negatif" if v == "Negatif" else v)
def format_desimal(v): return f"{v:.2f}" if pd.notna(v) and v != 0 else "-"
def format_angka(v): return f"{int(v):,}".replace(",", ".") if pd.notna(v) else "-"

def format_singkat_vol(v):
    if pd.isna(v): return "-"
    if v >= 1_000_000: return f"{v/1_000_000:.2f} M Lot"
    elif v >= 1_000: return f"{v/1_000:.2f} K Lot"
    return f"{v:.0f} Lot"

def format_singkat_rp(v):
    if pd.isna(v): return "-"
    if v >= 1_000_000_000_000: return f"Rp {v/1_000_000_000_000:.2f} T"
    elif v >= 1_000_000_000: return f"Rp {v/1_000_000_000:.2f} M"
    elif v >= 1_000_000: return f"Rp {v/1_000_000:.2f} Jt"
    return f"Rp {v:,.0f}".replace(",", ".")

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

# ==============================================================================
# DEKLARASI TABS UTAMA
# ==============================================================================
if not df_hasil.empty:
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 Market Overview", "📌 Screener Utama", "📖 Kamus Istilah", "💡 Strategi Pakar", "⚙️ Asisten AI Spesial", "💼 Portofolio Bot"
    ])
    
    # ==========================================================================
    # [TAB 1] MARKET OVERVIEW
    # ==========================================================================
    with tab1:
        st.markdown("### 📊 Ringkasan Pasar IHSG")
        
        total_saham = len(df_hasil)
        saham_naik = len(df_hasil[df_hasil['Change (%)'] > 0]) if 'Change (%)' in df_hasil.columns else 0
        saham_turun = len(df_hasil[df_hasil['Change (%)'] < 0]) if 'Change (%)' in df_hasil.columns else 0
        saham_stagnan = total_saham - saham_naik - saham_turun
        
        if 'Turnover' not in df_hasil.columns:
            if 'Volume' in df_hasil.columns and 'Harga (Rp)' in df_hasil.columns:
                df_hasil['Turnover'] = df_hasil['Harga (Rp)'] * df_hasil['Volume'] * 100
            else:
                df_hasil['Turnover'] = 0

        if saham_naik > (saham_turun * 1.5): sentimen_teks, warna_sentimen = "🔥 Sangat Bullish", "#4ade80"
        elif saham_turun > (saham_naik * 1.5): sentimen_teks, warna_sentimen = "🩸 Sangat Bearish", "#f87171"
        else: sentimen_teks, warna_sentimen = "⚖️ Konsolidasi (Ragu)", "#facc15"
                
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.markdown(f"<div class='metric-container'><h3>🔍 Total Saham</h3><h2>{total_saham}</h2></div>", unsafe_allow_html=True)
        m2.markdown(f"<div class='metric-container'><h3>🟢 Menguat</h3><h2 style='color: #4ade80;'>{saham_naik}</h2></div>", unsafe_allow_html=True)
        m3.markdown(f"<div class='metric-container'><h3>🔴 Melemah</h3><h2 style='color: #f87171;'>{saham_turun}</h2></div>", unsafe_allow_html=True)
        m4.markdown(f"<div class='metric-container'><h3>⚪ Stagnan</h3><h2 style='color: #94a3b8;'>{saham_stagnan}</h2></div>", unsafe_allow_html=True)
        m5.markdown(f"<div class='metric-container'><h3>🧭 Sentimen Pasar</h3><h3 style='color: {warna_sentimen}; margin-top:5px;'>{sentimen_teks}</h3></div>", unsafe_allow_html=True)
        
        st.markdown("---")
        
        c1, c2 = st.columns(2)
        c3, c4 = st.columns(2)

        def render_top_table(df_top, cols, format_dict):
            styler = df_top[cols].style.format(format_dict)
            tabel_warna = styler.map(warna_tabel, subset=['Change (%)']) if hasattr(styler, 'map') else styler.applymap(warna_tabel, subset=['Change (%)'])
            st.dataframe(tabel_warna, use_container_width=True, hide_index=True)

        with c1:
            st.markdown("#### 🔥 Top Gainers")
            if 'Change (%)' in df_hasil.columns:
                df_gainer = df_hasil.nlargest(10, 'Change (%)')
                render_top_table(df_gainer, ['Ticker', 'Harga (Rp)', 'Change (%)'], {'Harga (Rp)': format_angka, 'Change (%)': format_pct})
            
        with c2:
            st.markdown("#### 🩸 Top Losers")
            if 'Change (%)' in df_hasil.columns:
                df_loser = df_hasil.nsmallest(10, 'Change (%)')
                render_top_table(df_loser, ['Ticker', 'Harga (Rp)', 'Change (%)'], {'Harga (Rp)': format_angka, 'Change (%)': format_pct})
            
        st.markdown("<br>", unsafe_allow_html=True)
            
        with c3:
            st.markdown("#### 🌊 Top Volume")
            if 'Volume' in df_hasil.columns:
                df_vol = df_hasil.nlargest(10, 'Volume')
                render_top_table(df_vol, ['Ticker', 'Harga (Rp)', 'Volume', 'Change (%)'], {'Harga (Rp)': format_angka, 'Volume': format_singkat_vol, 'Change (%)': format_pct})
            
        with c4:
            st.markdown("#### 💰 Top Value (Turnover)")
            if 'Turnover' in df_hasil.columns:
                df_val = df_hasil.nlargest(10, 'Turnover')
                render_top_table(df_val, ['Ticker', 'Harga (Rp)', 'Turnover', 'Change (%)'], {'Harga (Rp)': format_angka, 'Turnover': format_singkat_rp, 'Change (%)': format_pct})

    # ==========================================================================
    # [TAB 2] SCREENER UTAMA
    # ==========================================================================
    with tab2:
        with st.expander("🛠️ Buka Panel Filter Lengkap", expanded=False):
            col_f1, col_f2, col_f3, col_f4 = st.columns(4)
            filter_terpilih = {}
            for idx, (db_key, info) in enumerate(MASTER_FILTERS.items()):
                target_col = col_f1 if idx % 4 == 0 else (col_f2 if idx % 4 == 1 else (col_f3 if idx % 4 == 2 else col_f4))
                with target_col:
                    val_sekarang = st.session_state.get(f"main_{db_key}", info["options"][0])
                    idx_opsi = info["options"].index(val_sekarang) if val_sekarang in info["options"] else 0
                    filter_terpilih[db_key] = st.selectbox(info["label"], info["options"], index=idx_opsi, key=f"main_{db_key}", on_change=manual_override)

        col_search, col_broker, col_min, col_max = st.columns([1.5, 1.5, 1, 1])
        with col_search: 
            search_ticker = st.text_input("🔍 Cari Kode Saham", "", placeholder="Contoh: BBCA")
        with col_broker: 
            search_broker = st.text_input("👤 Cari Kode Broker", "", placeholder="Contoh: MG / YP")
        with col_min: 
            min_price = st.number_input("⬇️ Harga Minimal (Rp)", min_value=0, value=0, step=10)
        with col_max: 
            max_price = st.number_input("⬆️ Harga Maksimal (Rp)", min_value=0, value=0, step=10)

        df_filtered = df_hasil.copy()
        
        if search_ticker: 
            df_filtered = df_filtered[df_filtered["Ticker"].astype(str).str.contains(search_ticker.upper(), na=False)]
        if search_broker and "Broksum" in df_filtered.columns: 
            df_filtered = df_filtered[df_filtered["Broksum"].astype(str).str.contains(search_broker.upper(), na=False)]
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
            mode_tampilan = st.radio("👁️ Pilih Mode Tampilan Tabel:", ["🚀 Ringkasan Cepat", "👤 Bandarmologi & Wyckoff", "📈 Teknikal & Support", "💎 Fundamental & Likuiditas", "🌌 Tampilkan Semua Kolom"], horizontal=True)
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

    # ==========================================================================
    # [TAB 3] KAMUS ISTILAH
    # ==========================================================================
    with tab3:
        st.markdown("### 📖 Kamus Edukasi")
        for k, v in KAMUS_EDUKASI.items(): st.write(f"**{k}**: {v}")

    # ==========================================================================
    # [TAB 4] STRATEGI PAKAR
    # ==========================================================================
    with tab4:
        st.markdown("### 💡 Panduan Strategi")
        for k, v in STRATEGI_SIMULASI.items(): st.write(f"**{k}**: {v}")

    # ==========================================================================
    # [TAB 5] ASISTEN AI SPESIAL
    # ==========================================================================
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

        t_screen, t_ai = st.tabs(["📌 Tabel Screener", "⚙️ Turnamen AI & Bot"])
        
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
                                        if "429" in str(e).lower() or "413" in str(e).lower() or "tokens" in str(e).lower():
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
                            prompt_final = f"Select TOP 5 stocks from these finalists.\nDATA:\n{payload_final}\nOUTPUT JSON ARRAY ONLY WITHOUT ANY TEXT: [{{\"Peringkat\": 1, \"Ticker\": \"A\", \"Target_TP\": 100, \"Target_CL\": 90, \"Alasan\": \"Bagus\"}}]"
                            
                            with st.spinner(f"AI meracik Grand Final {nama_rumus}..."):
                                sukses_final, percobaan_final = False, 0
                                while not sukses_final and percobaan_final < 3:
                                    percobaan_final += 1
                                    try:
                                        res_final = client.chat.completions.create(model=MODEL_ANDALAN, messages=[{"role": "user", "content": prompt_final}], temperature=0.2, max_tokens=2500)
                                        jawaban_raw = res_final.choices[0].message.content.strip()
                                        
                                        if "</think>" in jawaban_raw:
                                            jawaban_raw = jawaban_raw.split("</think>")[-1].strip()
                                            
                                        awal = jawaban_raw.find('[')
                                        akhir = jawaban_raw.rfind(']')
                                        
                                        if awal != -1 and akhir != -1:
                                            bersihkan = jawaban_raw[awal:akhir+1]
                                            df_tampil = pd.DataFrame(json.loads(bersihkan))
                                            st.table(df_tampil)
                                            df_tampil[['Ticker', 'Target_TP', 'Target_CL']].to_csv(file_output, index=False)
                                            st.success("🎉 Sinyal sukses dikirim ke Bot Simulator Tab 6!")
                                            sukses_final = True
                                        else:
                                            raise ValueError("Format JSON Array tidak ditemukan.")
                                            
                                    except Exception as e:
                                        if "429" in str(e).lower() or "413" in str(e).lower():
                                            lyr_err = st.empty()
                                            for d in range(60, 0, -1):
                                                lyr_err.error(f"🛑 Tembok Limit Tertabrak! AI tidur {d} detik...")
                                                time.sleep(1)
                                            lyr_err.empty()
                                        else:
                                            st.warning(f"⚠️ Ekstrak JSON gagal. Mengulang (Percobaan {percobaan_final}/3)...")
                                            time.sleep(2)
                                            if percobaan_final == 3:
                                                st.error(f"❌ Gagal Grand Final: {e}")

    # ==========================================================================
    # [TAB 6] PORTOFOLIO BOT
    # ==========================================================================
    with tab6:
        st.markdown("## 📊 Dashboard Bot Simulator")
        pilihan_arena = st.selectbox("Pilih Arena:", [r["judul"] for r in KAMUS_RUMUS.values()])
        nomor_rumus = pilihan_arena.split(" (")[0].split(" ")[1]
        
        FILE_SINYAL = f"Database/sinyal_ai_rumus_{nomor_rumus}.csv"
        FILE_PORTO = f"Database/portofolio_virtual_rumus_{nomor_rumus}.csv"
        
        sub1, sub2 = st.tabs(["📌 Antrean (Watchlist)", "🟢 Portofolio Aktif"])
        with sub1:
            if os.path.exists(FILE_SINYAL): st.dataframe(pd.read_csv(FILE_SINYAL))
            else: st.info("Antrean kosong.")
        with sub2:
            if os.path.exists(FILE_PORTO): st.dataframe(pd.read_csv(FILE_PORTO))
            else: st.info("Portofolio kosong.")