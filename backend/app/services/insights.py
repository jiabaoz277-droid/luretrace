"""个性化经验统计（确定性，基于战报历史聚合）。"""
from __future__ import annotations

from sqlalchemy.orm import Session

from ..models.report import RESULT_LABELS, CatchReport

DEFAULT_USER = "default"


def compute(session: Session, user_id: str = DEFAULT_USER) -> dict:
    reports = (
        session.query(CatchReport)
        .filter(CatchReport.user_id == user_id)
        .order_by(CatchReport.id.desc())
        .all()
    )

    result_dist: dict[str, int] = {}
    species_count: dict[str, int] = {}
    for r in reports:
        label = RESULT_LABELS.get(r.result_type, r.result_type)
        result_dist[label] = result_dist.get(label, 0) + 1
        sp = r.species or (r.inferred or {}).get("species")
        if sp:
            species_count[sp] = species_count.get(sp, 0) + 1

    top_species = sorted(species_count.items(), key=lambda x: -x[1])[:3]
    return {
        "total": len(reports),
        "result_dist": result_dist,
        "top_species": [{"species": k, "count": v} for k, v in top_species],
        "recent": [r.to_dict() for r in reports[:3]],
    }
