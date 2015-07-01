from selenium import selenium
import unittest, time, re
from base import Base

class NoQuestionnaire(Base):

    def test_no_questionnaire(self):
        sel = self.selenium
        sel.open("/")
        sel.click("link=Registries on this site")
        sel.click("link=FH Registry v0.1.6")
        sel.wait_for_page_to_load("30000")
        self.assertEqual("National Registry for Familial Hypercholesterolemia", sel.get_text("css=p.text-center"))
        sel.open("/fh/questionnaire")
        self.assertEqual("No questionnaire for registry fh", sel.get_text("css=div.alert.alert-danger"))
