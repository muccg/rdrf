import os
import random
import string

from lettuce import *

from selenium import webdriver
import lettuce_webdriver.webdriver
import time


from lettuce_webdriver.webdriver import contains_content


@step('I fill in "(.*)" with "(.*)" year')
def fill_in_year_type(step, field, value):
    year_field = world.browser.find_element_by_xpath('.//input[@id="%s"][@type="year"]' % field)
    year_field.clear()
    year_field.send_keys(value)


@step('I fill in "(.*)" with random text')
def fill_in_year_type(step, field):
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


@step('I log in as "(.*)" with "(.*)" password')
def login_as_user(step, username, password):
    time.sleep(15)
    username_field = world.browser.find_element_by_xpath('.//input[@name="username"]')
    username_field.send_keys(username)
    password_field = world.browser.find_element_by_xpath('.//input[@name="password"]')
    password_field.send_keys(password)
    password_field.submit()


@step('I choose "(.*)" radio')
def radio_button(step, field):
    radio = world.browser.find_element_by_xpath('.//input[@id="%s"][@type="radio"]' % field)
    radio.click()


@step('Given I go to "(.*)"')
def our_goto(step, relative_url):
    """
    NB. This allows tests to run in different contexts ( locally, staging.)
    We delegate to the library supplied version of the step with the same pattern after fixing the path
    """
    absolute_url = world.site_url + relative_url
    lettuce_webdriver.webdriver.goto(step, absolute_url)
    #time.sleep(15)


@step('Then I should see "(.*)"')
def eventually(step, expectation):
    #number_of_seconds_to_wait = getattr(world, "wait_seconds", 30)
    lettuce_webdriver.webdriver.should_see(step, expectation)#, number_of_seconds_to_wait)


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
    """
    :return: http://example.com:8081
    """
    import os
    site_url_file = "/tmp/%s_site_url" % app_name
    if not os.path.exists(site_url_file):
        return default_url
    else:
        with open(site_url_file) as f:
            site_url = f.read()
        #os.unlink(site_url_file)
        return site_url.strip()


#def get_default_page_timeout_seconds():
#    return 10
