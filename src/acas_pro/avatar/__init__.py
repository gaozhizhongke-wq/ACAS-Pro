"""
AI数字人模块 - 虚拟主播/品牌代言人系统
"""

from .avatar_engine import AvatarEngine, DigitalAvatar, AvatarType, AvatarStyle
from .lip_sync import LipSyncEngine, LipSyncModel
from .gesture_generator import GestureGenerator, GestureType
from .scene_adapter import SceneAdapter, SceneType

__all__ = [
    "AvatarEngine",
    "DigitalAvatar",
    "AvatarType",
    "AvatarStyle",
    "LipSyncEngine",
    "LipSyncModel",
    "GestureGenerator",
    "GestureType",
    "SceneAdapter",
    "SceneType",
]
