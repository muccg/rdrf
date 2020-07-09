import logging

from aloe import step, world
from aloe.registry import STEP_REGISTRY
from aloe_webdriver.webdriver import contains_content

from nose.tools import assert_true, assert_equal

from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.alert import Alert
from selenium.common.exceptions import NoSuchElementException as Nse

from . import utils

from collections import OrderedDict
import time

logger = logging.getLogger(__name__)

# Clearing all the aloe step definitions before we register our own.
STEP_REGISTRY.clear()


@step('I try to log in')
def try_to_login(step):
    world.browser.get(world.site_url + "login?next=/router/")


@step('I should be logged in as an Angelman user called "([^"]+)"')
def login_as_angelman_user(step, user_name):
    world.expected_login_message = "Welcome {0} to the Angelman Registry".format(user_name)


@step('I should be at the welcome page and see a message which says "([^"]+)"')
def angelman_user_logged_in(step, welcome_message):
    login_message = world.browser.find_element_by_tag_name('h4').text

    # Ensure that the user sees the expected page after successfully logging in
    assert world.expected_login_message in login_message


@step('the administrator manually activates the user')
def try_to_manually_activate_new_user(step):
    world.browser.get(world.site_url + "admin/registration/registrationprofile/")
    world.browser.find_element_by_id('action-toggle').send_keys(Keys.SPACE)

    world.browser.find_element_by_xpath(
        "//select[@name='action']/option[text()='Activate users']").click()
    world.browser.find_element_by_xpath("//*[@title='Run the selected action']").click()


@step('the user should be activated')
def check_user_activated(step):
    # Ensure that the user has been successfully activated by checking for the green tick icon
    assert not (world.browser.find_elements_by_css_selector(
        'img[src$="/static/admin/img/icon-yes.svg"].ng-hide'))

    # Log out as the admin user
    world.browser.get(world.site_url + "logout?next=/router/")


@step(
    'I try to register as an "([^"]+)" user called "([^"]+)" using the email address "([^"]+)" and the password "([^"]+)"')
def try_to_register(step, registry, client_name, email_address, password):
    registry_code = ''

    if registry == 'Angelman':
        registry_code = 'ang'

    world.browser.get(world.site_url + registry_code + "/register")

    client_first_name = client_name.split()[0]
    client_last_name = client_name.split()[1]

    # Plain text field parameters
    params = OrderedDict([
        ('id_username', email_address),
        ('id_password1', password),
        ('id_password2', password),
        ('id_parent_guardian_first_name', client_first_name),
        ('id_parent_guardian_last_name', client_last_name),
        ('id_parent_guardian_date_of_birth', '1980-09-01'),
        # Gender radio button
        ('id_parent_guardian_address', 'Australia'),
        ('id_parent_guardian_suburb', 'Australia'),
        # Country dropdown
        # State dropdown
        ('id_parent_guardian_postcode', '6000'),
        ('id_parent_guardian_phone', '98765432')
    ])

    # Populate plain text fields
    for key, value in params.items():
        world.browser.find_element_by_id(key).send_keys(value + Keys.TAB)

    # Select the gender radio button
    # 1 - Male, 2 - Female, 3 - Indeterminate
    world.browser.find_element_by_css_selector("input[type='radio'][value='1']").click()

    # Select the country and state dropdowns
    world.browser.find_element_by_xpath(
        "//select[@name='parent_guardian_country']/option[text()='Australia']").click()
    world.browser.find_element_by_xpath(
        "//select[@name='parent_guardian_state']/option[text()='Western Australia']").click()

    # Fill out the patient details
    world.browser.find_element_by_id('ui-id-2').click()

    patient_params = OrderedDict([
        ('id_first_name', 'Patient_First'),
        ('id_surname', 'Patient_Surname'),
        ('id_date_of_birth', '1985-01-01'),
        # Gender radio button
        # "Same details" checkbox
    ])

    for key, value in patient_params.items():
        world.browser.find_element_by_id(key).send_keys(value + Keys.TAB)

    radio = world.browser.find_element_by_id('id_gender')
    world.browser.execute_script("arguments[0].click();", radio)

    world.browser.find_element_by_id('same_address').send_keys(Keys.SPACE)

    captcha_iframe_element = world.browser.find_element_by_xpath(
        "//iframe[@role='presentation']")

    world.browser.switch_to.frame(captcha_iframe_element)
    utils.scroll_to_y(500)

    world.browser.find_element_by_id('recaptcha-anchor').send_keys(Keys.SPACE)

    time.sleep(4)
    world.browser.switch_to_default_content()
    world.browser.find_element_by_id('registration-submit').click()


@step('I should have successfully registered and would see a "([^"]+)" message')
def registration_successful(step, expected_success_message):
    # Ensure that the registration has successfully completed
    actual_message = world.browser.find_element_by_tag_name('h3').text
    assert expected_success_message in actual_message


@step('I try to surf the site...')
def sleep_for_admin(step):
    '''
    This is just a helper function to prevent the browser from closing.
    '''
    time.sleep(200000)


@step('development fixtures')
def load_development_fixtures(step):
    utils.django_init_dev()
    utils.django_reloadrules()


