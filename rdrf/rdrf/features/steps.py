import logging
import os

from aloe import step, world
from aloe.registry import STEP_REGISTRY
from aloe_webdriver.webdriver import contains_content

from nose.tools import assert_true, assert_equal

from selenium.webdriver.common.alert import Alert

from . import utils


logger = logging.getLogger(__name__)

# Clearing all the aloe step definitions before we register our own.
STEP_REGISTRY.clear()


@step('development fixtures')
def load_development_fixtures(step):
    utils.django_init_dev()
    utils.django_reloadrules()


@step('export "(.*)"')
def load_export(step, export_name):
    utils.load_export(export_name)
    utils.reset_password_change_date()


@step('should see "([^"]+)"$')
def should_see(step, text):
    assert_true(contains_content(world.browser, text))


@step('click "(.*)"')
def click_link(step, link_text):
    link = world.browser.find_element_by_partial_link_text(link_text)
    utils.click(link)


@step('should see a link to "(.*)"')
def should_see_link_to(step, link_text):
    return world.browser.find_element_by_xpath('//a[contains(., "%s")]' % link_text)


@step('should NOT see a link to "(.*)"')
def should_not_see_link_to(step, link_text):
    links = world.browser.find_elements_by_xpath('//a[contains(., "%s")]' % link_text)
    assert_equal(len(links), 0)


@step('press the "(.*)" button')
def press_button(step, button_text):
    button = world.browser.find_element_by_xpath('//button[contains(., "%s")]' % button_text)
    utils.click(button)


@step('I click "(.*)" on patientlisting')
def click_patient_listing(step, patient_name):
    link = world.browser.find_element_by_partial_link_text(patient_name)
    utils.click(link)


@step('I click on "(.*)" in "(.*)" group in sidebar')
def click_sidebar_group_item(step, item_name, group_name):
    # E.g. And I click "Clinical Data" in "Main" group in sidebar
    wrap = world.browser.find_element_by_id("wrap")
    sidebar = wrap.find_element_by_xpath('//div[@class="well"]')
    form_group_panel = sidebar.find_element_by_xpath(
        '//div[@class="panel-heading"][contains(., "%s")]' % group_name).find_element_by_xpath("..")
    form_link = form_group_panel.find_element_by_partial_link_text(item_name)
    utils.click(form_link)


@step('I press "(.*)" button in "(.*)" group in sidebar')
def click_button_sidebar_group(step, button_name, group_name):
    wrap = world.browser.find_element_by_id("wrap")
    sidebar = wrap.find_element_by_xpath('//div[@class="well"]')
    form_group_panel = sidebar.find_element_by_xpath(
        '//div[@class="panel-heading"][contains(., "%s")]' % group_name).find_element_by_xpath("..")
    button = form_group_panel.find_element_by_xpath('//a[@class="btn btn-info btn-xs pull-right"]')
    utils.click(button)


@step('I enter value "(.*)" for form "(.*)" section "(.*)" cde "(.*)"')
def enter_cde_on_form(step, cde_value, form, section, cde):
    # And I enter "02-08-2016" for  section "" cde "Consent date"
    location_is(step, form)  # sanity check

    form_block = world.browser.find_element_by_id("main-form")
    section_div_heading = form_block.find_element_by_xpath(
        ".//div[@class='panel-heading'][contains(., '%s')]" % section)
    section_div = section_div_heading.find_element_by_xpath("..")

    label_expression = ".//label[contains(., '%s')]" % cde

    for label_element in section_div.find_elements_by_xpath(label_expression):
        input_div = label_element.find_element_by_xpath(".//following-sibling::div")
        try:
            input_element = input_div.find_element_by_xpath(".//input")
            input_element.send_keys(cde_value)
            return
        except:
            pass

    raise Exception("could not find cde %s" % cde)


@step('I click the "(.*)" button')
def click_submit_button(step, value):
    """click submit button with given value
    This enables us to click on button, input or a elements that look like buttons.
    """
    submit_element = world.browser.find_element_by_xpath("//*[@id='submit-btn' and @value='{0}']".format(value))
    utils.click(submit_element)


