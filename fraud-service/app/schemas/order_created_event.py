from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from uuid import UUID

class OrderCreatedEvent(BaseModel):
    event_id: str = Field(alias = "eventId")
    order_id: UUID = Field(alias = "orderId")
    amount: float 
    created_at: datetime = Field(alias = "createdAt")

    model_config = ConfigDict(
        populate_by_name = True,
        extra = 'ignore' # Ignora campos extras que o .NET pode envia
    )
