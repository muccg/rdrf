import os
import logging
from contextlib import contextmanager
from aloe import before, after, around, world
from selenium import webdriver
from . import utils
from django.conf import settings

logger = logging.getLogger(__name__)

TEST_BROWSER = os.environ.get('TEST_BROWSER')
TEST_SELENIUM_HUB = os.environ.get('TEST_SELENIUM_HUB') or 'http://localhost:4444/wd/hub'
TEST_WAIT = int(os.environ.get('TEST_WAIT') or '10')
TEST_APP_URL = os.environ.get('TEST_APP_URL')
TEST_DISABLE_TEARDOWN = bool(os.environ.get('TEST_DISABLE_TEARDOWN')
                             ) if 'TEST_DISABLE_TEARDOWN' in os.environ else False


def get_desired_capabilities(browser):
    return {
        'firefox': webdriver.DesiredCapabilities.FIREFOX,
        'chrome': webdriver.DesiredCapabilities.CHROME,
    }.get(browser, webdriver.DesiredCapabilities.FIREFOX)


@around.all
@contextmanager
def with_browser():
    desired_capabilities = get_desired_capabilities(TEST_BROWSER)

    world.browser = webdriver.Remote(
        desired_capabilities=desired_capabilities,
        command_executor=TEST_SELENIUM_HUB
    )
    world.browser.implicitly_wait(TEST_WAIT)

    yield

    if do_teardown():
        world.browser.quit()

    delattr(world, "browser")


def set_site_url():
    world.site_url = TEST_APP_URL


def do_teardown():
    return not TEST_DISABLE_TEARDOWN


@before.all
def before_all():
    if not os.path.exists(settings.WRITABLE_DIRECTORY):
        os.makedirs(settings.WRITABLE_DIRECTORY)
    set_site_url()
    utils.save_minimal_snapshot()


def delete_cookies():
    # delete all cookies so when we browse to a url at the start we have to log in
    world.browser.delete_all_cookies()


@before.each_example
def before_scenario(scenario, outline, steps):
    delete_cookies()


@after.each_example
def after_scenario(scenario, outline, test_steps):
    passfail = "PASS" if test_steps and all(step.passed for step in test_steps) else "FAIL"
    world.browser.get_screenshot_as_file(os.path.join(
        settings.WRITABLE_DIRECTORY, "{0}-scenario-{1}.png".format(passfail, scenario.name)))
    if do_teardown():
        utils.restore_minimal_snapshot()


@after.each_step
def screenshot_step(step):
    if not step.passed and getattr(step, "scenario", None) is not None:
        step_name = "%s_%s" % (step.scenario.name, step.sentence)
        step_name = step_name.replace(" ", "")
        file_name = os.path.join(
            settings.WRITABLE_DIRECTORY,
            "FAIL-step-{0}.png".format(step_name))
        world.browser.get_screenshot_as_file(file_name)
