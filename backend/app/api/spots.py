"""收藏钓点接口（第 3 阶段）。"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..core import db
from ..models.spot import FavoriteSpot
from ..schemas.spot import SpotCreate

router = APIRouter(prefix="/spots", tags=["spots"])


@router.post("")
def add_spot(body: SpotCreate):
    with db.get_session() as s:
        spot = FavoriteSpot(name=body.name, location=body.location)
        s.add(spot)
        s.commit()
        s.refresh(spot)
        return spot.to_dict()


@router.get("")
def list_spots():
    with db.get_session() as s:
        return [
            sp.to_dict()
            for sp in s.query(FavoriteSpot).order_by(FavoriteSpot.id.desc()).all()
        ]


@router.delete("/{spot_id}")
def delete_spot(spot_id: int):
    with db.get_session() as s:
        sp = s.get(FavoriteSpot, spot_id)
        if not sp:
            raise HTTPException(status_code=404, detail="收藏不存在")
        s.delete(sp)
        s.commit()
        return {"deleted": spot_id}
