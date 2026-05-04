from enum import Enum

class FraudStatus(str, Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"