@step('export "(.*)"')
def load_export(step, export_name):
    utils.load_export(export_name)
    utils.reset_password_change_date()
    utils.reset_last_login_date()


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
        '//div[@class="panel-heading"][contains(., "%s")]' %
        group_name).find_element_by_xpath("..")
    form_link = form_group_panel.find_element_by_partial_link_text(item_name)
    utils.click(form_link)


@step('I press "(.*)" button in "(.*)" group in sidebar')
def click_button_sidebar_group(step, button_name, group_name):
    wrap = world.browser.find_element_by_id("wrap")
    sidebar = wrap.find_element_by_xpath('//div[@class="well"]')
    form_group_panel = sidebar.find_element_by_xpath(
        '//div[@class="panel-heading"][contains(., "%s")]' %
        group_name).find_element_by_xpath("..")
    button = form_group_panel.find_element_by_xpath(
        '//a[@class="btn btn-info btn-xs pull-right"]')
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
        except BaseException:
            pass

    raise Exception("could not find cde %s" % cde)


@step(r'I enter value "(.*)" for form "(.*)" multisection "(.*)" cde "(.*)" in item (\d+)')
def enter_cde_on_form_multisection(step, cde_value, form, section, cde, item):
    formset_number = int(item) - 1
    formset_string = "-%s-" % formset_number

    def correct_item(input_element):
        input_id = input_element.get_attribute("id")
        return formset_string in input_id

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
            if not correct_item(input_element):
                continue
            input_element.send_keys(cde_value)
            input_id = input_element.get_attribute("id")
            print("input id %s sent keys '%s'" % (input_id,
                                                  cde_value))

            return
        except BaseException:
            pass

    raise Exception("could not find cde %s" % cde)


@step('I click the "(.*)" button')
def click_submit_button(step, value):
    """click submit button with given value
    This enables us to click on button, input or a elements that look like buttons.
    """
    submit_element = world.browser.find_element_by_xpath(
        "//*[@id='submit-btn' and @value='{0}']".format(value))
    utils.click(submit_element)


@step('error message is "(.*)"')
def error_message_is(step, error_message):
    # <div class="alert alert-alert alert-danger">Patient Fred SMITH not saved due to validation errors</div>
    world.browser.find_element_by_xpath(
        '//div[@class="alert alert-alert alert-danger" and contains(text(), "%s")]' %
        error_message)


@step('location is "(.*)"')
def location_is(step, location_name):
    world.browser.find_element_by_xpath(
        '//div[@class="banner"]').find_element_by_xpath('//h3[contains(., "%s")]' % location_name)


@step('When I click Module "(.*)" for patient "(.*)" on patientlisting')
def click_module_dropdown_in_patient_listing(step, module_name, patient_name):
    # module_name is "Main/Clinical Form" if we indicate context group  or
    # "FormName" is just Modules list ( no groups)
    if "/" in module_name:
        button_caption, form_name = module_name.split("/")
    else:
        button_caption, form_name = "Modules", module_name

    patients_table = world.browser.find_element_by_id("patients_table")

    patient_row = patients_table.find_element_by_xpath(
        "//tr[td[1]//text()[contains(., '%s')]]" % patient_name)

    form_group_button = patient_row.find_element_by_xpath(
        '//button[contains(., "%s")]' % button_caption)

    utils.click(form_group_button)
    form_link = form_group_button.find_element_by_xpath(
        "..").find_element_by_partial_link_text(form_name)
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
        label = world.browser.find_element_by_xpath(
            '//label[contains(., "%s")]' %
            dropdown_label_or_id)
        select_id = label.get_attribute('for')
    option = world.browser.find_element_by_xpath(
        '//select[@id="%s"]/option[contains(., "%s")]' %
        (select_id, option))
    utils.click(option)


@step('option "(.*)" from "(.*)" should be selected')
def option_should_be_selected(step, option, dropdown_label):
    label = world.browser.find_element_by_xpath('//label[contains(., "%s")]' % dropdown_label)
    option = world.browser.find_element_by_xpath(
        '//select[@id="%s"]/option[contains(., "%s")]' %
        (label.get_attribute('for'), option))
    assert_true(option.get_attribute('selected'))


@step('search for "(.*)"')
def search_for_text(step, text):
    search = world.browser.find_element_by_xpath('//input[@type="search"]')
    search.send_keys(text)


@step('fill in "(.*)" with "(.*)"')
def fill_in_textfield(step, textfield_label, text):
    label = world.browser.find_element_by_xpath('//label[contains(., "%s")]' % textfield_label)
    textfield = world.browser.find_element_by_xpath(
        '//input[@id="%s"]' % label.get_attribute('for'))
    textfield.send_keys(text)


@step('I click the add button in "(.*)" section')
def click_add_for_inline(step, section):
    section_div_heading = world.browser.find_element_by_xpath(
        "//div[@class='panel-heading'][contains(., '%s')]" % section)
    add_link_xpath = """//a[starts-with(@onclick,"add_form")]"""
    add_link = section_div_heading.find_element_by_xpath(add_link_xpath)
    utils.click(add_link)
    wait_n_seconds(step, 5)