@step('error message is "(.*)"')
def error_message_is(step, error_message):
    # <div class="alert alert-alert alert-danger">Patient Fred SMITH not saved due to validation errors</div>
    world.browser.find_element_by_xpath(
        '//div[@class="alert alert-alert alert-danger" and contains(text(), "%s")]' % error_message)


@step('location is "(.*)"')
def location_is(step, location_name):
    world.browser.find_element_by_xpath(
        '//div[@class="banner"]').find_element_by_xpath('//h3[contains(., "%s")]' % location_name)


@step('When I click Module "(.*)" for patient "(.*)" on patientlisting')
def click_module_dropdown_in_patient_listing(step, module_name, patient_name):
    # module_name is "Main/Clinical Form" if we indicate context group  or "FormName" is just Modules list ( no groups)
    if "/" in module_name:
        button_caption, form_name = module_name.split("/")
    else:
        button_caption, form_name = "Modules", module_name

    patients_table = world.browser.find_element_by_id("patients_table")

    patient_row = patients_table.find_element_by_xpath("//tr[td[1]//text()[contains(., '%s')]]" % patient_name)

    form_group_button = patient_row.find_element_by_xpath('//button[contains(., "%s")]' % button_caption)

    utils.click(form_group_button)
    form_link = form_group_button.find_element_by_xpath("..").find_element_by_partial_link_text(form_name)
    utils.click(form_link)


@step('press the navigate back button')
def press_back_button(step):
    button = world.browser.find_element_by_xpath('//a[@class="previous-form"]')
    utils.click(button)


@step('press the navigate forward button')
def press_forward_button(step):
    button = world.browser.find_element_by_xpath('//a[@class="next-form"]')
    utils.click(button)


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
    utils.click(option)


@step('option "(.*)" from "(.*)" should be selected')
def option_should_be_selected(step, option, dropdown_label):
    label = world.browser.find_element_by_xpath('//label[contains(., "%s")]' % dropdown_label)
    option = world.browser.find_element_by_xpath('//select[@id="%s"]/option[contains(., "%s")]' %
                                                 (label.get_attribute('for'), option))
    assert_true(option.get_attribute('selected'))


@step('fill in "(.*)" with "(.*)"')
def fill_in_textfield(step, textfield_label, text):
    label = world.browser.find_element_by_xpath('//label[contains(., "%s")]' % textfield_label)
    textfield = world.browser.find_element_by_xpath('//input[@id="%s"]' % label.get_attribute('for'))
    textfield.send_keys(text)


@step('fill "(.*)" with "(.*)" in MultiSection "(.*)" index "(.*)"')
def fill_in_textfield(step, label, keys, multi, index):
    multisection = multi + '-' + index
    label = world.browser.find_element_by_xpath('//label[contains(@for, "{0}") and contains(., "{1}")]'.format(multisection, label))
    textfield = world.browser.find_element_by_xpath('//input[@id="%s"]' % label.get_attribute('for'))
    textfield.send_keys(keys)


@step('value of "(.*)" should be "(.*)"')
def value_is(step, textfield_label, expected_value):
    label = world.browser.find_element_by_xpath('//label[contains(., "%s")]' % textfield_label)
    textfield = world.browser.find_element_by_xpath('//input[@id="%s"]' % label.get_attribute('for'))
    assert_equal(textfield.get_attribute('value'), expected_value)


@step('check "(.*)"')
def check_checkbox(step, checkbox_label):
    label = world.browser.find_element_by_xpath('//label[contains(., "%s")]' % checkbox_label)
    checkbox = world.browser.find_element_by_xpath('//input[@id="%s"]' % label.get_attribute('for'))
    if not checkbox.is_selected():
        utils.click(checkbox)


