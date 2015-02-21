import os
import random
import string

from lettuce import *

from selenium import webdriver
import lettuce_webdriver.webdriver

from rdrf import steps


@before.all
def set_browser():
    desired_capabilities = webdriver.DesiredCapabilities.FIREFOX

    world.browser = webdriver.Remote(
        desired_capabilities=desired_capabilities,
        command_executor="http://seleniumhub:4444/wd/hub"
    )


@before.all
def set_site_url():
    world.site_url = steps.get_site_url("rdrf", default_url="http://webselenium:8000")


@before.all
def set_wait_seconds():
    world.wait_seconds = 3


@before.each_scenario
def delete_cookies(scenario):
    # delete all cookies so when we browse to a url at the start we have to log in
    world.browser.delete_all_cookies()
