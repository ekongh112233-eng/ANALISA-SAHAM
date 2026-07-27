import yfinance as yf
import pandas as pd
import numpy as np
import os
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from datetime import datetime

# ==========================================
# SECTION 1: KONFIGURASI & SESSION ANTI-BLOKIR
# ==========================================
FILE_SAHAM = "saham.txt"
FILE_HASIL = "hasil_screener.csv"
LOCK_FILE = "sedang_update.lock"

def get_safe_session():
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
    retry = Retry(connect=5, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def load_tickers():
    if not os.path.exists(FILE_SAHAM):
        print(f"❌ Error: File '{FILE_SAHAM}' tidak ditemukan!")
        return []
    with open(FILE_SAHAM, "r") as file:
        return [baris.strip().upper() for baris in file if baris.strip()]

# ==========================================
# SECTION 2: KALKULASI FUNDAMENTAL RINGAN
# ==========================================
def get_fundamental(ticker_jk):
    try:
        ticker_obj = yf.Ticker(ticker_jk)
        info_data = ticker_obj.info
        mcap = info_data.get('marketCap', 0)
        per = info_data.get('trailingPE', 0)
        pbv = info_data.get('priceToBook', 0)
    except:
        mcap, per, pbv = 0, 0, 0

    if mcap > 10000000000000: kategori_saham = "Big Cap (Lapis 1)"
    elif mcap > 1000000000000: kategori_saham = "Mid Cap (Lapis 2)"
    elif mcap > 0: kategori_saham = "Small Cap (Lapis 3)"
    else: kategori_saham = "Tidak Diketahui"
    
    return kategori_saham, per, pbv

# ==========================================
# SECTION 3: KALKULASI TEKNIKAL & BANDARMOLOGI
# ==========================================
def hitung_semua_indikator(df_saham):
    close_today = df_saham['Close'].iloc[-1].item()
    close_yest = df_saham['Close'].iloc[-2].item()
    open_today = df_saham['Open'].iloc[-1].item()
    high_today = df_saham['High'].iloc[-1].item()
    low_today = df_saham['Low'].iloc[-1].item()
    vol_today = int(df_saham['Volume'].iloc[-1].item()) if not pd.isna(df_saham['Volume'].iloc[-1].item()) else 0
    
    change_rp = close_today - close_yest
    change_pct = (change_rp / close_yest) * 100
    momentum = "Positif" if change_rp > 0 else "Negatif"
    
    gap_pct = ((open_today - close_yest) / close_yest) * 100
    if gap_pct >= 2.0: status_gap = f"Gap Up (+{gap_pct:.1f}%)"
    elif gap_pct <= -2.0: status_gap = f"Gap Down ({gap_pct:.1f}%)"
    else: status_gap = "Normal"
    
    range_today = high_today - low_today
    if range_today > 0:
        buying_power = (close_today - low_today) / range_today
        if buying_power > 0.7: tekanan = "Dominan Beli (Hajar Kanan)"
        elif buying_power < 0.3: tekanan = "Dominan Jual (Guyur)"
        else: tekanan = "Seimbang / Adu Mekanik"
    else:
        tekanan = "Tidak Ada Transaksi"

    body_candle = abs(close_today - open_today)
    upper_shadow = high_today - max(open_today, close_today)
    lower_shadow = min(open_today, close_today) - low_today
    
    if body_candle <= (range_today * 0.1): pola_candle = "Doji (Ragu-ragu)"
    elif lower_shadow > (body_candle * 2) and upper_shadow < (body_candle * 0.2): pola_candle = "Hammer (Potensi Reversal)"
    elif body_candle > (range_today * 0.8) and close_today > open_today: pola_candle = "Marubozu (Strong Bullish)"
    else: pola_candle = "Normal"

    ma_20 = df_saham['Close'].rolling(window=20).mean().iloc[-1].item()
    ma_50 = df_saham['Close'].rolling(window=50).mean().iloc[-1].item() if len(df_saham) >= 50 else ma_20
    vol_ma_20 = df_saham['Volume'].rolling(window=20).mean().iloc[-1].item()
    ma_signal = "Uptrend" if close_today > ma_20 else "Downtrend"
    vol_breakout = "Tembus MA20" if vol_today > vol_ma_20 else "Normal"
    
    ma_5 = df_saham['Close'].rolling(window=5).mean().iloc[-1].item()
    ma_5_prev = df_saham['Close'].rolling(window=5).mean().iloc[-2].item()
    ma_20_prev = df_saham['Close'].rolling(window=20).mean().iloc[-2].item()
    
    if ma_5 > ma_20 and ma_5_prev <= ma_20_prev: ma_cross = "Golden Cross"
    elif ma_5 < ma_20 and ma_5_prev >= ma_20_prev: ma_cross = "Death Cross"
    elif ma_5 > ma_20: ma_cross = "Bullish"
    else: ma_cross = "Bearish"

    ema_12 = df_saham['Close'].ewm(span=12, adjust=False).mean()
    ema_26 = df_saham['Close'].ewm(span=26, adjust=False).mean()
    macd_line = ema_12 - ema_26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    macd_val = macd_line.iloc[-1].item()
    sig_val = signal_line.iloc[-1].item()
    
    if macd_val > sig_val and macd_val > 0: status_macd = "Strong Bullish"
    elif macd_val > sig_val: status_macd = "Bullish MACD"
    elif macd_val < sig_val and macd_val < 0: status_macd = "Strong Bearish"
    else: status_macd = "Bearish MACD"
    
    if vol_today > (vol_ma_20 * 2):
        if close_today > open_today: status_bandar = "Akumulasi Kuat"
        elif close_today < open_today: status_bandar = "Distribusi Kuat"
        else: status_bandar = "Normal"
    else:
        status_bandar = "Normal"

    obv = [0]
    for i in range(1, len(df_saham)):
        if df_saham['Close'].iloc[i] > df_saham['Close'].iloc[i-1]: obv.append(obv[-1] + df_saham['Volume'].iloc[i])
        elif df_saham['Close'].iloc[i] < df_saham['Close'].iloc[i-1]: obv.append(obv[-1] - df_saham['Volume'].iloc[i])
        else: obv.append(obv[-1])
    df_saham['OBV'] = obv
    
    obv_sekarang = df_saham['OBV'].iloc[-1]
    obv_5_hari_lalu = df_saham['OBV'].iloc[-6] if len(df_saham['OBV']) >= 6 else obv_sekarang
    if obv_sekarang > obv_5_hari_lalu: obv_trend = "Akumulasi (Naik)"
    elif obv_sekarang < obv_5_hari_lalu: obv_trend = "Distribusi (Turun)"
    else: obv_trend = "Netral"
    
    std_20 = df_saham['Close'].rolling(window=20).std().iloc[-1].item()
    upper_bb = ma_20 + (std_20 * 2)
    lower_bb = ma_20 - (std_20 * 2)
    bandwidth = ((upper_bb - lower_bb) / ma_20) * 100 if ma_20 != 0 else 0
        
    if bandwidth < 8.0: status_bb = "Squeeze"
    elif close_today > upper_bb: status_bb = "Breakout Upper"
    elif close_today > lower_bb and (abs(close_today - lower_bb) / lower_bb) < 0.02: status_bb = "Bottom Rebound"
    else: status_bb = "Normal"

    support_20 = df_saham['Low'].rolling(window=20).min().iloc[-1].item()
    resist_20 = df_saham['High'].rolling(window=20).max().iloc[-1].item()

    jarak_support = ((close_today - support_20) / support_20) * 100 if support_20 > 0 else 0
    if jarak_support <= 3.0: posisi_entry = "Dekat Support (Low Risk)"
    elif jarak_support >= 10.0: posisi_entry = "Rawan Pucuk (High Risk)"
    else: posisi_entry = "Area Tengah"

    if bandwidth > 15.0: risiko = "Tinggi"
    elif bandwidth > 8.0: risiko = "Sedang"
    else: risiko = "Rendah"
    
    delta = df_saham['Close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
    rs = avg_gain / avg_loss
    rsi_raw = (100 - (100 / (1 + rs))).iloc[-1].item()
    rsi = int(round(rsi_raw)) if not pd.isna(rsi_raw) else 0

    typical_price = (df_saham['High'] + df_saham['Low'] + df_saham['Close']) / 3
    vwap_5 = (typical_price * df_saham['Volume']).rolling(window=5).sum() / (df_saham['Volume'].rolling(window=5).sum() + 1)
    vwap_val = vwap_5.iloc[-1].item()
    if close_today > (vwap_val * 1.01): posisi_vwap = "Di Atas VWAP (Kuat)"
    elif close_today < (vwap_val * 0.99): posisi_vwap = "Di Bawah VWAP (Lemah)"
    else: posisi_vwap = "Persis di VWAP"

    penyebut_ad = df_saham['High'] - df_saham['Low']
    penyebut_ad = penyebut_ad.replace(0, 0.0001) 
    mfm = ((df_saham['Close'] - df_saham['Low']) - (df_saham['High'] - df_saham['Close'])) / penyebut_ad
    mfv = mfm * df_saham['Volume']
    ad_line = mfv.cumsum()
    ad_sekarang = ad_line.iloc[-1].item()
    ad_5_hari_lalu = ad_line.iloc[-6].item() if len(ad_line) >= 6 else ad_sekarang
    
    if ad_sekarang > ad_5_hari_lalu: smart_money = "Akumulasi Pro (Smart Money)"
    elif ad_sekarang < ad_5_hari_lalu: smart_money = "Distribusi Pro (Guyuran)"
    else: smart_money = "Netral"

    vol_5_avg = df_saham['Volume'].rolling(window=5).mean().iloc[-1].item()
    val_transaksi = vol_5_avg * close_today
    if val_transaksi > 50_000_000_000: kelas_transaksi = "Sultan (> 50M/hari)"
    elif val_transaksi > 5_000_000_000: kelas_transaksi = "Ritel Aktif (5M - 50M)"
    else: kelas_transaksi = "Gorengan Sepi (< 5M)"

    vol_avg_10 = df_saham['Volume'].rolling(window=10).mean().iloc[-1].item()
    if vol_avg_10 > 0:
        rvol_pct = (vol_today / vol_avg_10) * 100
        if rvol_pct > 300: rvol_status = "Ledakan Ekstrem (> 300%)"
        elif rvol_pct > 150: rvol_status = "Anomali Tinggi (150-300%)"
        elif rvol_pct < 50: rvol_status = "Sepi (< 50%)"
        else: rvol_status = "Normal (50-150%)"
    else:
        rvol_status = "Normal (50-150%)"
        
    if close_today > ma_20 and ma_20 > ma_50: siklus = "Mark-Up (Fase Pesta)"
    elif close_today < ma_20 and ma_20 < ma_50: siklus = "Mark-Down (Fase Runtuh)"
    elif close_today > ma_20 and ma_20 <= ma_50: siklus = "Accumulation (Kumpul Barang)"
    elif close_today < ma_20 and ma_20 >= ma_50: siklus = "Distribution (Fase Jualan)"
    else: siklus = "Sideways"

    df_20 = df_saham.tail(20)
    range_harian = df_20['High'] - df_20['Low'] + 0.0001
    ekor_atas = df_20['High'] - df_20[['Open', 'Close']].max(axis=1)
    rasio_ekor = ekor_atas / range_harian
    tiang_jemuran = (rasio_ekor > 0.5).sum()
    
    if tiang_jemuran >= 4: karakter_bandar = "Spesialis Tiang Jemuran (Banting Pucuk)"
    elif tiang_jemuran == 0: karakter_bandar = "Solid (Jarang Dibanting)"
    else: karakter_bandar = "Normal"

    df_saham['H-L'] = df_saham['High'] - df_saham['Low']
    df_saham['H-PC'] = abs(df_saham['High'] - df_saham['Close'].shift(1))
    df_saham['L-PC'] = abs(df_saham['Low'] - df_saham['Close'].shift(1))
    df_saham['TR'] = df_saham[['H-L', 'H-PC', 'L-PC']].max(axis=1)
    atr_14 = df_saham['TR'].rolling(window=14).mean().iloc[-1].item()
    if pd.isna(atr_14) or atr_14 == 0: atr_14 = range_today if range_today > 0 else 1

    target_tp = int(close_today + (atr_14 * 1.5))
    target_cl = int(close_today - atr_14)
    auto_plan = f"TP: {target_tp} | CL: {target_cl}"

    if lower_shadow > (body_candle * 2) and lower_shadow > (range_today * 0.5): 
        deteksi_shakeout = "Jarum Bawah (Sinyal Pantulan Kuat)"
    else: 
        deteksi_shakeout = "Normal"

    streak_count = 0
    arah_streak = 0
    for i in range(1, min(10, len(df_saham))):
        c_curr = df_saham['Close'].iloc[-i].item()
        c_prev = df_saham['Close'].iloc[-(i+1)].item()
        if i == 1:
            if c_curr > c_prev: arah_streak = 1
            elif c_curr < c_prev: arah_streak = -1
            else: break
            streak_count = 1
        else:
            if arah_streak == 1 and c_curr > c_prev: streak_count += 1
            elif arah_streak == -1 and c_curr < c_prev: streak_count += 1
            else: break
            
    if arah_streak == 1 and streak_count >= 1: info_streak = f"Naik {streak_count} Hari Beruntun"
    elif arah_streak == -1 and streak_count >= 1: info_streak = f"Turun {streak_count} Hari Beruntun"
    else: info_streak = "Sideways / Stagnan"

    # ====================================================
    # TAMBAHAN 4: OPEN=LOW & RISK REWARD RATIO (BARU)
    # ====================================================
    if open_today == low_today and close_today > open_today: status_open = "Open = Low (Bullish Kuat)"
    elif open_today == high_today and close_today < open_today: status_open = "Open = High (Tekanan Jual)"
    else: status_open = "Normal"

    potensi_upside = ((resist_20 - close_today) / close_today) * 100 if close_today > 0 else 0
    risiko_downside = ((close_today - support_20) / close_today) * 100 if close_today > 0 else 0
    if risiko_downside > 0:
        rrr_val = potensi_upside / risiko_downside
        if rrr_val >= 3: status_rrr = "Sangat Menarik (> 1:3)"
        elif rrr_val >= 1.5: status_rrr = "Ideal (1:2)"
        elif rrr_val < 1: status_rrr = "Tidak Ideal (< 1:1)"
        else: status_rrr = "Menengah (1:1)"
    else:
        status_rrr = "Di Area Support"

    return {
        "Harga (Rp)": close_today, "Harga MA20": int(ma_20), "Support": int(support_20), "Resistance": int(resist_20),
        "Change (%)": change_pct, "Volume": vol_today, "Vol Breakout": vol_breakout, "RSI (14D)": rsi,
        "Momentum": momentum, "MA Signal": ma_signal, "MA Cross": ma_cross, "MACD": status_macd,
        "Status Bandar": status_bandar, "OBV Trend": obv_trend, "Status Gap": status_gap, "Tekanan Bandar": tekanan, 
        "Status BB": status_bb, "Risiko": risiko,
        "Pola Candle": pola_candle, "Posisi Entry": posisi_entry,
        "Likuiditas": "> 1 Miliar" if (close_today * vol_today) > 1000000000 else "< 1 Miliar",
        "Posisi VWAP": posisi_vwap, "Kekuatan A/D": smart_money, "Kelas Transaksi": kelas_transaksi,
        "RVOL (Anomali Vol)": rvol_status, "Fase Siklus Bandar": siklus, "Karakter Gorengan": karakter_bandar,
        "Sinyal Cuci Barang": deteksi_shakeout, "Streak Harian": info_streak, "Auto Trading Plan": auto_plan,
        "Status Open": status_open, "Risk/Reward Ratio": status_rrr # DATA BARU
    }

# ==========================================
# SECTION 4: EKSEKUSI UTAMA (MODE DETEKTIF)
# ==========================================
def main():
    if os.path.exists(LOCK_FILE): os.remove(LOCK_FILE)
    with open(LOCK_FILE, "w") as f: f.write("SEDANG PROSES")

    try:
        print("⏳ Memulai pembaruan data saham (Ultimate Diagnostic Mode)...")
        daftar_saham = load_tickers()
        if not daftar_saham: return
        
        tickers_jk = [f"{t}.JK" for t in daftar_saham]
        tickers_str = " ".join(tickers_jk)
        aman_session = get_safe_session()
        
        print(f"📥 Mengunduh {len(daftar_saham)} data saham secara bersamaan (Maks 8 jalur)...")
        data_mentah = yf.download(
            tickers_str, period="3mo", interval="1d", group_by='ticker', threads=8, session=aman_session, progress=False
        )
        
        if data_mentah.empty:
            print("❌ ERROR FATAL: Yahoo Finance menolak permintaan data.")
            return

        hasil = []
        error_count = 0

        for ticker in daftar_saham:
            try:
                t_jk = f"{ticker}.JK"
                if t_jk in data_mentah:
                    df_saham = data_mentah[t_jk].dropna(subset=['Open', 'Close', 'Volume', 'High', 'Low'])
                    if len(df_saham) >= 50:
                        ind = hitung_semua_indikator(df_saham)
                        kat, per, pbv = get_fundamental(t_jk)
                        
                        score = 0
                        if ind["Vol Breakout"] == "Tembus MA20": score += 1
                        if ind["RSI (14D)"] > 50: score += 1
                        if ind["Momentum"] == "Positif": score += 1
                        if ind["MA Signal"] == "Uptrend": score += 1
                        if ind["MA Cross"] in ["Golden Cross", "Bullish"]: score += 1
                        if ind["MACD"] in ["Strong Bullish", "Bullish MACD"]: score += 1
                        if ind["Status Bandar"] == "Akumulasi Kuat": score += 1  
                        if ind["OBV Trend"] == "Akumulasi (Naik)": score += 1   
                        if ind["Tekanan Bandar"] == "Dominan Beli (Hajar Kanan)": score += 1
                        if "Gap Up" in ind["Status Gap"]: score += 1

                        rekomendasi = "BELI" if score >= 7 else "WAIT & SEE"
                        
                        if per > 0 and per < 15 and pbv > 0 and pbv < 1.5: valuasi = "Undervalued (Murah)"
                        elif per > 25 or pbv > 3.0: valuasi = "Overvalued (Mahal)"
                        else: valuasi = "Fair Value (Wajar)"
                        
                        data_akhir = {"Ticker": ticker, "Kategori": kat, "Valuasi": valuasi, "PER (x)": per, "PBV (x)": pbv}
                        data_akhir.update(ind)
                        data_akhir.update({
                            "Total Score": score, "Rekomendasi": rekomendasi, 
                            "Status Akuisisi": "TIDAK ADA", "Terakhir Update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                        hasil.append(data_akhir)
            except Exception as e:
                error_count += 1
                print(f"⚠️ Error pada perhitungan saham {ticker}: {e}")

        if hasil:
            df_hasil = pd.DataFrame(hasil)
            df_hasil.to_csv(FILE_HASIL, index=False)
            print(f"✅ Selesai! Data {len(hasil)} saham berhasil diperbarui.")
        else:
            print("\n⚠️ GAGAL TOTAL: Proses selesai namun list hasil kosong.")
    finally:
        if os.path.exists(LOCK_FILE): os.remove(LOCK_FILE)

if __name__ == "__main__":
    main()