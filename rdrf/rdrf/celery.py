from celery import Celery


app = Celery('rdrf')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))


@app.task(bind=True)
def run_custom_action(user,
                      custom_action_model,
                      patient_model=None):
    return custom_action_model.execute(user,
                                       patient_model)
