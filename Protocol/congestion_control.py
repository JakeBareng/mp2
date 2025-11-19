
FAST_RECOVERY = 3

class CongestionControl:
    def __init__(self):
        self.cwnd = 1.0               # Congestion Window
        self.ssthresh = 64            # Slow Start Threshold
        self.dup_acks = 0             # Counter for Triple Duplicate ACKs
        self.last_ack_received = -1   # To track duplicates

    def on_ack_received(self, ack_num):
        """
        Updates cwnd based on ACK.
        Returns True if Fast Retransmit is needed (3 dup ACKs).
        """
        # TCP RENO Logic
        if ack_num == self.last_ack_received:
            self.dup_acks += 1
            if self.dup_acks == 3: # Triple Duplicate ACKs -> Fast Retransmit
                self.ssthresh = max(self.cwnd / 2, 2)
                self.cwnd = self.ssthresh + FAST_RECOVERY
                return True 
            elif self.dup_acks > 3:
                self.cwnd += 1  # increase cwnd for each additional dup ACK since it indicates network is still flowing
                return False
        else:
            # New ACK 
            self.dup_acks = 0
            self.last_ack_received = ack_num
            
            # Slow Start vs Congestion Avoidance
            if self.cwnd < self.ssthresh:
                self.cwnd += 1  # Exponential growth
            else:
                self.cwnd += 1.0 / self.cwnd  # Linear growth
        
        return False

    def on_timeout(self):
        """
        Handles Timeout Event.
        Resets cwnd to 1 and updates ssthresh.
        """
        self.ssthresh = max(self.cwnd / 2, 2)
        self.cwnd = 1
        self.dup_acks = 0
    
    def get_window_size(self):
        """Returns the integer window size for the Reliability Layer."""
        return int(self.cwnd)