class CalculatedFieldParseError(Exception):
    pass

class CalculatedFieldParser(object):

    def __init__(self, cde):
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
        self.context_indicator = "context"
        self.pattern =  r"\b%s\.(.+?)\b" % self.context_indicator
        self.result_name = "result"
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

    def get_script(self):
        observer_code = self.cde.code # e.g. #CDE01
        subject_codes_string = ",".join(self.subjects)  # e.g. CDE02,CDE05
        calculation_body = self.calculation  # E.g. context.result = parseInt(context.CDE05) + parseInt(context.CDE02)
        javascript = """
            <script>
            $(document).ready(function(){
                 $("#id_%s").add_calculation({
                    subjects: "%s",
                    calculation: function (context) { %s },
                    observer: "%s"
                    });
                });

            </script>""" % (observer_code, subject_codes_string, calculation_body, observer_code)

        logger.debug("calculated field js: %s" % javascript)
        return javascript
