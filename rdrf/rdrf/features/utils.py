import logging
import os
import subprocess

from aloe import world


logger = logging.getLogger(__name__)


def utils_path():
    return os.path.dirname(os.path.realpath(__file__))


def exported_data_path():
    return os.path.join(utils_path(), 'exported_data')


def subprocess_logging(command):
    p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    if stdout:
        logger.info(str(stdout))
    if stderr:
        logger.error(str(stderr))
    if p.returncode != 0:
        logger.error("Return code {0}".format(p.returncode))
    return (p.returncode, str(stdout), str(stderr))


def drop_all_mongo():
    logger.info("Dropping all mongo databases")
    cmd = "db.getMongo().getDBNames().forEach(function(i){db.getSiblingDB(i).dropDatabase()})"
    try:
        subprocess_logging(["mongo", "--host", "mongo", "--eval", cmd])
    except subprocess.CalledProcessError:
        logger.exception("Dropping mongo databases failed")


def reset_database_connection():
    from django import db
    db.connection.close()


def have_snapshot(export_name):
    code, out, err = subprocess_logging(["stellar", "list"])
    return (out.find(export_name) != -1)


def remove_snapshot(snapshot_name):
    logger.info(snapshot_name)
    subprocess_logging(["stellar", "remove", snapshot_name])
    subprocess_logging(["rm", "-f", snapshot_name + ".mongo"])


def save_snapshot(snapshot_name):
    logger.info(snapshot_name)
    if have_snapshot(snapshot_name):
        remove_snapshot(snapshot_name)
    subprocess_logging(["stellar", "snapshot", snapshot_name])
    subprocess_logging(["mongodump", "--host", "mongo", "--archive=" + snapshot_name + ".mongo"])


def save_minimal_snapshot():
    # delete everything so we can import clean later
    drop_all_mongo()
    django_flush()
    save_snapshot("minimal")


def restore_minimal_snapshot():
    restore_snapshot("minimal")


def restore_snapshot(snapshot_name):
    logger.info(snapshot_name)
    subprocess_logging(["stellar", "restore", snapshot_name])
    drop_all_mongo()
    subprocess_logging(["mongorestore", "--host", "mongo", "--drop", "--archive=" + snapshot_name + ".mongo"])


def load_export(export_name):
    """
    To save time cache the stellar snapshots ( one per export file )
    Create / reset on first use
    """
    if have_snapshot(export_name):
        restore_snapshot(export_name)
    else:
        django_import(export_name)
        save_snapshot(export_name)

    reset_database_connection()
    show_stats(export_name)


def django_import(export_name):
    django_admin(["import", "{0}/{1}".           format(exported_data_path(), export_name)])


def django_reloadrules():
    django_admin(["reload_rules"])


def django_init_dev():
    django_admin(["init", "DEV"])


def django_flush():
    django_admin(["flush", "--noinput"])


def django_migrate():
    django_admin(["migrate", "--noinput"])


def django_admin(args):
    logger.info(args)
    subprocess_logging(["django-admin.py"] + args)


def show_stats(export_name):
    """
    show some stats after import
    """
    from rdrf.models import Registry
    from registry.patients.models import Patient
    logger.info("Stats after import of export file %s:" % export_name)
    for r in Registry.objects.all():
        logger.info("\tregistry = %s" % r)

    for p in Patient.objects.all():
        logger.info("\t\tPatient %s" % p)


def click(element):
    scrollElementIntoMiddle = "var viewPortHeight = Math.max(document.documentElement.clientHeight, window.innerHeight || 0);" + \
                              "var elementTop  = arguments[0].getBoundingClientRect().top;" + \
                              "window.scrollBy(0, elementTop-(viewPortHeight/2));"
    world.browser.execute_script(scrollElementIntoMiddle, element)
    element.click()


def debug_links():
    for link in world.browser.find_elements_by_xpath('//a'):
        logger.debug('link {0} {1}'.format(link.text, link.get_attribute("href")))
