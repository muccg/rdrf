import logging
logger = logging.getLogger("registry_log")

from django.core.exceptions import ValidationError

class ValidatorFactory(object):
    def __init__(self, cde):
        self.cde = cde

    def _is_numeric(self):
        return self.cde.datatype.lower() in ["integer", "float"]

    def _is_string(self):
        return self.cde.datatype.lower() in ["string", "alphanumeric" ]

    def _is_range(self):
        return self.cde.pv_group is not None

    def create_validators(self):
        validators = []

        if self._is_numeric():
            if self.cde.max_value:
                def validate_max(value):
                    logger.debug("%s validaton: value = %s max value = %s" % (self.cde, value, self.cde.max_value))
                    if value > self.cde.max_value:
                        raise ValidationError("Value of %s for %s is more than maximum value %s" % (value, self.cde.code, self.cde.max_value))
                validators.append(validate_max)

            if self.cde.min_value:
                def validate_min(value):
                    if value < self.cde.min_value:
                        raise ValidationError("Value of %s for %s is less than minimum value %s" % (value, self.cde.code, self.cde.min_value))

                validators.append(validate_min)

        if self._is_string():
            if self.cde.pattern:
                import re
                try:
                    re_pattern = re.compile(self.cde.pattern)
                    def validate_pattern(value):
                        if not re_pattern.match(value):
                            raise ValidationError("Value of %s for %s does not match pattern '%s'" % (value, self.cde.code, self.cde.pattern))
                    validators.append(validate_pattern)
                except Exception,ex:
                    logger.error("Could not pattern validator for string field of cde %s pattern %s: %s" % (self.cde.code, self.cde.pattern, ex))

            if self.cde.max_length:
                def validate_length(value):
                    if len(value) > self.cde.length:
                        raise ValidationError("Value of '%s' for %s is longer than max length of %s" % (value, self.cde.code, self.cde.max_length))
                validators.append(validate_length)


        return validators
