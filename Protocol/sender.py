import os
import time
from typing import Optional
from Transport.socket_wrapper import SocketWrapper
from Protocol.segment import Segment, SegmentFlags
from Protocol.reliability import ReliabilityLayer
from Protocol.congestion_control import CongestionControl


class SenderState:
    CLOSED = 0
    SYN_SENT = 1
    ESTABLISHED = 2
    FIN_WAIT_1 = 3
    FIN_WAIT_2 = 4
    TIME_WAIT = 5


class Sender:
    def __init__(self, local_ip: str, local_port: int,
                 remote_ip: str, remote_port: int, file_path: str,
                 loss_rate: float = 0.0, corruption_rate: float = 0.0,
                 delay_range: tuple = (0.0, 0.0)):
        self.local_addr = (local_ip, local_port)
        self.remote_addr = (remote_ip, remote_port)
        self.file_path = file_path

        self.sock_wrapper = SocketWrapper(
            local_addr=self.local_addr,
            remote_addr=self.remote_addr,
            loss_rate=loss_rate,
            corruption_rate=corruption_rate,
            delay_range=delay_range
        )

        self.state = SenderState.CLOSED
        self.reliability = ReliabilityLayer(window_size=1, timeout_interval=1.0)
        self.congestion_control = CongestionControl()

        self.seq_num = 0
        self.file_size = 0
        self.bytes_sent = 0
        
    def connect(self) -> bool:
        """Establish connection using three-way handshake"""
        if not os.path.exists(self.file_path):
            print(f"File not found: {self.file_path}")
            return False
            
        self.file_size = os.path.getsize(self.file_path)
        print(f"Connecting to {self.remote_addr}...")
        
        syn_segment = Segment(
            seq_num=self.seq_num,
            flags=SegmentFlags.SYN,
            window_size=8192
        )
        
        self.sock_wrapper.send_segment(syn_segment.serialize())
        self.state = SenderState.SYN_SENT
        
        try:
            data, _ = self.sock_wrapper.recv_segment(timeout=5.0)
            syn_ack = Segment.deserialize(data)
            
            if (syn_ack and syn_ack.is_syn() and syn_ack.is_ack() and
                syn_ack.ack_num == self.seq_num + 1):
                
                self.seq_num += 1
                ack_segment = Segment(
                    seq_num=self.seq_num,
                    ack_num=syn_ack.seq_num + 1,
                    flags=SegmentFlags.ACK,
                    window_size=8192
                )
                
                self.sock_wrapper.send_segment(ack_segment.serialize())
                self.state = SenderState.ESTABLISHED
                self.reliability.send_base = self.seq_num
                self.reliability.next_seq_num = self.seq_num
                print("Connection established")
                return True
                
        except Exception as e:
            print(f"Connection failed: {e}")
            
        self.state = SenderState.CLOSED
        return False
        
    def send_file(self) -> bool:
        """Send file using reliable transport with flow and congestion control"""
        if self.state != SenderState.ESTABLISHED:
            return False
            
        print(f"Sending file: {self.file_path} ({self.file_size} bytes)")
        
        with open(self.file_path, 'rb') as file:
            while self.bytes_sent < self.file_size:
                self._update_window_size()
                
                while (self.bytes_sent < self.file_size and 
                       self.reliability.can_send()):
                    
                    chunk = file.read(Segment.MAX_PAYLOAD_SIZE)
                    if not chunk:
                        break
                        
                    data_segment = Segment(
                        seq_num=0,  # Will be set by reliability layer
                        flags=SegmentFlags.ACK,
                        window_size=8192,
                        payload=chunk
                    )
                    
                    if self.reliability.send_segment(data_segment, self.sock_wrapper):
                        self.bytes_sent += len(chunk)
                        
                self._process_acks()
                self._handle_timeouts()
                
        self._wait_for_all_acks()
        print("File transfer completed")
        return True
        
    def _update_window_size(self):
        """Update reliability window based on congestion control"""
        congestion_window = self.congestion_control.get_window_size()
        self.reliability.update_window_size(congestion_window)
        
    def _process_acks(self):
        """Process incoming ACKs"""
        try:
            data, _ = self.sock_wrapper.recv_segment(timeout=0.01)
            ack_segment = Segment.deserialize(data)
            
            if ack_segment and ack_segment.is_ack():
                old_send_base = self.reliability.send_base
                packets_acked = self.reliability.receive_ack(ack_segment.ack_num)
                
                if packets_acked > 0:
                    is_new_ack = ack_segment.ack_num > old_send_base
                    
                    if self.congestion_control.on_ack_received(
                        ack_segment.ack_num, is_new_ack):
                        self._fast_retransmit()
                        
        except Exception:
            pass
            
    def _handle_timeouts(self):
        """Handle timeout events"""
        if self.reliability.check_timeouts(self.sock_wrapper):
            self.congestion_control.on_timeout()
            
    def _fast_retransmit(self):
        """Perform fast retransmit"""
        oldest_seq = self.reliability.get_oldest_unacked_seq()
        if oldest_seq is not None:
            self.reliability.retransmit_segment(oldest_seq, self.sock_wrapper)
            
    def _wait_for_all_acks(self):
        """Wait for all segments to be acknowledged"""
        timeout_start = time.time()
        
        while (self.reliability.send_base < self.reliability.next_seq_num and
               time.time() - timeout_start < 10.0):
            self._process_acks()
            self._handle_timeouts()
            time.sleep(0.01)
            
    def disconnect(self) -> bool:
        """Close connection using four-way handshake"""
        if self.state != SenderState.ESTABLISHED:
            return False
            
        print("Closing connection...")
        
        fin_segment = Segment(
            seq_num=self.reliability.next_seq_num,
            flags=SegmentFlags.FIN,
            window_size=0
        )
        
        self.sock_wrapper.send_segment(fin_segment.serialize())
        self.state = SenderState.FIN_WAIT_1
        
        try:
            data, _ = self.sock_wrapper.recv_segment(timeout=5.0)
            ack_segment = Segment.deserialize(data)
            
            if ack_segment and ack_segment.is_ack():
                self.state = SenderState.FIN_WAIT_2
                
                data, _ = self.sock_wrapper.recv_segment(timeout=5.0)
                fin_segment = Segment.deserialize(data)
                
                if fin_segment and fin_segment.is_fin():
                    final_ack = Segment(
                        seq_num=self.reliability.next_seq_num + 1,
                        ack_num=fin_segment.seq_num + 1,
                        flags=SegmentFlags.ACK,
                        window_size=0
                    )
                    
                    self.sock_wrapper.send_segment(final_ack.serialize())
                    self.state = SenderState.TIME_WAIT
                    time.sleep(1.0)  # Brief wait
                    
        except Exception as e:
            print(f"Disconnect error: {e}")
            
        self.state = SenderState.CLOSED
        self.sock_wrapper.close()
        print("Connection closed")
        return True
        
    def get_progress(self) -> float:
        """Get file transfer progress as percentage"""
        if self.file_size == 0:
            return 0.0
        return (self.bytes_sent / self.file_size) * 100.0