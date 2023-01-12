# flake8: noqa
# ignoring the linting because of all unused imports which were necessary for missed migrations.

from django.apps import AppConfig


class RDRFConfig(AppConfig):
    name = "rdrf"

    def ready(self):
        # migration wasn't being found - importing here fixed that
        import rdrf.account_handling.backends
        import rdrf.models.definition.models
        import rdrf.models.verification.models
        import rdrf.models.proms.models
        import rdrf.models.definition.review_models
        import rdrf.models.definition.verification_models
        import rdrf.models.task_models
        import dashboards.models
