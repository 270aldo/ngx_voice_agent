"""
Application Lifecycle Manager - Manages startup and shutdown of services.
Ensures proper cleanup of async tasks and resources.
"""

import asyncio
import logging
import signal
import sys
from typing import List, Callable, Any, Optional
from contextlib import asynccontextmanager

from src.utils.async_task_manager import get_task_registry, get_global_task_manager

logger = logging.getLogger(__name__)


class LifecycleManager:
    """
    Manages application lifecycle including:
    - Service initialization
    - Graceful shutdown
    - Signal handling
    - Resource cleanup
    """
    
    def __init__(self):
        """Initialize lifecycle manager."""
        self.services = []
        self.cleanup_callbacks = []
        self._shutdown_event = asyncio.Event()
        self._is_shutting_down = False
        
        # Setup signal handlers
        self._setup_signal_handlers()
        
        logger.info("LifecycleManager initialized")
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating shutdown")
            asyncio.create_task(self.shutdown())
        
        # Handle common termination signals
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Windows doesn't support SIGTERM
        if hasattr(signal, 'SIGTERM'):
            signal.signal(signal.SIGTERM, signal_handler)
    
    def register_service(self, service: Any):
        """
        Register a service for lifecycle management.
        
        Service should have a cleanup() method.
        """
        self.services.append(service)
        logger.debug(f"Registered service: {type(service).__name__}")
    
    def register_cleanup(self, callback: Callable):
        """
        Register a cleanup callback.
        
        Callback should be an async function.
        """
        self.cleanup_callbacks.append(callback)
        logger.debug(f"Registered cleanup callback: {callback.__name__}")
    
    async def wait_for_shutdown(self):
        """Wait for shutdown signal."""
        await self._shutdown_event.wait()
    
    async def shutdown(self, timeout: float = 30.0):
        """
        Perform graceful shutdown.
        
        Args:
            timeout: Maximum time to wait for cleanup
        """
        if self._is_shutting_down:
            logger.warning("Shutdown already in progress")
            return
        
        self._is_shutting_down = True
        logger.info("Starting graceful shutdown")
        
        try:
            # Set shutdown event
            self._shutdown_event.set()
            
            # Create cleanup tasks
            cleanup_tasks = []
            
            # Cleanup services
            for service in self.services:
                if hasattr(service, 'cleanup'):
                    cleanup_tasks.append(
                        asyncio.create_task(service.cleanup())
                    )
            
            # Run cleanup callbacks
            for callback in self.cleanup_callbacks:
                cleanup_tasks.append(
                    asyncio.create_task(callback())
                )
            
            # Shutdown task registry
            registry = get_task_registry()
            cleanup_tasks.append(
                asyncio.create_task(registry.shutdown_all())
            )
            
            # Shutdown global task manager
            global_manager = get_global_task_manager()
            cleanup_tasks.append(
                asyncio.create_task(global_manager.shutdown())
            )
            
            # Wait for all cleanup with timeout
            if cleanup_tasks:
                logger.info(f"Waiting for {len(cleanup_tasks)} cleanup tasks")
                
                done, pending = await asyncio.wait(
                    cleanup_tasks,
                    timeout=timeout,
                    return_when=asyncio.ALL_COMPLETED
                )
                
                if pending:
                    logger.warning(f"{len(pending)} cleanup tasks didn't complete in time")
                    # Cancel pending tasks
                    for task in pending:
                        task.cancel()
            
            logger.info("Graceful shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
        
        finally:
            # Exit the process
            sys.exit(0)


# Global lifecycle manager instance
_lifecycle_manager: Optional[LifecycleManager] = None


def get_lifecycle_manager() -> LifecycleManager:
    """Get or create the global lifecycle manager."""
    global _lifecycle_manager
    if _lifecycle_manager is None:
        _lifecycle_manager = LifecycleManager()
    return _lifecycle_manager


@asynccontextmanager
async def managed_application():
    """
    Context manager for managed application lifecycle.
    
    Usage:
        async with managed_application() as lifecycle:
            # Register services
            lifecycle.register_service(my_service)
            
            # Run application
            await lifecycle.wait_for_shutdown()
    """
    lifecycle = get_lifecycle_manager()
    
    try:
        yield lifecycle
    finally:
        await lifecycle.shutdown()


async def run_with_lifecycle(main_func: Callable, *args, **kwargs):
    """
    Run a main function with lifecycle management.
    
    Args:
        main_func: Async main function to run
        *args: Arguments for main function
        **kwargs: Keyword arguments for main function
    """
    lifecycle = get_lifecycle_manager()
    
    try:
        # Start main function
        main_task = asyncio.create_task(main_func(*args, **kwargs))
        
        # Wait for either main completion or shutdown
        shutdown_task = asyncio.create_task(lifecycle.wait_for_shutdown())
        
        done, pending = await asyncio.wait(
            [main_task, shutdown_task],
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # Cancel pending tasks
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        # Check if main task failed
        for task in done:
            if task == main_task and task.exception():
                raise task.exception()
    
    except Exception as e:
        logger.error(f"Application error: {e}")
        raise
    
    finally:
        await lifecycle.shutdown()


def cleanup_on_exit(func: Callable):
    """
    Decorator to register a cleanup function.
    
    Usage:
        @cleanup_on_exit
        async def cleanup_database():
            await db.close()
    """
    lifecycle = get_lifecycle_manager()
    lifecycle.register_cleanup(func)
    return func