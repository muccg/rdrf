from selenium import selenium
import unittest
import time
import re
from base import Base


class NoQuestionnaire(Base):

    def test_no_questionnaire(self):
        sel = self.selenium
        sel.open("/")
        sel.click("link=Registries on this site")
        sel.click("link=Sample Registry")
        sel.wait_for_page_to_load("30000")
        self.assertEqual(
            "Sample Registry",
            sel.get_text("//div[@class='container']/h1/text()"))
        sel.open("/sample/questionnaire")
        self.assertEqual(
            "No questionnaire for registry sample", sel.get_text("css=div.alert.alert-danger"))
