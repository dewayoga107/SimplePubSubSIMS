import random
from datetime import datetime, timedelta

from encryption import derive_child_key, decrypt_packet

DATE_FORMAT = "%Y-%m-%d"

# Fungsi pembantu untuk parsing tanggal dari string.
def parse_date(value: str) -> datetime:
    return datetime.strptime(value, DATE_FORMAT)

# Fungsi pembantu untuk mengubah datetime menjadi string.
def format_date(value: datetime) -> str:
    return value.strftime(DATE_FORMAT)

# Class Subscriber
class Subscriber:
    def __init__(self, name: str):
        self.name = name
        self.range_start = None
        self.range_end = None
        self.keys = []
        self.total_packets_delivered = 0
        self.total_received = 0
        self.total_failed = 0

    # Subscriber memilih random range start dan range end
    # dari domain datetime yang tersedia pada publisher.
    def choose_random_range(self, domain_start: datetime, domain_end: datetime) -> None:
        total_days = (domain_end - domain_start).days

        random_start_offset = random.randint(0, total_days)
        random_end_offset = random.randint(0, total_days)

        chosen_start = domain_start + timedelta(days=min(random_start_offset, random_end_offset))
        chosen_end = domain_start + timedelta(days=max(random_start_offset, random_end_offset))

        self.range_start = format_date(chosen_start)
        self.range_end = format_date(chosen_end)

    # Subscriber menerima access keys dari publisher setelah subscribe.
    def receive_access_keys(self, access_keys: list) -> None:
        self.keys = access_keys

    # Subscriber menerima encrypted packet dari broker.
    def receive(self, topic: str, encrypted_packet: dict) -> None:
        # Counter ini mencatat seluruh packet yang benar-benar diteruskan broker
        # ke subscriber, terlepas dari apakah packet tersebut masuk range
        # subscriber atau berhasil didekripsi.
        self.total_packets_delivered += 1

        event_date = parse_date(encrypted_packet["event_datetime"])

        if not self._event_in_range(event_date):
            self.total_failed += 1
            return

        valid_auth_key = self._find_key(encrypted_packet)

        if valid_auth_key is None:
            self.total_failed += 1
            return

        try:
            leaf_key = self._derive_child_key(
                auth_key=valid_auth_key,
                encrypted_packet=encrypted_packet
            )

            decrypt_packet(
                encrypted_packet=encrypted_packet,
                key=leaf_key
            )

            self.total_received += 1

        except Exception:
            self.total_failed += 1

    # Fungsi pembantu untuk memeriksa apakah event datetime berada dalam range yang diizinkan subscriber.
    def _event_in_range(self, event_date: datetime) -> bool:
        if self.range_start is None or self.range_end is None:
            return False

        start_date = parse_date(self.range_start)
        end_date = parse_date(self.range_end)
        return start_date <= event_date <= end_date

    # Fungsi pembantu untuk mencari authorization key yang valid.
    def _find_key(self, encrypted_packet: dict):
        for auth_key in self.keys:
            auth_label = auth_key["node_label"]
            packet_label = encrypted_packet["datetime_label"]

            is_auth_node_ancestor = (
                auth_label == "" or packet_label.startswith(auth_label)
            )

            if is_auth_node_ancestor:
                return auth_key

        return None

    # Fungsi pembantu untuk menurunkan child key dari authorization key menggunakan key chain pada encrypted packet.
    def _derive_child_key(self, auth_key: dict, encrypted_packet: dict) -> bytes:
        key = auth_key["key"]
        auth_label = auth_key["node_label"]
        key_chain = encrypted_packet["key_chain"]

        auth_index = None

        for index, node_info in enumerate(key_chain):
            if node_info["label"] == auth_label:
                auth_index = index
                break

        if auth_index is None:
            raise ValueError("Authorization label tidak ditemukan pada key chain.")

        for node_info in key_chain[auth_index + 1:]:
            key = derive_child_key(
                parent_key=key,
                child_label=node_info["label"]
            )

        return key
