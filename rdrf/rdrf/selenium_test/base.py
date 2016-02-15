from selenium import selenium
import unittest
import time
import re
import string
import random
import os

class Base(unittest.TestCase):

    def setUp(self):
        self.verificationErrors = []
        self.selenium = selenium("hub", 4444, "*firefox", "http://web:8000")
        #self.selenium = selenium("hub", 4444, "*googlechrome", "http://web:8000")
        self.selenium.start()

    def tearDown(self):
        self.selenium.stop()
        self.assertEqual([], self.verificationErrors)

    def random_string(self, size):
        return ''.join(
            random.choice(
                string.ascii_uppercase +
                string.digits) for _ in range(size))

    def import_registry(self, yaml_file_name):
        sel = self.selenium
        sel.open("/admin/")
        sel.wait_for_page_to_load("30000")
        sel.type("id=id_username", "admin")
        sel.type("id=id_password", "admin")
        # sel.click("//input[@value='Log in']")
        # sel.wait_for_page_to_load("30000")
        # sel.click("link=Settings")
        # sel.click("link=Importer")
        # sel.wait_for_page_to_load("30000")
        # if not os.path.exists(yaml_file_name):
        #     raise Exception("yaml file %s does not exist" % yaml_file_name)
        # absolute_path = os.path.abspath(yaml_file_name)
        import requests
        from requests.auth import HTTPBasicAuth
        url = 'http://web:8000/import/'
        files = {'file': open(yaml_file_name, 'rb')}
        requests.post(url, files=files, auth=HTTPBasicAuth('admin', 'admin'))
        # sel.type("id=id_registry_yaml_file", absolute_path)
        # sel.click("id=submit-form-btn")
        # sel.wait_for_page_to_load("30000")

    def set_grid_permissions(self, group_name="Working Group Curators"):
        sel = self.selenium
        sel.open("/admin/")
        sel.type("id=id_username", "admin")
        sel.type("id=id_password", "admin")
        sel.click("//input[@value='Log in']")
        sel.wait_for_page_to_load("30000")
        sel.click("link=admin admin")
        sel.click("link=Settings")
        sel.click("link=Groups")
        sel.wait_for_page_to_load("30000")
        sel.click("link=%s" % group_name)
        sel.wait_for_page_to_load("30000")
        sel.add_selection("id=id_permissions_from", "label=patients | patient | Can see Data Modules column")
        sel.add_selection("id=id_permissions_from", "label=patients | patient | Can see Diagnosis Currency column")
        sel.add_selection("id=id_permissions_from", "label=patients | patient | Can see Diagnosis Progress column")
        sel.add_selection("id=id_permissions_from", "label=patients | patient | Can see Date of Birth column")

        sel.click("id=id_permissions_add_link")
        sel.click("link=admin admin")
        sel.click("link=Logout")
        sel.wait_for_page_to_load("30000")

