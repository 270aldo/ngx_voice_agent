"""
Health Monitoring and Redundancy System
Ensures 99.9% uptime through active monitoring and failover
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import aiohttp
import psutil
import os

from src.utils.async_task_manager import AsyncTaskManager, get_task_registry

logger = logging.getLogger(__name__)


class ComponentStatus(Enum):
    """Component health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class FailoverStrategy(Enum):
    """Failover strategies for components."""
    ACTIVE_PASSIVE = "active_passive"
    ACTIVE_ACTIVE = "active_active"
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"


@dataclass
class HealthCheck:
    """Health check configuration."""
    name: str
    check_function: Callable
    interval_seconds: int = 30
    timeout_seconds: int = 10
    failure_threshold: int = 3
    recovery_threshold: int = 2
    critical: bool = True


@dataclass
class ComponentHealth:
    """Component health status."""
    name: str
    status: ComponentStatus
    last_check: datetime
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    response_time_ms: Optional[float] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None


class HealthMonitor:
    """Monitors system health and manages failover."""
    
    def __init__(self):
        self.components: Dict[str, ComponentHealth] = {}
        self.health_checks: Dict[str, HealthCheck] = {}
        self.failover_handlers: Dict[str, Callable] = {}
        self.monitoring_active = False
        self._tasks: List[asyncio.Task] = []
        self.task_manager: Optional[AsyncTaskManager] = None
        
        # Initialize async components
        asyncio.create_task(self._initialize_async())
        
        # System metrics thresholds
        self.thresholds = {
            "cpu_percent": 80.0,
            "memory_percent": 85.0,
            "disk_percent": 90.0,
            "response_time_ms": 1000.0
        }
        
        # Initialize default health checks
        self._initialize_default_checks()
    
    async def _initialize_async(self):
        """Async initialization including task manager setup."""
        try:
            # Get task manager from registry
            registry = get_task_registry()
            self.task_manager = await registry.register_service("health_monitor")
            
            logger.info("HealthMonitor async initialization complete")
        except Exception as e:
            logger.error(f"Failed to initialize HealthMonitor async: {e}")
    
    def _initialize_default_checks(self):
        """Initialize default health checks."""
        # Database health check
        self.register_health_check(HealthCheck(
            name="database",
            check_function=self._check_database_health,
            interval_seconds=30,
            critical=True
        ))
        
        # API health check
        self.register_health_check(HealthCheck(
            name="api",
            check_function=self._check_api_health,
            interval_seconds=15,
            critical=True
        ))
        
        # ML services health check
        self.register_health_check(HealthCheck(
            name="ml_services",
            check_function=self._check_ml_services_health,
            interval_seconds=60,
            critical=False
        ))
        
        # Cache health check
        self.register_health_check(HealthCheck(
            name="cache",
            check_function=self._check_cache_health,
            interval_seconds=20,
            critical=False
        ))
        
        # System resources check
        self.register_health_check(HealthCheck(
            name="system_resources",
            check_function=self._check_system_resources,
            interval_seconds=10,
            critical=True
        ))
    
    def register_health_check(self, health_check: HealthCheck):
        """Register a health check."""
        self.health_checks[health_check.name] = health_check
        self.components[health_check.name] = ComponentHealth(
            name=health_check.name,
            status=ComponentStatus.UNKNOWN,
            last_check=datetime.now()
        )
    
    def register_failover_handler(self, component: str, handler: Callable):
        """Register a failover handler for a component."""
        self.failover_handlers[component] = handler
    
    async def start_monitoring(self):
        """Start health monitoring."""
        if self.monitoring_active:
            return
            
        self.monitoring_active = True
        logger.info("Starting health monitoring...")
        
        # Create monitoring tasks
        if self.task_manager:
            for name, check in self.health_checks.items():
                task = await self.task_manager.create_task(
                    self._monitor_component(name, check),
                    name=f"monitor_{name}"
                )
                self._tasks.append(task)
            
            # Start system metrics monitoring
            task = await self.task_manager.create_task(
                self._monitor_system_metrics(),
                name="monitor_system_metrics"
            )
            self._tasks.append(task)
        else:
            # Fallback if task manager not ready
            for name, check in self.health_checks.items():
                task = asyncio.create_task(
                    self._monitor_component(name, check)
                )
                self._tasks.append(task)
            
            # Start system metrics monitoring
            task = asyncio.create_task(self._monitor_system_metrics())
            self._tasks.append(task)
    
    async def stop_monitoring(self):
        """Stop health monitoring."""
        self.monitoring_active = False
        
        # Cancel all tasks
        for task in self._tasks:
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        
        logger.info("Health monitoring stopped")
    
    async def _monitor_component(self, name: str, check: HealthCheck):
        """Monitor a single component."""
        while self.monitoring_active:
            try:
                # Perform health check
                start_time = datetime.now()
                
                try:
                    result = await asyncio.wait_for(
                        check.check_function(),
                        timeout=check.timeout_seconds
                    )
                    
                    response_time = (datetime.now() - start_time).total_seconds() * 1000
                    
                    if result:
                        await self._handle_check_success(name, check, response_time)
                    else:
                        await self._handle_check_failure(name, check, "Check returned False")
                        
                except asyncio.TimeoutError:
                    await self._handle_check_failure(name, check, "Health check timeout")
                except Exception as e:
                    await self._handle_check_failure(name, check, str(e))
                
                # Wait for next check
                await asyncio.sleep(check.interval_seconds)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health monitor for {name}: {e}")
                await asyncio.sleep(check.interval_seconds)
    
    async def _handle_check_success(
        self,
        name: str,
        check: HealthCheck,
        response_time: float
    ):
        """Handle successful health check."""
        component = self.components[name]
        component.consecutive_failures = 0
        component.consecutive_successes += 1
        component.response_time_ms = response_time
        component.error_message = None
        component.last_check = datetime.now()
        
        # Update status based on recovery threshold
        if component.status != ComponentStatus.HEALTHY:
            if component.consecutive_successes >= check.recovery_threshold:
                component.status = ComponentStatus.HEALTHY
                logger.info(f"Component {name} recovered to HEALTHY status")
                
                # Trigger recovery handler if exists
                if f"{name}_recovery" in self.failover_handlers:
                    await self.failover_handlers[f"{name}_recovery"]()
    
    async def _handle_check_failure(
        self,
        name: str,
        check: HealthCheck,
        error_message: str
    ):
        """Handle failed health check."""
        component = self.components[name]
        component.consecutive_failures += 1
        component.consecutive_successes = 0
        component.error_message = error_message
        component.last_check = datetime.now()
        
        # Update status based on failure threshold
        if component.consecutive_failures >= check.failure_threshold:
            if component.status != ComponentStatus.UNHEALTHY:
                component.status = ComponentStatus.UNHEALTHY
                logger.error(f"Component {name} is UNHEALTHY: {error_message}")
                
                # Trigger failover if critical
                if check.critical and name in self.failover_handlers:
                    logger.info(f"Triggering failover for {name}")
                    await self.failover_handlers[name]()
        else:
            component.status = ComponentStatus.DEGRADED
            logger.warning(f"Component {name} is DEGRADED: {error_message}")
    
    async def _monitor_system_metrics(self):
        """Monitor system-wide metrics."""
        while self.monitoring_active:
            try:
                metrics = {
                    "cpu_percent": psutil.cpu_percent(interval=1),
                    "memory_percent": psutil.virtual_memory().percent,
                    "disk_percent": psutil.disk_usage('/').percent,
                    "active_connections": len(psutil.net_connections()),
                    "process_count": len(psutil.pids())
                }
                
                # Check thresholds
                alerts = []
                for metric, value in metrics.items():
                    if metric in self.thresholds and value > self.thresholds[metric]:
                        alerts.append(f"{metric}: {value:.1f}% (threshold: {self.thresholds[metric]}%)")
                
                if alerts:
                    logger.warning(f"System resource alerts: {', '.join(alerts)}")
                
                await asyncio.sleep(10)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error monitoring system metrics: {e}")
                await asyncio.sleep(10)
    
    # Health check implementations
    async def _check_database_health(self) -> bool:
        """Check database health."""
        try:
            from ...integrations.supabase import get_supabase_client
            client = supabase_client
            
            # Simple query to check connection
            response = client.table("conversations").select("id").limit(1).execute()
            return len(response.data) >= 0
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    async def _check_api_health(self) -> bool:
        """Check API health."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "http://localhost:8000/health",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"API health check failed: {e}")
            return False
    
    async def _check_ml_services_health(self) -> bool:
        """Check ML services health."""
        try:
            # Check if models are loaded
            from ...services.objection_prediction_service import ObjectionPredictionService
            service = ObjectionPredictionService()
            
            # Simple prediction to verify service
            result = await service.predict_objection("test message", {})
            return result is not None
        except Exception as e:
            logger.error(f"ML services health check failed: {e}")
            return False
    
    async def _check_cache_health(self) -> bool:
        """Check cache health."""
        try:
            from ...services.cache.decision_cache import DecisionCacheLayer
            cache = DecisionCacheLayer()
            
            # Test cache operations
            test_key = "_health_check_test"
            cache.cache.set(test_key, "test_value")
            value = cache.cache.get(test_key)
            cache.cache.delete(test_key)
            
            return value == "test_value"
        except Exception as e:
            logger.error(f"Cache health check failed: {e}")
            return False
    
    async def _check_system_resources(self) -> bool:
        """Check system resources."""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory_percent = psutil.virtual_memory().percent
            disk_percent = psutil.disk_usage('/').percent
            
            return (
                cpu_percent < self.thresholds["cpu_percent"] and
                memory_percent < self.thresholds["memory_percent"] and
                disk_percent < self.thresholds["disk_percent"]
            )
        except Exception as e:
            logger.error(f"System resources check failed: {e}")
            return False
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get current health status of all components."""
        overall_status = ComponentStatus.HEALTHY
        unhealthy_components = []
        degraded_components = []
        
        for name, component in self.components.items():
            if component.status == ComponentStatus.UNHEALTHY:
                unhealthy_components.append(name)
                if self.health_checks[name].critical:
                    overall_status = ComponentStatus.UNHEALTHY
            elif component.status == ComponentStatus.DEGRADED:
                degraded_components.append(name)
                if overall_status == ComponentStatus.HEALTHY:
                    overall_status = ComponentStatus.DEGRADED
        
        return {
            "overall_status": overall_status.value,
            "components": {
                name: {
                    "status": component.status.value,
                    "last_check": component.last_check.isoformat(),
                    "response_time_ms": component.response_time_ms,
                    "error": component.error_message
                }
                for name, component in self.components.items()
            },
            "unhealthy_components": unhealthy_components,
            "degraded_components": degraded_components,
            "uptime_percentage": self._calculate_uptime()
        }
    
    def _calculate_uptime(self) -> float:
        """Calculate uptime percentage."""
        # Simple calculation based on healthy components
        if not self.components:
            return 100.0
            
        healthy_count = sum(
            1 for c in self.components.values()
            if c.status == ComponentStatus.HEALTHY
        )
        
        return (healthy_count / len(self.components)) * 100
    
    async def cleanup(self):
        """
        Cleanup resources and stop background tasks.
        
        This should be called when shutting down the service.
        """
        logger.info("Cleaning up HealthMonitor")
        
        try:
            # Stop monitoring
            await self.stop_monitoring()
            
            # Unregister from task registry
            if self.task_manager:
                registry = get_task_registry()
                await registry.unregister_service("health_monitor")
                self.task_manager = None
            
            logger.info("HealthMonitor cleanup complete")
            
        except Exception as e:
            logger.error(f"Error during HealthMonitor cleanup: {e}")


# Global health monitor instance
health_monitor = HealthMonitor()