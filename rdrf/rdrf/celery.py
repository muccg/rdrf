from celery import Celery


app = Celery('rdrf')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()
