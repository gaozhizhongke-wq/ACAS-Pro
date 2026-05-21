"""Inspect actual enum values and class attributes for test fixes"""
import sys, os
sys.path.insert(0, 'src')

# Check AlertPriority
from acas_pro.alert.notifier import AlertPriority, AlertNotifier, AlertMessage
print("AlertPriority:", list(AlertPriority))
print("AlertNotifier.configure_channel signature:", AlertNotifier.configure_channel.__code__.co_varnames[:5])

# Check PasswordValidator
from acas_pro.core.security import PasswordValidator
result = PasswordValidator.validate("test")
print("PasswordValidator result type:", type(result), result)

# Check AgentEngine
from acas_pro.llm.agent_engine import AgentEngine, AgentTask
import inspect
print("AgentEngine.__init__ params:", inspect.signature(AgentEngine.__init__))
print("AgentTask fields:", [f for f in dir(AgentTask) if not f.startswith('_')])
print("AgentTask is dataclass:", hasattr(AgentTask, '__dataclass_fields__'))
if hasattr(AgentTask, '__dataclass_fields__'):
    print("AgentTask fields:", list(AgentTask.__dataclass_fields__.keys()))

# Check PublishManager
from acas_pro.publisher.publish_manager import PublishManager
print("PublishManager.__init__ params:", inspect.signature(PublishManager.__init__))
print("PublishManager has _db:", hasattr(PublishManager, '_db'))
print("PublishManager has db:", hasattr(PublishManager, 'db'))

# Check VideoMaker
from acas_pro.video.video_maker import VideoMaker
print("VideoMaker has _db:", hasattr(VideoMaker, '_db'))
print("VideoMaker has db:", hasattr(VideoMaker, 'db'))

# Check AnalyticsLogic
from acas_pro.ui.logic.analytics_logic import AnalyticsLogic
print("AnalyticsLogic.calculate_growth_rate:", inspect.signature(AnalyticsLogic.calculate_growth_rate))
print("AnalyticsLogic.calculate_engagement_rate:", inspect.signature(AnalyticsLogic.calculate_engagement_rate))

# Check LLMConfig
from acas_pro.llm.llm_client import LLMConfig
if hasattr(LLMConfig, '__dataclass_fields__'):
    print("LLMConfig fields:", list(LLMConfig.__dataclass_fields__.keys()))
