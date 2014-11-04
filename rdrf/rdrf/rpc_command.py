import logging
logger = logging.getLogger('registry_log')


def create_patient(data):
    logger.debug("creating patient with data %s" % data)
