from .settings import INSTALLED_APPS
from .settings import *  # noqa

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
