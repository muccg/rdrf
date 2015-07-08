from selenium import selenium
import unittest
import time
import re
from base import Base


class AddPatient(Base):

    def todo_add_patient(self):
        sel = self.selenium
        sel.open("/admin/")
        sel.type("id=id_username", "admin")
        sel.type("id=id_password", "admin")
        # btn btn-success pull-right
        sel.click("css=input.btn.btn-success")
        sel.wait_for_page_to_load("30000")
        self.assertEqual("Quick access links", sel.get_text("css=h4"))
        sel.click("xpath=(//a[contains(text(),'Patients')])[4]")
        sel.wait_for_page_to_load("30000")
        sel.click("link=Add patient")
        sel.wait_for_page_to_load("30000")
        sel.click("id=id_consent")
        sel.remove_selection("id=id_rdrf_registry", "label=Lee2 (boo)")
        sel.add_selection("id=id_rdrf_registry", "label=FH Registry (fh)")
        sel.add_selection("id=id_working_groups", "label=Western Australia")
        sel.type("id=id_family_name", "John")
        sel.type("id=id_given_names", "Doe")
        sel.click("css=img.ui-datepicker-trigger")
        sel.click("link=3")
        sel.select("id=id_sex", "label=Male")
        sel.click("name=_save")
        sel.wait_for_page_to_load("30000")
        self.assertEqual(u"\xd7 The patient \"JOHN Doe\" was added successfully.", sel.get_text(
            "//div[@id='suit-center']/div"))
        sel.click("link=Log out")
        sel.wait_for_page_to_load("30000")
