"""
Base classes for pipeline architecture.
"""

import logging
from abc import ABC, abstractmethod
from typing import List, Optional
import time

from src.services.conversation.conversation_context import ConversationContext
from src.services.conversation.service_registry import ServiceRegistry

logger = logging.getLogger(__name__)


class PipelineStage(ABC):
    """Abstract base class for pipeline stages."""
    
    def __init__(self, name: str, service_registry: ServiceRegistry):
        """
        Initialize pipeline stage.
        
        Args:
            name: Stage name for logging
            service_registry: Service registry for dependencies
        """
        self.name = name
        self.service_registry = service_registry
        self.enabled = True
    
    async def process(self, context: ConversationContext) -> ConversationContext:
        """
        Process the context through this stage.
        
        Args:
            context: Conversation context
            
        Returns:
            Updated context
        """
        if not self.enabled or context.should_skip_remaining():
            return context
        
        start_time = time.time()
        
        try:
            logger.debug(f"Starting pipeline stage: {self.name}")
            context = await self._process(context)
            
            # Record timing
            duration = time.time() - start_time
            context.metadata.add_timing(self.name, duration)
            
            logger.debug(f"Completed pipeline stage: {self.name} ({duration:.2f}s)")
            
        except Exception as e:
            logger.error(f"Error in pipeline stage {self.name}: {e}")
            context.mark_error(f"Pipeline stage {self.name} failed: {str(e)}")
        
        return context
    
    @abstractmethod
    async def _process(self, context: ConversationContext) -> ConversationContext:
        """
        Implement stage-specific processing logic.
        
        Args:
            context: Conversation context
            
        Returns:
            Updated context
        """
        pass
    
    def disable(self):
        """Disable this stage."""
        self.enabled = False
        logger.info(f"Pipeline stage {self.name} disabled")
    
    def enable(self):
        """Enable this stage."""
        self.enabled = True
        logger.info(f"Pipeline stage {self.name} enabled")


class Pipeline:
    """Manages a sequence of pipeline stages."""
    
    def __init__(self, name: str, stages: Optional[List[PipelineStage]] = None):
        """
        Initialize pipeline.
        
        Args:
            name: Pipeline name
            stages: List of pipeline stages
        """
        self.name = name
        self.stages = stages or []
        
        logger.info(f"Pipeline {name} initialized with {len(self.stages)} stages")
    
    def add_stage(self, stage: PipelineStage):
        """Add a stage to the pipeline."""
        self.stages.append(stage)
        logger.debug(f"Added stage {stage.name} to pipeline {self.name}")
    
    def remove_stage(self, stage_name: str):
        """Remove a stage by name."""
        self.stages = [s for s in self.stages if s.name != stage_name]
        logger.debug(f"Removed stage {stage_name} from pipeline {self.name}")
    
    async def process(self, context: ConversationContext) -> ConversationContext:
        """
        Process context through all stages.
        
        Args:
            context: Conversation context
            
        Returns:
            Updated context
        """
        logger.info(f"Starting pipeline: {self.name}")
        start_time = time.time()
        
        for stage in self.stages:
            if context.should_skip_remaining():
                logger.info(f"Skipping remaining stages in pipeline {self.name}")
                break
            
            context = await stage.process(context)
        
        duration = time.time() - start_time
        logger.info(f"Completed pipeline: {self.name} ({duration:.2f}s)")
        
        return context
    
    def get_stage(self, stage_name: str) -> Optional[PipelineStage]:
        """Get a stage by name."""
        for stage in self.stages:
            if stage.name == stage_name:
                return stage
        return None
    
    def list_stages(self) -> List[str]:
        """List all stage names."""
        return [stage.name for stage in self.stages]