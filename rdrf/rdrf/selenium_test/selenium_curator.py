from selenium import selenium
import unittest
import time
import re
from base import Base


class Curator(Base):

    def test_curator(self):
        #self.set_grid_permissions()
        sel = self.selenium
        sel.open("/")
        sel.click("link=Registries on this site")
        sel.click("link=Sample Registry")
        sel.wait_for_page_to_load("30000")
        self.assertEqual(
            "Sample Registry",
            sel.get_text("//div[@class='container']/h1/text()"))

        sel.click("link=Log in")
        sel.wait_for_page_to_load("30000")
        sel.type("id=id_username", "curator")
        sel.type("id=id_password", "curator")
        sel.click("//input[@value='Log in']")
        sel.wait_for_page_to_load("30000")

        sel.click("css=span.glyphicon.glyphicon-user")
        sel.click("link=Logout")
        sel.wait_for_page_to_load("30000")
        self.assertEqual("Log in", sel.get_text("link=Log in"))
