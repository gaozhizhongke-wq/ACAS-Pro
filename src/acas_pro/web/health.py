"""ACAS Pro Web - Health Checks

Comprehensive health checking for production monitoring.
"""
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

from acas_pro.core.database import DatabaseManager
from acas_pro.core.config import config
from acas_pro.core.logging import get_logger

logger = get_logger(__name__)


class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class HealthCheckResult:
    name: str
    status: HealthStatus
    response_time_ms: float
    message: str = ""
    details: Dict = field(default_factory=dict)


class HealthChecker:
    """Comprehensive health checker for ACAS Pro"""
    
    def __init__(self):
        self.checks: List[callable] = [
            self._check_database,
            self._check_config,
            self._check_disk_space,
            self._check_llm,
        ]
    
    def check_all(self) -> Dict:
        """Run all health checks"""
        start_time = time.time()
        results = []
        
        for check in self.checks:
            try:
                result = check()
                results.append(result)
            except Exception as e:
                logger.error(f"Health check {check.__name__} failed: {e}")
                results.append(HealthCheckResult(
                    name=check.__name__.replace('_check_', ''),
                    status=HealthStatus.UNHEALTHY,
                    response_time_ms=0,
                    message=f"Check failed: {str(e)}"
                ))
        
        total_time = (time.time() - start_time) * 1000
        
        # Determine overall status
        if any(r.status == HealthStatus.UNHEALTHY for r in results):
            overall = HealthStatus.UNHEALTHY
        elif any(r.status == HealthStatus.DEGRADED for r in results):
            overall = HealthStatus.DEGRADED
        else:
            overall = HealthStatus.HEALTHY
        
        return {
            'status': overall.value,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'version': config().version,
            'environment': config().environment,
            'response_time_ms': round(total_time, 2),
            'checks': [
                {
                    'name': r.name,
                    'status': r.status.value,
                    'response_time_ms': r.response_time_ms,
                    'message': r.message,
                    'details': r.details
                }
                for r in results
            ]
        }
    
    def _check_database(self) -> HealthCheckResult:
        """Check database connectivity"""
        start = time.time()
        try:
            db = DatabaseManager()
            # Try a simple query
            result = db.execute_one("SELECT 1 as health_check")
            
            if result and result.get('health_check') == 1:
                return HealthCheckResult(
                    name='database',
                    status=HealthStatus.HEALTHY,
                    response_time_ms=(time.time() - start) * 1000,
                    message='Database connection OK',
                    details={'type': config().database.type}
                )
            else:
                return HealthCheckResult(
                    name='database',
                    status=HealthStatus.UNHEALTHY,
                    response_time_ms=(time.time() - start) * 1000,
                    message='Database query returned unexpected result'
                )
        except Exception as e:
            logger.error(f"Unhandled exception: " + str(e))
            return HealthCheckResult(
                name='database',
                status=HealthStatus.UNHEALTHY,
                response_time_ms=(time.time() - start) * 1000,
                message=f'Database connection failed: {str(e)}'
            )
    
    def _check_config(self) -> HealthCheckResult:
        """Check configuration validity"""
        start = time.time()
        issues = []
        
        # Check critical config values
        if not config().security.secret_key or len(config().security.secret_key) < 32:
            issues.append('SECRET_KEY too short or not set')
        
        if config().environment == 'production':
            if config().security.secret_key in ('acas-pro-secret-key-change-me', 'dev-key-change-in-production'):
                issues.append('Using default SECRET_KEY in production')
        
        if issues:
            return HealthCheckResult(
                name='configuration',
                status=HealthStatus.DEGRADED,
                response_time_ms=(time.time() - start) * 1000,
                message='Configuration issues detected',
                details={'issues': issues}
            )
        
        return HealthCheckResult(
            name='configuration',
            status=HealthStatus.HEALTHY,
            response_time_ms=(time.time() - start) * 1000,
            message='Configuration valid'
        )
    
    def _check_disk_space(self) -> HealthCheckResult:
        """Check available disk space"""
        start = time.time()
        try:
            import shutil
            import os
            
            # Check data directory
            data_dir = config().data_dir or 'data'
            os.makedirs(data_dir, exist_ok=True)
            
            stat = shutil.disk_usage(data_dir)
            free_gb = stat.free / (1024**3)
            total_gb = stat.total / (1024**3)
            used_percent = (stat.used / stat.total) * 100
            
            if free_gb < 1:  # Less than 1GB free
                status = HealthStatus.UNHEALTHY
                message = f'Critical: Only {free_gb:.2f}GB free'
            elif free_gb < 5:  # Less than 5GB free
                status = HealthStatus.DEGRADED
                message = f'Warning: Only {free_gb:.2f}GB free'
            else:
                status = HealthStatus.HEALTHY
                message = f'Disk space OK: {free_gb:.2f}GB free'
            
            return HealthCheckResult(
                name='disk_space',
                status=status,
                response_time_ms=(time.time() - start) * 1000,
                message=message,
                details={
                    'free_gb': round(free_gb, 2),
                    'total_gb': round(total_gb, 2),
                    'used_percent': round(used_percent, 2)
                }
            )
        except Exception as e:
            logger.error(f"Unhandled exception: " + str(e))
            return HealthCheckResult(
                name='disk_space',
                status=HealthStatus.DEGRADED,
                response_time_ms=(time.time() - start) * 1000,
                message=f'Disk check failed: {str(e)}'
            )


    def _check_llm(self) -> HealthCheckResult:
        """Check LLM service availability and configuration"""
        start = time.time()
        try:
            if not config().llm.enabled:
                return HealthCheckResult(
                    name='llm',
                    status=HealthStatus.DEGRADED,
                    response_time_ms=(time.time() - start) * 1000,
                    message='LLM is disabled',
                    details={'enabled': False}
                )
            
            if not config().llm.api_key:
                return HealthCheckResult(
                    name='llm',
                    status=HealthStatus.DEGRADED,  # Changed from UNHEALTHY - missing API key is config issue, not outage
                    response_time_ms=(time.time() - start) * 1000,
                    message='LLM API key not configured',
                    details={'enabled': True, 'api_key_set': False}
                )
            
            # Try to import and test LLM client
            try:
                from acas_pro.llm.llm_client import LLMClient, LLMProvider, LLMConfig as ClientConfig
                
                llm_config = ClientConfig(
                    provider=LLMProvider(config().llm.provider),
                    api_key=config().llm.api_key,
                    model=config().llm.model,
                    base_url=config().llm.base_url
                )
                
                client = LLMClient(llm_config)
                
                # Simple test - just verify client can be instantiated
                # Don't make actual API call in health check to avoid rate limits
                return HealthCheckResult(
                    name='llm',
                    status=HealthStatus.HEALTHY,
                    response_time_ms=(time.time() - start) * 1000,
                    message=f'LLM configured: {config().llm.provider}/{config().llm.model}',
                    details={
                        'enabled': True,
                        'api_key_set': True,
                        'provider': config().llm.provider,
                        'model': config().llm.model
                    }
                )
            except ImportError as e:
                return HealthCheckResult(
                    name='llm',
                    status=HealthStatus.DEGRADED,
                    response_time_ms=(time.time() - start) * 1000,
                    message=f'LLM module not available: {str(e)}',
                    details={'enabled': True, 'module_error': True}
                )
            except Exception as e:
                logger.error(f"Unhandled exception: " + str(e))
                return HealthCheckResult(
                    name='llm',
                    status=HealthStatus.DEGRADED,
                    response_time_ms=(time.time() - start) * 1000,
                    message=f'LLM configuration error: {str(e)}',
                    details={'enabled': True, 'config_error': str(e)}
                )
                
        except Exception as e:
            logger.error(f"Unhandled exception: " + str(e))
            return HealthCheckResult(
                name='llm',
                status=HealthStatus.UNHEALTHY,
                response_time_ms=(time.time() - start) * 1000,
                message=f'LLM check failed: {str(e)}'
            )


# Singleton instance
health_checker = HealthChecker()
