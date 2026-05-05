from pydantic import BaseModel
from uuid import UUID

class EntityBase(BaseModel):
    id: UUID