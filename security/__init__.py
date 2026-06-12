# Security Module - ACAS Pro Production Security Layer
# 高智中科（北京）科技有限公司

from .key_manager import KeyManager, get_key_manager, init_security_keys
from .auth_v2 import AuthManager, UserRole, User, Permission, require_auth, require_permission
from .rate_limiter import RateLimiter, RateLimitTier, rate_limit, rate_limit_exempt
from .cert_manager import CertificateManager, init_certificates

def init_security():
    """初始化完整安全体系"""
    # 1. 初始化密钥管理
    init_security_keys()
    
    # 2. 初始化认证系统
    from .auth_v2 import init_auth
    init_auth()
    
    # 3. 初始化限流器
#     get_rate_limiter()
    
    return True

__all__ = [
    'KeyManager', 'get_key_manager', 'init_security_keys',
    'AuthManager', 'UserRole', 'User', 'Permission', 'require_auth', 'require_permission',
    'RateLimiter', 'RateLimitTier', 'rate_limit', 'rate_limit_exempt',
    'CertificateManager', 'init_certificates',
    'init_security'
]