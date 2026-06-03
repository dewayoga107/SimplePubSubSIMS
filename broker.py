class Broker:
    """
    Broker hanya meneruskan encrypted packet dari publisher
    ke subscriber aktif.
    """

    def __init__(self):
        self.subscribers = {}

    # Fungsi untuk subscriber bergabung ke topic publisher.
    def subscribe(self, topic: str, subscriber) -> bool:
        """
        Menambahkan subscriber ke topic tertentu.
        """

        if topic not in self.subscribers:
            self.subscribers[topic] = []

        if subscriber in self.subscribers[topic]:
            return False

        self.subscribers[topic].append(subscriber)
        print(f"{subscriber.name} JOIN topic '{topic}'.")
        
        return True

    # Fungsi untuk mempublikasikan packet ke semua subscriber aktif.
    def publish(self, topic: str, encrypted_packet: dict) -> None:
        """
        Mempublikasikan packet ke semua subscriber aktif.
        """

        active_subscribers = self.subscribers.get(topic, [])

        if not active_subscribers:
            print(f"Broker: tidak ada subscriber aktif untuk topic '{topic}'.")
            return

        for subscriber in active_subscribers.copy():
            subscriber.receive(topic, encrypted_packet)

    # Fungsi untuk mendapatkan daftar subscriber aktif untuk sebuah topic.
    def get_active_subscribers(self, topic: str) -> list:
        """
        Mengembalikan daftar subscriber aktif untuk sebuah topic.
        """

        return self.subscribers.get(topic, []).copy()

    # Fungsi untuk mendapatkan jumlah subscriber aktif untuk sebuah topic.
    def get_active_subscriber_count(self, topic: str) -> int:
        """
        Mengembalikan jumlah subscriber aktif untuk sebuah topic.
        """
        
        return len(self.subscribers.get(topic, []))
