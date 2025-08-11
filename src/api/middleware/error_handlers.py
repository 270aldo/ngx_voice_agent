"""
Manejadores de errores para la API.

Este módulo proporciona manejadores de errores personalizados para la API,
garantizando que los errores se manejen de manera consistente y segura.
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
import os
import traceback
from typing import Dict, Any, Optional

from src.utils.error_sanitizer import sanitize_error, safe_error_response

# Configurar el logger
logger = logging.getLogger("api.error_handlers")

def get_error_response(
    status_code: int,
    error_code: str,
    message: str,
    details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Genera una respuesta de error estandarizada.
    
    Args:
        status_code: Código de estado HTTP
        error_code: Código de error interno
        message: Mensaje de error
        details: Detalles adicionales del error (opcional)
        
    Returns:
        Dict: Respuesta de error estandarizada
    """
    response = {
        "success": False,
        "error": {
            "code": error_code,
            "message": message
        }
    }
    
    # Añadir detalles solo en entornos no productivos
    if details and os.getenv("ENVIRONMENT", "production").lower() != "production":
        response["error"]["details"] = details
    
    return response

async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """
    Manejador para excepciones HTTP.
    
    Args:
        request: La solicitud HTTP
        exc: La excepción HTTP
        
    Returns:
        JSONResponse: Respuesta JSON con el error
    """
    # Registrar el error
    logger.warning(f"Error HTTP {exc.status_code}: {exc.detail}")
    
    # Mapear códigos de estado comunes a códigos de error internos
    error_codes = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        429: "TOO_MANY_REQUESTS"
    }
    
    error_code = error_codes.get(exc.status_code, "HTTP_ERROR")
    
    return JSONResponse(
        status_code=exc.status_code,
        content=get_error_response(
            status_code=exc.status_code,
            error_code=error_code,
            message=str(exc.detail)
        )
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Manejador para excepciones de validación.
    
    Args:
        request: La solicitud HTTP
        exc: La excepción de validación
        
    Returns:
        JSONResponse: Respuesta JSON con el error
    """
    # Registrar el error
    logger.warning(f"Error de validación: {exc}")
    
    # Extraer errores de validación
    errors = []
    for error in exc.errors():
        error_info = {
            "loc": error.get("loc", []),
            "msg": error.get("msg", ""),
            "type": error.get("type", "")
        }
        errors.append(error_info)
    
    # Crear mensaje de error amigable
    if errors:
        error_message = "Error de validación en los datos de entrada"
        if len(errors) == 1 and errors[0]["loc"]:
            field = ".".join(str(loc) for loc in errors[0]["loc"] if loc != "body")
            error_message = f"Error en el campo '{field}': {errors[0]['msg']}"
    else:
        error_message = "Error de validación en los datos de entrada"
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=get_error_response(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="VALIDATION_ERROR",
            message=error_message,
            details={"errors": errors}
        )
    )

async def internal_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Manejador para excepciones internas con sanitización de errores.
    
    Args:
        request: La solicitud HTTP
        exc: La excepción interna
        
    Returns:
        JSONResponse: Respuesta JSON con el error sanitizado
    """
    # Obtener request_id si está disponible
    request_id = getattr(request.state, "request_id", None)
    
    # Contexto para el error
    context = {
        "method": request.method,
        "path": request.url.path,
        "client": request.client.host if request.client else None
    }
    
    # Sanitizar el error
    sanitized = sanitize_error(exc, request_id, context)
    
    # Obtener stack trace sanitizado para entornos no productivos
    stack_trace = None
    if os.getenv("ENVIRONMENT", "production").lower() != "production":
        from src.utils.error_sanitizer import error_sanitizer
        raw_trace = traceback.format_exception(type(exc), exc, exc.__traceback__)
        stack_trace = error_sanitizer.sanitize_stack_trace("".join(raw_trace))
    
    # Construir respuesta basada en el error sanitizado
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=get_error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=sanitized.error_code,
            message=sanitized.user_message,
            details={
                "request_id": sanitized.request_id,
                "stack_trace": stack_trace
            } if stack_trace else {"request_id": sanitized.request_id}
        )
    )
