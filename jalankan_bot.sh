#!/bin/bash

# Masuk ke folder repositori
cd /home/kaltaraid/Documents/ANALISA-SAHAM/

# 1. Jalankan skrip Python untuk update data bursa
/usr/bin/python update_data.py

# 2. JALANKAN BOT SIMULATOR (Berjalan otomatis setelah data ditarik)
/usr/bin/python bot_simulator.py

# ==========================================
# FITUR SAPU OTOMATIS (MAX 50 HARI)
# Menghapus file .csv di folder arsip yang umurnya lebih dari 50 hari
find Arsip_Data_Saham/ -name "*.csv" -type f -mtime +50 -delete
# ==========================================

# Simpan dan kirim ke GitHub
git pull origin main
git add hasil_screener.csv
git add Arsip_Data_Saham/
git add portofolio_virtual.csv
git add history_trade.csv
git add sinyal_ai.csv
git commit -m "Auto-update data, arsip, dan bot simulator" || echo "Tidak ada perubahan"
git push