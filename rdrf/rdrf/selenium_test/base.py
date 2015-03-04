from selenium import selenium
import unittest, time, re

class Base(unittest.TestCase):
    def setUp(self):
        self.verificationErrors = []
        self.selenium = selenium("hub", 4444, "*firefox", "http://web:8000")
        self.selenium.start()
    
    def tearDown(self):
        self.selenium.stop()
        self.assertEqual([], self.verificationErrors)