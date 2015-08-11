from selenium import selenium
import unittest
import time
import re
import string
import random


class Base(unittest.TestCase):

    def setUp(self):
        self.verificationErrors = []
        #self.selenium = selenium("hub", 4444, "*firefox", "http://web:8000")
        self.selenium = selenium("hub", 4444, "*googlechrome", "http://web:8000")
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
        sel.click("//input[@value='Log in']")
        sel.wait_for_page_to_load("30000")
        sel.click("link=Settings")
        sel.click("link=Importer")
        sel.wait_for_page_to_load("30000")
        sel.type("id=id_registry_yaml_file", "definitions/registries/%s" % yaml_file_name)
        sel.click("id=submit-form-btn")
        sel.wait_for_page_to_load("30000")