@step('fill out "(.*)" textarea in "(.*)" section "(.*)" with "(.*)"')
def fill_in_inline_textarea(step, textfield_label, section, index, text):
    section_div_heading = world.browser.find_element_by_xpath(
        ".//div[@class='panel-heading'][contains(., '%s')]" % section)
    section_div = section_div_heading.find_element_by_xpath("..")

    label = section_div.find_element_by_xpath(".//label[normalize-space()='%s']" % textfield_label)
    css_id = label.get_attribute('for')
    css_id = css_id.replace('__prefix__', str(int(index) - 1))
    text_area = world.browser.find_element_by_xpath(
        '//textarea[@id="%s"]' % css_id)
    text_area.send_keys(text)


@step('fill out "(.*)" in "(.*)" section "(.*)" with "(.*)"')
def fill_in_inline_textfield(step, textfield_label, section, index, text):
    section_div_heading = world.browser.find_element_by_xpath(
        ".//div[@class='panel-heading'][contains(., '%s')]" % section)
    section_div = section_div_heading.find_element_by_xpath("..")

    label = section_div.find_element_by_xpath('.//label[contains(., "%s")]' % textfield_label)
    css_id = label.get_attribute('for')
    css_id = css_id.replace('__prefix__', str(int(index) - 1))
    textfield = world.browser.find_element_by_xpath('//input[@id="%s"]' % css_id)
    textfield.send_keys(text)


@step('choose "(.*)" from "(.*)" in "(.*)" section "(.*)"')
def select_from_inline_list(step, option, dropdown_label_or_id, section, index):
    section_div_heading = world.browser.find_element_by_xpath(
        ".//div[@class='panel-heading'][contains(., '%s')]" % section)
    section_div = section_div_heading.find_element_by_xpath("..")
    utils.scroll_to(section_div)
    label = section_div.find_element_by_xpath(
        './/label[contains(., "%s")]' %
        dropdown_label_or_id)
    select_id = label.get_attribute('for')
    select_id = select_id.replace('__prefix__', str(int(index) - 1))
    option = section_div.find_element_by_xpath(
        '//select[@id="%s"]/option[contains(., "%s")]' %
        (select_id, option))
    utils.click(option)


@step('fill "(.*)" with "(.*)" in MultiSection "(.*)" index "(.*)"')
def fill_in_textfield2(step, label, keys, multi, index):
    multisection = multi + '-' + index
    label = world.browser.find_element_by_xpath(
        '//label[contains(@for, "{0}") and contains(., "{1}")]'.format(multisection, label))
    textfield = world.browser.find_element_by_xpath(
        '//input[@id="%s"]' % label.get_attribute('for'))
    textfield.send_keys(keys)


@step('value of "(.*)" should be "(.*)"')
def value_is(step, textfield_label, expected_value):
    label = world.browser.find_element_by_xpath('//label[contains(., "%s")]' % textfield_label)
    textfield = world.browser.find_element_by_xpath(
        '//input[@id="%s"]' % label.get_attribute('for'))
    assert_equal(textfield.get_attribute('value'), expected_value)


@step('form value of section "(.*)" cde "(.*)" should be "(.*)"')
def value_is2(step, section, cde, expected_value):
    form_block = world.browser.find_element_by_id("main-form")
    section_div_heading = form_block.find_element_by_xpath(
        ".//div[@class='panel-heading'][contains(., '%s')]" % section)
    section_div = section_div_heading.find_element_by_xpath("..")
    label_expression = ".//label[contains(., '%s')]" % cde
    label_element = section_div.find_element_by_xpath(label_expression)
    input_div = label_element.find_element_by_xpath(".//following-sibling::div")
    input_element = input_div.find_element_by_xpath(".//input")
    assert_equal(input_element.get_attribute('value'), expected_value)


@step('check "(.*)"')
def check_checkbox(step, checkbox_label):
    label = world.browser.find_element_by_xpath('//label[contains(., "%s")]' % checkbox_label)
    checkbox = world.browser.find_element_by_xpath(
        '//input[@id="%s"]' % label.get_attribute('for'))
    if not checkbox.is_selected():
        utils.click(checkbox)


@step('the "(.*)" checkbox should be checked')
def checkbox_should_be_checked(step, checkbox_label):
    label = world.browser.find_element_by_xpath('//label[contains(., "%s")]' % checkbox_label)
    checkbox = world.browser.find_element_by_xpath(
        '//input[@id="%s"]' % label.get_attribute('for'))
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
    go_to_registry(step, world.registry)
    login_as_user(step, role, role)


@step('log in as "(.*)" with "(.*)" password')
def login_as_user(step, username, password):
    utils.click(world.browser.find_element_by_link_text("Log in"))
    username_field = world.browser.find_element_by_xpath('.//input[@name="auth-username"]')
    username_field.send_keys(username)
    password_field = world.browser.find_element_by_xpath('.//input[@name="auth-password"]')
    password_field.send_keys(password)
    password_field.submit()


@step('should be logged in')
def should_be_logged_in(step):
    user_link = world.browser.find_element_by_partial_link_text(world.user)
    utils.click(user_link)
    world.browser.find_element_by_link_text('Logout')


@step('should be on the login page')
def should_be_on_the_login_page(step):
    world.browser.find_element_by_xpath(
        './/div[@class="panel-heading"][text()[contains(.,"Login")]]')
    world.browser.find_element_by_xpath('.//label[text()[contains(.,"Username")]]')
    world.browser.find_element_by_xpath('.//label[text()[contains(.,"Password")]]')


