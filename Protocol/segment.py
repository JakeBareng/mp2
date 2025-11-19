class Segment:
    def __init__(self, src_port, dest_port, seq_num, ack_num, flags, window, data=b''):
        self.src_port = src_port
        self.dest_port = dest_port
        self.seq_num = seq_num
        self.ack_num = ack_num
        self.flags = flags
        self.window = window
        self.checksum = 0 
        self.data = data

    def encode(self):
        # field to bytes
        src_bytes = self.src_port.to_bytes(2, 'big')      # 2 bytes 
        dest_bytes = self.dest_port.to_bytes(2, 'big')    # 2 bytes 
        seq_bytes = self.seq_num.to_bytes(4, 'big')       # 4 bytes 
        ack_bytes = self.ack_num.to_bytes(4, 'big')       # 4 bytes 
        flag_bytes = self.flags.to_bytes(1, 'big')        # 1 byte  
        chk_bytes = self.checksum.to_bytes(2, 'big')      # 2 bytes 
        win_bytes = self.window.to_bytes(2, 'big')        # 2 bytes 
        
        header = (src_bytes + dest_bytes + seq_bytes + ack_bytes + 
                  flag_bytes + chk_bytes + win_bytes)
                  
        return header + self.data

    @classmethod
    def decode(cls, packet_bytes):
        # Header is 17 bytes total
        
        src = int.from_bytes(packet_bytes[0:2], 'big')
        dest = int.from_bytes(packet_bytes[2:4], 'big')
        seq = int.from_bytes(packet_bytes[4:8], 'big')
        ack = int.from_bytes(packet_bytes[8:12], 'big')
        flags = int.from_bytes(packet_bytes[12:13], 'big')
        checksum = int.from_bytes(packet_bytes[13:15], 'big')
        window = int.from_bytes(packet_bytes[15:17], 'big')
        
        data = packet_bytes[17:]
        
        seg = cls(src, dest, seq, ack, flags, window, data)
        seg.checksum = checksum
        return seg