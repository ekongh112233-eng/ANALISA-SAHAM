import feedparser
import pandas as pd
import os

def load_keywords(filename):
    """Memuat daftar kata kunci dari file txt."""
    if not os.path.exists(filename):
        print(f"⚠️ Peringatan: File '{filename}' tidak ditemukan.")
        return []
    with open(filename, "r", encoding="utf-8") as file:
        return [line.strip().lower() for line in file if line.strip()]

def get_news_titles(ticker):
    """Menarik judul berita terbaru dari Google News RSS"""
    query = f"saham+{ticker}+akuisisi"
    url = f"https://news.google.com/rss/search?q={query}&hl=id&gl=ID&ceid=ID:id"
    feed = feedparser.parse(url)
    titles = [entry.title for entry in feed.entries[:5]]
    return " | ".join(titles) if titles else "Tidak ada berita terbaru."

def analyze_acquisition_status(news_text, kata_rencana, kata_dalam):
    if news_text == "Tidak ada berita terbaru.":
        return "TIDAK ADA"
        
    teks_kecil = news_text.lower()
    
    # Hanya ambil yang panjangnya >= 2 kata
    dalam_valid = [k for k in kata_dalam if len(k.split()) >= 2]
    rencana_valid = [k for k in kata_rencana if len(k.split()) >= 2]
    
    # Prioritas: DALAM AKUISISI
    if any(k in teks_kecil for k in dalam_valid):
        return "DALAM AKUISISI"
        
    # Prioritas kedua: RENCANA AKUISISI
    if any(k in teks_kecil for k in rencana_valid):
        return "RENCANA AKUISISI"
        
    return "TIDAK ADA"

def main():
    print("🔍 Memulai pemindaian berita dengan logika prioritas (3 kata -> 1 kata)...")
    
    if not os.path.exists("saham.txt"):
        print("❌ Error: File 'saham.txt' tidak ditemukan!")
        return

    # Memuat kata kunci dari file eksternal
    kata_rencana = load_keywords("RENCANA_AKUISISI.txt")
    kata_dalam = load_keywords("DALAM_AKUISISI.txt")

    with open("saham.txt", "r") as file:
        daftar_saham = [baris.strip().upper() for baris in file if baris.strip()]
        
    hasil_akuisisi = []
    
    for ticker in daftar_saham:
        print(f"Memindai berita untuk {ticker}...")
        berita = get_news_titles(ticker)
        status = analyze_acquisition_status(berita, kata_rencana, kata_dalam)
        
        hasil_akuisisi.append({
            "Ticker": ticker,
            "Status Akuisisi": status
        })
        
    if hasil_akuisisi:
        df = pd.DataFrame(hasil_akuisisi)
        df.to_csv("data_akuisisi.csv", index=False)
        print("✅ Selesai! File 'data_akuisisi.csv' berhasil diperbarui.")

if __name__ == "__main__":
    main()