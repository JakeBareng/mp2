class CongestionState:
    SLOW_START = 0
    CONGESTION_AVOIDANCE = 1
    FAST_RECOVERY = 2


class CongestionControl:
    def __init__(self, initial_cwnd: float = 1.0, initial_ssthresh: float = 64.0):
        self.cwnd = initial_cwnd
        self.ssthresh = initial_ssthresh
        self.state = CongestionState.SLOW_START
        
        self.dup_ack_count = 0
        self.last_ack_num = -1
        self.fast_recovery_ack_target = 0
        
    def on_ack_received(self, ack_num: int, is_new_ack: bool = True) -> bool:
        """
        Process ACK and update congestion window.
        Returns True if fast retransmit should be triggered.
        """
        if ack_num == self.last_ack_num:
            self.dup_ack_count += 1
            
            if self.state != CongestionState.FAST_RECOVERY:
                if self.dup_ack_count == 3:
                    return self._enter_fast_recovery(ack_num)
                    
            elif self.state == CongestionState.FAST_RECOVERY:
                self.cwnd += 1.0
                
        else:
            if self.state == CongestionState.FAST_RECOVERY:
                if ack_num >= self.fast_recovery_ack_target:
                    self._exit_fast_recovery()
                else:
                    self.cwnd += 1.0
            else:
                self._normal_ack_processing(ack_num)
                
            self.dup_ack_count = 0
            self.last_ack_num = ack_num
            
        return False
        
    def _enter_fast_recovery(self, ack_num: int) -> bool:
        """Enter fast recovery state"""
        self.ssthresh = max(self.cwnd / 2.0, 2.0)
        self.cwnd = self.ssthresh + 3.0
        self.state = CongestionState.FAST_RECOVERY
        self.fast_recovery_ack_target = ack_num + 1
        return True
        
    def _exit_fast_recovery(self):
        """Exit fast recovery and enter congestion avoidance"""
        self.cwnd = self.ssthresh
        self.state = CongestionState.CONGESTION_AVOIDANCE
        
    def _normal_ack_processing(self, ack_num: int):
        """Process ACK in normal states (slow start or congestion avoidance)"""
        if self.state == CongestionState.SLOW_START:
            self.cwnd += 1.0
            if self.cwnd >= self.ssthresh:
                self.state = CongestionState.CONGESTION_AVOIDANCE
                
        elif self.state == CongestionState.CONGESTION_AVOIDANCE:
            self.cwnd += 1.0 / self.cwnd
            
    def on_timeout(self):
        """Handle timeout event"""
        self.ssthresh = max(self.cwnd / 2.0, 2.0)
        self.cwnd = 1.0
        self.state = CongestionState.SLOW_START
        self.dup_ack_count = 0
        
    def get_window_size(self) -> int:
        """Get current congestion window size as integer"""
        return max(1, int(self.cwnd))
        
    def get_ssthresh(self) -> float:
        """Get slow start threshold"""
        return self.ssthresh
        
    def get_state(self) -> int:
        """Get current congestion control state"""
        return self.state
        
    def is_slow_start(self) -> bool:
        """Check if in slow start phase"""
        return self.state == CongestionState.SLOW_START
        
    def is_congestion_avoidance(self) -> bool:
        """Check if in congestion avoidance phase"""
        return self.state == CongestionState.CONGESTION_AVOIDANCE
        
    def is_fast_recovery(self) -> bool:
        """Check if in fast recovery phase"""
        return self.state == CongestionState.FAST_RECOVERY
        
    def reset(self, initial_cwnd: float = 1.0, initial_ssthresh: float = 64.0):
        """Reset congestion control state"""
        self.cwnd = initial_cwnd
        self.ssthresh = initial_ssthresh
        self.state = CongestionState.SLOW_START
        self.dup_ack_count = 0
        self.last_ack_num = -1
        self.fast_recovery_ack_target = 0