@step('click the User Dropdown Menu')
def click_user_menu(step):
    click_link(step, world.user)


@step('the progress indicator should be "(.*)"')
def the_progress_indicator_should_be(step, percentage):
    progress_bar = world.browser.find_element_by_xpath(
        '//div[@class="progress"]/div[@class="progress-bar"]')
    assert_equal(progress_bar.text.strip(), percentage)


@step('I go home')
def go_home(step):
    world.browser.get(world.site_url)


@step('go to the registry "(.*)"')
def go_to_registry(step, name):
    world.browser.get(world.site_url)
    utils.click(world.browser.find_element_by_link_text('Registries on this site'))
    utils.click(world.browser.find_element_by_partial_link_text(name))


@step('go to page "(.*)"')
def go_to_page(setp, page_ref):
    if page_ref.startswith("/"):
        page_ref = page_ref[1:]
    url = world.site_url + page_ref
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
    link = world.browser.find_element_by_xpath(
        '//a[@class="btn btn-danger" and contains(., "Cancel")]')
    utils.click(link)


@step('I reload iprestrict')
def reload_iprestrict(step):
    utils.django_reloadrules()


@step('click radio button value "(.*)" for section "(.*)" cde "(.*)"')
def click_radio_button(step, value, section, cde):
    # NB. this is actually just clicking the first radio at the moment
    # and ignores the value
    section_div_heading = world.browser.find_element_by_xpath(
        "//div[@class='panel-heading'][contains(., '%s')]" % section)
    section_div = section_div_heading.find_element_by_xpath("..")
    label_expression = ".//label[contains(., '%s')]" % cde
    label_element = section_div.find_element_by_xpath(label_expression)
    input_div = label_element.find_element_by_xpath(".//following-sibling::div")
    # must be getting first ??
    input_element = input_div.find_element_by_xpath(".//input")
    utils.click(input_element)


@step(r'upload file "(.*)" for multisection "(.*)" cde "(.*)" in item (\d+)')
def upload_file(step, upload_filename, section, cde, item):
    input_element = utils.scroll_to_multisection_cde(section, cde, item)
    input_element.send_keys(upload_filename)


@step('upload file "(.*)" for section "(.*)" cde "(.*)"')
def upload_file2(step, upload_filename, section, cde):
    input_element = utils.scroll_to_element(step, section, cde)
    input_element.send_keys(upload_filename)


@step('scroll to section "(.*)" cde "(.*)"')
def scroll_to_element(step, section, cde):
    input_element = utils.scroll_to_cde(section, cde)
    if not input_element:
        raise Exception("could not scroll to section %s cde %s" % (section,
                                                                   cde))
    return input_element


@step('should be able to download "(.*)"')
def should_be_able_to_download(step, download_name):
    import re
    link_pattern = re.compile(r".*\/uploads\/\d+$")
    download_link_element = world.browser.find_element_by_link_text(download_name)
    if not download_link_element:
        raise Exception("Could not locate download link %s" % download_name)

    download_link_href = download_link_element.get_attribute("href")
    if not link_pattern.match(download_link_href):
        raise Exception("%s does not look like a download link: href= %s" %
                        download_link_href)


@step('should not be able to download "(.*)"')
def should_not_be_able_download(step, download_name):
    can_download = False
    try:
        should_be_able_to_download(step, download_name)
        can_download = True
    except BaseException:
        pass

    if can_download:
        raise Exception("should NOT be able to download %s" % download_name)
    else:
        print("%s is not downloadable as expected" % download_name)


@step('History for form "(.*)" section "(.*)" cde "(.*)" shows "(.*)"')
def check_history_popup(step, form, section, cde, history_values_csv):
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as ec
    from selenium.webdriver.support.ui import WebDriverWait

    history_values = history_values_csv.split(",")
    form_block = world.browser.find_element_by_id("main-form")
    section_div_heading = form_block.find_element_by_xpath(
        "//div[@class='panel-heading'][contains(., '%s')]" % section)
    section_div = section_div_heading.find_element_by_xpath("..")
    label_expression = ".//label[contains(., '%s')]" % cde
    label_element = section_div.find_element_by_xpath(label_expression)
    input_div = label_element.find_element_by_xpath(".//following-sibling::div")
    input_element = input_div.find_element_by_xpath(".//input")
    history_widget = label_element.find_elements_by_xpath(
        ".//a[@onclick='rdrf_click_form_field_history(event, this)']")[0]

    utils.scroll_to(input_element)

    # this causes the history component to become visible/clickable
    utils.click(input_element)
    utils.click(history_widget)

    WebDriverWait(world.browser, 60).until(
        ec.visibility_of_element_located((By.XPATH, ".//a[@href='#cde-history-table']"))
    )

    def find_cell(historical_value):
        element = world.browser.find_element_by_xpath(
            '//td[@data-value="%s"]' % historical_value)
        if element is None:
            raise Exception("Can't locate history value '%s'" % historical_value)

    for historical_value in history_values:
        find_cell(historical_value)


