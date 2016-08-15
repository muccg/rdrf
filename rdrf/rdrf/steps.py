import os
import random
import string

from lettuce import step, world
import lettuce_webdriver.webdriver
from lettuce_webdriver.webdriver import contains_content
from lettuce_webdriver.util import assert_false
from lettuce_webdriver.util import assert_true

from rdrf.models import Registry
from registry.groups.models import CustomUser


@step('a user named "(.*)"')
def create_user(step, username):
    world.user = CustomUser.objects.get(username=username)


@step('a registry named "(.*)"')
def create_registry(step, name):
    world.registry = Registry.objects.get(name=name)


@step('I am logged in as (.*)')
def login_as_role(step, role):
    # Could map from role to user later if required
    go_to_registry(step, world.registry.name)
    login_as_user(step, role, role)
    world.user = CustomUser.objects.get(username=role)


@step('I log in as "(.*)" with "(.*)" password')
def login_as_user(step, username, password):
    world.browser.find_element_by_link_text("Log in").click()
    username_field = world.browser.find_element_by_xpath('.//input[@name="username"]')
    username_field.send_keys(username)
    password_field = world.browser.find_element_by_xpath('.//input[@name="password"]')
    password_field.send_keys(password)
    password_field.submit()


@step('I click the User Dropdown Menu')
def click_user_menu(step):
    click_link(step, world.user.get_full_name())


@step('I click "(.*)"')
def click_link(step, link_text):
    link = world.browser.find_element_by_partial_link_text(link_text)
    link.click()


@step('I go to the registry "(.*)"')
def go_to_registry(step, name):
    world.browser.get(world.site_url)
    world.browser.find_element_by_link_text('Registries on this site').click()
    world.browser.find_element_by_link_text(name).click()


@step(u'I should NOT see a link to "(.*)"')
def should_not_see_link_to(step, link_text):
    links = world.browser.find_elements_by_xpath('//a[contains(., "%s")]' % link_text)
    assert_true(step, len(links) == 0)


@step(u'I should see a link to "(.*)"')
def should_see_link_to(step, link_text):
    return world.browser.find_element_by_xpath('//a[contains(., "%s")]' % link_text)


@step(u'I should be logged in')
def i_should_be_logged_in(step):
    user_link = world.browser.find_element_by_partial_link_text(world.user.get_full_name())
    user_link.click()
    world.browser.find_element_by_link_text('Logout')


@step('I should be on the login page')
def eventually(step):
    world.browser.find_element_by_xpath('.//label[text()[contains(.,"Username")]]')
    world.browser.find_element_by_xpath('.//label[text()[contains(.,"Password")]]')
    world.browser.find_element_by_xpath('.//input[@type="submit" and @value="Log in"]')


@step('I should see "(.*)"')
def eventually(step, expectation):
    # number_of_seconds_to_wait = getattr(world, "wait_seconds", 30)
    lettuce_webdriver.webdriver.should_see(step, expectation)  # , number_of_seconds_to_wait)


# Old


@step('I fill in "(.*)" with "(.*)" year')
def fill_in_year_type1(step, field, value):
    year_field = world.browser.find_element_by_xpath('.//input[@id="%s"][@type="year"]' % field)
    year_field.clear()
    year_field.send_keys(value)


@step('I fill in "(.*)" with random text')
def fill_in_year_type2(step, field):
    field = find_field_only(field)
    value = generate_random_str(8)
    field.clear()
    field.send_keys(value)


@step('I log in as "(.*)" with "(.*)" password expects "(.*)"')
def login_as_user_with_expectations(step, username, password, expectation):
    username_field = world.browser.find_element_by_xpath('.//input[@name="username"]')
    username_field.send_keys(username)
    password_field = world.browser.find_element_by_xpath('.//input[@name="password"]')
    password_field.send_keys(password)
    password_field.submit()
    assert contains_content(world.browser, expectation)


@step('I choose "(.*)" radio')
def radio_button(step, field):
    radio = world.browser.find_element_by_xpath('.//input[@id="%s"][@type="radio"]' % field)
    radio.click()


@step('I go to "(.*)"')
def our_goto(step, relative_url):
    """
    NB. This allows tests to run in different contexts ( locally, staging.)
    We delegate to the library supplied version of the step with the same pattern after fixing the path
    """
    absolute_url = world.site_url + relative_url
    lettuce_webdriver.webdriver.goto(step, absolute_url)


def generate_random_str(length):
    s = string.lowercase + string.uppercase
    return ''.join(random.sample(s, length))


def find_field_only(field):
    return find_field_no_value_by_id(field) or find_field_no_value_by_name(field)


def find_field_no_value_by_id(field):
    ele = world.browser.find_elements_by_xpath('.//input[@id="%s"]' % field)
    if not ele:
        return False
    return ele[0]


def find_field_no_value_by_name(field):
    ele = world.browser.find_elements_by_xpath('.//input[@name="%s"]' % field)
    if not ele:
        return False
    return ele[0]


def get_site_url(app_name, default_url):
    return os.environ.get('RDRF_URL', default_url).rstrip('/')
