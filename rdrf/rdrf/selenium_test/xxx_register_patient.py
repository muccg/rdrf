from selenium import selenium
import unittest, time, re
from base import Base

class RegisterPatient(Base):

    def test_register_patient(self):
        sel = self.selenium
        sel.open("/DM1/register/")
        sel.type("id=id_first_name", "John")
        sel.type("id=id_surname", "Doe")
        sel.type("id=id_date_of_birth", "1975-01-01")
        sel.click("id=id_gender")
        sel.type("id=id_address", "100 Neverland Street")
        sel.type("id=id_suburb", "Somwhere")
        sel.type("id=id_state", "WA")
        sel.type("id=id_postcode", "6161")
        sel.select("id=id_country", "label=Antarctica")
        sel.select("id=id_clinician", "label=John Clinician (Western Australia)")
        sel.type("id=id_username", "%s@bogus.com" % self.random_string(8))
        sel.type("id=id_password1", "password")
        sel.type("id=id_password2", "password")
        sel.click("id=registration-submit")
        sel.wait_for_page_to_load("30000")
        self.assertEqual("Thank you for registration.", sel.get_text("css=h3"))
