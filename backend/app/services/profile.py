"""装备偏好存取（FR-06）。"""
from __future__ import annotations

from sqlalchemy.orm import Session

from ..models.profile import Profile
from ..schemas.profile import ProfileData

DEFAULT_USER = "default"


def get_or_create(session: Session, user_id: str = DEFAULT_USER) -> Profile:
    p = session.query(Profile).filter(Profile.user_id == user_id).first()
    if p is None:
        p = Profile(user_id=user_id)
        session.add(p)
        session.commit()
        session.refresh(p)
    return p


def get_profile(session: Session, user_id: str = DEFAULT_USER) -> ProfileData:
    p = get_or_create(session, user_id)
    return ProfileData(**p.to_dict())


def save_profile(session: Session, data: ProfileData, user_id: str = DEFAULT_USER) -> ProfileData:
    p = get_or_create(session, user_id)
    for k, v in data.model_dump().items():
        setattr(p, k, v)
    session.commit()
    session.refresh(p)
    return ProfileData(**p.to_dict())
