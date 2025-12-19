from app.external_api.management.registry import registry
from app.external_api.api_services.base import ExternalApiServiceBase
from .client import CoingeckoClient
from .methods import CoingeckoMethods


@registry.register_service()
class CoingeckoService(ExternalApiServiceBase):
    NAME = 'coingecko'

    def __init__(self):
        self.client = CoingeckoClient(self.name)
        self.methods = CoingeckoMethods(self.client)
