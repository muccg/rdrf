import sys
from datetime import datetime, timedelta
from django.core.management import BaseCommand
from rdrf.models.definition.models import Registry
from rdrf.services.io.notifications.reminders import ReminderProcessor
from rdrf.services.io.notifications.email_notification import process_notification

from registry.groups.models import CustomUser


def send_reminder(user, registry_model, process_func=None):
    if process_func:
        rp = ReminderProcessor(user, registry_model, process_func)
    else:
        rp = ReminderProcessor(user, registry_model)
    sent = rp.process()
    return sent


class Command(BaseCommand):
    help = "Lists users who haven't logged in for a while"

    def add_arguments(self, parser):
        parser.add_argument('-r', "--registry_code",
                            action='store',
                            dest='registry_code',
                            help='Code of registry to check')

        parser.add_argument("-d", "--days",
                            action="store",
                            dest="days",
                            type=int,
                            help="Number of days since last login.")

        parser.add_argument("-a", "--action",
                            action="store",
                            dest="action",
                            choices=['print', 'send-reminders'],
                            default='print',
                            help="Action to perform")

        parser.add_argument("-t", "--test-mode",
                            action="store_true",
                            dest="test_mode",
                            default=False,
                            help="Action to perform")

    def _print(self, msg):
        self.stdout.write(msg + "\n")

    def _error(self, msg):
        self.stderr.write(msg + "\n")

    def _dummy_send(self, reg_code, description=None, template_data={}):
        msg = "dummy send reg_code=%s description=%s template_data=%s" % (reg_code,
                                                                          description,
                                                                          template_data)
        self._print(msg)

    def _get_numdays(self, registry_model):
        metadata = registry_model.metadata
        if "reminders" in metadata:
            reminder_dict = metadata["reminders"]
            last_login_days = reminder_dict.get("last_login_days", 365)
            return last_login_days
        else:
            return 365

    def _get_threshold(self, num_days):
        return datetime.now() - timedelta(days=num_days)

    def handle(self, *args, **options):
        action = options.get("action")
        if action is None:
            self._error("no action?")
            sys.exit(1)

        registry_code = options.get("registry_code")
        if registry_code is None:
            self._error("Registry code required")
            sys.exit(1)

        try:
            registry_model = Registry.objects.get(code=registry_code)
        except Registry.DoesNotExist:
            self._error("Registry does not exist")
            sys.exit(1)

        days = options.get("days", self._get_numdays(registry_model))
        threshold = self._get_threshold(days)

        test_mode = options.get("test_mode", False)

        if action == "print":
            def action_func(user):
                return self._print(user.username)
        elif action == "send-reminders":
            if test_mode:
                def action_func(user):
                    return send_reminder(
                        user,
                        registry_model,
                        self._dummy_send)
            else:
                def action_func(user):
                    return send_reminder(
                        user,
                        registry_model,
                        process_notification)
        else:
            self._error("Unknown action: %s" % action)
            sys.exit(1)

        for user in self._get_users(registry_model):
            if user.last_login is None or user.last_login < threshold:
                try:
                    reminders_sent = action_func(user)
                    if test_mode:
                        if not reminders_sent:
                            self._print("not sent")
                except Exception as ex:
                    self._error("Error performing %s on user %s: %s" % (action,
                                                                        user,
                                                                        ex))

    def _get_users(self, registry_model):
        for user in CustomUser.objects.filter(registry__in=[registry_model],
                                              is_active=True):
            if user.is_patient or user.is_parent:
                yield user
