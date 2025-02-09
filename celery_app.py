from celery import Celery


celery_app = Celery(
    "tasks",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0"
)
celery_app.conf.timezone = "UTC"

import tasks.update_price_assets
celery_app.autodiscover_tasks(["tasks"])

celery_app.conf.beat_schedule = {
    'print-every-10-seconds': {
        'task': 'tasks.update_price_assets.test_task',
        'schedule': 60.0,  # Запуск каждые 10 секунд
    },
}