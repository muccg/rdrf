from selenium import selenium
import unittest, time, re
from base import Base

class AdminLogin(Base):

    def test_admin_login(self):
        sel = self.selenium
        sel.open("/admin/")
        sel.type("id=id_username", "admin")
        sel.type("id=id_password", "admin")
        sel.click("css=input.btn.btn-info")
        sel.wait_for_page_to_load("30000")
        self.assertEqual("Show full list of links", sel.get_text("css=#full-menu-alert > h4"))
        sel.click("link=Log out")
        sel.wait_for_page_to_load("30000")
        self.assertEqual("The following registries are defined on this site", sel.get_text("css=h3"))