@step('check the clear checkbox for multisection "(.*)" cde "(.*)" file "(.*)"')
def clear_file_upload(step, section, cde, download_name):
    # NB. the nots here! We avoid dummy empty forms and the hidden history
    import time
    download_link_element = world.browser.find_element_by_link_text(download_name)
    clear_checkbox = download_link_element.find_element_by_xpath(
        ".//following-sibling::input[@type='checkbox']")
    y = int(utils.scroll_to(clear_checkbox))
    attempts = 1
    succeeded = False

    # ugh
    while attempts <= 10:
        try:
            clear_checkbox.click()
            print("clicked the clear checkbox OK")
            succeeded = True
            break
        except BaseException:
            print("clear checkbox could not be clicked on attempt %s" % attempts)
            time.sleep(2)
            attempts += 1
        y = y + 10
        utils.scroll_to_y(y)
        print("scrolled to y = %s" % y)

    if not succeeded:
        raise Exception("Could not click the file clear checkbox")


@step('when I scroll to section "(.*)"')
def scroll_to_section(step, section):
    from selenium.webdriver.common.action_chains import ActionChains
    mover = ActionChains(world.browser)
    print("scrolling to section %s" % section)
    section_xpath = ".//div[@class='panel panel-default' and contains(.,'%s') and not(contains(., '__prefix__')) and not(contains(.,'View previous values'))]" % section
    section_element = world.browser.find_element_by_xpath(section_xpath)
    if not section_element:
        raise Exception("could not find section %s" % section)
    y = utils.scroll_to(section_element)
    mover.move_to_element(section_element)
    print("scrolled to section %s y = %s" % (section, y))


@step('I click the add button for multisection "(.*)"')
def add_multisection_item(step, section):
    xpath = ".//div[@class='panel-heading' and contains(.,'%s') and not(contains(., '__prefix__')) and not(contains(.,'View previous values'))]" % section
    div = world.browser.find_element_by_xpath(xpath)
    add_link_xpath = """.//a[starts-with(@onclick,"add_form('formset_")]"""
    add_link = div.find_element_by_xpath(add_link_xpath)
    add_link.click()
    # sometimes the next cde send keys was going to the wrong item
    wait_n_seconds(step, 5)


@step(r'I wait (\d+) seconds')
def wait_n_seconds(step, seconds):
    import time
    n = int(seconds)
    time.sleep(n)


@step(r'I mark multisection "(.*)" item (\d+) for deletion')
def mark_item_for_deletion(step, multisection, item):
    formset_string = "-%s-" % (int(item) - 1)
    xpath = "//div[@class='panel-heading' and contains(., '%s')]" % multisection
    default_panel = world.browser.find_element_by_xpath(xpath).find_element_by_xpath("..")
    # now locate the delete checkbox for the item
    checkbox_xpath = ".//input[@type='checkbox' and contains(@id, '-DELETE') and contains(@id, '%s')]" % formset_string
    delete_checkbox = default_panel.find_element_by_xpath(checkbox_xpath)

    if delete_checkbox:
        print("found delete_checkbox for multisection %s item %s" % (multisection,
                                                                     item))
    else:
        raise Exception(
            "Could not found delete checkbox for multisection %s item %s" %
            (multisection, item))

    utils.click(delete_checkbox)


@step(r'the value of multisection "(.*)" cde "(.*)" item (\d+) is "(.*)"')
def check_multisection_value(step, multisection, cde, item, expected_value):
    """
    Check the value of an entered field in a multisection
    """
    input_element = utils.scroll_to_multisection_cde(multisection, cde, item)
    actual_value = input_element.get_attribute("value")
    error_msg = "Multisection %s cde %s item %s expected value %s - actual value %s" % (
        multisection, cde, item, expected_value, actual_value)

    assert actual_value == expected_value, error_msg


def find(xp):
    try:
        return world.browser.find_element_by_xpath(xp)
    except Nse:
        raise Exception('Unable to find element by xpath:  {0}'.format(xp))
    pass


def find_multiple(xp):
    """
    Helper function to find multiple items with the same xpath.
    Initially created so that a list of elements could be iterated over,
    and a particular attribute extracted for each item.
    Slow (5s) if the element does not exist, but returns an empty vector
    rather than a NoSuchElementException.
    """
    return world.browser.find_elements_by_xpath(xp)


def scroll_to_centre(xp):
    """
    Helper function to scroll an element to the centre of the viewport.
    Should stop Selenium's ElementClickInterceptedException, which previously
    would occur due to the banners at the top and bottom of the viewport.
    """
    y = find(xp).location["y"]
    off = world.browser.get_window_size()["height"]
    move = y - (1 / 2) * off
    world.browser.execute_script("scrollTo(0, %s)" % move)


@step('I return to patientlisting')
def return_to_patientlisting(step):
    world.browser.get(
        find("//a[text()='Patient List']").get_attribute("href")
    )


@step('sidebar contains a section named "(.*)"')
def sidebar_contains_section(step, name):
    try:
        find(
            (
                "//div[@class='well']"
                "//div[@class='panel-heading' and contains(., '%s')]"
                % name
            )
        )
    except Nse:
        raise Exception("Could not find sidebar section named %s" % name)


