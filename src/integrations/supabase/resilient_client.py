"""
Cliente de Supabase con capacidades de resiliencia y reintentos automáticos.
Extiende el cliente estándar con manejo de errores robusto y reintentos.
Incluye soporte para encriptación automática de PII.
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List, Callable, TypeVar, Union, Tuple
import json

from src.integrations.supabase.client import SupabaseClient as BaseSupabaseClient
from src.utils.retry_utils import retry_db, retry_async_operation
from src.utils.cache_utils import local_cache
from src.database.encryption_middleware import EncryptedSupabaseClient, get_encryption_middleware

# Configurar logging
logger = logging.getLogger(__name__)

# Definir tipo genérico para resultados
T = TypeVar('T')

class ResilientSupabaseClient:
    """
    Cliente de Supabase con capacidades de resiliencia.
    Implementa reintentos automáticos y manejo de errores mejorado.
    """
    
    def __init__(self, base_client: Optional[BaseSupabaseClient] = None, enable_encryption: bool = True):
        """
        Inicializar el cliente resiliente.
        
        Args:
            base_client: Cliente base de Supabase (opcional)
            enable_encryption: Si habilitar encriptación automática de PII
        """
        from src.integrations.supabase.client import supabase_client
        self._base_client = base_client or supabase_client
        self._enable_encryption = enable_encryption
        self._encryption_middleware = get_encryption_middleware() if enable_encryption else None
        
        # Crear cliente encriptado si está habilitado
        if self._enable_encryption and self._base_client:
            self._encrypted_client = EncryptedSupabaseClient(self._base_client)
        else:
            self._encrypted_client = None
            
        logger.info(f"Cliente resiliente de Supabase inicializado (encriptación: {enable_encryption})")
    
    async def execute_query(
        self, 
        query_func: Callable[..., Any],
        max_retries: int = 3,
        admin: bool = False,
        use_cache: bool = True,
        cache_table: Optional[str] = None,
        cache_operation: str = "select",
        cache_data: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = None,
        cache_filters: Optional[Dict[str, Any]] = None,
        *args,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Ejecuta una consulta con reintentos automáticos y soporte de caché.
        
        Args:
            query_func: Función de consulta a ejecutar
            max_retries: Número máximo de reintentos
            admin: Si se debe usar el cliente administrativo
            use_cache: Si se debe utilizar la caché local
            cache_table: Nombre de la tabla para la caché
            cache_operation: Tipo de operación (select, insert, update, upsert, delete)
            cache_data: Datos para operaciones de escritura
            cache_filters: Filtros para operaciones de lectura
            *args, **kwargs: Argumentos para la función de consulta
            
        Returns:
            Dict: Resultado de la consulta
            
        Raises:
            Exception: Si la consulta falla después de los reintentos
        """
        async def _execute_query():
            client = self._base_client.get_client(admin=admin)
            
            # Ejecutar la consulta
            result = query_func(client, *args, **kwargs)
            
            # Si el resultado es una promesa o coroutine, esperar su resolución
            if asyncio.iscoroutine(result):
                result = await result
                
            return result
        
        try:
            # Intentar ejecutar la consulta con reintentos
            result = await retry_async_operation(
                _execute_query,
                max_retries=max_retries,
                base_delay=0.5,
                jitter=True,
                exceptions_to_retry=(Exception,),
                retry_condition=self._should_retry_db_error
            )
            
            # Si la operación es de escritura y hay caché, actualizar la caché
            if use_cache and cache_table and cache_operation in ["insert", "update", "upsert", "delete"] and cache_data:
                local_cache.set(cache_table, cache_data, cache_operation)
                
            return result
            
        except Exception as e:
            logger.warning(f"Error al ejecutar consulta en Supabase: {e}. Intentando usar caché local.")
            
            # Si hay un error y se debe usar la caché
            if use_cache and cache_table:
                if cache_operation == "select":
                    # Para operaciones de lectura, intentar obtener de la caché
                    cached_data = local_cache.get(cache_table, filters=cache_filters)
                    logger.info(f"Usando datos de caché local para tabla {cache_table}: {len(cached_data)} registros")
                    return {"data": cached_data}
                elif cache_operation in ["insert", "update", "upsert", "delete"] and cache_data:
                    # Para operaciones de escritura, guardar en la caché y registrar como pendiente
                    cache_result = local_cache.set(cache_table, cache_data, cache_operation)
                    logger.info(f"Operación {cache_operation} guardada en caché local para tabla {cache_table}")
                    return {"data": cache_result.get("data", [])}
            
            # Si no se puede usar la caché, propagar el error
            raise
    
    def _should_retry_db_error(self, exception: Exception) -> bool:
        """
        Determina si un error de base de datos debería provocar un reintento.
        
        Args:
            exception: Excepción capturada
            
        Returns:
            bool: True si se debe reintentar, False en caso contrario
        """
        error_msg = str(exception).lower()
        
        # Errores que deberían provocar reintentos
        retryable_errors = [
            'timeout', 
            'connection', 
            'network', 
            'temporarily unavailable',
            'too many connections', 
            'server is busy',
            'rate limit',
            '429',  # Too Many Requests
            '500',  # Internal Server Error
            '502',  # Bad Gateway
            '503',  # Service Unavailable
            '504'   # Gateway Timeout
        ]
        
        # Errores que NO deberían provocar reintentos
        non_retryable_errors = [
            'not found',
            'permission denied',
            'invalid input',
            'duplicate key',
            'violates foreign key constraint',
            'violates unique constraint',
            '400',  # Bad Request
            '401',  # Unauthorized
            '403',  # Forbidden
            '404',  # Not Found
            '409'   # Conflict
        ]
        
        # Si es un error que no debería provocar reintentos, retornar False
        if any(err in error_msg for err in non_retryable_errors):
            return False
            
        # Si es un error que debería provocar reintentos, retornar True
        if any(err in error_msg for err in retryable_errors):
            return True
            
        # Por defecto, reintentar
        return True
    
    async def select(
        self, 
        table: str, 
        columns: str = "*", 
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        order_by: Optional[str] = None,
        order_direction: str = "asc",
        admin: bool = False,
        max_retries: int = 3,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Seleccionar registros de una tabla con reintentos automáticos.
        
        Args:
            table: Nombre de la tabla
            columns: Columnas a seleccionar
            filters: Filtros a aplicar
            limit: Límite de registros
            order_by: Campo para ordenar
            order_direction: Dirección de ordenamiento (asc/desc)
            admin: Si se debe usar el cliente administrativo
            max_retries: Número máximo de reintentos
            
        Returns:
            List[Dict]: Lista de registros encontrados
        """
        def query_func(client, *args, **kwargs):
            query = client.table(table).select(columns)
            
            # Aplicar filtros
            if filters:
                for field, value in filters.items():
                    query = query.eq(field, value)
            
            # Aplicar ordenamiento
            if order_by:
                query = query.order(order_by, desc=(order_direction.lower() == "desc"))
            
            # Aplicar límite
            if limit:
                query = query.limit(limit)
            
            # Ejecutar consulta
            return query.execute()
        
        result = await self.execute_query(
            query_func,
            max_retries=max_retries,
            admin=admin
        )
        
        # Extraer datos del resultado
        # La respuesta puede ser un objeto con atributo data o un diccionario con clave 'data'
        if hasattr(result, 'data'):
            return result.data
        elif isinstance(result, dict):
            return result.get('data', [])
        else:
            return result
    
    async def insert(
        self, 
        table: str, 
        data: Union[Dict[str, Any], List[Dict[str, Any]]],
        admin: bool = False,
        max_retries: int = 3,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Insertar registros en una tabla con reintentos automáticos.
        
        Args:
            table: Nombre de la tabla
            data: Datos a insertar (diccionario o lista de diccionarios)
            admin: Si se debe usar el cliente administrativo
            max_retries: Número máximo de reintentos
            use_cache: Si se debe utilizar la caché local
            
        Returns:
            Dict: Resultado de la operación
        """
        def query_func(client, *args, **kwargs):
            return client.table(table).insert(data).execute()
        
        result = await self.execute_query(
            query_func,
            max_retries=max_retries,
            admin=admin,
            use_cache=use_cache,
            cache_table=table,
            cache_operation="insert",
            cache_data=data
        )
        
        # Procesar el resultado
        if hasattr(result, 'data'):
            return {"data": result.data}
        elif isinstance(result, dict):
            return result
        else:
            return {"data": result}
    
    async def update(
        self, 
        table: str, 
        data: Dict[str, Any],
        filters: Dict[str, Any],
        admin: bool = False,
        max_retries: int = 3,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Actualizar registros en una tabla con reintentos automáticos.
        
        Args:
            table: Nombre de la tabla
            data: Datos a actualizar
            filters: Filtros para identificar los registros a actualizar
            admin: Si se debe usar el cliente administrativo
            max_retries: Número máximo de reintentos
            use_cache: Si se debe utilizar la caché local
            
        Returns:
            Dict: Resultado de la operación
        """
        def query_func(client, *args, **kwargs):
            query = client.table(table).update(data)
            
            # Aplicar filtros
            for field, value in filters.items():
                query = query.eq(field, value)
            
            return query.execute()
        
        result = await self.execute_query(
            query_func,
            max_retries=max_retries,
            admin=admin
        )
        
        # Procesar el resultado
        if hasattr(result, 'data'):
            return {"data": result.data}
        elif isinstance(result, dict):
            return result
        else:
            return {"data": result}
    
    async def upsert(
        self, 
        table: str, 
        data: Union[Dict[str, Any], List[Dict[str, Any]]],
        admin: bool = False,
        max_retries: int = 3,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Insertar o actualizar registros en una tabla con reintentos automáticos.
        
        Args:
            table: Nombre de la tabla
            data: Datos a insertar o actualizar
            admin: Si se debe usar el cliente administrativo
            max_retries: Número máximo de reintentos
            use_cache: Si se debe utilizar la caché local
            
        Returns:
            Dict: Resultado de la operación
        """
        def query_func(client, *args, **kwargs):
            return client.table(table).upsert(data).execute()
        
        result = await self.execute_query(
            query_func,
            max_retries=max_retries,
            admin=admin,
            use_cache=use_cache,
            cache_table=table,
            cache_operation="upsert",
            cache_data=data
        )
        
        # Procesar el resultado
        if hasattr(result, 'data'):
            return {"data": result.data}
        elif isinstance(result, dict):
            return result
        else:
            return {"data": result}
    
    async def delete(
        self, 
        table: str, 
        filters: Dict[str, Any],
        admin: bool = False,
        max_retries: int = 3,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Eliminar registros de una tabla con reintentos automáticos.
        
        Args:
            table: Nombre de la tabla
            filters: Filtros para identificar los registros a eliminar
            admin: Si se debe usar el cliente administrativo
            max_retries: Número máximo de reintentos
            use_cache: Si se debe utilizar la caché local
            
        Returns:
            Dict: Resultado de la operación
        """
        def query_func(client, *args, **kwargs):
            query = client.table(table).delete()
            
            # Aplicar filtros
            for field, value in filters.items():
                query = query.eq(field, value)
            
            return query.execute()
        
        result = await self.execute_query(
            query_func,
            max_retries=max_retries,
            admin=admin,
            use_cache=use_cache,
            cache_table=table,
            cache_operation="delete",
            cache_data=filters
        )
        
        # Procesar el resultado
        if hasattr(result, 'data'):
            return {"data": result.data}
        elif isinstance(result, dict):
            return result
        else:
            return {"data": result}
    
    async def execute_rpc(
        self, 
        function_name: str, 
        params: Dict[str, Any],
        admin: bool = False,
        max_retries: int = 3,
        use_cache: bool = False
    ) -> Dict[str, Any]:
        """
        Ejecutar una función RPC con reintentos automáticos.
        
        Args:
            function_name: Nombre de la función RPC
            params: Parámetros para la función
            admin: Si se debe usar el cliente administrativo
            max_retries: Número máximo de reintentos
            
        Returns:
            Dict: Resultado de la operación
        """
        def query_func(client, *args, **kwargs):
            return client.rpc(function_name, params).execute()
        
        result = await self.execute_query(
            query_func,
            max_retries=max_retries,
            admin=admin
        )
        
        # Procesar el resultado
        if hasattr(result, 'data'):
            return {"data": result.data}
        elif isinstance(result, dict):
            return result
        else:
            return {"data": result}
    
    def table(self, table_name: str):
        """
        Obtener un objeto de tabla para operaciones encadenadas.
        Provee compatibilidad con el patrón client.table().select().execute()
        
        Args:
            table_name: Nombre de la tabla
            
        Returns:
            TableQueryBuilder o EncryptedTable: Constructor de consultas para la tabla
        """
        if self._enable_encryption and self._encrypted_client:
            # Retornar tabla encriptada
            return self._encrypted_client.table(table_name)
        else:
            # Retornar tabla normal con query builder
            return TableQueryBuilder(self, table_name)
    
    async def check_connection(self, max_retries: int = 3) -> bool:
        """
        Verificar la conexión a Supabase con reintentos automáticos.
        
        Args:
            max_retries: Número máximo de reintentos
            
        Returns:
            bool: True si la conexión es exitosa, False en caso contrario
        """
        try:
            # Intentar realizar una consulta simple para verificar la conexión
            def query_func(client, *args, **kwargs):
                return client.table("conversations").select("*").limit(1).execute()
                
            result = await self.execute_query(
                query_func,
                max_retries=max_retries,
                admin=False
            )
            
            logger.info("Conexión a Supabase exitosa (cliente resiliente)")
            return True
        except Exception as e:
            logger.error(f"Error al verificar la conexión a Supabase (cliente resiliente): {e}")
            return False

class TableQueryBuilder:
    """
    Constructor de consultas para compatibilidad con el patrón table().select().execute()
    """
    
    def __init__(self, client: ResilientSupabaseClient, table_name: str):
        self.client = client
        self.table_name = table_name
        self._query_type = None
        self._query_data = None
        self._columns = "*"
        self._filters = {}
        self._limit_value = None
        self._order_by_field = None
        self._order_desc = False
        
    def select(self, columns: str = "*"):
        """Configurar consulta SELECT"""
        self._query_type = "select"
        self._columns = columns
        return self
        
    def insert(self, data: Union[Dict[str, Any], List[Dict[str, Any]]]):
        """Configurar consulta INSERT"""
        self._query_type = "insert"
        self._query_data = data
        return self
        
    def update(self, data: Dict[str, Any]):
        """Configurar consulta UPDATE"""
        self._query_type = "update"
        self._query_data = data
        return self
        
    def upsert(self, data: Union[Dict[str, Any], List[Dict[str, Any]]]):
        """Configurar consulta UPSERT"""
        self._query_type = "upsert"
        self._query_data = data
        return self
        
    def delete(self):
        """Configurar consulta DELETE"""
        self._query_type = "delete"
        return self
        
    def eq(self, column: str, value: Any):
        """Agregar filtro de igualdad"""
        self._filters[column] = value
        return self
        
    def limit(self, count: int):
        """Limitar número de resultados"""
        self._limit_value = count
        return self
        
    def order(self, column: str, desc: bool = False):
        """Ordenar resultados"""
        self._order_by_field = column
        self._order_desc = desc
        return self
    
    async def execute(self):
        """Ejecutar la consulta construida"""
        if self._query_type == "select":
            result = await self.client.select(
                table=self.table_name,
                columns=self._columns,
                filters=self._filters if self._filters else None,
                limit=self._limit_value,
                order_by=self._order_by_field,
                order_direction="desc" if self._order_desc else "asc"
            )
            return {"data": result}
            
        elif self._query_type == "insert":
            return await self.client.insert(
                table=self.table_name,
                data=self._query_data
            )
            
        elif self._query_type == "update":
            return await self.client.update(
                table=self.table_name,
                data=self._query_data,
                filters=self._filters
            )
            
        elif self._query_type == "upsert":
            return await self.client.upsert(
                table=self.table_name,
                data=self._query_data
            )
            
        elif self._query_type == "delete":
            return await self.client.delete(
                table=self.table_name,
                filters=self._filters
            )
        else:
            raise ValueError(f"Tipo de consulta no válido: {self._query_type}")

# Instancia singleton del cliente resiliente
resilient_supabase_client = ResilientSupabaseClient()

# Función de compatibilidad para importación
def get_resilient_client():
    """Obtener la instancia del cliente resiliente."""
    return resilient_supabase_client
