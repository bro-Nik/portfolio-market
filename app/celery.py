import os

from dotenv import load_dotenv
from celery import Celery
from celery.schedules import crontab

load_dotenv()


celery = Celery(
    'portfolio_platform_market',
    broker=os.getenv('CELERY_BROKER_URL', ''),
    backend=os.getenv('CELERY_RESULT_BACKEND', ''),
    include=['app.tasks']
)

# Настройки Celery
celery.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    beat_scheduler='redbeat.RedBeatScheduler',
    beat_max_loop_interval=300,
)
