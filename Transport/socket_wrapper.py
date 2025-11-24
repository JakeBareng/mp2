import socket
import random
import time
from typing import Tuple, Optional


class SocketWrapper:
    def __init__(self,
                 local_addr: Optional[Tuple[str, int]] = None,
                 remote_addr: Optional[Tuple[str, int]] = None,
                 loss_rate: float = 0.0,
                 corruption_rate: float = 0.0,
                 delay_range: Tuple[float, float] = (0.0, 0.0)):
        """
        Initialize socket wrapper with network simulation parameters

        Args:
            local_addr: Local address to bind to
            remote_addr: Remote address to send to
            loss_rate: Probability of packet loss (0.0 to 1.0)
            corruption_rate: Probability of bit corruption (0.0 to 1.0)
            delay_range: Min and max delay in seconds (min_delay, max_delay)
        """
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.local_addr = local_addr
        self.remote_addr = remote_addr
        self.loss_rate = loss_rate
        self.corruption_rate = corruption_rate
        self.delay_range = delay_range
        self.handshake_mode = True  # Don't drop packets during handshake

        if local_addr is not None:
            self.sock.bind(local_addr)


    def bind(self, addr: Tuple[str, int]):
        self.sock.bind(addr)

    def _simulate_delay(self):
        """Simulate network delay"""
        if self.delay_range[1] > 0:
            delay = random.uniform(self.delay_range[0], self.delay_range[1])
            time.sleep(delay)

    def _simulate_corruption(self, data: bytes) -> bytes:
        """Simulate bit corruption in data"""
        if random.random() < self.corruption_rate:
            data_array = bytearray(data)
            if len(data_array) > 0:
                corrupt_index = random.randint(0, len(data_array) - 1)
                corrupt_bit = random.randint(0, 7)
                data_array[corrupt_index] ^= (1 << corrupt_bit)
            return bytes(data_array)
        return data

    def send_segment(self, segment: bytes):
        """Send segment with simulated network conditions"""
        # Don't drop packets during handshake
        if not self.handshake_mode and random.random() < self.loss_rate:
            return

        self._simulate_delay()

        segment = self._simulate_corruption(segment)

        self.sock.sendto(segment, self.remote_addr)

    def enable_loss_simulation(self):
        """Enable packet loss simulation (after handshake)"""
        self.handshake_mode = False

    def recv_segment(self, timeout: Optional[float] = None):
        if timeout is not None:
            self.sock.settimeout(timeout)
        return self.sock.recvfrom(2048)

    def close(self):
        self.sock.close()
