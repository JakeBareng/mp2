import struct
import hashlib
from typing import Optional


class SegmentFlags:
    SYN = 0x01
    ACK = 0x02
    FIN = 0x04
    RST = 0x08
    PSH = 0x10
    URG = 0x20


class Segment:
    MAX_PAYLOAD_SIZE = 1024
    HEADER_SIZE = 18
    
    def __init__(self, seq_num: int = 0, ack_num: int = 0, flags: int = 0, 
                 window_size: int = 8192, payload: bytes = b''):
        self.seq_num = seq_num
        self.ack_num = ack_num
        self.flags = flags
        self.window_size = window_size
        self.payload = payload
        self.checksum = 0
        
    def calculate_checksum(self) -> int:
        """Calculate MD5 checksum of segment data"""
        data = struct.pack('!IIHH',
                          self.seq_num,
                          self.ack_num,
                          self.flags,
                          self.window_size)
        data += self.payload

        md5_hash = hashlib.md5(data).digest()
        return struct.unpack('!I', md5_hash[:4])[0]

    def serialize(self) -> bytes:
        """Serialize segment to bytes"""
        self.checksum = self.calculate_checksum()

        header = struct.pack('!IIHHIH',
                           self.seq_num,
                           self.ack_num,
                           self.flags,
                           self.window_size,
                           self.checksum,
                           len(self.payload))
        return header + self.payload
        
    @classmethod
    def deserialize(cls, data: bytes) -> Optional['Segment']:
        """Deserialize bytes to segment"""
        if len(data) < cls.HEADER_SIZE:
            return None

        try:
            header = struct.unpack('!IIHHIH', data[:cls.HEADER_SIZE])
            seq_num, ack_num, flags, window_size, received_checksum, payload_len = header

            payload = data[cls.HEADER_SIZE:cls.HEADER_SIZE + payload_len]

            segment = cls(seq_num, ack_num, flags, window_size, payload)
            segment.checksum = received_checksum

            if not segment.verify_checksum():
                return None

            return segment

        except struct.error:
            return None

    def verify_checksum(self) -> bool:
        """Verify segment checksum"""
        stored_checksum = self.checksum
        calculated_checksum = self.calculate_checksum()
        return stored_checksum == calculated_checksum
            
    def is_syn(self) -> bool:
        """Check if SYN flag is set"""
        return bool(self.flags & SegmentFlags.SYN)
        
    def is_ack(self) -> bool:
        """Check if ACK flag is set"""
        return bool(self.flags & SegmentFlags.ACK)
        
    def is_fin(self) -> bool:
        """Check if FIN flag is set"""
        return bool(self.flags & SegmentFlags.FIN)
        
    def is_rst(self) -> bool:
        """Check if RST flag is set"""
        return bool(self.flags & SegmentFlags.RST)
        
    def set_flag(self, flag: int):
        """Set a specific flag"""
        self.flags |= flag
        
    def clear_flag(self, flag: int):
        """Clear a specific flag"""
        self.flags &= ~flag
        
    def __str__(self) -> str:
        flags_str = []
        if self.is_syn(): flags_str.append('SYN')
        if self.is_ack(): flags_str.append('ACK')
        if self.is_fin(): flags_str.append('FIN')
        if self.is_rst(): flags_str.append('RST')
        
        return (f"Segment(seq={self.seq_num}, ack={self.ack_num}, "
                f"flags={','.join(flags_str) or 'NONE'}, "
                f"window={self.window_size}, payload_len={len(self.payload)})")