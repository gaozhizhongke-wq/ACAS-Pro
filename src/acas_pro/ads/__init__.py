"""
智能广告投放系统
支持巨量引擎、磁力引擎、腾讯广告等平台
"""

from .ad_manager import AdManager, AdPlatform, AdCampaign, AdSet, AdCreative
from .bidding_engine import BiddingEngine, BiddingStrategy
from .audience_targeting import AudienceTargeting, AudienceSegment

__all__ = [
    'AdManager',
    'AdPlatform',
    'AdCampaign',
    'AdSet',
    'AdCreative',
    'BiddingEngine',
    'BiddingStrategy',
    'AudienceTargeting',
    'AudienceSegment',
]
