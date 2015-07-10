import logging
from functools import reduce
logger = logging.getLogger('registry_log')


class SimpleReport(object):
    NAME = ""
    SPEC = []
    QUERY = None

    def query(self):
        raise NotImplementedError("Subclasses must override and return a Django Query Object")

    def _get_report_field(self, field_spec):
        return field_spec[0]

    def _get_selector_function(self, field_spec):
        selector = field_spec[1]

        if isinstance(selector, str) or isinstance(selector, basestring):

            def mk_lookup(selector):
                def g(obj):
                    parts = selector.split(".")
                    return reduce(getattr, parts, obj)
                return g

            return mk_lookup(selector)

        elif callable(selector):
            return selector
        else:
            raise Exception("Unknown selector: %s" % selector)

    def _get_formatting_function(self, field_spec):
        if len(field_spec) == 3:
            return field_spec[2]
        else:
            return lambda value: "%s" % value

    def _data_rows(self):
        results = []
        spec = [[self._get_report_field(field_spec),
                 self._get_selector_function(field_spec),
                 self._get_formatting_function(field_spec)] for field_spec in self.SPEC]

        logger.info("starting report %s" % self.NAME)

        for obj in self.query():
            logger.debug("checking %s" % obj)
            items = {}
            for report_field, selector_function, formatting_function in spec:
                try:
                    report_value = formatting_function(selector_function(obj))
                    logger.debug("%s = %s" % (report_field, report_value))
                except Exception as ex:
                    obj_class_name = obj.__class__.__name__
                    id = obj.pk
                    e = "Error retrieving %s in %s report for %s id %s: %s" % (report_field,
                                                                               self.NAME,
                                                                               obj_class_name,
                                                                               id,
                                                                               ex)
                    report_value = "#ERROR"
                    logger.error(e)

                items[report_field] = report_value
            results.append(items)

        logger.info("finished report %s" % self.NAME)

        return results

    def write_with(self, writer):
        headers = [field_spec[0] for field_spec in self.SPEC]
        writer.writerow(headers)

        for row_data in self._data_rows():
            row = [row_data[field_spec[0]] for field_spec in self.SPEC]
            writer.writerow(row)