@step('the "(.*)" checkbox should be checked')
def checkbox_should_be_checked(step, checkbox_label):
    label = world.browser.find_element_by_xpath('//label[contains(., "%s")]' % checkbox_label)
    checkbox = world.browser.find_element_by_xpath('//input[@id="%s"]' % label.get_attribute('for'))
    assert_true(checkbox.is_selected())


@step('a registry named "(.*)"')
def create_registry(step, name):
    world.registry = name


@step('a user named "(.*)"')
def create_user(step, username):
    world.user = username


@step('a patient named "(.*)"')
def set_patient(step, name):
    world.patient = name


@step("navigate to the patient's page")
def goto_patient(step):
    select_from_list(step, world.registry, "#registry_options")
    click_link(step, world.patient)


@step('the page header should be "(.*)"')
def the_page_header_should_be(step, header):
    header = world.browser.find_element_by_xpath('//h3[contains(., "%s")]' % header)


@step('I am logged in as (.*)')
def login_as_role(step, role):
    # Could map from role to user later if required

    world.user = role  # ?
    logger.debug("about to login as %s registry %s" % (world.user, world.registry))
    go_to_registry(step, world.registry)
    logger.debug("selected registry %s OK" % world.registry)
    login_as_user(step, role, role)
    logger.debug("login_as_user %s OK" % role)


@step('log in as "(.*)" with "(.*)" password')
def login_as_user(step, username, password):
    utils.click(world.browser.find_element_by_link_text("Log in"))
    username_field = world.browser.find_element_by_xpath('.//input[@name="username"]')
    username_field.send_keys(username)
    password_field = world.browser.find_element_by_xpath('.//input[@name="password"]')
    password_field.send_keys(password)
    password_field.submit()


@step('should be logged in')
def should_be_logged_in(step):
    user_link = world.browser.find_element_by_partial_link_text(world.user)
    utils.click(user_link)
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
def the_progress_indicator_should_be(step, percentage):
    progress_bar = world.browser.find_element_by_xpath('//div[@class="progress"]/div[@class="progress-bar"]')

    logger.info(progress_bar.text.strip())
    logger.info(percentage)

    assert_equal(progress_bar.text.strip(), percentage)


@step('I go home')
def go_home(step):
    world.browser.get(world.site_url)


@step('go to the registry "(.*)"')
def go_to_registry(step, name):
    logger.debug("**********  in go_to_registry *******")
    world.browser.get(world.site_url)
    logger.debug("navigated to %s" % world.site_url)
    utils.click(world.browser.find_element_by_link_text('Registries on this site'))
    logger.debug("clicked dropdown for registry")
    utils.click(world.browser.find_element_by_partial_link_text(name))
    logger.debug("found link text to click")


@step('go to page "(.*)"')
def go_to_page(setp, page_ref):
    if page_ref.startswith("/"):
        page_ref = page_ref[1:]
    url = world.site_url + page_ref
    logger.debug("going to go to page url %s" % url)
    world.browser.get(url)


@step('navigate away then back')
def refresh_page(step):
    current_url = world.browser.current_url
    world.browser.get(world.site_url)
    world.browser.get(current_url)


@step('accept the alert')
def accept_alert(step):
    Alert(world.browser).accept()


@step('When I click "(.*)" in sidebar')
def sidebar_click(step, sidebar_link_text):
    utils.click(world.browser.find_element_by_link_text(sidebar_link_text))


@step('I click Cancel')
def click_cancel(step):
    link = world.browser.find_element_by_xpath('//a[@class="btn btn-danger" and contains(., "Cancel")]')
    utils.click(link)


@step('I reload iprestrict')
def reload_iprestrict(step):
    utils.django_reloadrules()


@step('enter value "(.*)" for "(.*)"')
def enter_value_for_named_element(step, value, name):
    # try to find place holders, labels etc
    for element_type in ['placeholder']:
        xpath_expression = '//input[@placeholder="{0}"]'.format(name)
        input_element = world.browser.find_element_by_xpath(xpath_expression)
        if input_element:
            input_element.send_keys(value)
            return
    raise Exception("can't find element '%s'" % name)


