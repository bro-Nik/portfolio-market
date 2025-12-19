from typing import Dict, List, Optional, Type

from app.external_api.api_services.base import ExternalApiServiceBase


class ExternalApiRegistry:
    """Реестр внешних API сервисов"""

    SERVICE_MAPPING: Dict[str, Type[ExternalApiServiceBase]] = {}

    @classmethod
    def register_service(cls):
        """Декоратор для регистрации сервисов"""
        def decorator(service_class: Type[ExternalApiServiceBase]):
            cls.SERVICE_MAPPING[service_class.NAME] = service_class
            return service_class
        return decorator

    @classmethod
    def get_service(cls, service_name: str) -> Optional[ExternalApiServiceBase]:
        """Получает по имени сервиса"""
        service_class = cls.SERVICE_MAPPING.get(service_name)
        if service_class:
            return service_class()

    @classmethod
    def get_service_methods(cls, service_name: str) -> dict:
        """Получает методы по имени сервиса"""
        methods = {}
        service = cls.get_service(service_name)
        if service:
            for name, func in vars(service.methods).items():
                if not name.startswith('_'):
                    methods[name] = func
        return methods


registry = ExternalApiRegistry()
