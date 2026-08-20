import os
import glob
import pandas as pd
import re
import streamlit as st
from groq import Groq

# ==========================================
# 🧠 SISTEM ARSIP CERDAS: GPS & PEMERAS DATA
# ==========================================
def ekstrak_sari_pati_arsip(daftar_ticker_terpilih, df_utama):
    base_folder = "Arsip_Data_Saham"
    hasil_perasan_ai = {}

    for ticker in daftar_ticker_terpilih:
        try:
            harga = df_utama[df_utama['Ticker'] == ticker]['Harga (Rp)'].values[0]
        except:
            harga = 0

        if 1 <= harga <= 200:
            nama_folder = "Kelas_1_Gorengan_50_200"
        elif 201 <= harga <= 1000:
            nama_folder = "Kelas_2_Midcap_201_1000"
        else:
            nama_folder = "Kelas_3_Bluechip_1001_Plus"

        jalur_file = os.path.join(base_folder, nama_folder, f"{ticker}_arsip.csv")

        if os.path.exists(jalur_file):
            try:
                df_arsip = pd.read_csv(jalur_file)
                df_arsip['Waktu'] = pd.to_datetime(df_arsip['Waktu'])
                batas_waktu = pd.to_datetime('17:30').time()
                df_arsip = df_arsip[df_arsip['Waktu'].dt.time <= batas_waktu]

                if not df_arsip.empty:
                    harga_pagi = df_arsip['Harga'].iloc[0]
                    harga_sore = df_arsip['Harga'].iloc[-1]
                    idx_ledakan = df_arsip['Volume'].idxmax()
                    jam_ledakan = df_arsip.loc[idx_ledakan, 'Waktu'].strftime('%H:%M')
                    vol_ledakan = df_arsip.loc[idx_ledakan, 'Volume']
                    status = "Uptrend" if harga_sore > harga_pagi else ("Downtrend" if harga_sore < harga_pagi else "Sideways")

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
            payload_text += f"Historical Trace (Intraday):\n{data['histori']}\n"

        prompt = f"""
        You are the mastermind of an elite Indonesian stock market syndicate. 
        Your task: Select ONLY THE TOP 5 STOCKS that have completed stealth accumulation today and are ready for a Mark-Up tomorrow.
        STOCK DATA TO ANALYZE: {payload_text}
        RULES: 
        1. Indonesian language.
        2. Top 5 selections only.
        3. Table: [Peringkat, Ticker, Skor Ledakan (0-100%), Status Saat Ini].
        4. Brutally analytical explanation below table.
        """
        completion = client.chat.completions.create(
            model=model_andalan, messages=[{"role": "user", "content": prompt}],
            temperature=0.3, max_tokens=3000, top_p=1, stream=False,
        )
        return completion.choices[0].message.content + f"\n\n---\n⚡ *Dianalisa menggunakan mesin: **{model_andalan}** via Groq*"
    except Exception as e: return f"❌ Gagal memproses data dengan Groq. Error: {e}"

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
        except: pass 

        payload_text = ""
        for ticker, data in data_saham_dict.items():
            payload_text += f"\n--- STOCK: {ticker} ---\nBroker Summary: {data['broksum']}\n{data['histori']}\n"

        prompt = f"""
        You are a Stock Market Forensic Expert in Indonesia.
        Find the common "DNA" in these stocks 1 to 3 days BEFORE they skyrocketed to ARA.
        DATA STOCKS: {payload_text}
        MY FILTERS: {master_filters_keys}
        RULES: 
        1. Indonesian language.
        2. Format: "### 🧬 DNA & Pola", "### 🎛️ Resep Filter", "### 💡 Rekomendasi Baru".
        """
        completion = client.chat.completions.create(
            model=model_andalan, messages=[{"role": "user", "content": prompt}],
            temperature=0.2, max_tokens=3000, top_p=1, stream=False,
        )
        return completion.choices[0].message.content + f"\n\n---\n🔬 *Lab Forensik AI: **{model_andalan}** via Groq*"
    except Exception as e: return f"❌ Gagal memproses data dengan Groq. Error: {e}"

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
        You are a Strict Quantitative Filter for an Indonesian Hedge Fund. Evaluate these {len(data_saham_dict)} stocks: {payload_text}
        RULES: ELIMINATE illiquid or heavily distributed stocks. KEEP only stealth accumulation stocks.
        OUTPUT: ONLY a comma-separated list of Tickers. If none, output: SKIP_GRUP.
        """
        completion = client.chat.completions.create(
            model=model_andalan, messages=[{"role": "user", "content": prompt}],
            temperature=0.1, max_tokens=100, top_p=1, stream=False,
        )
        return completion.choices[0].message.content
    except: return "ERROR"

def ai_grand_final_top5(data_saham_dict, api_key):
    try:
        client = Groq(api_key=api_key)
        model_andalan = "llama-3.3-70b-versatile"
        try:
            daftar_model = client.models.list()
            semua_model = [m.id for m in daftar_model.data]
            model_deepseek = [m for m in semua_model if 'deepseek' in m.lower()]
            if model_deepseek:
                ds_70b = [m for m in model_deepseek if '70b' in m.lower()]
                model_andalan = ds_70b[0] if ds_70b else model_deepseek[0]
        except: pass

        payload_text = ""
        for ticker, data in data_saham_dict.items():
            payload_text += f"\n--- {ticker} ---\n Harga: {data['harga']} | Vol: {data['volume']} | Broksum: {data['broksum']} | Tekanan: {data['tekanan_bandar']} | Supply: {data['supply']} | OBV: {data['obv']} | Fibo: {data['fibo']} | VWAP: {data['vwap']} | Candle: {data['pola_candle']}\n"

        prompt = f"""
        You are the CIO of a Top-Tier Indonesian Hedge Fund. Evaluate these Elite Semi-Finalist stocks:
        {payload_text}
        MISSION: Select EXACTLY the TOP 5 BEST STOCKS with the highest probability of Gap Up tomorrow.
        RULES: Indonesian Language. Markdown table [Peringkat, Ticker, Skor, Trigger]. Detailed explanation and Trading Plan below.
        """
        completion = client.chat.completions.create(
            model=model_andalan, messages=[{"role": "user", "content": prompt}],
            temperature=0.3, max_tokens=4000, top_p=1, stream=False,
        )
        raw_content = completion.choices[0].message.content
        clean_content = re.sub(r'<think>.*?</think>', '', raw_content, flags=re.DOTALL).strip()
        return clean_content + f"\n\n---\n🏆 *Grand Final AI: **{model_andalan}** via Groq*"
    except Exception as e: return f"❌ Gagal memproses Grand Final. Error: {e}"