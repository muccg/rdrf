import os
import logging
from lettuce import before, after, world
from selenium import webdriver
from rdrf import steps
from selenium.common.exceptions import NoAlertPresentException

logger = logging.getLogger(__name__)


def get_desired_capabilities(browser):
    return {
        'firefox': webdriver.DesiredCapabilities.FIREFOX,
        'chrome': webdriver.DesiredCapabilities.CHROME,
    }.get(browser, webdriver.DesiredCapabilities.FIREFOX)


def setup_browser():
    desired_capabilities = get_desired_capabilities(os.environ.get('TEST_BROWSER'))

    world.browser = webdriver.Remote(
        desired_capabilities=desired_capabilities,
        command_executor="http://hub:4444/wd/hub"
    )
    world.browser.implicitly_wait(15)
    # world.browser.set_script_timeout(30)


def reset_snapshot_dict():
    world.snapshot_dict = {}
    logger.info("set snapshot_dict to %s" % world.snapshot_dict)


def set_site_url():
    world.site_url = steps.get_site_url(default_url="http://web:8000")
    logger.info("world.site_url = %s" % world.site_url)


@before.all
def before_all():
    logger.info('')
    setup_browser()
    reset_snapshot_dict()
    set_site_url()
    steps.save_minimal_snapshot()


def delete_cookies():
    # delete all cookies so when we browse to a url at the start we have to log in
    world.browser.delete_all_cookies()


@before.each_scenario
def before_each_scenario(scenario):
    logger.info(scenario.name)
    delete_cookies()


@after.each_scenario
def screenshot(scenario):
    world.browser.get_screenshot_as_file(
        "/data/{0}-{1}.png".format(scenario.passed, scenario.name))


@after.each_step
def screenshot_step(step):
    if not step.passed and step.scenario != None:
        step_name = "%s_%s" % (step.scenario.name, step)
        step_name = step_name.replace(" ", "")
        file_name = "/data/False-step-{0}.png".format(step_name)
        world.browser.get_screenshot_as_file(file_name)


@after.each_step
def accept_alerts(step):
    from selenium.webdriver.support import expected_conditions as EC
    try:
        if EC.alert_is_present:
            logger.info("alert is present - accepting !")
            world.browser.switch_to_alert().accept()
        else:
            logger.info("No alert present - nothing to do")
    except NoAlertPresentException:
        pass
