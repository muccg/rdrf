from selenium import selenium
import unittest
import time
import re
from base import Base


class Curator(Base):

    def test_curator(self):
        sel = self.selenium
        sel.open("/")
        sel.click("link=Registries on this site")
        sel.click("link=FH Registry v0.1.6")
        sel.wait_for_page_to_load("30000")
        self.assertEqual(
            "National Registry for Familial Hypercholesterolemia",
            sel.get_text("css=p.text-center"))
        sel.click("link=Log in")
        sel.wait_for_page_to_load("30000")
        sel.type("id=id_username", "fhcurator")
        sel.type("id=id_password", "fhcurator")
        sel.click("//input[@value='Log in']")
        sel.wait_for_page_to_load("30000")
        self.assertEqual("Updated < 365 days", sel.get_text(
            "//table[@id='grid']/thead/tr/th[5]/a/span"))
        sel.click("css=span.glyphicon.glyphicon-user")
        sel.click("link=Logout")
        sel.wait_for_page_to_load("30000")
        self.assertEqual("Log in", sel.get_text("link=Log in"))
