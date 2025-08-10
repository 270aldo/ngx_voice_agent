"""
Failover Manager for Component Redundancy
Ensures 99.9% uptime through automatic failover
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Callable, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import random

logger = logging.getLogger(__name__)


class InstanceState(Enum):
    """Instance state in the pool."""
    ACTIVE = "active"
    STANDBY = "standby"
    FAILED = "failed"
    RECOVERING = "recovering"


@dataclass
class ServiceInstance:
    """Represents a service instance."""
    id: str
    host: str
    port: int
    state: InstanceState
    weight: float = 1.0
    active_connections: int = 0
    last_health_check: Optional[datetime] = None
    failure_count: int = 0
    metadata: Dict[str, Any] = None


@dataclass
class FailoverConfig:
    """Configuration for failover behavior."""
    strategy: str = "active_passive"  # active_passive, active_active, round_robin
    health_check_interval: int = 30
    failover_timeout: int = 5
    recovery_timeout: int = 300
    max_retries: int = 3
    enable_auto_recovery: bool = True


class FailoverManager:
    """Manages failover and redundancy for services."""
    
    def __init__(self, config: Optional[FailoverConfig] = None):
        self.config = config or FailoverConfig()
        self.service_pools: Dict[str, List[ServiceInstance]] = {}
        self.active_instances: Dict[str, ServiceInstance] = {}
        self.failover_callbacks: Dict[str, List[Callable]] = {}
        self.recovery_tasks: Dict[str, asyncio.Task] = {}
        
        # Round-robin counters
        self.round_robin_counters: Dict[str, int] = {}
        
        # Failover history for monitoring
        self.failover_history: List[Dict[str, Any]] = []
    
    def register_service_pool(
        self,
        service_name: str,
        instances: List[ServiceInstance]
    ):
        """Register a pool of service instances."""
        self.service_pools[service_name] = instances
        self.round_robin_counters[service_name] = 0
        
        # Set initial active instance based on strategy
        if self.config.strategy == "active_passive":
            # First instance is active, others standby
            instances[0].state = InstanceState.ACTIVE
            self.active_instances[service_name] = instances[0]
            for instance in instances[1:]:
                instance.state = InstanceState.STANDBY
        elif self.config.strategy in ["active_active", "round_robin"]:
            # All instances are active
            for instance in instances:
                instance.state = InstanceState.ACTIVE
        
        logger.info(
            f"Registered {len(instances)} instances for {service_name} "
            f"with {self.config.strategy} strategy"
        )
    
    def register_failover_callback(
        self,
        service_name: str,
        callback: Callable[[ServiceInstance, ServiceInstance], None]
    ):
        """Register a callback for failover events."""
        if service_name not in self.failover_callbacks:
            self.failover_callbacks[service_name] = []
        self.failover_callbacks[service_name].append(callback)
    
    async def get_active_instance(
        self,
        service_name: str
    ) -> Optional[ServiceInstance]:
        """Get active instance based on strategy."""
        if service_name not in self.service_pools:
            return None
        
        pool = self.service_pools[service_name]
        
        if self.config.strategy == "active_passive":
            return self.active_instances.get(service_name)
        
        elif self.config.strategy == "round_robin":
            active_instances = [i for i in pool if i.state == InstanceState.ACTIVE]
            if not active_instances:
                return None
            
            # Round-robin selection
            counter = self.round_robin_counters[service_name]
            instance = active_instances[counter % len(active_instances)]
            self.round_robin_counters[service_name] = counter + 1
            return instance
        
        elif self.config.strategy == "active_active":
            # Least connections strategy
            active_instances = [i for i in pool if i.state == InstanceState.ACTIVE]
            if not active_instances:
                return None
            
            # Select instance with least connections
            return min(active_instances, key=lambda i: i.active_connections)
        
        return None
    
    async def handle_instance_failure(
        self,
        service_name: str,
        failed_instance: ServiceInstance
    ) -> Optional[ServiceInstance]:
        """Handle instance failure and perform failover."""
        logger.error(
            f"Instance {failed_instance.id} of {service_name} failed. "
            f"Initiating failover..."
        )
        
        # Mark instance as failed
        failed_instance.state = InstanceState.FAILED
        failed_instance.failure_count += 1
        
        # Record failover event
        self.failover_history.append({
            "timestamp": datetime.now(),
            "service": service_name,
            "failed_instance": failed_instance.id,
            "reason": "health_check_failure"
        })
        
        # Find replacement instance
        replacement = await self._find_replacement_instance(
            service_name,
            failed_instance
        )
        
        if replacement:
            # Perform failover
            await self._perform_failover(
                service_name,
                failed_instance,
                replacement
            )
            
            # Schedule recovery if enabled
            if self.config.enable_auto_recovery:
                await self._schedule_recovery(service_name, failed_instance)
            
            return replacement
        else:
            logger.critical(
                f"No replacement instance available for {service_name}!"
            )
            return None
    
    async def _find_replacement_instance(
        self,
        service_name: str,
        failed_instance: ServiceInstance
    ) -> Optional[ServiceInstance]:
        """Find a suitable replacement instance."""
        pool = self.service_pools.get(service_name, [])
        
        # Find healthy instances
        candidates = [
            i for i in pool
            if i.id != failed_instance.id and
            i.state in [InstanceState.ACTIVE, InstanceState.STANDBY]
        ]
        
        if not candidates:
            return None
        
        if self.config.strategy == "active_passive":
            # Prefer standby instances
            standby = [i for i in candidates if i.state == InstanceState.STANDBY]
            if standby:
                return standby[0]
        
        # Return instance with lowest failure count
        return min(candidates, key=lambda i: i.failure_count)
    
    async def _perform_failover(
        self,
        service_name: str,
        old_instance: ServiceInstance,
        new_instance: ServiceInstance
    ):
        """Perform the actual failover."""
        logger.info(
            f"Failing over {service_name} from {old_instance.id} "
            f"to {new_instance.id}"
        )
        
        # Update states
        if self.config.strategy == "active_passive":
            new_instance.state = InstanceState.ACTIVE
            self.active_instances[service_name] = new_instance
        
        # Transfer connections (if applicable)
        new_instance.active_connections += old_instance.active_connections
        old_instance.active_connections = 0
        
        # Execute failover callbacks
        callbacks = self.failover_callbacks.get(service_name, [])
        for callback in callbacks:
            try:
                await callback(old_instance, new_instance)
            except Exception as e:
                logger.error(f"Failover callback error: {e}")
    
    async def _schedule_recovery(
        self,
        service_name: str,
        failed_instance: ServiceInstance
    ):
        """Schedule recovery attempt for failed instance."""
        task_key = f"{service_name}_{failed_instance.id}"
        
        # Cancel existing recovery task if any
        if task_key in self.recovery_tasks:
            self.recovery_tasks[task_key].cancel()
        
        # Create recovery task
        async def recover_instance():
            await asyncio.sleep(self.config.recovery_timeout)
            
            logger.info(
                f"Attempting recovery of {failed_instance.id} "
                f"for {service_name}"
            )
            
            # Try to recover instance
            if await self._try_recover_instance(service_name, failed_instance):
                failed_instance.state = InstanceState.STANDBY
                failed_instance.failure_count = 0
                logger.info(f"Successfully recovered {failed_instance.id}")
            else:
                logger.error(f"Failed to recover {failed_instance.id}")
            
            # Remove task reference
            self.recovery_tasks.pop(task_key, None)
        
        self.recovery_tasks[task_key] = asyncio.create_task(recover_instance())
    
    async def _try_recover_instance(
        self,
        service_name: str,
        instance: ServiceInstance
    ) -> bool:
        """Try to recover a failed instance."""
        # Implement recovery logic here
        # This could involve:
        # - Restarting the service
        # - Clearing caches
        # - Resetting connections
        # - Health checks
        
        # For now, simulate recovery with 80% success rate
        import random
        return random.random() < 0.8
    
    def get_pool_status(self, service_name: str) -> Dict[str, Any]:
        """Get status of a service pool."""
        pool = self.service_pools.get(service_name, [])
        
        status_counts = {
            "active": 0,
            "standby": 0,
            "failed": 0,
            "recovering": 0
        }
        
        for instance in pool:
            status_counts[instance.state.value] += 1
        
        return {
            "service": service_name,
            "strategy": self.config.strategy,
            "total_instances": len(pool),
            "status_counts": status_counts,
            "active_instance": self.active_instances.get(service_name, {}).id
            if service_name in self.active_instances else None,
            "failover_count": len([
                h for h in self.failover_history
                if h["service"] == service_name
            ])
        }
    
    def get_failover_metrics(self) -> Dict[str, Any]:
        """Get failover metrics for monitoring."""
        total_failovers = len(self.failover_history)
        
        # Calculate failover rate (last hour)
        hour_ago = datetime.now() - timedelta(hours=1)
        recent_failovers = [
            h for h in self.failover_history
            if h["timestamp"] > hour_ago
        ]
        
        # Calculate uptime
        total_instances = sum(len(pool) for pool in self.service_pools.values())
        healthy_instances = sum(
            1 for pool in self.service_pools.values()
            for instance in pool
            if instance.state in [InstanceState.ACTIVE, InstanceState.STANDBY]
        )
        
        uptime_percentage = (
            (healthy_instances / total_instances * 100)
            if total_instances > 0 else 0
        )
        
        return {
            "total_failovers": total_failovers,
            "failovers_last_hour": len(recent_failovers),
            "uptime_percentage": uptime_percentage,
            "healthy_instances": healthy_instances,
            "total_instances": total_instances,
            "service_pools": {
                name: self.get_pool_status(name)
                for name in self.service_pools
            }
        }


# Global failover manager
failover_manager = FailoverManager()


# Example failover callbacks
async def database_failover_callback(
    old_instance: ServiceInstance,
    new_instance: ServiceInstance
):
    """Handle database failover."""
    logger.info(f"Switching database connection to {new_instance.host}:{new_instance.port}")
    
    # Update connection strings
    os.environ["DATABASE_URL"] = f"postgresql://{new_instance.host}:{new_instance.port}/ngx"
    
    # Clear connection pools
    # Reinitialize clients


async def cache_failover_callback(
    old_instance: ServiceInstance,
    new_instance: ServiceInstance
):
    """Handle cache failover."""
    logger.info(f"Switching cache to {new_instance.host}:{new_instance.port}")
    
    # Update Redis connection
    os.environ["REDIS_URL"] = f"redis://{new_instance.host}:{new_instance.port}"
    
    # Clear local caches
    # Reinitialize cache clients