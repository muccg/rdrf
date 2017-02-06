import logging
import os
import subprocess

from django.conf import settings

from aloe import world


logger = logging.getLogger(__name__)


def utils_path():
    return os.path.dirname(os.path.realpath(__file__))


def exported_data_path():
    return os.path.join(utils_path(), 'exported_data')


def stellar_config_path():
    return os.path.join(utils_path(), 'stellar')


def reset_password_change_date():
    logger.info('')
    from registry.groups.models import CustomUser
    from django.utils import timezone
    CustomUser.objects.update(password_change_date=timezone.now())


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
        subprocess_logging(["mongo", "--host", settings.MONGOSERVER, "--eval", cmd])
    except subprocess.CalledProcessError:
        logger.exception("Dropping mongo databases failed")


def reset_database_connection():
    from django import db
    db.connection.close()


def have_snapshot(export_name):
    code, out, err = stellar_multidb(["stellar", "list"])
    return (out.find(export_name) != -1)


def stellar_multidb(args):
    """ Use stellar across multiple databases
    A hack that searches for stellar configs in multiple dirs to allow for snapshot/restore in a multidb setup
    """
    logger.info(args)
    cwd = os.getcwd()
    rval_code = 0
    rval_out = ''
    rval_err = ''

    for work_dir in [some_dir[0] for some_dir in os.walk(stellar_config_path())]:
        # ignore dirs that don't have a stellar config
        if not os.path.isfile(os.path.join(work_dir, 'stellar.yaml')):
            continue

        # cd and invoke stellar
        os.chdir(work_dir)
        code, out, err = subprocess_logging(args)

        # some calling methods want to parse the output so, lets preserve that
        rval_out += out
        rval_err += err
        if rval_code == 0:
            rval_code = code

    os.chdir(cwd)

    return (rval_code, rval_out, rval_err)


def remove_snapshot(snapshot_name):
    logger.info(snapshot_name)
    stellar_multidb(["stellar", "remove", snapshot_name])


def save_snapshot(snapshot_name):
    logger.info(snapshot_name)
    if have_snapshot(snapshot_name):
        remove_snapshot(snapshot_name)
    stellar_multidb(["stellar", "snapshot", snapshot_name])


def save_minimal_snapshot():
    # delete everything so we can import clean later
    drop_all_mongo()
    django_flush()
    django_flush(['--database', 'clinical'])
    django_migrate()
    django_migrate(['--database', 'clinical'])
    save_snapshot("minimal")


def restore_minimal_snapshot():
    restore_snapshot("minimal")


def restore_snapshot(snapshot_name):
    logger.info(snapshot_name)
    stellar_multidb(["stellar", "restore", snapshot_name])


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
    django_admin(["import", "{0}/{1}".format(exported_data_path(), export_name)], fail_on_error=True)


def django_reloadrules():
    django_admin(["reload_rules"])


def django_init_dev():
    django_admin(["init", "DEV"])


def django_flush(args=[]):
    django_admin(["flush", "--noinput"] + args)


def django_migrate(args=[]):
    django_admin(["migrate", "--noinput"] + args)


def django_admin(args, fail_on_error=False):
    logger.info(args)
    return_code, _, _ = subprocess_logging(["django-admin.py"] + args)

    if fail_on_error and return_code != 0:
        raise Exception("'%s' command failed with error code %d" % (' '.join(["django-admin.py"] + args), return_code))


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
