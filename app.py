import streamlit as st
import pandas as pd
import numpy as np
import os
import json
from datetime import datetime
import plotly.express as px

# ==========================================
# SECTION 1: PENGATURAN UI/UX & FILE EKSTERNAL
# ==========================================
st.set_page_config(page_title="Screener Saham IHSG", layout="wide", initial_sidebar_state="expanded")

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
    
    /* CSS BARU: Mengatasi text terpotong di dropdown tanpa merubah ukuran font */
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
        "MACD": {"label": "📈 MACD", "options": ["Semua", "Strong Bullish", "Bullish MACD", "Strong Bearish", "Bearish MACD"]}
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
    if "Status Open" not in cek_config.get("MASTER_FILTERS", {}):
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

# ==========================================
# FITUR BARU: MANAJEMEN PRESET (EDIT/HAPUS)
# ==========================================
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
                # Hapus nama lama jika user me-rename presetnya
                if pilih_edit != "-- Buat Baru --" and pilih_edit != nama_preset_baru.strip():
                    del kustom_presets[pilih_edit]
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
                if st.session_state.preset_selector == pilih_hapus:
                    st.session_state.preset_selector = "Matikan Preset (Manual)"
                st.success("Preset dihapus!")
                st.rerun()
        else:
            st.info("Belum ada preset kustom.")

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
        if any(x in val for x in ["Positif", "Uptrend", "BELI", "Breakout Upper", "Bottom Rebound", "DALAM AKUISISI", "Rendah", "▲", "Golden Cross", "Bullish", "Tembus MA20", "Akumulasi", "Big Cap", "Gap Up", "Dominan Beli", "Undervalued", "Marubozu", "Dekat Support", "Hammer", "Di Atas VWAP", "Sultan", "Ledakan Ekstrem", "Solid", "Mark-Up", "Jarum Bawah", "Naik", "Open = Low", "Sangat Menarik"]): 
            return 'color: #22c55e; font-weight: 600;'
        elif any(x in val for x in ["Negatif", "Downtrend", "WAIT & SEE", "Tinggi", "▼", "Death Cross", "Bearish", "Distribusi", "Small Cap", "Gap Down", "Dominan Jual", "Overvalued", "Rawan Pucuk", "Di Bawah VWAP", "Gorengan Sepi", "Sepi", "Tiang Jemuran", "Mark-Down", "Turun", "Open = High", "Tidak Ideal"]): 
            return 'color: #ef4444; font-weight: 600;'
        elif val == "> 1 Miliar": 
            return 'color: #3b82f6; font-weight: 600;'
        elif any(x in val for x in ["Squeeze", "RENCANA AKUISISI", "Sedang", "Mid Cap", "Seimbang", "Fair Value", "Area Tengah", "Doji", "Ritel Aktif", "Anomali", "Accumulation", "Sideways", "Ideal", "Menengah"]): 
            return 'color: #eab308; font-weight: 600;'
        elif "⭐" in val: 
            return 'color: #22c55e;' if len(val) >= 6 else 'color: #ef4444;'
    return ''

