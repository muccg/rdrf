import os

import django

from django_nose.plugin import ResultPlugin, TestReorderer
from django_nose.runner import NoseTestSuiteRunner, _get_plugins_from_settings

from aloe.runner import Runner


class GherkinNoDjangoTestDBTestRunner(NoseTestSuiteRunner):
    """
    A runner enabling the Gherkin plugin in nose.
    This is the same as the GherkinTestRunner from aloe_django, but we don't use
    the DjangoSetUpPlugin.
    Our aloe tests are running against a stack we start up with the normal DB settings,
    so we want to avoid the setup and usage of the test database.
    """

    def run_suite(self, nose_argv):
        """
        Use Gherkin main program to run Nose.
        """

        result_plugin = ResultPlugin()
        plugins_to_add = [  # Disabling the DjangoSetUpPlugin
            # DjangoSetUpPlugin(self),
            result_plugin,
            TestReorderer()]

        for plugin in _get_plugins_from_settings():
            plugins_to_add.append(plugin)

        django.setup()

        # Set up Gherkin test subclass
        test_class = getattr(django.conf.settings, 'GHERKIN_TEST_CLASS',
                             'aloe_django.TestCase')
        env = os.environ.copy()
        env['NOSE_GHERKIN_CLASS'] = test_class

        Runner(argv=nose_argv, exit=False,
               addplugins=plugins_to_add,
               env=env)
        return result_plugin.result
