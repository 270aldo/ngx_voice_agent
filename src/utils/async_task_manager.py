"""
Async Task Manager - Manages lifecycle of background tasks.
Ensures proper cleanup and prevents task leaks.
"""

import asyncio
import logging
import weakref
from typing import Set, Dict, Any, Optional, Callable, Coroutine, List
from dataclasses import dataclass, field
from datetime import datetime
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


@dataclass
class ManagedTask:
    """Represents a managed async task."""
    name: str
    task: asyncio.Task
    created_at: datetime = field(default_factory=datetime.now)
    cancel_on_shutdown: bool = True
    
    @property
    def is_done(self) -> bool:
        """Check if task is done."""
        return self.task.done()
    
    @property
    def is_cancelled(self) -> bool:
        """Check if task was cancelled."""
        return self.task.cancelled()
    
    def get_status(self) -> Dict[str, Any]:
        """Get task status."""
        return {
            "name": self.name,
            "done": self.is_done,
            "cancelled": self.is_cancelled,
            "created_at": self.created_at.isoformat(),
            "running_time": (datetime.now() - self.created_at).total_seconds()
        }


class AsyncTaskManager:
    """
    Manages background async tasks with proper lifecycle management.
    
    Features:
    - Tracks all created tasks
    - Ensures cleanup on shutdown
    - Provides task monitoring
    - Handles task cancellation gracefully
    - Prevents task leaks
    """
    
    def __init__(self, name: str = "default"):
        """
        Initialize task manager.
        
        Args:
            name: Name of this task manager instance
        """
        self.name = name
        self._tasks: Dict[str, ManagedTask] = {}
        self._shutdown = False
        self._cleanup_task: Optional[asyncio.Task] = None
        
        logger.info(f"AsyncTaskManager '{name}' initialized")
    
    async def __aenter__(self):
        """Context manager entry."""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        await self.shutdown()
    
    async def start(self):
        """Start the task manager."""
        if not self._cleanup_task:
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
            logger.info(f"Started task manager '{self.name}'")
    
    async def create_task(
        self,
        coro: Coroutine,
        name: Optional[str] = None,
        cancel_on_shutdown: bool = True
    ) -> asyncio.Task:
        """
        Create and manage an async task.
        
        Args:
            coro: Coroutine to run
            name: Optional task name
            cancel_on_shutdown: Whether to cancel on shutdown
            
        Returns:
            The created task
        """
        if self._shutdown:
            raise RuntimeError("Cannot create tasks after shutdown")
        
        # Generate name if not provided
        if not name:
            name = f"task_{len(self._tasks) + 1}"
        
        # Create the task
        task = asyncio.create_task(coro)
        
        # Wrap in ManagedTask
        managed_task = ManagedTask(
            name=name,
            task=task,
            cancel_on_shutdown=cancel_on_shutdown
        )
        
        # Store reference
        self._tasks[name] = managed_task
        
        # Add done callback for cleanup
        task.add_done_callback(lambda t: self._task_done(name))
        
        logger.debug(f"Created task '{name}' in manager '{self.name}'")
        
        return task
    
    def _task_done(self, task_name: str):
        """Callback when a task is done."""
        task = self._tasks.get(task_name)
        if task:
            try:
                # Log any exceptions
                if task.task.exception():
                    logger.error(
                        f"Task '{task_name}' failed with exception",
                        exc_info=task.task.exception()
                    )
            except asyncio.CancelledError:
                logger.debug(f"Task '{task_name}' was cancelled")
            except Exception:
                pass  # Task might not have finished yet
    
    async def cancel_task(self, name: str, timeout: float = 5.0) -> bool:
        """
        Cancel a specific task.
        
        Args:
            name: Task name
            timeout: Timeout for graceful cancellation
            
        Returns:
            True if cancelled successfully
        """
        managed_task = self._tasks.get(name)
        if not managed_task or managed_task.is_done:
            return False
        
        logger.info(f"Cancelling task '{name}'")
        
        managed_task.task.cancel()
        
        try:
            await asyncio.wait_for(
                asyncio.shield(managed_task.task),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.warning(f"Task '{name}' did not finish within timeout")
        except asyncio.CancelledError:
            logger.debug(f"Task '{name}' cancelled successfully")
        except Exception as e:
            logger.error(f"Error cancelling task '{name}': {e}")
        
        return True
    
    async def wait_for_task(self, name: str, timeout: Optional[float] = None) -> Any:
        """
        Wait for a specific task to complete.
        
        Args:
            name: Task name
            timeout: Optional timeout
            
        Returns:
            Task result
        """
        managed_task = self._tasks.get(name)
        if not managed_task:
            raise ValueError(f"Task '{name}' not found")
        
        if timeout:
            return await asyncio.wait_for(managed_task.task, timeout=timeout)
        else:
            return await managed_task.task
    
    def get_task_status(self, name: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific task."""
        managed_task = self._tasks.get(name)
        return managed_task.get_status() if managed_task else None
    
    def get_all_tasks_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all tasks."""
        return {
            name: task.get_status()
            for name, task in self._tasks.items()
        }
    
    def get_active_tasks(self) -> List[str]:
        """Get list of active (not done) tasks."""
        return [
            name for name, task in self._tasks.items()
            if not task.is_done
        ]
    
    async def _periodic_cleanup(self):
        """Periodically clean up completed tasks."""
        while not self._shutdown:
            try:
                # Wait before cleanup
                await asyncio.sleep(60)  # Clean every minute
                
                # Find completed tasks
                completed = [
                    name for name, task in self._tasks.items()
                    if task.is_done
                ]
                
                # Remove completed tasks
                for name in completed:
                    del self._tasks[name]
                
                if completed:
                    logger.debug(f"Cleaned up {len(completed)} completed tasks")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {e}")
    
    async def shutdown(self, timeout: float = 30.0):
        """
        Shutdown the task manager and cancel all tasks.
        
        Args:
            timeout: Timeout for graceful shutdown
        """
        if self._shutdown:
            return
        
        logger.info(f"Shutting down task manager '{self.name}'")
        self._shutdown = True
        
        # Cancel cleanup task
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Get tasks to cancel
        tasks_to_cancel = [
            (name, task) for name, task in self._tasks.items()
            if not task.is_done and task.cancel_on_shutdown
        ]
        
        if tasks_to_cancel:
            logger.info(f"Cancelling {len(tasks_to_cancel)} tasks")
            
            # Cancel all tasks
            for name, managed_task in tasks_to_cancel:
                managed_task.task.cancel()
            
            # Wait for cancellation with timeout
            tasks = [t.task for _, t in tasks_to_cancel]
            try:
                await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=timeout
                )
                logger.info("All tasks cancelled successfully")
            except asyncio.TimeoutError:
                logger.warning(f"Some tasks did not finish within {timeout}s timeout")
        
        # Clear all tasks
        self._tasks.clear()
        
        logger.info(f"Task manager '{self.name}' shutdown complete")


# Global task manager instance
_global_manager: Optional[AsyncTaskManager] = None


def get_global_task_manager() -> AsyncTaskManager:
    """Get or create the global task manager."""
    global _global_manager
    if _global_manager is None:
        _global_manager = AsyncTaskManager("global")
    return _global_manager


async def create_managed_task(
    coro: Coroutine,
    name: Optional[str] = None,
    manager: Optional[AsyncTaskManager] = None
) -> asyncio.Task:
    """
    Convenience function to create a managed task.
    
    Args:
        coro: Coroutine to run
        name: Optional task name
        manager: Task manager to use (defaults to global)
        
    Returns:
        The created task
    """
    if manager is None:
        manager = get_global_task_manager()
    
    return await manager.create_task(coro, name)


@asynccontextmanager
async def managed_task_group(name: str = "group"):
    """
    Context manager for a group of managed tasks.
    
    Usage:
        async with managed_task_group() as manager:
            await manager.create_task(some_coroutine(), "task1")
            await manager.create_task(another_coroutine(), "task2")
        # All tasks are cancelled on exit
    """
    manager = AsyncTaskManager(name)
    try:
        await manager.start()
        yield manager
    finally:
        await manager.shutdown()


class TaskRegistry:
    """
    Registry for long-running service tasks.
    Useful for services that create background tasks.
    """
    
    def __init__(self):
        self._managers: Dict[str, AsyncTaskManager] = {}
    
    async def register_service(self, service_name: str) -> AsyncTaskManager:
        """Register a service and get its task manager."""
        if service_name not in self._managers:
            manager = AsyncTaskManager(f"service_{service_name}")
            await manager.start()
            self._managers[service_name] = manager
        return self._managers[service_name]
    
    async def unregister_service(self, service_name: str):
        """Unregister a service and cleanup its tasks."""
        manager = self._managers.pop(service_name, None)
        if manager:
            await manager.shutdown()
    
    async def shutdown_all(self):
        """Shutdown all registered services."""
        logger.info("Shutting down all registered services")
        
        shutdown_tasks = [
            manager.shutdown()
            for manager in self._managers.values()
        ]
        
        if shutdown_tasks:
            await asyncio.gather(*shutdown_tasks, return_exceptions=True)
        
        self._managers.clear()
        logger.info("All services shutdown complete")


# Global task registry
_task_registry = TaskRegistry()


def get_task_registry() -> TaskRegistry:
    """Get the global task registry."""
    return _task_registry