@step('sidebar contains a link to "(.*)"')
def sidebar_contains_link(step, name):
    try:
        find("//div[@class='well']//a[contains(., '%s')]" % name)
    except Nse:
        raise Exception("Could not find a sidebar link to %s" % name)


@step('sidebar contains a link in section "(.*)" to "(.*)"')
def sidebar_contains_link_in_section(step, sec, name):
    try:
        find(
            (
                "//div[@class='panel-heading' and contains(., '%s')]"
                "/following-sibling::div//a[contains(., '%s')]"
                % (sec, name)
            )
        )
    except Nse:
        raise Exception(
            "Could not find a link to %s in section %s in sidebar"
            % (name, sec)
        )


def find_option(label, option):
    """
    Helper function for finding an option in a list.
    Returns None if the object isn't found.
    """
    xp = (
        "//label[contains(.,\"%s\")]/following-sibling::*"
        "//option[contains(.,\"%s\")]"
        % (label, option)
    )
    try:
        item = find(xp)
    except Nse:
        item = None
    return item


@step('should see (survey name|communication type) option "(.*)"')
def proms_checks(step, which, option):
    assert world.browser.current_url.endswith("/clinicalproms"),\
        "Not on PROMS request page!"
    if not find_option(label=which.capitalize(), option=option):
        raise Exception(
            "Unable to find %s option %s"
            % (which, option)
        )


@step('the menu "([^\"]+)" (contains|DOES NOT contain) "([^\"]+)"')
def menu_contains_yn_general(step, menu, check, item):
    if check == "contains":
        xp = (
            "//a[contains(.,'%s')]/following-sibling::ul/li/a[contains(.,'%s')]"
            % (menu, item)
        )
        try:
            find(xp)
        except Nse:
            raise Exception(
                "Could not find menu \"%s\" item \"%s\"\n"
                "xpath:  %s"
                % (menu, item, xp)
            )
    elif check == "DOES NOT contain":
        xp = (
            "//a[contains(.,'%s')]/following-sibling::ul/li"
            % (menu)
        )
        ls1 = find_multiple(xp)
        ls2 = []
        for obj in ls1:
            ls2.append(obj.get_attribute("text"))
        if item in ls2:
            raise Exception(
                "Found menu \"%s\" item \"%s\", but should not exist.\n"
                % (menu, item)
            )
        else:
            pass
    else:
        raise Exception("Do not recognise check type:  %s" % check)


class Xpath:
    ADD_PATIENT_BUTTON = "//button[@id='add_patient']"
    REGISTRY_OPTION_CRC = "//option[contains(., 'ICHOM Colorectal Cancer')]"
    REGISTRY_OPTION_BC = '//option[contains(., "ICHOM Breast Cancer")]'
    CENTRE_OPTION_CRC_SJOG = "//option[contains(., 'ICHOMCRC SJOG')]"
    CENTRE_OPTION_BC_WA = '//option[contains(., "ICHOMBC WA")]'
    SURNAME_FIELD = "//input[@name='family_name']"
    FIRSTNAME_FIELD = "//input[@name='given_names']"
    DOB_FIELD = "//input[@name='date_of_birth']"
    SEX_LIST = "//select[@name='sex']"
    SEX_OPTION_MALE = "//select[@name='sex']/option[text()='Male']"
    SEX_OPTION_FEMALE = "//select[@name='sex']/option[text()='Female']"
    SUBMIT_BUTTON = "//button[@id='submit-btn']"


@step('I add patient name "(.*)" sex "(.*)" birthdate "(.*)"')
def add_new_patient(step, name, sex, birthdate):
    surname, firstname = name.split(' ')
    world.browser.get(
        world.site_url + "patientslisting"
    )
    find(Xpath.ADD_PATIENT_BUTTON).click()
    if 'ICHOMCRC' in world.browser.current_url:
        find(Xpath.REGISTRY_OPTION_CRC).click()
        find(Xpath.CENTRE_OPTION_CRC_SJOG).click()
    elif 'ICHOMBC' in world.browser.current_url:
        find(Xpath.REGISTRY_OPTION_BC).click()
        find(Xpath.CENTRE_OPTION_BC_WA).click()
    else:
        raise Exception(
            'Cannot identify current registry from URL\n'
            'URL:  {0}'.format(world.browser.current_url)
        )
    find(Xpath.SURNAME_FIELD).send_keys(surname)
    find(Xpath.FIRSTNAME_FIELD).send_keys(firstname)
    find(Xpath.DOB_FIELD).send_keys(birthdate, Keys.ESCAPE)
    scroll_to_centre(Xpath.SEX_LIST)
    find(Xpath.SEX_LIST).click()
    if sex.capitalize() == "Male":
        find(Xpath.SEX_OPTION_MALE).click()
    else:
        find(Xpath.SEX_OPTION_FEMALE).click()
    find(Xpath.SUBMIT_BUTTON).click()
    assert "Patient added successfully" in world.browser.page_source,\
        "Patient add success message not found"


@step('I select radio value "([^\"]+)" for cde "([^\"]+)"')
def radio_select(step, value, cde):
    xp = (
        "//label[contains(.,'%s')]/following-sibling::div"
        "/label[contains(.,'%s')]"
        % (cde, value)
    )
    try:
        scroll_to_centre(xp)
        find(xp).click()
    except Nse:
        raise Exception(
            "Cannot find value \"%s\" for CDE \"%s\"\n"
            "xpath:  %s"
            % (value, cde, xp)
        )


