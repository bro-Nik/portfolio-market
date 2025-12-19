from app.core.celery import celery
from app.external_api.management.manager import ApiManager


@celery.task(bind=True)
def update_market_data(self, api_service = None, method = None, **kwargs):
    """Универсальная задача для работы с внешними API"""
    if not (api_service and method):
        return {'status': 'error', 'message': 'Отсутствуют переменные api_service или method'}

    # ID задачи из БД
    db_task_id = self.request.headers.get('db_task_id')

    api_manager = ApiManager(api_service)
    result = api_manager.execute(method, db_task_id=db_task_id, **kwargs)

    return result
