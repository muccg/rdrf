import logging
import subprocess
from django import db
from lettuce import before, after, world
from selenium import webdriver
from rdrf import steps


logger = logging.getLogger(__name__)

@before.all
def import_registry_and_snapshot_db():
    subprocess.call(["django-admin.py", "import", "/app/rdrf/rdrf/features/exported_data/dd_with_data.zip"])
    # Remove snapshot if exists, but just continue if it doesn't
    subprocess.call(["stellar", "remove", "lettuce_snapshot"])
    subprocess.check_call(["stellar", "snapshot", "lettuce_snapshot"])
    subprocess.check_call(["mongodump", "--host", "mongo"])


@before.all
def set_browser():
    desired_capabilities = webdriver.DesiredCapabilities.FIREFOX

    world.browser = webdriver.Remote(
        desired_capabilities=desired_capabilities,
        command_executor="http://hub:4444/wd/hub"
    )
    world.browser.implicitly_wait(5)


@before.all
def set_site_url():
    world.site_url = steps.get_site_url("rdrf", default_url="http://web:8000")



@before.each_scenario
def delete_cookies(scenario):
    # delete all cookies so when we browse to a url at the start we have to log in
    world.browser.delete_all_cookies()


# Should be @before.each_scenario, but that's slower so let's see how this works out
@before.each_feature
def restore_db(scenario):
    subprocess.check_call(["stellar", "restore", "lettuce_snapshot"])
    subprocess.check_call(["mongorestore", "--host", "mongo"])
    # DB reconnect
    db.connection.close()


@after.each_scenario
def screenshot(scenario):
    world.browser.get_screenshot_as_file(
        "/data/{0}-{1}.png".format(scenario.passed, scenario.name))


#@before.each_step
def log(step):
    logger.info('Before Step %s', step)


#@after.each_step
def log(step):
    logger.info('After Step %s', step)
