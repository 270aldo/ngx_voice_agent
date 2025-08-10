"""
Sistema de caché multi-capa para DecisionEngineService.

Implementa un sistema de caché L1 (memoria) y L2 (Redis) para optimizar
el rendimiento del motor de decisiones.
"""

import asyncio
import hashlib
import json
import time
from collections import OrderedDict
from typing import Dict, Any, Optional, Tuple, Union, List
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class LRUCache:
    """Cache LRU (Least Recently Used) en memoria."""
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 300):
        """
        Inicializa el cache LRU.
        
        Args:
            max_size: Tamaño máximo del cache
            ttl_seconds: Tiempo de vida en segundos
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache: OrderedDict[str, Tuple[Any, float]] = OrderedDict()
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        
    def get(self, key: str) -> Optional[Any]:
        """Obtiene un valor del cache."""
        if key in self.cache:
            value, timestamp = self.cache[key]
            
            # Verificar TTL
            if time.time() - timestamp > self.ttl_seconds:
                del self.cache[key]
                self.misses += 1
                return None
            
            # Mover al final (más reciente)
            self.cache.move_to_end(key)
            self.hits += 1
            return value
        
        self.misses += 1
        return None
    
    def set(self, key: str, value: Any) -> None:
        """Establece un valor en el cache."""
        # Si ya existe, actualizarlo
        if key in self.cache:
            self.cache.move_to_end(key)
        else:
            # Si está lleno, eliminar el más antiguo
            if len(self.cache) >= self.max_size:
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
                self.evictions += 1
        
        self.cache[key] = (value, time.time())
    
    def clear(self) -> None:
        """Limpia todo el cache."""
        self.cache.clear()
        self.hits = 0
        self.misses = 0
        self.evictions = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del cache."""
        total_requests = self.hits + self.misses
        hit_rate = self.hits / total_requests if total_requests > 0 else 0
        
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "hit_rate": hit_rate,
            "total_requests": total_requests
        }


