from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from uuid import UUID

class OrderCreatedEvent(BaseModel):
    order_id: UUID = Field(alias = "orderId")
    amount: float 
    description: str
    created_at: datetime = Field(alias = "createdAt")

    model_config = ConfigDict(
        populate_by_name = True,
        extra = 'ignore' # Ignora campos extras que o .NET pode envia
    )
