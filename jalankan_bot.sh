#!/bin/bash

# Masuk ke folder repositori
cd /home/kaltaraid/Documents/SAHAM-SCREENING

# Jalankan skrip Python
/usr/bin/python update_data.py

# Simpan dan kirim ke GitHub
git pull origin main
git add hasil_screener.csv
git commit -m "Auto-update dari Laptop" || echo "Tidak ada perubahan"
git push