@step('the cde "([^\"]+)" is (NOT )?marked as (abnormal|important|required)')
def is_marked_as(step, cde, no, mark):
    xp = "//label[contains(.,'%s')]" % cde
    try:
        outerhtml = find(xp).get_attribute("outerHTML")
    except Nse:
        raise Exception(
            "Cannot find cde label \"%s\"\n"
            "xpath:  %s"
            % (cde, xp)
        )
    html_map = {
        "abnormal": "glyphicon glyphicon-warning-sign",
        "important": (
            "class=\"glyphicon glyphicon-asterisk\" "
            "style=\"color: green;\""
        ),
        "required": (
            "class=\"glyphicon glyphicon-asterisk\" "
            "style=\"color: red;\""
        )
    }
    if no:
        assert html_map[mark] not in outerhtml,\
            "Found mark for cde marked as %s, but should not be present" % mark
    else:
        assert html_map[mark] in outerhtml,\
            "Could not find mark for cde marked as %s" % mark


@step(
    '(radio|dropdown) value "([^\"]+)" for cde "([^\"]+)" '
    'should (NOT )?be selected'
)
def check_radio_or_dropdown_value(step, field, value, cde, no):
    xp_part = "//label[contains(.,'%s')]/following-sibling::div" % cde
    if field == "dropdown":
        xp = xp_part + "/select/option[contains(.,'%s')]" % value
        flag = "selected"
    elif field == "radio":
        xp = xp_part + "/label[contains(.,'%s')]" % value
        flag = "checked"
    else:
        raise Exception(
            "Field type not recognised.\n"
            "Type:  %s" % field
        )
    try:
        innerhtml = find(xp).get_attribute("innerHTML")
    except Nse:
        raise Exception(
            "Cannot find cde label \"%s\"\n"
            "xpath:  %s"
            % (cde, xp)
        )
    if no:
        assert flag not in innerhtml,\
            (
                "Option \"%s\" for CDE \"%s\" selected, but should not be.\n"
                "innerHTML:  %s"
                % (value, cde, innerhtml)
            )
    else:
        assert flag in innerhtml,\
            (
                "Option \"%s\" for CDE \"%s\" not selected, but should be.\n"
                "innerHTML:  %s"
                % (value, cde, innerhtml)
            )


def s_find(xp):
    scroll_to_centre(xp)
    return find(xp)


@step('check the checkbox for cde "([^\"]+)"')
def click_checkbox(step, cde_label):
    xp = (
        '//label[contains(., "{0}")]/following-sibling::div'
        '/input'.format(cde_label)
    )
    box = s_find(xp)
    if 'checked' in box.get_attribute('outerHTML'):
        raise Exception(
            'Checkbox already checked.\n'
            'CDE:     {0}\n'.format(cde_label)
        )
    box.click()
    pass


@step('uncheck the checkbox for cde "([^\"]+)"')
def click_checkbox(step, cde_label):
    xp = (
        '//label[contains(., "{0}")]/following-sibling::div'
        '/input'.format(cde_label)
    )
    box = s_find(xp)
    if 'checked' not in box.get_attribute('outerHTML'):
        raise Exception(
            'Checkbox not already checked.\n'
            'CDE:     {0}\n'.format(cde_label)
        )
    box.click()
    pass


@step('enter "([^\"]*)" for date cde "([^\"]+)"')
def enter_date(step, entry, cde_label):
    xp = (
        '//label[contains(., "{0}")]/following-sibling::div'
        '/input'.format(cde_label)
    )
    date_box = s_find(xp)
    date_box.clear()
    date_box.send_keys([entry, Keys.ESCAPE])
    pass


@step('check "([^\"]+)" for multiple cde "([^\"]+)"')
def click_multiple(step, entry, cde_label):
    xp = (
        '//label[contains(., "{0}")]/following-sibling::div'
        '/ul/li/label[contains(., "{1}")]'.format(cde_label, entry)
    )
    option = s_find(xp)
    # Looks to see if the box is already checked, because it will be
    # unchecked by a click if already checked.
    if 'checked' in option.get_attribute('outerHTML'):
        raise Exception(
            'Multiple CDE option already checked.\n'
            'CDE:     {0}\nOption:  {1}'.format(cde_label, entry)
        )
    option.click()
    pass


@step('uncheck "([^\"]+)" for multiple cde "([^\"]+)"')
def uncheck_multiple(step, entry, cde_label):
    xp = (
        '//label[contains(., "{0}")]/following-sibling::div'
        '/ul/li/label[contains(., "{1}")]'.format(cde_label, entry)
    )
    option = s_find(xp)
    if 'checked' not in option.get_attribute('outerHTML'):
        raise Exception(
            'Multiple CDE option not already checked.\n'
            'CDE:     {0}\nOption:  {1}'.format(cde_label, entry)
        )
    option.click()
    pass


