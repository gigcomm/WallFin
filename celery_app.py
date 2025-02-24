import os

from celery import Celery
from dotenv import load_dotenv

load_dotenv("tg_bot/.env")


celery_app = Celery(
    "tasks",
    broker=os.getenv("REDIS_URL"),
    backend=os.getenv("REDIS_URL")
)
celery_app.conf.timezone = "UTC"

import tasks.update_price_assets
celery_app.autodiscover_tasks(["tasks"])

celery_app.conf.beat_schedule = {
    'print-every-60-seconds': {
        'task': 'tasks.update_price_assets.test_task',
        'schedule': 60.0,  # Запуск каждые 60 секунд
    },

    'update_assets': {
        'task': 'tasks.update_price_assets.update_price',
        'schedule': 60.0
    }
}