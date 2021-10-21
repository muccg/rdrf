from .settings import *  # noqa
from .settings import INSTALLED_APPS

INSTALLED_APPS += [
    'aloe_django',
    'django_nose',
]

SOUTH_TESTS_MIGRATE = True

TEST_RUNNER = 'xmlrunner.extra.djangotestrunner.XMLTestRunner'

# Used by Aloe tests, custom TestRunner
# We don't want to run against the Test DB and we don't want a Transaction Test Case
GHERKIN_TEST_RUNNER = 'rdrf.testing.behaviour.features.runner.GherkinNoDjangoTestDBTestRunner'
GHERKIN_TEST_CLASS = 'aloe.testclass.TestCase'

MIGRATION_MODULES = {"iprestrict": None}
IPRESTRICT_GEOIP_ENABLED = False
CACHE_DISABLED = True
HUB_ENABLED = True
HL7_VERSION = "2.6"
APP_ID = "CIC"
SENDING_FACILITY = "9999^cicfacility.9999^L"
HUB_APP_ID = "ESB^HdwaApplication.ESB^L"
HUB_FACILITY = "ESB^HdwaApplication.ESB^L"
HUB_PORT = 30000
HUB_MOCKED = True
HUB_ENDPOINT = "mock"
