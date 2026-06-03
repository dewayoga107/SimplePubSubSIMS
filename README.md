# SimplePubSubSIMS

SimplePubSubSIMS adalah simulasi sistem **publish/subscribe** untuk data time-series (harga saham) dengan mekanisme distribusi kunci berbasis **Hierarchical Key Tree** dan pendekatan **NAKT (Node-based Access Key Tree)**.

## Gambaran Singkat

Repository ini mensimulasikan alur:
1. `Publisher` membaca data CSV (`Date`, `Close`).
2. Publisher membangun tree range tanggal dan menurunkan key per node.
3. `Subscriber` bergabung ke topik dengan range tanggal acak.
4. Publisher memberi authorization key minimum sesuai range subscriber.
5. Paket terenkripsi dipublikasikan melalui `Broker`.
6. Subscriber mencoba menurunkan leaf key, lalu dekripsi paket.
7. Metrik disimpan melalui modul `Laporan`.

## Struktur Utama

- `main.py` — entry point simulasi dan konfigurasi utama.
- `publisher.py` — logika publisher, pembuatan tree datetime, enkripsi payload, dan distribusi key.
- `subscriber.py` — logika subscriber, validasi range, derivasi key, dan dekripsi.
- `broker.py` — broker sederhana untuk subscribe/publish.
- `subscriber_manager.py` — pengaturan aktivasi subscriber bertahap.
- `encryption.py` — utilitas kriptografi berbasis HMAC-SHA256.
- `laporan.py` — pencatatan metrik dan ekspor CSV.
- `data/GoogleStock_Dataset_V2.csv` — dataset input simulasi.
- `laporan/` — contoh output evaluasi/visualisasi.

## Kebutuhan

- Python 3.10+ (disarankan)
- Dependensi:
  - `pandas`

Install dependensi:

```bash
pip install pandas
```

## Menjalankan Simulasi

Dari root repository:

```bash
python main.py
```

## Konfigurasi Simulasi

Semua parameter utama ada di `main.py`, antara lain:

- `CSV_PATH` — lokasi dataset.
- `SIMULATION_DURATION_SECONDS` — durasi simulasi.
- `PUBLISH_INTERVAL_SECONDS` — interval publish antar paket.
- `LCNUM` — least count untuk menentukan granularitas leaf tree.
- `INITIAL_SUBSCRIBERS` — jumlah subscriber awal aktif.
- `ADD_SUBSCRIBERS_INTERVAL` — interval penambahan subscriber.
- `SUBSCRIBERS_ADDED_PER_INTERVAL` — jumlah subscriber ditambah tiap interval.
- `TOTAL_SUBSCRIBERS` — total subscriber dalam pool simulasi.
- `MASTER_KEY` — master key untuk root key derivation.

## Output

Saat simulasi selesai, program akan:

- Menampilkan ringkasan metrik di terminal.
- Menyimpan CSV laporan ke folder `laporan/` dengan nama:
  - `laporan_key_per_subscriber_<timestamp>.csv`

## Catatan

- Proyek ini bersifat simulasi/eksperimen untuk evaluasi distribusi key, bukan implementasi production-ready.
- Modul `ProofingEvaluation.ipynb` dan file di folder `laporan/` dapat digunakan untuk analisis lanjutan hasil simulasi.
