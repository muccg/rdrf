# -*- coding: utf-8 -*-
from selenium import selenium
import unittest, time, re
from base import Base


class SaveNewlyCreatedRegisterForm(Base):

    def test_adding_registry_form_is_ok(self):
        sel = self.selenium
        sel.open("/login?next=/router/")
        sel.wait_for_page_to_load("30000")
        sel.type("id=id_password", "admin")
        sel.type("id=id_username", "admin")
        sel.click("css=input.btn.btn-success")
        sel.wait_for_page_to_load("30000")
        sel.open("/admin/rdrf/registryform/")
        sel.wait_for_page_to_load("30000")
        sel.click("link=Add")
        sel.wait_for_page_to_load("30000")
        sel.select("id=id_registry", "label=Facioscapulohumeral Muscular Dystrophy (fshd)")
        sel.type("id=id_name", "testingformforfshd")
        sel.click("name=_save")
        sel.wait_for_page_to_load("30000")
        try: self.assertEqual("Please correct the errors below.", sel.get_text("css=p.errornote"))
        except AssertionError, e: self.verificationErrors.append(str(e))
        sel.type("id=id_sections", "adummysection")
        sel.click("name=_save")
        sel.wait_for_page_to_load("30000")
        try: self.assertEqual(u"× The registry form \"Facioscapulohumeral Muscular Dystrophy (fshd) testingformforfshd Form comprising adummysection\" was added successfully.", sel.get_text("//div[@id='suit-center']/div"))
        except AssertionError, e: self.verificationErrors.append(str(e))