from celery_app import celery_app

@celery_app.task
def test_task():
    return "✅ Celery работает!"