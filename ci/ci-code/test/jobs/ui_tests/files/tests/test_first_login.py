import unittest
from src.commands import *
from src.logger import get_logger

logger = get_logger(__name__)


class FirstLoginTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """
        Set up the webdriver, login to kaapana and open the url to the meta_dashboard.
        This method is called once at initialization of the class
        """
        from src.helper import MainDriver

        MainDriver.start()

    def test_first_login(self):
        logger.info("Start first login to platform.")
        self.assertTrue(
            first_login(
                user="kaapana", default_password="kaapana", new_password="admin"
            )
        )

    @classmethod
    def tearDownClass(cls):
        MainDriver.quit()
