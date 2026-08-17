import pandas as pd
import os
from datetime import datetime

# ==========================================
# ⚙️ KONFIGURASI BOT SIMULATOR
# ==========================================
FILE_PORTOFOLIO = "portofolio_virtual.csv"
FILE_HISTORY = "history_trade.csv"
FILE_SINYAL = "sinyal_ai.csv"        # File ini nanti dibuat oleh app.py (Tab 5)
FILE_MARKET = "hasil_screener.csv"   # Data live 5-menitan Anda

MODAL_AWAL = 100000000.0  # Rp 100 Juta
FEE_BELI = 0.0015         # 0.15%
FEE_JUAL = 0.0025         # 0.25%

# ==========================================
# 🛠️ FUNGSI PEMBANTU (DATABASE MINI)
# ==========================================
def inisialisasi_database():
    """Membuat file database jika belum ada di sistem"""
    if not os.path.exists(FILE_PORTOFOLIO):
        df_porto = pd.DataFrame(columns=[
            'Tanggal_Beli', 'Ticker', 'Harga_Beli', 'Lot', 'Total_Modal', 'Target_TP', 'Target_CL'
        ])
        df_porto.to_csv(FILE_PORTOFOLIO, index=False)
        
    if not os.path.exists(FILE_HISTORY):
        df_hist = pd.DataFrame(columns=[
            'Tanggal_Beli', 'Tanggal_Jual', 'Ticker', 'Harga_Beli', 'Harga_Jual', 
            'Status', 'Total_Return_Rp', 'Return_%'
        ])
        df_hist.to_csv(FILE_HISTORY, index=False)

def cek_saldo_tersedia(df_porto):
    """Menghitung sisa kas/cash yang belum dibelikan saham"""
    if df_porto.empty:
        return MODAL_AWAL
    modal_terpakai = df_porto['Total_Modal'].sum()
    return MODAL_AWAL - modal_terpakai

