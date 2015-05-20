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
        try:
            self.assertEqual("Home", sel.get_text("css=li.active"))
        except AssertionError, e:
            self.verificationErrors.append(str(e))
        sel.click("link=Log out")
        sel.wait_for_page_to_load("30000")
        self.assertEqual("Need a patient registry for your department, clinic or community?", sel.get_text("css=h3"))