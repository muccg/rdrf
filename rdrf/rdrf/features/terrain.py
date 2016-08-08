import logging
import subprocess
from django import db
from lettuce import before, after, world
from selenium import webdriver
from rdrf import steps

logger = logging.getLogger(__name__)


class RDRFGui(object):
    def __init__(self, world):
        self.world = world
        self.browser = world.browser

    def login(self, user):
        pass

    def logout(self):
        pass
        
    def select_registry(self, registry_name):
        pass


@before.all
def create_minimal_snapshot():
    logger.info("creating minimal snapshot")
    # some data is in the cdes collection already ?? - following line removes everything!
    subprocess.check_call(["mongo", "--host", "mongo", "/app/lettuce_dropall.js"])
    subprocess.call(["stellar", "remove", "lettuce_snapshot"])
    subprocess.check_call(["stellar", "snapshot", "lettuce_snapshot"])
    subprocess.check_call(["mongodump", "--host", "mongo"])

@before.all
def setup():
    desired_capabilities = webdriver.DesiredCapabilities.FIREFOX

    world.browser = webdriver.Remote(
        desired_capabilities=desired_capabilities,
        command_executor="http://hub:4444/wd/hub"
    )
    world.browser.implicitly_wait(30)
    #world.browser.set_script_timeout(30)
    

@before.all
def set_site_url():
    world.site_url = steps.get_site_url("rdrf", default_url="http://web:8000")
    logger.info("world.site_url = %s" % world.site_url)

@before.each_scenario
def delete_cookies(scenario):
    # delete all cookies so when we browse to a url at the start we have to log in
    world.browser.delete_all_cookies()


@before.each_scenario
def restore_minimal_snapshot(scenario):
    # it is the feature's background that loads the import file
    logger.info("restoring minimal snapshot ...")
    subprocess.check_call(["stellar", "restore", "lettuce_snapshot"])
    subprocess.check_call(["mongorestore", "--host", "mongo"])
    # DB reconnect
    db.connection.close()


#@after.each_scenario
def screenshot(scenario):
    world.browser.get_screenshot_as_file(
        "/data/{0}-{1}.png".format(scenario.passed, scenario.name))


#@after.each_step
def screenshot_step(step):
    step_name = "%s_%s" % (step.scenario, step)
    step_name = step_name.replace(" ", "")
    file_name = "/data/{0}-{1}.png".format(step.passed, step_name)
    logger.debug("screenshot filename = %s" % file_name)
    #world.browser.get_screenshot_as_file(file_name)
    

@after.each_step
def accept_alerts(step):
    from selenium.webdriver.common.alert import Alert
    try:
        Alert(world.browser).accept()
    except:
        pass


@after.each_step
def log_step(step):
    logger.info("successfully completed step %s" % step)
        
