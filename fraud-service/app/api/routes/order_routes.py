from fastapi import APIRouter, Depends, HTTPException, status


from app.core.dependencies import get_order_repository
from app.infrastructure.database.repositories.mongo_order_repository import MongoOrderRepository


router = APIRouter(
    prefix = "/orders",
    tags = ["Orders"]
)

@router.get("/{order_id}")
async def get_order_analysis(
    order_id: str,
    repository: MongoOrderRepository = Depends(get_order_repository)
):
    order = await repository.get_by_id(order_id)

    if not order:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail = "Order not found"
        )
    
@router.get("/")
async def list_orders(
    repository: MongoOrderRepository = Depends(get_order_repository)
):
    
    return await repository.list_all()
    
