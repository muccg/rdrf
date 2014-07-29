import logging
from django.conf import settings

logger = logging.getLogger('registry_log')

class CalculatedFieldParseError(Exception):
    pass

class CalculatedFieldParser(object):

    def __init__(self, registry, registry_form, section, cde):
        """
        A calculation is valid javascript like:

        var score = 23;
        if (context.CDE01 > 5) {
            score += 100;
        }

        score += context.CDE02;

        context.result = score;


        :param cde:
        :return:
        """
        # test
        self.context_indicator = "context"
        self.pattern =  r"\b%s\.(.+?)\b" % self.context_indicator
        self.result_name = "result"
        self.registry = registry
        self.registry_form = registry_form
        self.section = section
        self.cde = cde
        self.subjects = []
        self.calculation = self.cde.calculation.strip()
        self.observer = self.cde.code
        self.script = None
        self._parse_calculation()


    def _parse_calculation(self):
        if self.calculation:
            self.subjects = self._parse_subjects(self.calculation)

        calculation_result = self.context_indicator + "." + self.result_name
        if not calculation_result in self.calculation:
            raise CalculatedFieldParseError("Calculation does not contain %s" % calculation_result)
        if not self.subjects:
            raise CalculatedFieldParseError("Calculation does not depend on any fields")

    def _parse_subjects(self, calculation):
        import re
        return filter(lambda code: code != self.result_name, re.findall(self.pattern, calculation))

    def _get_id_in_section(self, cde_code):
        """

        :param cde_code:
        :return: in the section of the form this cde is in
        """
        return self.registry_form.name + FORM_SECTION_DELIMITER + self.section.code + FORM_SECTION_DELIMITER + cde_code

    def _replace_cde_calc(self,old_code, calc):
        s = "context.%s" % old_code
        new_s = """context["%s"]""" % (self._get_id_in_section(old_code))
        return calc.replace(s,new_s)


    def _fix_calc(self, calc):
        # hack to fix the ids to the section
        c = self._replace_cde_calc(self.cde.code,calc)
        for s in self.subjects:
            c = self._replace_cde_calc(s,c)
        return c

    def get_script(self):
        prefix = self.registry_form.name + settings.FORM_SECTION_DELIMITER + self.section.code + settings.FORM_SECTION_DELIMITER
        observer_code = self.cde.code
        subject_codes_string = ",".join(self.subjects)  # e.g. CDE02,CDE05
        calculation_body = self.calculation

        # ergh - used to map context cde codes to
        # actual dom ids
        prefix = self.registry_form.name + settings.FORM_SECTION_DELIMITER + self.section.code + settings.FORM_SECTION_DELIMITER

        javascript = """
            <script>
            $(document).ready(function(){
                 $("#id_%s%s").add_calculation({
                    subjects: "%s",
                    prefix: "%s",
                    calculation: function (context) { %s },
                    observer: "%s"
                    });
                });

            </script>""" % (prefix, observer_code, subject_codes_string, prefix, calculation_body, observer_code)

        logger.debug("calculated field js: %s" % javascript)
        return javascript
