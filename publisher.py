import hashlib
import json
from datetime import datetime, timedelta

import pandas as pd

from encryption import (
    create_root_key,
    derive_child_key,
    encrypt_payload,
)

DATE_FORMAT = "%Y-%m-%d"

def parse_date(value: str) -> datetime:
    return datetime.strptime(value, DATE_FORMAT)

def format_date(value: datetime) -> str:
    return value.strftime(DATE_FORMAT)

class TreeNode:
    """
    Node untuk Hierarchical Key Tree.
    Setiap node merepresentasikan range tanggal:
    start_date <= event_date <= end_date
    """

    def __init__(self, label: str, start_date: datetime, end_date: datetime, key: bytes, left=None, right=None):
        self.label = label
        self.start_date = start_date
        self.end_date = end_date
        self.key = key
        self.left = left
        self.right = right

    # Fungsi pembantu untuk memeriksa apakah event datetime berada dalam range node.
    def contains(self, date_value: datetime) -> bool:
        return self.start_date <= date_value <= self.end_date

    # Fungsi pembantu untuk memeriksa apakah node adalah leaf (tidak memiliki anak).
    def is_leaf(self) -> bool:
        return self.left is None and self.right is None

    # Fungsi pembantu untuk menghitung total hari dalam range node.
    def total_days(self) -> int:
        return (self.end_date - self.start_date).days + 1

    # Fungsi pembantu untuk mendapatkan label node (bisa dipakai untuk debugging atau metadata).
    def key_label(self) -> str:
        return self.label

