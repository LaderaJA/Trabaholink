"""
Health check views for Docker container monitoring
"""
from django.http import JsonResponse
from django.db import connections
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)


def health_check(request):
    """
    Basic health check endpoint for Docker HEALTHCHECK
    Returns 200 if the application is healthy
    """
    return JsonResponse({
        'status': 'healthy',
        'service': 'trabaholink'
    })


def health_check_detailed(request):
    """
    Detailed health check that verifies all dependencies
    Checks database, cache (Redis), and other critical services
    """
    health_status = {
        'status': 'healthy',
        'checks': {}
    }
    
    # Check database connection
    try:
        db_conn = connections['default']
        db_conn.cursor()
        health_status['checks']['database'] = 'healthy'
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_status['checks']['database'] = 'unhealthy'
        health_status['status'] = 'unhealthy'
    
    # Check Redis/Cache connection
    try:
        cache.set('health_check', 'ok', 10)
        cache_value = cache.get('health_check')
        if cache_value == 'ok':
            health_status['checks']['cache'] = 'healthy'
        else:
            health_status['checks']['cache'] = 'unhealthy'
            health_status['status'] = 'unhealthy'
    except Exception as e:
        logger.error(f"Cache health check failed: {e}")
        health_status['checks']['cache'] = 'unhealthy'
        health_status['status'] = 'unhealthy'
    
    # Return appropriate status code
    status_code = 200 if health_status['status'] == 'healthy' else 503
    return JsonResponse(health_status, status=status_code)