# ==========================================
# SECTION 6: RENDER TABS
# ==========================================
if not df_hasil.empty:
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Ringkasan Pasar", "🎯 Screener Utama", "💡 Insight & Edukasi", "📈 Simulasi & Strategi", "🦅 Radar Bandar (Fast Trade)"])
    
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
                fig_pie = px.pie(df_rek, names='Rekomendasi', values='Jumlah', hole=0.5, color='Rekomendasi', color_discrete_map={'BELI': '#22c55e', 'WAIT & SEE': '#ef4444'})
                st.plotly_chart(fig_pie, use_container_width=True)
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

        col_search, _ = st.columns([1, 2])
        with col_search: search_ticker = st.text_input("🔍 Cari Kode Saham", "", placeholder="Contoh: BBCA")

        df_filtered = df_hasil.copy()
        if search_ticker: df_filtered = df_filtered[df_filtered["Ticker"].str.contains(search_ticker.upper(), na=False)]
        
        for db_key, nilai in filter_terpilih.items():
            if nilai != "Semua":
                if db_key == "RSI (14D)":
                    if "RSI (14D)" in df_filtered.columns: df_filtered = df_filtered[df_filtered["RSI (14D)"] > 50] if "Bullish" in nilai else df_filtered[df_filtered["RSI (14D)"] <= 50]
                elif db_key == "Total Score":
                    if "Total Score" in df_filtered.columns: df_filtered = df_filtered[df_filtered["Total Score"] == int(nilai)]
                elif db_key in df_filtered.columns:
                    df_filtered = df_filtered[df_filtered[db_key] == nilai]

        if not df_filtered.empty:
            st.caption(f"Menampilkan **{len(df_filtered)}** saham yang lolos filter dari total **{len(df_hasil)}** saham.")
            
            st.markdown("<div class='view-mode-container'>", unsafe_allow_html=True)
            mode_tampilan = st.radio(
                "👁️ Pilih Mode Tampilan Tabel (Agar tidak perlu geser layar):",
                ["🚀 Ringkasan Cepat (Default)", "🕵️ Bandarmologi & Wyckoff", "📈 Teknikal & Support", "💎 Fundamental & Likuiditas", "🌌 Tampilkan Semua Kolom"],
                horizontal=True
            )
            st.markdown("</div>", unsafe_allow_html=True)
            
            cp1, cp2, cp3 = st.columns([1, 1, 2])
            with cp1: per_hal = st.selectbox("Tampilkan baris:", [20, 50, 100])
            tot_hal = int(np.ceil(len(df_filtered) / per_hal))
            with cp2: hal_aktif = st.selectbox("Halaman:", range(1, tot_hal + 1)) if tot_hal > 0 else 1
                    
            idx_awal = (hal_aktif - 1) * per_hal
            df_tampil = df_filtered.iloc[idx_awal : idx_awal + per_hal].copy()
            if "Total Score" in df_tampil.columns: df_tampil["Total Score"] = df_tampil["Total Score"].apply(format_skor)
            
            kolom_ringkasan = ["Ticker", "Harga (Rp)", "Change (%)", "Rekomendasi", "Status Open", "Posisi VWAP", "Total Score", "Volume", "Auto Trading Plan"]
            kolom_bandar = ["Ticker", "Harga (Rp)", "Change (%)", "Fase Siklus Bandar", "Kekuatan A/D", "Status Bandar", "RVOL (Anomali Vol)", "Karakter Gorengan", "Tekanan Bandar", "OBV Trend"]
            kolom_teknikal = ["Ticker", "Harga (Rp)", "Change (%)", "Auto Trading Plan", "Risk/Reward Ratio", "Sinyal Cuci Barang", "Posisi Entry", "Pola Candle", "MA Signal", "Status BB", "RSI (14D)", "MACD"]
            kolom_fundamental = ["Ticker", "Harga (Rp)", "Kategori", "Valuasi", "PER (x)", "PBV (x)", "Kelas Transaksi", "Likuiditas"]
            kolom_semua = [
                "Ticker", "Status Open", "Risk/Reward Ratio", "Auto Trading Plan", "Streak Harian", "Sinyal Cuci Barang", 
                "Kategori", "Kelas Transaksi", "Valuasi", "Harga (Rp)", "PER (x)", "PBV (x)", "Harga MA20", "Posisi VWAP", 
                "Support", "Resistance", "Posisi Entry", "Pola Candle", "Change (%)", "Volume", "RVOL (Anomali Vol)", 
                "Vol Breakout", "Status Gap", "Fase Siklus Bandar", "Karakter Gorengan", "Tekanan Bandar", "Kekuatan A/D", 
                "Status Bandar", "OBV Trend", "RSI (14D)", "Momentum", "MA Signal", "MA Cross", "MACD", "Status BB", 
                "Risiko", "Likuiditas", "Total Score", "Rekomendasi"
            ] # Terakhir Update sudah dibuang dari list agar tidak merusak tabel
            
            if "Ringkasan" in mode_tampilan: kolom_pilih = kolom_ringkasan
            elif "Bandarmologi" in mode_tampilan: kolom_pilih = kolom_bandar
            elif "Teknikal" in mode_tampilan: kolom_pilih = kolom_teknikal
            elif "Fundamental" in mode_tampilan: kolom_pilih = kolom_fundamental
            else: kolom_pilih = kolom_semua

            kolom_ada = [c for c in kolom_pilih if c in df_tampil.columns]

            format_dict = {}
            if "Harga (Rp)" in df_tampil.columns: format_dict["Harga (Rp)"] = format_angka
            if "Harga MA20" in df_tampil.columns: format_dict["Harga MA20"] = format_angka
            if "Support" in df_tampil.columns: format_dict["Support"] = format_angka
            if "Resistance" in df_tampil.columns: format_dict["Resistance"] = format_angka
            if "Volume" in df_tampil.columns: format_dict["Volume"] = format_angka
            if "Change (%)" in df_tampil.columns: format_dict["Change (%)"] = format_pct
            if "Momentum" in df_tampil.columns: format_dict["Momentum"] = format_mom
            if "PER (x)" in df_tampil.columns: format_dict["PER (x)"] = format_desimal
            if "PBV (x)" in df_tampil.columns: format_dict["PBV (x)"] = format_desimal
            if "RSI (14D)" in df_tampil.columns: format_dict["RSI (14D)"] = "{:.0f}"

            styler_obj = df_tampil[kolom_ada].style.format(format_dict)
            subset_warna = [c for c in kolom_ada if c not in ["Ticker", "Auto Trading Plan"]]
            tabel_akhir = styler_obj.map(warna_tabel, subset=subset_warna) if hasattr(styler_obj, 'map') else styler_obj.applymap(warna_tabel, subset=subset_warna)
            
            st.dataframe(tabel_akhir, use_container_width=True, hide_index=True)
            
            st.markdown("---")
            col_dl, col_wl = st.columns([1, 1])
            with col_dl:
                csv_filter = df_filtered[kolom_ada].to_csv(index=False).encode('utf-8')
                st.download_button(
                    label=f"📥 Download Data Tabel CSV",
                    data=csv_filter,
                    file_name=f"Screener_View_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv",
                    key="dl_tab2"
                )
            with col_wl:
                daftar_ticker = ", ".join(df_filtered["Ticker"].tolist())
                st.code(daftar_ticker, language="text")
                st.caption("📋 Klik icon 'Copy' untuk paste massal ke TradingView/Broker.")
        else: 
            st.warning("Tidak ada data sesuai filter.")

    with tab3:
        st.markdown("### 📚 Kamus Istilah Kolom")
        if not KAMUS_EDUKASI:
            st.warning(f"⚠️ File '{FILE_KAMUS}' tidak ditemukan. Silakan buat file json tersebut di folder yang sama agar penjelasan muncul.")
        else:
            st.info("Berikut adalah penjelasan untuk membaca semua metrik di Tab Screener:")
            for kolom_nama, penjelasan in KAMUS_EDUKASI.items():
                st.markdown(f"🔹 **{kolom_nama}**: {penjelasan}")

    with tab4:
        st.markdown("### 📈 Strategi & Simulasi Trading Profesional (Termasuk BSJP)")
        st.success("Terapkan kombinasi filter Screener Anda menggunakan pendekatan para ahli di bawah ini.")
        for judul, deskripsi in STRATEGI_SIMULASI.items():
            with st.expander(f"💼 {judul}", expanded=False): st.write(deskripsi)
                
        st.markdown("---")
        st.markdown("#### 🛠️ Analisis Status Pasar Saat Ini")
        if 'Status Bandar' in df_hasil.columns:
            dominasi_bandar = len(df_hasil[df_hasil['Status Bandar'] == 'Akumulasi Kuat'])
            if dominasi_bandar > (len(df_hasil) * 0.1): st.info("🔥 **SIMULASI:** Saat ini banyak saham (>10% pasar) sedang diakumulasi bandar. Fokus pada strategi **BSJP** dan **HAKA Pagi**.")
            else: st.warning("⚖️ **SIMULASI:** Pasar sedang sepi dari pergerakan bandar masif. Disarankan menggunakan strategi **Buy on Weakness** atau Reversal.")

    with tab5:
        st.markdown("## 🦅 Radar Copet Bandar (Fast Trade Lapis 3)")
        st.markdown("<div class='bandar-box'><b>⚠️ PERINGATAN RISIKO TINGGI:</b> Tab ini murni mendeteksi volatilitas ekstrem pada saham Lapis 3. Patuhi Auto Trading Plan (TP/CL)!</div>", unsafe_allow_html=True)
        
        if 'Tekanan Bandar' not in df_hasil.columns:
            st.warning("⏳ **Fitur Radar Bandar belum menerima data terbaru.** Harap klik tombol 'Muat Ulang Data Server'.")
        else:
            df_lapis3 = df_hasil[df_hasil['Kategori'].str.contains("Small Cap", na=False)]
            
            df_markup = df_lapis3[(df_lapis3['Status Bandar'] == 'Akumulasi Kuat') & (df_lapis3['Tekanan Bandar'] == 'Dominan Beli (Hajar Kanan)')].copy()
            
            kondisi_senyap = (
                (
                    ((df_lapis3['Kekuatan A/D'] == 'Akumulasi Pro (Smart Money)') & (df_lapis3['Status BB'] == 'Squeeze')) | 
                    (df_lapis3['Sinyal Cuci Barang'] == 'Jarum Bawah (Sinyal Pantulan Kuat)')
                ) & 
                (~df_lapis3['Karakter Gorengan'].str.contains("Tiang Jemuran", na=False)) &
                (df_lapis3['OBV Trend'] == 'Akumulasi (Naik)') & 
                (df_lapis3['Kelas Transaksi'] != 'Gorengan Sepi (< 5M)') &
                (df_lapis3['Risk/Reward Ratio'].isin(["Sangat Menarik (> 1:3)", "Ideal (1:2)", "Di Area Support"]))
            )
            
            df_senyap = df_lapis3[kondisi_senyap].copy()
            df_guyur = df_lapis3[(df_lapis3['Status Bandar'] == 'Distribusi Kuat') | (df_lapis3['Tekanan Bandar'] == 'Dominan Jual (Guyur)')].copy()

            st.markdown("---")
            st.markdown("### 🔥 Fase Mark-Up (Sedang Digoreng Naik)")
            st.caption("Cocok untuk dipantau pagi hari. Algoritma: Saham Lapis 3 + Volume Akumulasi Kuat + Hajar Kanan.")
            if not df_markup.empty:
                if "Total Score" in df_markup.columns: df_markup["Total Score"] = df_markup["Total Score"].apply(format_skor)
                kolom_b = ["Ticker", "Harga (Rp)", "Change (%)", "Status Open", "Volume", "RVOL (Anomali Vol)", "Tekanan Bandar", "Status Bandar", "Auto Trading Plan"]
                kolom_b = [c for c in kolom_b if c in df_markup.columns]
                styler_markup = df_markup.style.format({"Harga (Rp)": format_angka, "Volume": format_angka, "Change (%)": format_pct})
                subset_m = [c for c in kolom_b if c not in ["Ticker", "Auto Trading Plan"]]
                tabel_markup = styler_markup.map(warna_tabel, subset=subset_m) if hasattr(styler_markup, 'map') else styler_markup.applymap(warna_tabel, subset=subset_m)
                st.dataframe(tabel_markup, use_container_width=True, hide_index=True, column_order=kolom_b)
                
                c1, c2 = st.columns([1, 1])
                c1.download_button("📥 Download Mark-Up (CSV)", df_markup[kolom_b].to_csv(index=False).encode('utf-8'), "Fase_MarkUp.csv", "text/csv", key="dl_markup")
                c2.code(", ".join(df_markup["Ticker"].tolist()), language="text")
            else: st.info("Belum ada saham gorengan yang ditarik kuat oleh Bandar hari ini.")

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("### 🤫 Fase Akumulasi Senyap / Shakeout (Curi Start) - VIP Filter")
            st.caption("Telah Difilter Ketat! Saham wajib ada uang masuk (OBV Naik), Risk/Reward bagus, liquid, dan Smart Money terdeteksi akumulasi diam-diam.")
            if not df_senyap.empty:
                sort_cols = [c for c in ['Total Score', 'Volume'] if c in df_senyap.columns]
                if sort_cols: df_senyap = df_senyap.sort_values(by=sort_cols, ascending=[False, False]).reset_index(drop=True)
                df_senyap.insert(0, 'Prioritas', ['🏆 #1'] + [f'#{i+1}' for i in range(1, len(df_senyap))])
                if "Total Score" in df_senyap.columns: df_senyap["Total Score"] = df_senyap["Total Score"].apply(format_skor)
                
                kolom_senyap = ["Prioritas", "Ticker", "Harga (Rp)", "Change (%)", "Kekuatan A/D", "Sinyal Cuci Barang", "Status BB", "Volume", "Auto Trading Plan"]
                kolom_senyap = [c for c in kolom_senyap if c in df_senyap.columns]
                styler_senyap = df_senyap.style.format({"Harga (Rp)": format_angka, "Volume": format_angka, "Change (%)": format_pct})
                subset_s = [c for c in kolom_senyap if c not in ["Ticker", "Prioritas", "Auto Trading Plan"]]
                tabel_senyap = styler_senyap.map(warna_tabel, subset=subset_s) if hasattr(styler_senyap, 'map') else styler_senyap.applymap(warna_tabel, subset=subset_s)
                st.dataframe(tabel_senyap, use_container_width=True, hide_index=True, column_order=kolom_senyap)
                
                c1, c2 = st.columns([1, 1])
                c1.download_button("📥 Download Curi Start (CSV)", df_senyap[kolom_senyap].to_csv(index=False).encode('utf-8'), "Fase_CuriStart.csv", "text/csv", key="dl_senyap")
                c2.code(", ".join(df_senyap["Ticker"].tolist()), language="text")
            else: st.info("Sistem tidak mendeteksi ada saham dengan kriteria Curi Start yang aman saat ini.")

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("### ☠️ Fase Guyuran / Distribusi (HINDARI!)")
            if not df_guyur.empty:
                if "Total Score" in df_guyur.columns: df_guyur["Total Score"] = df_guyur["Total Score"].apply(format_skor)
                kolom_b = ["Ticker", "Harga (Rp)", "Change (%)", "Tekanan Bandar", "Status Bandar", "Karakter Gorengan", "Total Score"]
                kolom_b = [c for c in kolom_b if c in df_guyur.columns]
                styler_guyur = df_guyur.style.format({"Harga (Rp)": format_angka, "Change (%)": format_pct})
                subset_g = [c for c in kolom_b if c not in ["Ticker"]]
                tabel_guyur = styler_guyur.map(warna_tabel, subset=subset_g) if hasattr(styler_guyur, 'map') else styler_guyur.applymap(warna_tabel, subset=subset_g)
                st.dataframe(tabel_guyur, use_container_width=True, hide_index=True, column_order=kolom_b)
                
                c1, c2 = st.columns([1, 1])
                c1.download_button("📥 Download Guyuran (CSV)", df_guyur[kolom_b].to_csv(index=False).encode('utf-8'), "Fase_Guyuran.csv", "text/csv", key="dl_guyur")
                c2.code(", ".join(df_guyur["Ticker"].tolist()), language="text")
            else: st.success("Pasar Lapis 3 terpantau bersih dari aksi guyuran berat Bandar hari ini.")
else:
    st.error("Silakan jalankan `update_data.py` terlebih dahulu di terminal untuk memuat data!")