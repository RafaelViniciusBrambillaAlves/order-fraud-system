from fastapi import Request

from app.domain.repositories.order_repository_interface import IOrderRepository

def get_order_repository(request: Request) -> IOrderRepository:
    
    return request.app.state.order_repository