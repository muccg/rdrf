from selenium import selenium
import unittest, time, re
from base import Base

class NoQuestionnaire(Base):

    def test_no_questionnaire(self):
        sel = self.selenium
        sel.open("/admin/")
        sel.type("id=id_username", "admin")
        sel.type("id=id_password", "admin")
        sel.click("css=input.btn.btn-success")
        sel.wait_for_page_to_load("30000")
        sel.click("link=Registry forms")
        sel.wait_for_page_to_load("30000")
        sel.click("link=Myotonic Dystrophy (DM1)")
        sel.wait_for_page_to_load("30000")
        try: self.assertEqual("off", sel.get_value("id=id_is_questionnaire"))
        except AssertionError, e: self.verificationErrors.append(str(e))
        sel.click("name=_save")
        sel.wait_for_page_to_load("30000")
        sel.click("link=Log out")
        sel.wait_for_page_to_load("30000")
        sel.open("/DM1/questionnaire/")
        self.assertEqual("No questionnaire for registry DM1", sel.get_text("css=div.alert.alert-danger"))
