import socket
from typing import Tuple, Optional


class SocketWrapper:
    def __init__(self, 
                 local_addr: Optional[Tuple[str, int]] = None, 
                 remote_addr: Optional[Tuple[str, int]] = None):

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.local_addr = local_addr
        self.remote_addr = remote_addr
        if local_addr is not None:
            self.sock.bind(local_addr)


    def bind(self, addr: Tuple[str, int]):
        self.sock.bind(addr)

    def send_segment(self, segment: bytes):
        self.sock.sendto(segment, self.remote_addr)

    def recv_segment(self, timeout: Optional[float] = None):
        if timeout is not None:
            self.sock.settimeout(timeout)
        return self.sock.recvfrom(1024)

    def close(self):
        self.sock.close()
