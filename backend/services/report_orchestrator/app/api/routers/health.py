"""
Health Check Router
健康检查路由
"""

import time
from datetime import datetime

import httpx
from fastapi import APIRouter

router = APIRouter()

# Track startup time
startup_time = time.time()


@router.get("/health-v2", tags=["System V2"])
async def health_check_v2():
    """
    新架构健康检查端点

    Returns:
        Health status of the service and its dependencies
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "report_orchestrator",
        "version": "3.0.0-v2",
        "architecture": "Phase 4 - New Routers",
        "checks": {}
    }

    # Check LLM Gateway
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://llm_gateway:8003/health", timeout=2.0)
            if response.status_code == 200:
                health_status["checks"]["llm_gateway"] = {
                    "status": "healthy",
                    "message": "LLM Gateway is reachable"
                }
            else:
                health_status["checks"]["llm_gateway"] = {
                    "status": "degraded",
                    "message": f"LLM Gateway returned status {response.status_code}"
                }
    except Exception as e:
        health_status["checks"]["llm_gateway"] = {
            "status": "degraded",
            "message": f"LLM Gateway unreachable: {str(e)}"
        }

    # Check Kafka
    try:
        async with httpx.AsyncClient() as client:
            # Kafka UI health check
            response = await client.get("http://kafka-ui:8080/actuator/health", timeout=2.0)
            health_status["checks"]["kafka"] = {
                "status": "healthy" if response.status_code == 200 else "degraded",
                "message": "Kafka available"
            }
    except Exception as e:
        health_status["checks"]["kafka"] = {
            "status": "unknown",
            "message": f"Cannot check Kafka: {str(e)}"
        }

    # System info
    health_status["system"] = {
        "python_version": "3.11",
        "uptime_seconds": int(time.time() - startup_time)
    }

    return health_status
