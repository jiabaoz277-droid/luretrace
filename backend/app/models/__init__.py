"""模型聚合：导入即注册全部表到 Base.metadata。"""
from .plan import Base, Plan
from .profile import Profile
from .report import CatchReport
from .spot import FavoriteSpot

__all__ = ["Base", "Plan", "Profile", "CatchReport", "FavoriteSpot"]
