from app.external_api.methods.smart_price_update import SmartPriceUpdater


class CoingeckoMethods:
    def __init__(self, client):
        self.smart_price_update = SmartPriceUpdater(client)
