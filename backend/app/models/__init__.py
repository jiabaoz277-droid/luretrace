"""模型聚合：导入即注册全部表到 Base.metadata。"""
from .plan import Base, Plan
from .conversation import ConversationSession
from .profile import Profile
from .prompt import PromptOverride
from .report import CatchReport
from .spot import FavoriteSpot

__all__ = [
    "Base",
    "Plan",
    "ConversationSession",
    "Profile",
    "PromptOverride",
    "CatchReport",
    "FavoriteSpot",
]