class DecisionCacheLayer:
    """
    Sistema de caché multi-capa para el motor de decisiones.
    
    Implementa:
    - L1: Cache en memoria (LRU)
    - L2: Cache Redis (si está disponible)
    """
    
    # Configuración de cache por tipo de dato
    CACHE_CONFIG = {
        "model_params": {
            "ttl": 3600,  # 1 hora
            "layer": "L1+L2",
            "max_size_kb": None
        },
        "decision_trees": {
            "ttl": 300,  # 5 minutos
            "layer": "L1+L2",
            "max_size_kb": 1024  # 1MB máximo
        },
        "predictions": {
            "ttl": 1800,  # 30 minutos
            "layer": "L2",
            "max_size_kb": 512
        },
        "objective_weights": {
            "ttl": 600,  # 10 minutos
            "layer": "L1",
            "max_size_kb": None
        },
        "conversation_stage": {
            "ttl": 120,  # 2 minutos
            "layer": "L1",
            "max_size_kb": None
        },
        "flow_optimization": {
            "ttl": 300,  # 5 minutos
            "layer": "L1+L2",
            "max_size_kb": 2048  # 2MB
        }
    }
    
    def __init__(self, redis_client=None, enable_l2: bool = True):
        """
        Inicializa el sistema de cache.
        
        Args:
            redis_client: Cliente Redis opcional para L2
            enable_l2: Si habilitar cache L2
        """
        # Inicializar caches L1 por tipo
        self.l1_caches = {}
        for cache_type, config in self.CACHE_CONFIG.items():
            if "L1" in config["layer"]:
                self.l1_caches[cache_type] = LRUCache(
                    max_size=100,  # Tamaño por tipo
                    ttl_seconds=config["ttl"]
                )
        
        # Cache L2 (Redis)
        self.redis_client = redis_client if enable_l2 else None
        self.enable_l2 = enable_l2 and redis_client is not None
        
        # Estadísticas
        self.stats = {
            "l1_hits": 0,
            "l2_hits": 0,
            "misses": 0,
            "errors": 0
        }
    
    def generate_cache_key(self, 
                          cache_type: str,
                          conversation_id: str,
                          message_count: int,
                          customer_profile_hash: Optional[str] = None,
                          objectives_hash: Optional[str] = None,
                          **kwargs) -> str:
        """
        Genera una clave de cache determinística.
        
        Args:
            cache_type: Tipo de cache (model_params, decision_trees, etc.)
            conversation_id: ID de la conversación
            message_count: Número de mensajes
            customer_profile_hash: Hash del perfil del cliente
            objectives_hash: Hash de los objetivos
            **kwargs: Parámetros adicionales
            
        Returns:
            Clave de cache
        """
        components = [
            f"ngx:decision:{cache_type}",
            conversation_id,
            f"msgs_{message_count}"
        ]
        
        if customer_profile_hash:
            components.append(f"prof_{customer_profile_hash[:8]}")
        
        if objectives_hash:
            components.append(f"obj_{objectives_hash[:8]}")
        
        # Añadir kwargs adicionales
        for key, value in sorted(kwargs.items()):
            if value is not None:
                components.append(f"{key}_{str(value)[:8]}")
        
        return ":".join(components)
    
    def _compute_hash(self, data: Any) -> str:
        """Calcula hash MD5 de datos."""
        if data is None:
            return "none"
        
        try:
            json_str = json.dumps(data, sort_keys=True, default=str)
            return hashlib.md5(json_str.encode()).hexdigest()
        except Exception:
            return hashlib.md5(str(data).encode()).hexdigest()
    
    async def get(self, cache_type: str, key: str) -> Optional[Any]:
        """
        Obtiene un valor del cache.
        
        Args:
            cache_type: Tipo de cache
            key: Clave de cache
            
        Returns:
            Valor del cache o None
        """
        try:
            config = self.CACHE_CONFIG.get(cache_type, {})
            layer = config.get("layer", "L1")
            
            # Intentar L1 primero
            if "L1" in layer and cache_type in self.l1_caches:
                value = self.l1_caches[cache_type].get(key)
                if value is not None:
                    self.stats["l1_hits"] += 1
                    return value
            
            # Intentar L2 si está habilitado
            if "L2" in layer and self.enable_l2 and self.redis_client:
                try:
                    redis_value = await self._get_from_redis(key)
                    if redis_value is not None:
                        self.stats["l2_hits"] += 1
                        
                        # Promover a L1 si corresponde
                        if "L1" in layer and cache_type in self.l1_caches:
                            self.l1_caches[cache_type].set(key, redis_value)
                        
                        return redis_value
                except Exception as e:
                    logger.warning(f"Error al obtener de Redis: {e}")
                    self.stats["errors"] += 1
            
            self.stats["misses"] += 1
            return None
            
        except Exception as e:
            logger.error(f"Error en cache.get: {e}")
            self.stats["errors"] += 1
            return None
    
    async def set(self, cache_type: str, key: str, value: Any) -> None:
        """
        Establece un valor en el cache.
        
        Args:
            cache_type: Tipo de cache
            key: Clave de cache
            value: Valor a cachear
        """
        try:
            config = self.CACHE_CONFIG.get(cache_type, {})
            layer = config.get("layer", "L1")
            ttl = config.get("ttl", 300)
            max_size_kb = config.get("max_size_kb")
            
            # Verificar tamaño si hay límite
            if max_size_kb:
                size_kb = len(json.dumps(value, default=str)) / 1024
                if size_kb > max_size_kb:
                    logger.warning(f"Valor muy grande para cache ({size_kb:.1f}KB > {max_size_kb}KB)")
                    return
            
            # Guardar en L1
            if "L1" in layer and cache_type in self.l1_caches:
                self.l1_caches[cache_type].set(key, value)
            
            # Guardar en L2
            if "L2" in layer and self.enable_l2 and self.redis_client:
                try:
                    await self._set_to_redis(key, value, ttl)
                except Exception as e:
                    logger.warning(f"Error al guardar en Redis: {e}")
                    self.stats["errors"] += 1
                    
        except Exception as e:
            logger.error(f"Error en cache.set: {e}")
            self.stats["errors"] += 1
    
    async def _get_from_redis(self, key: str) -> Optional[Any]:
        """Obtiene valor de Redis."""
        if not self.redis_client:
            return None
        
        try:
            value = await asyncio.to_thread(self.redis_client.get, key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.debug(f"Error al obtener de Redis: {e}")
            return None
    
    async def _set_to_redis(self, key: str, value: Any, ttl: int) -> None:
        """Guarda valor en Redis."""
        if not self.redis_client:
            return
        
        try:
            json_value = json.dumps(value, default=str)
            await asyncio.to_thread(
                self.redis_client.setex,
                key,
                ttl,
                json_value
            )
        except Exception as e:
            logger.debug(f"Error al guardar en Redis: {e}")
    
    def clear(self, cache_type: Optional[str] = None) -> None:
        """Limpia el cache."""
        if cache_type:
            if cache_type in self.l1_caches:
                self.l1_caches[cache_type].clear()
        else:
            for cache in self.l1_caches.values():
                cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del sistema de cache."""
        total_requests = (self.stats["l1_hits"] + 
                         self.stats["l2_hits"] + 
                         self.stats["misses"])
        
        l1_stats = {}
        for cache_type, cache in self.l1_caches.items():
            l1_stats[cache_type] = cache.get_stats()
        
        return {
            "total_requests": total_requests,
            "l1_hits": self.stats["l1_hits"],
            "l2_hits": self.stats["l2_hits"],
            "misses": self.stats["misses"],
            "errors": self.stats["errors"],
            "hit_rate": (self.stats["l1_hits"] + self.stats["l2_hits"]) / max(1, total_requests),
            "l1_hit_rate": self.stats["l1_hits"] / max(1, total_requests),
            "l2_hit_rate": self.stats["l2_hits"] / max(1, total_requests),
            "l1_caches": l1_stats,
            "l2_enabled": self.enable_l2
        }
    
    async def warmup(self, common_queries: List[Dict[str, Any]]) -> None:
        """
        Pre-calienta el cache con consultas comunes.
        
        Args:
            common_queries: Lista de consultas comunes para pre-cachear
        """
        logger.info(f"Pre-calentando cache con {len(common_queries)} consultas...")
        
        for query in common_queries:
            cache_type = query.get("cache_type")
            key = query.get("key")
            value = query.get("value")
            
            if cache_type and key and value:
                await self.set(cache_type, key, value)
        
        logger.info("Cache pre-calentado completado")