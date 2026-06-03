class SubscriberManager:
    """
    Mengatur jumlah subscriber yang aktif.
    """
    
    def __init__(self, broker, publisher, subscribers: list, subscriber_addition_interval: float, num_subscribers_per_interval: int): 
        self.broker = broker
        self.publisher = publisher
        self.subscribers = subscribers
        self.subscriber_addition_interval = subscriber_addition_interval
        self.num_subscribers_per_interval = num_subscribers_per_interval
        self.next_subscriber_index = 0
        self.next_add_time = 0
        
    # Memulai dengan sejumlah subscriber awal yang langsung aktif.
    def start_with_initial_subscribers(self, initial_count: int) -> None:
        for _ in range(initial_count):
            self._add_next_subscriber()

        self.next_add_time = self.subscriber_addition_interval

    # Menambahkan subscriber secara bertahap berdasarkan waktu yang telah berlalu.
    def add_subscribers_over_time(self, packet_number: int, elapsed_seconds: float) -> None:
        while (elapsed_seconds >= self.next_add_time and self.next_subscriber_index < len(self.subscribers)):
            for _ in range(self.num_subscribers_per_interval):
                if self.next_subscriber_index >= len(self.subscribers):
                    break

                self._add_next_subscriber()
            
            self.next_add_time += self.subscriber_addition_interval
            
        # active_count = self.broker.get_active_subscriber_count(self.publisher.name)
        # print(f"{active_count} subscriber aktif.")

    # Fungsi pembantu untuk menambahkan subscriber berikutnya ke broker dan memberikan authorization keys dari publisher.
    def _add_next_subscriber(self) -> None:
        if self.next_subscriber_index >= len(self.subscribers):
            return

        subscriber = self.subscribers[self.next_subscriber_index]
        self.next_subscriber_index += 1

        domain_start, domain_end = self.publisher.get_datetime_domain()
        subscriber.choose_random_range(
            domain_start=domain_start,
            domain_end=domain_end
        )

        joined = self.broker.subscribe(self.publisher.name, subscriber)

        if joined:
            self.publisher.issue_keys_for_subscriber(subscriber)
            active_count = self.broker.get_active_subscriber_count(self.publisher.name)
            print(f"{active_count} subscriber aktif.")
