#!/bin/bash

# Masuk ke folder repositori
cd /home/kaltaraid/Documents/ANALISA-SAHAM/

# Jalankan skrip Python
/usr/bin/python update_data.py

# ==========================================
# FITUR SAPU OTOMATIS (MAX 50 HARI)
# Menghari file .csv di folder arsip yang umurnya lebih dari 50 hari
find Arsip_Data_Harian/ -name "*.csv" -type f -mtime +50 -delete
# ==========================================

# Simpan dan kirim ke GitHub
git pull origin main
git add hasil_screener.csv
git add Arsip_Data_Harian/
git commit -m "Auto-update data dan arsip harian dari Laptop" || echo "Tidak ada perubahan"
git push