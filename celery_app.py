from celery import Celery

celery_app = Celery(
    "tasks",
    broker="redis://localhost:6379/0",  # Или "amqp://guest@localhost//" для RabbitMQ
    backend="redis://localhost:6379/0"
)

@celery_app.task
def test_task():
    return "✅ Celery работает!"
