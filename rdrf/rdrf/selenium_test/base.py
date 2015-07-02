from selenium import selenium
import unittest, time, re
import string
import random

class Base(unittest.TestCase):
    def setUp(self):
        self.verificationErrors = []
        #self.selenium = selenium("hub", 4444, "*firefox", "http://web:8000")
        self.selenium = selenium("hub", 4444, "*googlechrome", "http://web:8000")
        self.selenium.start()
    
    def tearDown(self):
        self.selenium.stop()
        self.assertEqual([], self.verificationErrors)
        
    def random_string(self, size):
        return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(size))
