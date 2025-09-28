import os

from celery import Celery
from dotenv import load_dotenv

load_dotenv("tg_bot/.env")

redis_url = f"redis://:{os.getenv('REDIS_PASSWORD')}@{os.getenv('REDIS_HOST')}:{os.getenv('REDIS_PORT')}/0"

celery_app = Celery(
    "tasks",
    broker=redis_url,
    backend=redis_url
)
celery_app.conf.timezone = "UTC"

import tasks.update_price_assets
celery_app.autodiscover_tasks(["tasks"])

celery_app.conf.beat_schedule = {
    'print-every-120-seconds': {
        'task': 'tasks.update_price_assets.test_task',
        'schedule': 120.0,
    },

    'update_assets': {
        'task': 'tasks.update_price_assets.update_price',
        'schedule': 120.0
    },
}