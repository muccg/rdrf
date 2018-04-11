from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class RDRFConfig(AppConfig):
    name = 'rdrf'

    def ready(self):
        logger.info("running RDRFConfig.ready ... ")
        import rdrf.account_handling.backends
        import rdrf.models.definition.models
        # migration wasn't being found - importing here fixed that
        import rdrf.models.verification.models

        # fkrp #431:
        # Write to a sentinel to a known location
        # so that the tasks.py ( running in a seperate process )
        # can detect that the app is ready
        with open("/tmp/webapp_initialised", "w") as f:
            f.write("initialised")
