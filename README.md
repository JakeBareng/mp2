# MP2 - Reliable Transport Protocol Implementation

A Python implementation of a reliable transport protocol built on top of UDP, featuring congestion control, sliding window flow control, and network simulation capabilities.

## Overview

This project implements a custom reliable transport protocol that provides TCP-like reliability over UDP. It includes mechanisms for:

- **Three-way handshake** for connection establishment
- **Sliding window flow control** for efficient data transmission
- **Congestion control** (Slow Start, Congestion Avoidance, Fast Recovery)
- **Network simulation** (packet loss, corruption, and delay)
- **Reliable file transfer** between sender and receiver

## Features

### Protocol Layer
- Custom segment format with checksums (MD5-based)
- Support for TCP-like flags (SYN, ACK, FIN, RST, PSH, URG)
- Cumulative acknowledgments
- Timeout-based and fast retransmission

### Congestion Control
- Slow Start phase with exponential growth
- Congestion Avoidance with additive increase
- Fast Recovery triggered by duplicate ACKs
- Dynamic congestion window adjustment

### Network Simulation
- Configurable packet loss rate
- Configurable bit corruption rate
- Variable network delay (min/max range)
- Simulation disabled during handshake for reliable connection establishment

### Reliability
- Sliding window protocol with configurable window size
- Automatic retransmission on timeout
- Fast retransmit on duplicate ACKs
- In-order delivery guarantee

## Project Structure

```
mp2/
├── Protocol/
│   ├── segment.py              # Segment structure and serialization
│   ├── sender.py               # Sender implementation
│   ├── receiver.py             # Receiver implementation
│   ├── reliability.py          # Reliability layer (sliding window)
│   └── congestion_control.py   # Congestion control algorithms
├── Transport/
│   └── socket_wrapper.py       # UDP socket with network simulation
├── sender_main.py              # Sender application entry point
├── receiver_main.py            # Receiver application entry point
├── create_test_files.py        # Utility to generate test files
├── test_files/                 # Directory for test files
├── captures/                   # Network capture files
└── PROTOCOL_REPORT.md          # Detailed protocol documentation
```

## Installation

### Prerequisites
- Python 3.7 or higher
- Standard Python libraries (no external dependencies required)

### Setup
```bash
git clone https://github.com/JakeBareng/mp2.git
cd mp2
```

## Usage

### Creating Test Files

Generate test files of various sizes:

```bash
python create_test_files.py
```

This creates small (1KB), medium (10KB), and large (100KB) text and binary files in the `test_files/` directory.

### Running the Receiver

Start the receiver to listen for incoming connections:

```bash
python receiver_main.py --local-ip 127.0.0.1 --local-port 9090 --output received_file.txt
```

Options:
- `--local-ip`: IP address to bind to (default: 127.0.0.1)
- `--local-port`: Port to listen on (default: 9090)
- `--output`: Output file path (required)
- `--loss-rate`: Packet loss simulation rate (0.0-1.0)
- `--corruption-rate`: Packet corruption rate (0.0-1.0)
- `--min-delay`: Minimum network delay in seconds
- `--max-delay`: Maximum network delay in seconds

### Running the Sender

Send a file to the receiver:

```bash
python sender_main.py --remote-ip 127.0.0.1 --remote-port 9090 --file test_files/medium.txt
```

Options:
- `--local-ip`: Local IP address (default: 127.0.0.1)
- `--local-port`: Local port (default: 8080)
- `--remote-ip`: Receiver IP address (required)
- `--remote-port`: Receiver port (required)
- `--file`: File to send (required)
- `--loss-rate`: Packet loss simulation rate (0.0-1.0)
- `--corruption-rate`: Packet corruption rate (0.0-1.0)
- `--min-delay`: Minimum network delay in seconds
- `--max-delay`: Maximum network delay in seconds

### Example: File Transfer with Network Simulation

Terminal 1 (Receiver):
```bash
python receiver_main.py --local-port 9090 --output received.txt --loss-rate 0.1
```

Terminal 2 (Sender):
```bash
python sender_main.py --remote-port 9090 --file test_files/large.txt --loss-rate 0.1
```

This simulates 10% packet loss on both sender and receiver sides.

## Protocol Details

### Segment Format

Each segment consists of an 18-byte header followed by the payload:

| Field | Size (bytes) | Description |
|-------|--------------|-------------|
| Sequence Number | 4 | Segment sequence number |
| Acknowledgment Number | 4 | Expected next sequence number |
| Flags | 2 | Control flags (SYN, ACK, FIN, etc.) |
| Window Size | 2 | Available receive window size |
| Checksum | 4 | MD5-based integrity check |
| Payload Length | 2 | Length of payload data |
| Payload | Variable | Data (max 1024 bytes) |

### Connection Establishment (Three-Way Handshake)

1. **SYN**: Sender sends SYN segment with initial sequence number
2. **SYN-ACK**: Receiver responds with SYN-ACK
3. **ACK**: Sender sends final ACK to establish connection

### Data Transfer

- Sender transmits data segments within the congestion window
- Receiver sends cumulative ACKs
- Timeout or duplicate ACKs trigger retransmission
- Congestion control adjusts sending rate dynamically

### Connection Termination

- FIN handshake for graceful connection teardown
- Proper state transitions ensure clean shutdown

## Performance Metrics

The sender displays transfer statistics upon completion:

- **File size**: Total bytes transferred
- **Duration**: Transfer time in seconds
- **Throughput**: Transfer rate in KB/s

## Testing

### Network Condition Scenarios

Test the protocol under various network conditions:

```bash
# No loss (ideal conditions)
--loss-rate 0.0 --corruption-rate 0.0

# Moderate loss
--loss-rate 0.1 --corruption-rate 0.05

# High loss
--loss-rate 0.3 --corruption-rate 0.1

# With network delay
--min-delay 0.01 --max-delay 0.05 --loss-rate 0.1
```

## Configuration

Key configurable parameters in the code:

- **Window Size**: Initial sliding window size (default: 5 for sender, 8 for receiver)
- **Timeout Interval**: Retransmission timeout (default: 1.0 seconds)
- **Max Payload Size**: Maximum segment payload (default: 1024 bytes)
- **Initial CWND**: Initial congestion window (default: 1.0)
- **Initial SSThresh**: Slow start threshold (default: 64.0)

## Limitations

- UDP-based, no connection migration support
- Single file transfer per connection
- No encryption or authentication
- Simplified congestion control (no delayed ACKs, no SACK)

## Future Improvements

- [ ] Selective acknowledgments (SACK)
- [ ] Adaptive timeout calculation (Jacobson/Karels algorithm)
- [ ] Nagle's algorithm for small packet optimization
- [ ] Path MTU discovery
- [ ] Persistent connections for multiple file transfers
- [ ] Flow control based on receiver buffer

## Documentation

See [PROTOCOL_REPORT.md](PROTOCOL_REPORT.md) for detailed protocol specification, implementation details, and analysis.

## License

This project is intended for educational purposes.

## Author

Jake Bareng

## Acknowledgments

This implementation is based on standard TCP/IP protocol concepts and reliable data transfer principles.
