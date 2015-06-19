from selenium import selenium
import unittest, time, re
from base import Base

class OpenQuestionnaire(Base):
    
    def test_open_questionnaire(self):
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
        sel.click("id=id_is_questionnaire")
        sel.click("name=_save")
        sel.wait_for_page_to_load("30000")
        sel.click("link=Log out")
        sel.wait_for_page_to_load("30000")
        sel.open("/DM1/questionnaire")
        self.assertEqual("Red fields are required", sel.get_text("id=msg-box"))
        sel.open("/admin/")
        sel.type("id=id_username", "admin")
        sel.type("id=id_password", "admin")
        sel.click("css=input.btn.btn-info")
        sel.wait_for_page_to_load("30000")
        sel.click("link=Registry forms")
        sel.wait_for_page_to_load("30000")
        sel.click("link=Myotonic Dystrophy (DM1)")
        sel.wait_for_page_to_load("30000")
        sel.click("id=id_is_questionnaire")
        sel.click("name=_save")
        sel.wait_for_page_to_load("30000")
        sel.click("link=Log out")
        sel.wait_for_page_to_load("30000")
