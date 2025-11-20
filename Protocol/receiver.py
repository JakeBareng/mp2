import time
from typing import Optional, Tuple
from Transport.socket_wrapper import SocketWrapper
from Protocol.segment import Segment, SegmentFlags
from Protocol.reliability import ReliabilityLayer


class ReceiverState:
    CLOSED = 0
    LISTEN = 1
    SYN_RCVD = 2
    ESTABLISHED = 3
    CLOSE_WAIT = 4
    LAST_ACK = 5


class Receiver:
    def __init__(self, local_ip: str, local_port: int,
                 loss_rate: float = 0.0, corruption_rate: float = 0.0,
                 delay_range: tuple = (0.0, 0.0)):
        self.local_addr = (local_ip, local_port)
        self.remote_addr = None

        self.sock_wrapper = SocketWrapper(
            local_addr=self.local_addr,
            loss_rate=loss_rate,
            corruption_rate=corruption_rate,
            delay_range=delay_range
        )
        self.state = ReceiverState.CLOSED
        self.reliability = ReliabilityLayer(window_size=8, timeout_interval=1.0)

        self.seq_num = 0
        self.expected_seq = 0
        self.received_data = bytearray()
        self.connection_established = False
        
    def listen(self) -> bool:
        """Start listening for incoming connections"""
        try:
            self.state = ReceiverState.LISTEN
            return True
        except Exception as e:
            print(f"Listen failed: {e}")
            return False
            
    def accept_connection(self, timeout: float = 30.0) -> bool:
        """Accept incoming connection using three-way handshake"""
        if self.state != ReceiverState.LISTEN:
            return False
            
        try:
            # Wait for SYN
            data, addr = self.sock_wrapper.recv_segment(timeout=timeout)
            syn_segment = Segment.deserialize(data)
            
            if syn_segment and syn_segment.is_syn():
                self.remote_addr = addr
                self.sock_wrapper.remote_addr = addr
                self.expected_seq = syn_segment.seq_num + 1
                
                # Send SYN-ACK
                syn_ack = Segment(
                    seq_num=self.seq_num,
                    ack_num=self.expected_seq,
                    flags=SegmentFlags.SYN | SegmentFlags.ACK,
                    window_size=8192
                )
                
                self.sock_wrapper.send_segment(syn_ack.serialize())
                self.state = ReceiverState.SYN_RCVD
                
                # Wait for ACK
                data, _ = self.sock_wrapper.recv_segment(timeout=5.0)
                ack_segment = Segment.deserialize(data)
                
                if (ack_segment and ack_segment.is_ack() and
                    ack_segment.ack_num == self.seq_num + 1):
                    
                    self.seq_num += 1
                    self.state = ReceiverState.ESTABLISHED
                    self.connection_established = True
                    return True
                    
        except Exception as e:
            print(f"Connection accept failed: {e}")
            
        self.state = ReceiverState.CLOSED
        return False
        
    def receive_data(self, timeout: float = 5.0) -> Optional[bytes]:
        """Receive data segments"""
        if not self.connection_established:
            return None
            
        try:
            data, _ = self.sock_wrapper.recv_segment(timeout=timeout)
            segment = Segment.deserialize(data)
            
            if not segment:
                return None
                
            # Handle FIN
            if segment.is_fin():
                self._handle_fin(segment)
                return None
                
            # Handle data segment
            if segment.payload and len(segment.payload) > 0:
                # Send ACK
                ack_segment = Segment(
                    seq_num=self.seq_num,
                    ack_num=segment.seq_num + len(segment.payload),
                    flags=SegmentFlags.ACK,
                    window_size=8192
                )
                
                self.sock_wrapper.send_segment(ack_segment.serialize())
                
                # Add to received data
                self.received_data.extend(segment.payload)
                return segment.payload
                
        except Exception:
            return None
            
        return None
        
    def _handle_fin(self, fin_segment: Segment):
        """Handle FIN segment for connection termination"""
        # Send ACK for FIN
        ack_segment = Segment(
            seq_num=self.seq_num,
            ack_num=fin_segment.seq_num + 1,
            flags=SegmentFlags.ACK,
            window_size=0
        )
        
        self.sock_wrapper.send_segment(ack_segment.serialize())
        self.state = ReceiverState.CLOSE_WAIT
        
        # Send FIN
        fin_response = Segment(
            seq_num=self.seq_num + 1,
            flags=SegmentFlags.FIN,
            window_size=0
        )
        
        self.sock_wrapper.send_segment(fin_response.serialize())
        self.state = ReceiverState.LAST_ACK
        
        # Wait for final ACK
        try:
            data, _ = self.sock_wrapper.recv_segment(timeout=5.0)
            final_ack = Segment.deserialize(data)
            
            if final_ack and final_ack.is_ack():
                self.state = ReceiverState.CLOSED
                self.connection_established = False
                
        except Exception:
            pass
            
    def get_received_data(self) -> bytes:
        """Get all received data"""
        return bytes(self.received_data)
        
    def close(self):
        """Close the receiver"""
        self.connection_established = False
        self.state = ReceiverState.CLOSED
        self.sock_wrapper.close()


if __name__ == '__main__':
    import sys
    import argparse

    parser = argparse.ArgumentParser(description='File Transfer Receiver')
    parser.add_argument('--local-ip', default='127.0.0.1', help='Local IP address')
    parser.add_argument('--local-port', type=int, required=True, help='Local port')
    parser.add_argument('--output', required=True, help='Output file path')
    parser.add_argument('--loss-rate', type=float, default=0.0,
                       help='Packet loss rate (0.0-1.0)')
    parser.add_argument('--corruption-rate', type=float, default=0.0,
                       help='Packet corruption rate (0.0-1.0)')
    parser.add_argument('--min-delay', type=float, default=0.0,
                       help='Minimum delay in seconds')
    parser.add_argument('--max-delay', type=float, default=0.0,
                       help='Maximum delay in seconds')

    args = parser.parse_args()

    receiver = Receiver(
        local_ip=args.local_ip,
        local_port=args.local_port,
        loss_rate=args.loss_rate,
        corruption_rate=args.corruption_rate,
        delay_range=(args.min_delay, args.max_delay)
    )

    try:
        print(f"Receiver listening on {args.local_ip}:{args.local_port}")

        if not receiver.listen():
            print("Failed to start listening")
            sys.exit(1)

        print("Waiting for connection...")
        if not receiver.accept_connection():
            print("Failed to accept connection")
            sys.exit(1)

        print("Connection established, receiving data...")

        while receiver.connection_established:
            data = receiver.receive_data(timeout=10.0)
            if data is None:
                break

        received_data = receiver.get_received_data()

        with open(args.output, 'wb') as f:
            f.write(received_data)

        print(f"File received successfully!")
        print(f"Saved to: {args.output}")
        print(f"Total bytes: {len(received_data)}")

        receiver.close()

    except KeyboardInterrupt:
        print("\nReceiver interrupted by user")
        receiver.close()
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        receiver.close()
        sys.exit(1)