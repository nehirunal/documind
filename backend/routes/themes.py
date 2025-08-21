from fastapi import APIRouter, Query, Body
from typing import List


from ..themes.memstore import set_items, clear_items

router = APIRouter(prefix="/themes", tags=["themes"])

@router.post("/ingest")
def ingest_today_newsletters(
    items: List[NewsletterItem] = Body(...),
    user_id: str = Query("1")
):
    """
    MCP/Gmail pipeline: bugünün newsletter içeriklerini memory'e yükler.
    """
    set_items(user_id, items)
    return {"ok": True, "count": len(items)}

@router.get("/today", response_model=List[ThemeCard])
def get_today_themes(user_id: str = Query("1")):
    """
    Bugünün Temaları: memory'deki item'lardan kart üretir.
    """
    cards = build_today_cards(user_id)
    return cards
