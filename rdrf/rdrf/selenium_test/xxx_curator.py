from selenium import selenium
import unittest, time, re
from base import Base

class Curator(Base):

    def test_curator_no_import(self):
        sel = self.selenium
        sel.open("/admin/")
        sel.type("id=id_username", "fhcurator")
        sel.type("id=id_password", "fhcurator")
        sel.click("css=input.btn.btn-success")
        sel.wait_for_page_to_load("30000")
        try: self.assertNotEqual("Import Registry", sel.get_text("//*"))
        except AssertionError, e: self.verificationErrors.append(str(e))