import time
from Protocol.segment import Segment 
import Transport.socket_wrapper as sw

class ReliabilityLayer:
    def __init__(self, window_size, timeout_interval):
        self.window_size = window_size
        self.timeout_interval = timeout_interval
        
        self.send_base = 0
        self.next_seq_num = 0
        self.buffer = {}            # {seq_num: segment_object}
        self.timer_start = None

    def can_send(self) -> bool:
        """Checks if the window is full."""
        return (self.next_seq_num - self.send_base) < self.window_size

    def send_packet(self, segment, sock_wrapper: sw.SocketWrapper) -> bool:
        """
        Sends a packet using the socket wrapper and buffers it.
        """
        if not self.can_send():
            return False 

        segment.seq_num = self.next_seq_num

        # Use the wrapper to send
        sock_wrapper.send_segment(segment.encode())
        
        # Buffer it for potential retransmission
        self.buffer[self.next_seq_num] = segment
        
        # Start timer if this is the oldest unacked packet
        if self.send_base == self.next_seq_num:
            self.timer_start = time.time()
            
        self.next_seq_num += 1
        return True

    def receive_ack(self, ack_num) -> int:
        """
        Handles Cumulative ACKs. Returns number of new packets acked.
        """
        packets_acked = 0
        if ack_num > self.send_base:
            packets_acked = ack_num - self.send_base
            
            # Remove acked packets from buffer
            for offset in range(packets_acked):
                self.buffer.pop(self.send_base + offset, None)
                
            self.send_base = ack_num
            
            # Reset or stop timer
            if self.send_base != self.next_seq_num:
                self.timer_start = time.time()
            else:
                self.timer_start = None # Window empty
                
        return packets_acked

    def check_timeout(self, sock_wrapper: sw.SocketWrapper) -> bool:
        """
        Checks if timeout occurred. Resends.
        Returns True if a timeout occurred (signal to Sender), False otherwise.
        """
        if self.timer_start is None:
            return False

        # if time since timer_start exceeds timeout_interval then timeout
        if (time.time() - self.timer_start) > self.timeout_interval:
            print(f"[Reliability] Timeout! Resending from {self.send_base}...")
            
            # Go-Back-N Retransmission
            for seq in range(self.send_base, self.next_seq_num):
                if seq in self.buffer:
                    seg = self.buffer[seq]
                    sock_wrapper.send_segment(seg.encode())
            
            # Restart timer
            self.timer_start = time.time()
            return True # Signal that timeout happened
            
        return False