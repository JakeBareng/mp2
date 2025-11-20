#!/usr/bin/env python3
import sys
import argparse
import time
from Protocol.sender import Sender


def main():
    parser = argparse.ArgumentParser(description='File Transfer Sender')
    parser.add_argument('--local-ip', default='127.0.0.1', help='Local IP address')
    parser.add_argument('--local-port', type=int, default=8080, help='Local port')
    parser.add_argument('--remote-ip', required=True, help='Remote IP address')
    parser.add_argument('--remote-port', type=int, required=True, help='Remote port')
    parser.add_argument('--file', required=True, help='File to send')
    parser.add_argument('--loss-rate', type=float, default=0.0, 
                       help='Packet loss rate (0.0-1.0)')
    parser.add_argument('--corruption-rate', type=float, default=0.0,
                       help='Packet corruption rate (0.0-1.0)')
    parser.add_argument('--min-delay', type=float, default=0.0,
                       help='Minimum delay in seconds')
    parser.add_argument('--max-delay', type=float, default=0.0,
                       help='Maximum delay in seconds')
    
    args = parser.parse_args()
    
    sender = Sender(
        local_ip=args.local_ip,
        local_port=args.local_port,
        remote_ip=args.remote_ip,
        remote_port=args.remote_port,
        file_path=args.file,
        loss_rate=args.loss_rate,
        corruption_rate=args.corruption_rate,
        delay_range=(args.min_delay, args.max_delay)
    )
    
    try:
        print("Starting file transfer...")
        print(f"Network simulation: loss={args.loss_rate}, corruption={args.corruption_rate}")
        
        if not sender.connect():
            print("Failed to establish connection")
            return 1
            
        start_time = time.time()
        
        if sender.send_file():
            end_time = time.time()
            duration = end_time - start_time
            file_size = sender.file_size
            throughput = file_size / duration / 1024  # KB/s
            
            print(f"Transfer completed successfully!")
            print(f"File size: {file_size} bytes")
            print(f"Duration: {duration:.2f} seconds")
            print(f"Throughput: {throughput:.2f} KB/s")
        else:
            print("File transfer failed")
            return 1
            
        if not sender.disconnect():
            print("Warning: Failed to properly close connection")
            
    except KeyboardInterrupt:
        print("\nTransfer interrupted by user")
        sender.disconnect()
        return 1
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
        
    return 0


if __name__ == '__main__':
    sys.exit(main())

