from selenium import selenium
from base import Base


class AdminLogin(Base):

    def test_admin_login(self):
        sel = self.selenium
        sel.open("/")
        sel.click("link=Registries on this site")
        sel.click("link=Sample Registry")
        sel.wait_for_page_to_load("30000")
        sel.click("link=Log in")
        sel.wait_for_page_to_load("30000")
        sel.type("id=id_username", "admin")
        sel.type("id=id_password", "admin")
        sel.click("//input[@value='Log in']")
        sel.wait_for_page_to_load("30000")
        self.assertEqual("Settings", sel.get_text("link=Settings"))
        sel.click("link=admin admin")
        sel.click("link=Logout")
        sel.wait_for_page_to_load("30000")
        self.assertEqual("Log in", sel.get_text("link=Log in"))
