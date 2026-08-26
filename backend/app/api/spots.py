"""收藏钓点接口（第 3 阶段，按用户隔离）。"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from ..core import db
from ..core.auth import current_user_id
from ..models.spot import FavoriteSpot
from ..schemas.spot import SpotCreate

router = APIRouter(prefix="/spots", tags=["spots"])


@router.post("")
def add_spot(body: SpotCreate, request: Request):
    user_id = current_user_id(request)
    with db.get_session() as s:
        spot = FavoriteSpot(
            user_id=user_id, name=body.name, location=body.location, lat=body.lat, lon=body.lon
        )
        s.add(spot)
        s.commit()
        s.refresh(spot)
        return spot.to_dict()


@router.get("")
def list_spots(request: Request):
    user_id = current_user_id(request)
    with db.get_session() as s:
        return [
            sp.to_dict()
            for sp in s.query(FavoriteSpot)
            .filter(FavoriteSpot.user_id == user_id)
            .order_by(FavoriteSpot.id.desc())
            .all()
        ]


@router.delete("/{spot_id}")
def delete_spot(spot_id: int, request: Request):
    user_id = current_user_id(request)
    with db.get_session() as s:
        sp = s.get(FavoriteSpot, spot_id)
        if not sp or sp.user_id != user_id:
            raise HTTPException(status_code=404, detail="收藏不存在")
        s.delete(sp)
        s.commit()
        return {"deleted": spot_id}