class Publisher:
    """
    Publisher tunggal dengan Hierarchical Key Tree berbasis range datetime dan least count.
    """

    def __init__(self, name: str, broker, laporan, csv_path: str, master_key: bytes, lcnum: int = 30):
        if lcnum < 1:
            raise ValueError("lcnum minimal bernilai 1.")

        self.name = name
        self.broker = broker
        self.laporan = laporan
        self.csv_path = csv_path
        self.master_key = master_key
        self.lcnum = lcnum

        self.df = None
        self.root = None
        self.leaf_nodes = []

    # Fungsi untuk menyiapkan Hierarchical Key Tree berdasarkan range datetime dari data CSV.
    def setup_datetime_tree(self) -> None:
        """
        Menyiapkan Hierarchical Key Tree berdasarkan range datetime dari data CSV.
        """

        self.df = pd.read_csv(self.csv_path, usecols=["Date", "Close"])
        self.df["Date"] = pd.to_datetime(self.df["Date"]).dt.strftime(DATE_FORMAT)

        if self.df.empty:
            raise ValueError("CSV tidak memiliki data yang dapat diproses.")

        all_dates = [
            parse_date(date_value)
            for date_value in self.df["Date"]
        ]
        min_date = min(all_dates)
        max_date = max(all_dates)

        root_label = ""
        root_key = create_root_key(
            master_key=self.master_key,
            root_label=root_label
        )

        self.leaf_nodes = []
        self.root = self._build_datetime_tree(
            label=root_label,
            start_date=min_date,
            end_date=max_date,
            key=root_key
        )

    # Fungsi untuk mendapatkan domain datetime dari tree yang sudah dibentuk.
    def get_datetime_domain(self) -> tuple[datetime, datetime]:
        if self.root is None:
            self.setup_datetime_tree()

        return self.root.start_date, self.root.end_date

    # Fungsi untuk membuat access key untuk subscriber berdasarkan range datetime.
    def issue_keys_for_subscriber(self, subscriber) -> list:
        """
        Membuat access key untuk subscriber berdasarkan range datetime.
        Range subscription subscriber ditutup oleh beberapa node minimal dari Hierarchical Key Tree.
        """

        range_start = parse_date(subscriber.range_start)
        range_end = parse_date(subscriber.range_end)

        included_nodes = self._retrieve_nodes_in_range(node=self.root, query_start=range_start, query_end=range_end)

        access_keys = []
        for node in included_nodes:
            access_keys.append(
                {
                    "node_label": node.label,
                    "range_start": format_date(node.start_date),
                    "range_end": format_date(node.end_date),
                    "key": node.key
                }
            )

        subscriber.receive_access_keys(access_keys)
        active_subscribers = self.broker.get_active_subscribers(self.name)
        self.laporan.catat_key_per_subscriber(
            active_subscribers=active_subscribers
        )

        return access_keys

    # Fungsi untuk mempublikasikan satu packet berikutnya.
    def publish_next_packet(self, sequence: int, record_index: int) -> bool:
        """
        Mempublikasikan satu packet berikutnya.
        """

        if not self.root and self.df is None:
            self.setup_datetime_tree()

        if record_index >= len(self.df):
            return False

        row = self.df.iloc[record_index]
        record = {
            "timestamp": str(row["Date"]),
            "close": float(row["Close"])
        }

        event_date = parse_date(record["timestamp"])
        leaf_node = self._retrieve_leaf(self.root, event_date)

        encrypted_packet = self._encrypt_payload(
            sequence=sequence,
            record=record,
            leaf_node=leaf_node
        )

        self.broker.publish(self.name, encrypted_packet)

        return True

    # Fungsi pembantu untuk mengenkripsi payload dengan key leaf node.
    def _encrypt_payload(self, sequence: int, record: dict, leaf_node: TreeNode) -> dict:
        """
        Mengenkripsi payload dengan key leaf node.
        Metadata label disusun dari root ke leaf untuk keperluan penurunan key oleh subscriber.
        """
        
        encrypted_data = encrypt_payload(
            payload=record,
            key=leaf_node.key
        )

        return {
            "sequence": sequence,
            "event_datetime": record["timestamp"],
            "datetime_label": leaf_node.label,
            "leaf_range": {
                "start": format_date(leaf_node.start_date),
                "end": format_date(leaf_node.end_date)
            },
            "lcnum": self.lcnum,
            "root": {
                "label": "",
                "start": format_date(self.root.start_date),
                "end": format_date(self.root.end_date)
            },
            "key_chain": self._assemble_leaf_key_path(leaf_node),
            "payload_hash": hashlib.sha256(
                json.dumps(record, sort_keys=True).encode("utf-8")
            ).hexdigest(),
            "nonce": encrypted_data["nonce"],
            "ciphertext": encrypted_data["ciphertext"]
        }

    # Fungsi rekursif untuk membangun Hierarchical Key Tree berdasarkan range datetime dan least count.
    def _build_datetime_tree(self, label: str, start_date: datetime, end_date: datetime, key: bytes) -> TreeNode:
        """
        Membangun Hierarchical Key Tree berdasarkan range datetime dan least count.
        Jika total hari dalam node lebih kecil atau sama dengan least count, node tersebut menjadi leaf.
        Jika tidak, node tersebut dibagi menjadi dua anak dengan range tanggal yang dibagi rata.
        """

        node = TreeNode(
            label=label,
            start_date=start_date,
            end_date=end_date,
            key=key
        )

        if node.total_days() <= self.lcnum:
            self.leaf_nodes.append(node)
            return node

        total_days = (end_date - start_date).days
        middle_date = start_date + timedelta(days=total_days // 2)

        left_start = start_date
        left_end = middle_date
        right_start = middle_date + timedelta(days=1)
        right_end = end_date

        left_label = label + "0"
        right_label = label + "1"

        left_key = derive_child_key(
            parent_key=key,
            child_label=left_label
        )

        right_key = derive_child_key(
            parent_key=key,
            child_label=right_label
        )

        node.left = self._build_datetime_tree(
            label=left_label,
            start_date=left_start,
            end_date=left_end,
            key=left_key
        )

        node.right = self._build_datetime_tree(
            label=right_label,
            start_date=right_start,
            end_date=right_end,
            key=right_key
        )

        return node


    # Fungsi untuk menghitung metrik jumlah key pada range tertentu.
    def get_key_metrics_for_range(self, range_start, range_end) -> dict:
        """
        Menghitung metrik validasi granularity untuk satu access range.

        tree_key_count:
            Jumlah node minimal dari Hierarchical Key Tree yang perlu diberikan
            kepada subscriber untuk menutup range akses.

        standard_key_count:
            Jumlah leaf key yang perlu diberikan jika tidak memakai kompresi
            hierarchical tree, yaitu key dibagikan satu per satu untuk setiap
            leaf yang beririsan dengan access range.
        """

        if self.root is None:
            self.setup_datetime_tree()

        if isinstance(range_start, str):
            range_start = parse_date(range_start)
        if isinstance(range_end, str):
            range_end = parse_date(range_end)

        if range_start > range_end:
            range_start, range_end = range_end, range_start

        tree_nodes = self._retrieve_nodes_in_range(
            node=self.root,
            query_start=range_start,
            query_end=range_end
        )

        leaf_nodes = self._retrieve_leaf_nodes_in_range(
            node=self.root,
            query_start=range_start,
            query_end=range_end
        )

        access_duration_days = (range_end - range_start).days + 1

        return {
            "lcnum": self.lcnum,
            "access_duration_days": access_duration_days,
            "tree_key_count": len(tree_nodes),
            "standard_key_count": len(leaf_nodes),
            "compression_ratio": (len(leaf_nodes) / len(tree_nodes)) if tree_nodes else 0,
            "total_leaf_count": len(self.leaf_nodes),
        }

    # Fungsi rekursif untuk menghitung semua leaf yang beririsan dengan range query.
    def _retrieve_leaf_nodes_in_range(self, node: TreeNode, query_start: datetime, query_end: datetime) -> list:
        if node.end_date < query_start or node.start_date > query_end:
            return []

        if node.is_leaf():
            return [node]

        return (
            self._retrieve_leaf_nodes_in_range(node.left, query_start, query_end)
            + self._retrieve_leaf_nodes_in_range(node.right, query_start, query_end)
        )

    # Fungsi rekursif untuk mencari node yang menutupi range query.
    def _retrieve_nodes_in_range(self, node: TreeNode, query_start: datetime, query_end: datetime) -> list:
        """
        Mencari node yang menutupi range query.
        Jika node sepenuhnya berada dalam range query, kembalikan node tersebut.
        Jika node tidak memiliki irisan dengan range query, abaikan node tersebut.
        Jika node memiliki irisan parsial dengan range query, teruskan pencarian ke anak nodenya.
        """

        if node.end_date < query_start or node.start_date > query_end:
            return []

        if query_start <= node.start_date and node.end_date <= query_end:
            return [node]

        if node.is_leaf():
            return [node]

        return (self._retrieve_nodes_in_range(node.left, query_start, query_end) + self._retrieve_nodes_in_range(node.right, query_start, query_end))

    # Fungsi rekursif untuk mencari leaf node yang sesuai dengan event datetime.
    def _retrieve_leaf(self, node: TreeNode, event_date: datetime) -> TreeNode:
        if node.is_leaf():
            return node

        if node.left.contains(event_date):
            return self._retrieve_leaf(node.left, event_date)

        return self._retrieve_leaf(node.right, event_date)

    # Fungsi pembantu untuk menyusun metadata label dari root ke leaf untuk keperluan penurunan key oleh subscriber.
    def _assemble_leaf_key_path(self, leaf_node: TreeNode) -> list:
        """
        Membuat metadata label dari root ke leaf.
        Subscriber yang punya authorization key di salah satu ancestor dapat menurunkan key sampai leaf menggunakan chain ini.
        """

        chain = []
        current = self.root

        while current is not None:
            chain.append(
                {
                    "label": current.label,
                    "range_start": format_date(current.start_date),
                    "range_end": format_date(current.end_date)
                }
            )

            if current.label == leaf_node.label:
                break

            if current.left is not None and leaf_node.label.startswith(current.left.label):
                current = current.left
            else:
                current = current.right

        return chain

    # Fungsi untuk mencetak struktur Hierarchical Key Tree.
    def print_tree(self):
        if not self.root:
            self.setup_datetime_tree()

        def _print_node(node, depth=0):
            indent = "  " * depth
            print(f"{indent}├── Label: {node.label}")
            print(f"{indent}    Range: {format_date(node.start_date)} - {format_date(node.end_date)}")
            if node.left:
                _print_node(node.left, depth + 1)
            if node.right:
                _print_node(node.right, depth + 1)

        print("Hierarchical Key Tree:")
        _print_node(self.root)
