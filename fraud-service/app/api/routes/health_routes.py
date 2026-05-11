from fastapi import APIRouter

router = APIRouter(tags = ["Infra"])

@router.get("/health")
def healt():
    return {
        "status": "ok",
        "service": "fraud-service"
    }