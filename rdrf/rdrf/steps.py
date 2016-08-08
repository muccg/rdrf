import logging
import os
import random
import string
from django import db

from lettuce.core import STEP_REGISTRY
from lettuce import step, world
from lettuce_webdriver.webdriver import contains_content, goto
from lettuce_webdriver.util import assert_true, assert_false

from selenium.webdriver.common.alert import Alert
from selenium.common.exceptions import NoAlertPresentException

from rdrf.models import Registry
from registry.groups.models import CustomUser
from registry.patients.models import Patient
import subprocess


logger = logging.getLogger(__name__)


def check_import():
    logger.info("Checking import:")
    from rdrf.models import Registry
    for r in Registry.objects.all():
        logger.info("\tregistry = %s" % r)
        

    
# We started from the step definitions from lettuce_webdriver, but 
# transitioned to our own (for example looking up form controls by label, not id)
# We still use utils from the lettuce_webdriver but importing them registers
# their step definitons and sometimes they are picked up instead of ours.
# Clearing all the lettuce_webdriver step definitions before we register our own.
STEP_REGISTRY.clear()

@step('export "(.*)"')
def load_export(step, export_name):
    logger.info("executing load of export for step %s" % step)
    logger.info("loading export %s" % export_name)
    logger.info("first deleting all mongo dbs!")
    subprocess.check_call(["mongo", "--host", "mongo", "/app/lettuce_dropall.js"])
    subprocess.check_call(["django-admin.py", "import", "/app/rdrf/rdrf/features/exported_data/%s" % export_name])
    check_import()

@step('should see "([^"]+)"$')
def should_see(step, text):
    assert_true(step, contains_content(world.browser, text))


@step('click "(.*)"')
def click_link(step, link_text):
    link = world.browser.find_element_by_partial_link_text(link_text)
    link.click()


@step(u'should see a link to "(.*)"')
def should_see_link_to(step, link_text):
    return world.browser.find_element_by_xpath('//a[contains(., "%s")]' % link_text)


@step(u'should NOT see a link to "(.*)"')
def should_not_see_link_to(step, link_text):
    links = world.browser.find_elements_by_xpath('//a[contains(., "%s")]' % link_text)
    assert_true(step, len(links) == 0)


@step(u'press the "(.*)" button')
def press_button(step, button_text):
    button = world.browser.find_element_by_xpath('//button[contains(., "%s")]' % button_text)
    button.click()


@step(u'press the navigate back button')
def press_button(step):
    button = world.browser.find_element_by_xpath('//a[@class="previous-form"]')
    button.click()


@step(u'press the navigate forward button')
def press_button(step):
    button = world.browser.find_element_by_xpath('//a[@class="next-form"]')
    button.click()


@step('select "(.*)" from "(.*)"')
def select_from_list(step, option, dropdown_label_or_id):
    select_id = dropdown_label_or_id
    if dropdown_label_or_id.startswith('#'):
        select_id = dropdown_label_or_id.lstrip('#')
    else:
        label = world.browser.find_element_by_xpath('//label[contains(., "%s")]' % dropdown_label_or_id)
        select_id = label.get_attribute('for')
    option = world.browser.find_element_by_xpath('//select[@id="%s"]/option[contains(., "%s")]' %
                (select_id, option))
    option.click()


@step('option "(.*)" from "(.*)" should be selected')
def option_should_be_selected(step, option, dropdown_label):
    label = world.browser.find_element_by_xpath('//label[contains(., "%s")]' % dropdown_label)
    option = world.browser.find_element_by_xpath('//select[@id="%s"]/option[contains(., "%s")]' %
                (label.get_attribute('for'), option))
    assert_true(step, option.get_attribute('selected'))


@step('fill in "(.*)" with "(.*)"')
def fill_in_textfield(step, textfield_label, text):
    label = world.browser.find_element_by_xpath('//label[contains(., "%s")]' % textfield_label)
    textfield = world.browser.find_element_by_xpath('//input[@id="%s"]' % label.get_attribute('for'))
    textfield.send_keys(text)


@step('value of "(.*)" should be "(.*)"')
def value_is(step, textfield_label, expected_value):
    label = world.browser.find_element_by_xpath('//label[contains(., "%s")]' % textfield_label)
    textfield = world.browser.find_element_by_xpath('//input[@id="%s"]' % label.get_attribute('for'))
    assert_true(step, textfield.get_attribute('value') == expected_value)


