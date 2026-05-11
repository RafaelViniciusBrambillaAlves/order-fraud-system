from enum import IntEnum

class OutboxStatus(IntEnum):
    PENDING = 0
    SENT = 1
    FAILED = 2