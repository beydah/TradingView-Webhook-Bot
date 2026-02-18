from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional
from app.core.config import settings
from app.services import tradingview_service
from app.core.logging import logger

router = APIRouter()

class WebhookPayload(BaseModel):
    symbol: str
    alert: str
    price: float
    key: str

@router.post("/webhook")
async def webhook(payload: WebhookPayload):
    try:
        # Validate Key
        if payload.key != settings.ALERT_KEY:
            raise HTTPException(status_code=403, detail="Invalid API key")
        
        # Validate Type
        # tradingview_service.validate_type check is simple string check.
        # We can do it here or inside service.
        if not tradingview_service.validate_type(payload.alert):
             raise HTTPException(status_code=400, detail="Invalid alert type")
             
        if payload.price <= 0:
             raise HTTPException(status_code=400, detail="Invalid price")

        # Process
        success = tradingview_service.add_to_queue(payload.symbol, payload.alert, payload.price)
        
        if success:
            # Trigger queue processing (fire and forget for now, or background task)
            # In FastAPI, we can use BackgroundTasks, but `tradingview_service` 
            # has its own thread/logic. 
            # We'll call the trigger function which spawns thread if needed.
            tradingview_service.trigger_queue_processing()
            return {"status": "success", "message": f"{payload.symbol} {payload.alert} added"}
        else:
            raise HTTPException(status_code=500, detail="Failed to add to queue")

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"[webhook] Error: {e}")
        raise HTTPException(status_code=500, detail="Internal error")

@router.get("/health")
async def health():
    return {"status": "ok", "service": "binance-bot-webhook"}
