import csv
from pathlib import Path
from datetime import datetime


class Laporan:
    """
    Laporan mencatat:
    - jumlah subscriber aktif
    - jumlah key NAKT yang dikelola per subscriber
    - jumlah packet yang sudah diteruskan broker per subscriber
    """

    def __init__(self):
        self.records = []

    def catat_key_per_subscriber(self, active_subscribers: list) -> None:
        jumlah_subscriber = len(active_subscribers)

        if jumlah_subscriber == 0:
            return

        total_key_dikelola = sum(
            len(subscriber.keys)
            for subscriber in active_subscribers
        )

        total_paket_terkirim = sum(
            subscriber.total_packets_delivered
            for subscriber in active_subscribers
        )

        Treekey_per_subs = total_key_dikelola / jumlah_subscriber
        Standarkey_per_subs = total_paket_terkirim / jumlah_subscriber

        self.records.append(
            {
                "jumlah_subscriber": jumlah_subscriber,
                "Treekey_per_subs": round(Treekey_per_subs, 6),
                "Standarkey_per_subs": round(Standarkey_per_subs, 6)
            }
        )

    def tampilkan_ringkasan(self) -> None:
        print("\nRingkasan Laporan Key per Subscriber:")

        if not self.records:
            print("Belum ada data key per subscriber yang tercatat.")
            return

        for record in self.records:
            print(
                f"Jumlah subscriber: {record['jumlah_subscriber']} | "
                f"Tree Key per subscriber: {record['Treekey_per_subs']:.6f} | "
                f"Standard Key per subscriber: "
                f"{record['Standarkey_per_subs']:.6f}"
            )

    def simpan_ke_csv(self, output_dir: str = "laporan") -> None:
        output_folder = Path(output_dir)
        output_folder.parent.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = output_folder/f"laporan_key_per_subscriber_{timestamp}.csv"

        with output_path.open(mode="w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(
                csv_file,
                fieldnames=[
                    "jumlah_subscriber",
                    "Treekey_per_subs",
                    "Standarkey_per_subs"
                ]
            )

            writer.writeheader()
            writer.writerows(self.records)

        print(f"Laporan CSV tersimpan di: {output_path}")
