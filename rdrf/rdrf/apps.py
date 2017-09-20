from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)

class RDRFConfig(AppConfig):
    name = 'rdrf'
    
    def ready(self):
        logger.debug("running RDRFConfig.ready ... ")
        import rdrf.backends 

