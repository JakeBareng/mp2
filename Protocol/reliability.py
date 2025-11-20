import time
from typing import Dict, Optional
from Protocol.segment import Segment
from Transport.socket_wrapper import SocketWrapper


class ReliabilityLayer:
    def __init__(self, window_size: int = 1, timeout_interval: float = 1.0):
        self.window_size = window_size
        self.timeout_interval = timeout_interval
        
        self.send_base = 0
        self.next_seq_num = 0
        self.buffer: Dict[int, Segment] = {}
        self.timers: Dict[int, float] = {}
        
    def can_send(self) -> bool:
        """Check if window allows sending new segment"""
        return (self.next_seq_num - self.send_base) < self.window_size
        
    def send_segment(self, segment: Segment, sock_wrapper: SocketWrapper) -> bool:
        """Send segment and buffer for potential retransmission"""
        if not self.can_send():
            return False
            
        segment.seq_num = self.next_seq_num
        sock_wrapper.send_segment(segment.serialize())
        
        self.buffer[self.next_seq_num] = segment
        self.timers[self.next_seq_num] = time.time()
        
        self.next_seq_num += 1
        return True
        
    def receive_ack(self, ack_num: int) -> int:
        """Process cumulative ACK and update window"""
        packets_acked = 0
        
        if ack_num > self.send_base:
            packets_acked = ack_num - self.send_base
            
            for seq in range(self.send_base, ack_num):
                self.buffer.pop(seq, None)
                self.timers.pop(seq, None)
                
            self.send_base = ack_num
            
        return packets_acked
        
    def check_timeouts(self, sock_wrapper: SocketWrapper) -> bool:
        """Check for timeouts and retransmit if necessary"""
        current_time = time.time()
        timeout_occurred = False
        
        for seq_num in list(self.timers.keys()):
            if seq_num < self.send_base:
                self.timers.pop(seq_num, None)
                continue
                
            if current_time - self.timers[seq_num] > self.timeout_interval:
                if seq_num in self.buffer:
                    segment = self.buffer[seq_num]
                    sock_wrapper.send_segment(segment.serialize())
                    self.timers[seq_num] = current_time
                    timeout_occurred = True
                    
        return timeout_occurred
        
    def get_oldest_unacked_seq(self) -> Optional[int]:
        """Get sequence number of oldest unacknowledged segment"""
        if self.send_base < self.next_seq_num:
            return self.send_base
        return None
        
    def is_segment_in_buffer(self, seq_num: int) -> bool:
        """Check if segment is in retransmission buffer"""
        return seq_num in self.buffer
        
    def retransmit_segment(self, seq_num: int, sock_wrapper: SocketWrapper) -> bool:
        """Retransmit specific segment (for fast retransmit)"""
        if seq_num in self.buffer:
            segment = self.buffer[seq_num]
            sock_wrapper.send_segment(segment.serialize())
            self.timers[seq_num] = time.time()
            return True
        return False
        
    def update_window_size(self, new_size: int):
        """Update sliding window size"""
        self.window_size = max(1, new_size)
        
    def get_window_usage(self) -> int:
        """Get current window usage"""
        return self.next_seq_num - self.send_base
        
    def is_window_full(self) -> bool:
        """Check if sending window is full"""
        return self.get_window_usage() >= self.window_size
        
    def reset(self):
        """Reset reliability layer state"""
        self.send_base = 0
        self.next_seq_num = 0
        self.buffer.clear()
        self.timers.clear()