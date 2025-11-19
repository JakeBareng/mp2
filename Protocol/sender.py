import sys
import os
import time
from Transport.socket_wrapper import SocketWrapper
from Protocol.segment import Segment
from Protocol.reliability import ReliabilityLayer
from Protocol.congestion_control import CongestionControl

# Constants
SYN = 0b00000010
ACK = 0b00010000
FIN = 0b00000001
ACK_POLL_TIMEOUT = 0.1  # seconds
MSS = 1000             # Maximum Segment Size

class Sender:
    def __init__(self, local_ip, local_port, target_ip, target_port, file_path):
        self.local_addr = (local_ip, local_port)
        self.remote_addr = (target_ip, target_port)
        self.file_path = file_path
        
        self.sock_wrapper = SocketWrapper(local_addr=self.local_addr, remote_addr=self.remote_addr)
        
        self.cc = CongestionControl()
        self.reliability = ReliabilityLayer(window_size=1, timeout_interval=1.0)

    def handshake(self) -> bool:
        """
        Executes 3-Way Handshake 
        returns True if successful, False otherwise. 
        """
        print("Starting Handshake...")
        
        # 1. SYN
        syn_seg = Segment(src_port=self.local_addr[1], dest_port=self.remote_addr[1], seq_num=0, ack_num=0, flags=SYN, window=1024)

        self.sock_wrapper.send_segment(syn_seg.encode())

        # 2. Wait for SYN-ACK
        try:
            data, _ = self.sock_wrapper.recv_segment(timeout=2.0)
            syn_ack = Segment.decode(data)
            
            if syn_ack.flags & (SYN | ACK):
                print("Received SYN-ACK!")
                # 3. ACK
                ack_seg = Segment(src_port=self.local_addr[1], dest_port=self.remote_addr[1], seq_num=1, ack_num=syn_ack.seq_num + 1, flags=ACK, window=1024)
                self.sock_wrapper.send_segment(ack_seg.encode())
                return True

        except Exception as e:
            print(f"Handshake failed: {e}")
            return False

    def start_transfer(self):
        # 1. Get file size for tracking progress
        try:
            file_size = os.path.getsize(self.file_path)
            total_chunks = (file_size + MSS - 1) // MSS
        except FileNotFoundError:
            print(f"File not found: {self.file_path}")
            return

        print(f"Transferring {total_chunks} packets...")

        # 2. Track Sequence Number handshake left off: 1
        current_seq_num = 1 
        chunks_sent = 0
        
        with open(self.file_path, 'rb') as f:
            # Main Loop: Continue until all packets are sent AND acked
            while self.reliability.send_base < (total_chunks + 1): # +1 to account for seq offset
                
                # --- SENDING PHASE ---
                # read from disk only if we are allowed to send
                while chunks_sent < total_chunks and self.reliability.can_send():
                    
                    # Seek to the correct position and read ONE chunk
                    f.seek(chunks_sent * MSS)
                    chunk_data = f.read(MSS)
                    
                    if not chunk_data:
                        break # EOF

                    # Create Segment
                    seg = Segment(
                        src_port=self.local_addr[1], 
                        dest_port=self.remote_addr[1], 
                        seq_num=current_seq_num, # Consistent numbering
                        ack_num=0, # No ACK in data segments
                        flags=0, 
                        window=1024, 
                        data=chunk_data
                    )
                    
                    # Hand off to reliability layer (It must buffer this for retrans!)
                    self.reliability.send_packet(seg, self.sock_wrapper)
                    current_seq_num += 1
                    chunks_sent += 1

                # --- RECEIVING ---
                
                # 1. Update Window
                self.reliability.window_size = self.cc.get_window_size()

                # 2. Check Timeout
                if self.reliability.check_timeout(self.sock_wrapper):
                    self.cc.on_timeout()

                # 3. Check for ACKs (Non-blocking if possible, or short timeout)
                try:
                    data, _ = self.sock_wrapper.recv_segment(timeout=0.01) 
                    ack_seg = Segment.decode(data)
                    
                    # CC Logic
                    if self.cc.on_ack_received(ack_seg.ack_num):
                        # Fast Retransmit logic...
                        missing_seq = self.reliability.send_base
                        if missing_seq in self.reliability.buffer:
                            print(f"Fast Retransmit: {missing_seq}")
                            retransmit_seg = self.reliability.buffer[missing_seq]
                            self.sock_wrapper.send_segment(retransmit_seg.encode())

                    # Update Sliding Window (removes acknowledged packets from buffer)
                    self.reliability.receive_ack(ack_seg.ack_num)

                except Exception:
                    # Socket timeout (expected if no ACKs pending)
                    pass

        # --- TEARDOWN ---
        print("File sent. Initiating teardown...")
        self.teardown(current_seq_num)
    
    def teardown(self, current_seq_num):
            """
            Graceful exit. Sends FIN and waits for ACK.
            """
            print("--- Initiating Teardown ---")
            
            max_retries = 5
            attempts = 0
            
            # The FIN packet takes up 1 sequence number
            fin_seq = current_seq_num
            
            while attempts < max_retries:
                # 1. Send FIN
                # Note: Window=0
                fin_seg = Segment(
                    src_port=self.local_addr[1], 
                    dest_port=self.remote_addr[1], 
                    seq_num=fin_seq, 
                    ack_num=0, 
                    flags=FIN, 
                    window=0
                )
                
                self.sock_wrapper.send_segment(fin_seg.encode())
                print(f"Sent FIN (Attempt {attempts + 1}/{max_retries})")

                # 2. Wait for ACK
                try:
                    # Wait up to 1.0 second for the goodbye confirmation
                    data, _ = self.sock_wrapper.recv_segment(timeout=1.0)
                    ack_seg = Segment.decode(data)

                    # Check if it's actually an ACK for our FIN
                    # (ACK number should be fin_seq + 1)
                    if (ack_seg.flags & ACK) and (ack_seg.ack_num == fin_seq + 1):
                        print("Received FIN-ACK. Connection closed clean.")
                        break
                    
                except Exception:
                    # Timeout occurred, loop back and resend FIN
                    pass
                
                attempts += 1

            if attempts == max_retries:
                print("Teardown timed out. Force closing.")

            # 3. Actually close the socket
            self.sock_wrapper.close()