# ==========================================
# 🤖 MESIN EKSEKUSI UTAMA
# ==========================================
def jalankan_bot():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Membangunkan Bot Simulator AI...")
    inisialisasi_database()
    
    # 1. BACA DATA HARGA MARKET SAAT INI
    if not os.path.exists(FILE_MARKET):
        print("Mata bot buta: Data hasil_screener.csv tidak ditemukan.")
        return
    df_market = pd.read_csv(FILE_MARKET)
    
    df_porto = pd.read_csv(FILE_PORTOFOLIO)
    df_history = pd.read_csv(FILE_HISTORY)
    
    # ==========================================
    # LOGIKA 1: MODE JUAL (PANTAU TAKE PROFIT / CUT LOSS)
    # ==========================================
    porto_baru = []
    
    for idx, posisi in df_porto.iterrows():
        ticker = posisi['Ticker']
        try:
            # Mengintip harga terakhir dari file screener 5-menitan
            harga_sekarang = df_market[df_market['Ticker'] == ticker]['Harga (Rp)'].values[0]
        except:
            porto_baru.append(posisi) # Data tidak ketemu, hold dulu
            continue
            
        harga_beli = posisi['Harga_Beli']
        tp = posisi['Target_TP']
        cl = posisi['Target_CL']
        lot = posisi['Lot']
        
        terjual = False
        status_jual = ""
        harga_jual = 0
        
        # Cek apakah menyentuh TP atau CL
        if harga_sekarang >= tp:
            terjual = True
            status_jual = "TAKE_PROFIT 🎯"
            harga_jual = harga_sekarang
        elif harga_sekarang <= cl:
            terjual = True
            status_jual = "CUT_LOSS ✂️"
            harga_jual = harga_sekarang
            
        if terjual:
            # Perhitungan Keuntungan Nyata (Dipotong Fee)
            nilai_jual_kotor = harga_jual * lot * 100
            potongan_fee = nilai_jual_kotor * FEE_JUAL
            nilai_jual_bersih = nilai_jual_kotor - potongan_fee
            
            profit_rp = nilai_jual_bersih - posisi['Total_Modal']
            profit_pct = (profit_rp / posisi['Total_Modal']) * 100
            
            # Catat ke Buku Sejarah
            catatan_baru = {
                'Tanggal_Beli': posisi['Tanggal_Beli'],
                'Tanggal_Jual': datetime.now().strftime("%Y-%m-%d %H:%M"),
                'Ticker': ticker,
                'Harga_Beli': harga_beli,
                'Harga_Jual': harga_jual,
                'Status': status_jual,
                'Total_Return_Rp': round(profit_rp, 2),
                'Return_%': round(profit_pct, 2)
            }
            df_history = pd.concat([df_history, pd.DataFrame([catatan_baru])], ignore_index=True)
            print(f"💰 EKSEKUSI JUAL: {ticker} di Rp {harga_jual} | Status: {status_jual} | Profit: {profit_pct:.2f}%")
        else:
            porto_baru.append(posisi) # Belum sentuh target, HOLD

    # Update tabel portofolio setelah ada yang terjual
    df_porto = pd.DataFrame(porto_baru)
    if df_porto.empty:
        df_porto = pd.DataFrame(columns=['Tanggal_Beli', 'Ticker', 'Harga_Beli', 'Lot', 'Total_Modal', 'Target_TP', 'Target_CL'])

    # ==========================================
    # LOGIKA 2: MODE BELI (BACA SINYAL DARI APP.PY)
    # ==========================================
    saldo_sekarang = cek_saldo_tersedia(df_porto)
    saham_dimiliki = df_porto['Ticker'].tolist() if not df_porto.empty else []
    
    if os.path.exists(FILE_SINYAL):
        df_sinyal = pd.read_csv(FILE_SINYAL)
        
        for _, sinyal in df_sinyal.iterrows():
            ticker = sinyal['Ticker']
            
            # Jangan beli jika saham tersebut sudah ada di portofolio
            if ticker in saham_dimiliki:
                continue
                
            try:
                harga_beli = df_market[df_market['Ticker'] == ticker]['Harga (Rp)'].values[0]
            except:
                continue
            
            # Alokasi dana: Maksimal Rp 5 Juta per transaksi agar aman
            alokasi_dana = min(5000000, saldo_sekarang)
            
            if alokasi_dana >= (harga_beli * 100 * 1.0015): # Minimal bisa beli 1 lot + fee
                # Menghitung kemampuan beli (berapa lot)
                harga_1_lot_plus_fee = (harga_beli * 100) * (1 + FEE_BELI)
                jumlah_lot = int(alokasi_dana // harga_1_lot_plus_fee)
                total_modal_dikeluarkan = jumlah_lot * harga_1_lot_plus_fee
                
                # Masukkan ke Portofolio
                posisi_baru = {
                    'Tanggal_Beli': datetime.now().strftime("%Y-%m-%d %H:%M"),
                    'Ticker': ticker,
                    'Harga_Beli': harga_beli,
                    'Lot': jumlah_lot,
                    'Total_Modal': total_modal_dikeluarkan,
                    'Target_TP': sinyal['Target_TP'],
                    'Target_CL': sinyal['Target_CL']
                }
                df_porto = pd.concat([df_porto, pd.DataFrame([posisi_baru])], ignore_index=True)
                saldo_sekarang -= total_modal_dikeluarkan
                print(f"🛒 EKSEKUSI BELI: {ticker} di Rp {harga_beli} | {jumlah_lot} Lot | TP: {sinyal['Target_TP']} CL: {sinyal['Target_CL']}")

        # Hapus file sinyal setelah semua dieksekusi agar besok tidak dibeli dua kali
        os.remove(FILE_SINYAL)

    # 3. SIMPAN PERUBAHAN KE DATABASE
    df_porto.to_csv(FILE_PORTOFOLIO, index=False)
    df_history.to_csv(FILE_HISTORY, index=False)
    print("✅ Pengecekan selesai.")

if __name__ == "__main__":
    jalankan_bot()