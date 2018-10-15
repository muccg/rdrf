from django_cron import CronJobBase, Schedule

class PROMSPullJob(CronJobBase):
    RUN_EVERY_MINS = 5 # one day
    MIN_NUM_FAILURES = 3
    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)
    code = 'rdrf.PROMSPullJob'

    def do(self):
        # pull down any proms surveys from any wired up proms system
        from django.core import management
        management.call_command('pull_proms')
