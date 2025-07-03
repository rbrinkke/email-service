# File: /opt/freeface/email/workers/circuit_breaker.py
# FreeFace Email System - Circuit Breaker
# Circuit breaker pattern for email provider failover

import time

class CircuitBreaker:
    """Circuit breaker for email provider failover"""
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60, recovery_threshold: int = 3):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.recovery_threshold = recovery_threshold
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
        self.success_count = 0
    
    def can_execute(self) -> bool:
        """Check if the circuit breaker allows execution"""
        if self.state == 'CLOSED':
            return True
        elif self.state == 'OPEN':
            if time.time() - self.last_failure_time > self.timeout:
                self.state = 'HALF_OPEN'
                self.success_count = 0
                return True
            return False
        else:  # HALF_OPEN
            return True
    
    def record_success(self):
        """Record successful execution"""
        if self.state == 'HALF_OPEN':
            self.success_count += 1
            if self.success_count >= self.recovery_threshold:
                self.state = 'CLOSED'
                self.failure_count = 0
        elif self.state == 'CLOSED':
            self.failure_count = max(0, self.failure_count - 1)
    
    def record_failure(self):
        """Record failed execution"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = 'OPEN'
