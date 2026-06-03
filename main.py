import time

from broker import Broker
from laporan import Laporan
from publisher import Publisher
from subscriber import Subscriber
from subscriber_manager import SubscriberManager


# =========================
# Setting simulasi
# Ubah bagian ini jika ingin mengganti konfigurasi program.
# =========================

# Lokasi file yang diperlukan untuk simulasi.
CSV_PATH = "data/GoogleStock_Dataset_V2.csv"

# Nama publisher/perangkat yang digunakan untuk subscribe di broker.
PUBLISHER_NAME = "GoogleStockPublisher"

# Durasi simulasi dalam detik.
# 10 berarti 10 detik.
# 60 berarti 1 menit.
SIMULATION_DURATION_SECONDS = 7200

# Jeda antar publish dalam detik.
PUBLISH_INTERVAL_SECONDS = 1

# Pengaturan lcnum (Least Count).
# 1  = leaf per hari
# 7  = leaf maksimum 7 hari
# 30 = leaf maksimum 30 hari
# Makin besar nilainya, makin sedikit leaf yang dibuat.
# Ubah granulisasi untuk tiap run dan efeknya. 
LCNUM = 30

# Pengaturan jumlah subscriber.
INITIAL_SUBSCRIBERS = 1
ADD_SUBSCRIBERS_INTERVAL = 3
SUBSCRIBERS_ADDED_PER_INTERVAL = 2
TOTAL_SUBSCRIBERS = 150

# Range datetime tidak lagi ditentukan dari main.
# Setiap subscriber akan memilih random range start dan range end
# ketika subscriber akan join ke publisher.

# Pengaturan master key untuk seed pembuatan root hierarchy tree.
MASTER_KEY = b"stock_price_master_key"

def main():
    broker = Broker()
    laporan = Laporan()

    publisher = Publisher(
        name=PUBLISHER_NAME,
        broker=broker,
        laporan=laporan,
        csv_path=CSV_PATH,
        master_key=MASTER_KEY,
        lcnum=LCNUM
    )

    publisher.setup_datetime_tree()
    # publisher.print_tree()

    subscribers = [
        Subscriber(
            name=f"Subscriber-{number}"
        )
        for number in range(1, TOTAL_SUBSCRIBERS + 1)
    ]

    manager = SubscriberManager(
        broker=broker,
        publisher=publisher,
        subscribers=subscribers,
        subscriber_addition_interval=ADD_SUBSCRIBERS_INTERVAL,
        num_subscribers_per_interval=SUBSCRIBERS_ADDED_PER_INTERVAL
    )

    manager.start_with_initial_subscribers(
        initial_count=INITIAL_SUBSCRIBERS
    )

    print("\nSimulasi dimulai.")
    print(f"Durasi simulasi: {SIMULATION_DURATION_SECONDS} detik.")
    print(f"Interval publish: {PUBLISH_INTERVAL_SECONDS} detik.\n")

    simulation_start_time = time.time()
    simulation_end_time = simulation_start_time + SIMULATION_DURATION_SECONDS

    packet_sequence = 0
    record_index = 0

    try:
        while time.time() < simulation_end_time:
            elapsed_seconds = time.time() - simulation_start_time

            packet_sequence += 1

            manager.add_subscribers_over_time(
                packet_number=packet_sequence,
                elapsed_seconds=elapsed_seconds
            )

            publish_success = publisher.publish_next_packet(
                sequence=packet_sequence,
                record_index=record_index
            )

            if not publish_success:
                print("Data publisher sudah habis. Simulasi dihentikan.")
                break

            record_index += 1

            if PUBLISH_INTERVAL_SECONDS > 0:
                time.sleep(PUBLISH_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        print("\nSimulasi dihentikan oleh user.")

    print(f"\nSimulasi selesai. Total encrypted packet dipublish: {record_index}")

    laporan.tampilkan_ringkasan()
    laporan.simpan_ke_csv()


if __name__ == "__main__":
    main()