@step('check "(.*)"')
def check_checkbox(step, checkbox_label):
    label = world.browser.find_element_by_xpath('//label[contains(., "%s")]' % checkbox_label)
    checkbox = world.browser.find_element_by_xpath('//input[@id="%s"]' % label.get_attribute('for'))
    if not checkbox.is_selected():
        checkbox.click()


@step('the "(.*)" checkbox should be checked')
def checkbox_should_be_checked(step, checkbox_label):
    label = world.browser.find_element_by_xpath('//label[contains(., "%s")]' % checkbox_label)
    checkbox = world.browser.find_element_by_xpath('//input[@id="%s"]' % label.get_attribute('for'))
    assert_true(step, checkbox.is_selected())


@step('a registry named "(.*)"')
def create_registry(step, name):
    #
    #world.registry = Registry.objects.get(name=name)
    world.registry = name


@step('a user named "(.*)"')
def create_user(step, username):
    #world.user = CustomUser.objects.get(username=username)
    world.user = username

@step('a patient named "(.*)"')
def set_patient(step, name):
    world.patient = name


@step("navigate to the patient's page")
def goto_patient(step):
    select_from_list(step, world.registry, "#registry_options")
    click_link(step, world.patient)


@step('I am on the "(.*)"')
def i_am_on_the(step, page):
    if page == "Patient List":
        return
    assert False, "Invalid page '%s'" % page


@step('the page header should be "(.*)"')
def the_page_header_should_be(step, header):
    header = world.browser.find_element_by_xpath('//h3[contains(., "%s")]' % header)


@step('I am logged in as (.*)')
def login_as_role(step, role):
    # Could map from role to user later if required
    
    world.user = role #?
    logger.debug("about to login as %s registry %s" % (world.user, world.registry))
    go_to_registry(step, world.registry)
    logger.debug("selected registry %s OK" % world.registry)
    login_as_user(step, role, role)
    logger.debug("login_as_user %s OK" % role)


@step('log in as "(.*)" with "(.*)" password')
def login_as_user(step, username, password):
    world.browser.find_element_by_link_text("Log in").click()
    username_field = world.browser.find_element_by_xpath('.//input[@name="username"]')
    username_field.send_keys(username)
    password_field = world.browser.find_element_by_xpath('.//input[@name="password"]')
    password_field.send_keys(password)
    password_field.submit()


@step(u'should be logged in')
def should_be_logged_in(step):
    user_link = world.browser.find_element_by_partial_link_text(world.user)
    user_link.click()
    world.browser.find_element_by_link_text('Logout')


@step('should be on the login page')
def should_be_on_the_login_page(step):
    world.browser.find_element_by_xpath('.//label[text()[contains(.,"Username")]]')
    world.browser.find_element_by_xpath('.//label[text()[contains(.,"Password")]]')
    world.browser.find_element_by_xpath('.//input[@type="submit" and @value="Log in"]')


@step('click the User Dropdown Menu')
def click_user_menu(step):
    click_link(step, world.user)


@step('the progress indicator should be "(.*)"')
def the_page_header_should_be(step, percentage):
    progress_bar = world.browser.find_element_by_xpath('//div[@class="progress"]/div[@class="progress-bar"]')
    assert_true(step, progress_bar.text.strip() == percentage)


@step('I go to "(.*)"')
def our_goto(step, relative_url):
    """
    NB. This allows tests to run in different contexts ( locally, staging.)
    We delegate to the library supplied version of the step with the same pattern after fixing the path
    """
    absolute_url = world.site_url + relative_url
    world.browser.get(absolute_url)


@step('go to the registry "(.*)"')
def go_to_registry(step, name):
    logger.info("**********  in go_to_registry *******")
    world.browser.get(world.site_url)
    logger.info("navigated to %s" % world.site_url)
    world.browser.find_element_by_link_text('Registries on this site').click()
    logger.info("clicked dropdown for registry")
    world.browser.find_element_by_partial_link_text(name).click()
    logger.info("found link text to click")


@step('navigate away then back')
def refresh_page(step):
    current_url = world.browser.current_url
    world.browser.get(world.site_url)
    # TODO For some reason the confirmation dialog about unsaved changes
    # appears after save, although it isn't visible on the screenshots.
    # Accepting the dialog for now to get around it
    try:
        Alert(world.browser).accept()
    except NoAlertPresentException:
        pass
    world.browser.get(current_url)


@step(u'accept the alert')
def accept_alert(step):
    Alert(world.browser).accept()


def get_site_url(app_name, default_url):
    return os.environ.get('RDRF_URL', default_url).rstrip('/')