@step('check "([^\"]+)" for radio cde "([^\"]+)"')
def click_radio(step, entry, cde_label):
    xp = (
        '//label[contains(., "{0}")]/following-sibling::div'
        '/label[contains(., "{1}")]/input'.format(cde_label, entry)
    )
    s_find(xp).click()
    pass


@step('click "([^\"]*)" for select cde "([^\"]+)"')
def click_select(step, entry, cde_label):
    xp = (
        '//label[contains(., "{0}")]/following-sibling::div'
        '/select/option[contains(., "{1}")]'.format(cde_label, entry)
    )
    s_find(xp).click()
    pass


@step('enter "([^\"]*)" for text cde "([^\"]+)"')
def enter_text(step, entry, cde_label):
    xp = (
        '//label[contains(., "{0}")]/following-sibling::div'
        '/input'.format(cde_label)
    )
    text_box = s_find(xp)
    text_box.clear()
    text_box.send_keys(entry)
    pass


@step('should see "([^\"]*)" in cde "([^\"]+)"')
def postcheck_text(step, entry, cde_label):
    xp = (
        '//label[contains(., "{0}")]/following-sibling::div'
        '/input'.format(cde_label)
    )
    assert entry in find(xp).get_attribute('value'),\
        'Value "{0}" not found in cde "{1}".'.format(entry, cde_label)
    pass


@step('should NOT see "([^\"]*)" in cde "([^\"]+)"')
def postcheck_text_not(step, entry, cde_label):
    xp = (
        '//label[contains(., "{0}")]/following-sibling::div'
        '/input'.format(cde_label)
    )
    value = find(xp).get_attribute('value')
    assert entry not in value,\
        (
            'Value "{0}" found in cde "{1}", but should not be present.'
            ''.format(entry, cde_label)
        )
    pass


@step('option "([^\"]+)" for multiple cde "([^\"]+)" should be checked')
def postcheck_multiple(step, entry, cde_label):
    xp = (
        '//label[contains(., "{0}")]/following-sibling::div'
        '/ul/li/label[contains(., "{1}")]/input'.format(cde_label, entry)
    )
    outer_html = find(xp).get_attribute('outerHTML')
    assert 'checked' in outer_html,\
        (
            'Option "{0}" for cde "{1}" is not checked, but should be.'
            ''.format(entry, cde_label)
        )
    pass


@step('option "([^\"]+)" for multiple cde "([^\"]+)" should NOT be checked')
def postcheck_multiple_not(step, entry, cde_label):
    xp = (
        '//label[contains(., "{0}")]/following-sibling::div'
        '/ul/li/label[contains(., "{1}")]/input'.format(cde_label, entry)
    )
    outer_html = find(xp).get_attribute('outerHTML')
    assert 'checked' not in outer_html,\
        (
            'Option "{0}" for cde "{1}" is checked, but should not be.'
            ''.format(entry, cde_label)
        )
    pass


@step('option "([^\"]+)" for radio cde "([^\"]+)" should be checked')
def postcheck_radio(step, entry, cde_label):
    xp = (
        '//label[contains(., "{0}")]/following-sibling::div'
        '/label[contains(., "{1}")]/input'.format(cde_label, entry)
    )
    outer_html = find(xp).get_attribute('outerHTML')
    assert 'checked' in outer_html,\
        (
            'Option "{0}" for cde "{1}" is not checked, but should be.'
            ''.format(entry, cde_label)
        )
    pass


@step('option "([^\"]+)" for radio cde "([^\"]+)" should NOT be checked')
def postcheck_radio_not(step, entry, cde_label):
    xp = (
        '//label[contains(., "{0}")]/following-sibling::div'
        '/label[contains(., "{1}")]/input'.format(cde_label, entry)
    )
    outer_html = find(xp).get_attribute('outerHTML')
    assert 'checked' not in outer_html,\
        (
            'Option "{0}" for cde "{1}" is checked, but should not be.'
            ''.format(entry, cde_label)
        )
    pass


@step('option "([^\"]+)" for select cde "([^\"]+)" should be selected')
def postcheck_select(step, entry, cde_label):
    xp = (
        '//label[contains(., "{0}")]/following-sibling::div'
        '/select/option[contains(., "{1}")]/input'.format(cde_label, entry)
    )
    outer_html = find(xp).get_attribute('outerHTML')
    assert 'selected' in outer_html,\
        (
            'Option "{0}" for cde "{1}" is not selected, but should be.'
            ''.format(entry, cde_label)
        )
    pass


@step('option "([^\"]+)" for select cde "([^\"]+)" should NOT be selected')
def postcheck_select_not(step, entry, cde_label):
    xp = (
        '//label[contains(., "{0}")]/following-sibling::div'
        '/select/option[contains(., "{1}")]/input'.format(cde_label, entry)
    )
    outer_html = find(xp).get_attribute('outerHTML')
    assert 'selected' not in outer_html,\
        (
            'Option "{0}" for cde "{1}" is selected, but should not be.'
            ''.format(entry, cde_label)
        )
    pass


@step('should see validation error message "([^\"]+)"')
def see_validation_error_message(step, message):
    xp = (
        '//span[@class="label label-danger" and contains(., "{0}")]'
        ''.format(message)
    )
    # Because find raises an exception if the element cannot be found,
    # this is equivalent to passing if found, and failing if not found.
    find(xp)
    pass
