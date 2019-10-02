import logging
import re

from django.core.exceptions import ValidationError
from django.utils.translation import ugettext as _

logger = logging.getLogger(__name__)


class ValidationType:
    MIN = 0
    MAX = 1
    PATTERN = 2
    LENGTH = 3


def make_validation_func(val_type, cde):
    if val_type == ValidationType.MIN:
        def vf(value):
            if value < cde.min_value:
                raise ValidationError(
                    _("Value of %(value)s for %(cdename)s is less than minimum value %(cdemin_value)s") %
                    {"value": value, "cdename": cde.name, "cdemin_value": cde.min_value})

        return vf
    elif val_type == ValidationType.MAX:
        def vf(value):
            if value > cde.max_value:
                raise ValidationError(
                    _("Value of %(value)s for %(cdename)s is more than maximum value %(cdemax_value)s") %
                    {"value": value, "cdename": cde.name, "cdemax_value": cde.max_value})
        return vf
    elif val_type == ValidationType.PATTERN:
        try:
            re_pattern = re.compile(cde.pattern)
        except Exception:
            logger.warning("CDE %s has bad pattern: %s" % (cde, cde.pattern))
            return None

        def vf(value):
            if not re_pattern.match(value):
                raise ValidationError(
                    _("Value of %(value)s for %(cdename)s does not match pattern '%(cdepattern)s'") % {
                        "value": value,
                        "cdename": cde.name,
                        "cdepattern": cde.pattern})
        return vf
    elif val_type == ValidationType.LENGTH:
        def vf(value):
            if len(value) > cde.max_length:
                raise ValidationError(
                    _("Value of '%(value)s' for %(name)s is longer than max length of %(max)s") % {
                        "value": value,
                        "name": cde.name,
                        "max": cde.max_length})
        return vf
    else:
        raise Exception(_("Unknown ValidationType %s") % val_type)


class ValidatorFactory(object):

    def __init__(self, cde):
        self.cde = cde

    def _is_numeric(self):
        return self.cde.datatype.lower() in ["integer", "float"]

    def _is_string(self):
        return self.cde.datatype.lower() in ["string", "alphanumeric"]

    def _is_range(self):
        return self.cde.pv_group is not None

    def create_validators(self):
        validators = []

        if self._is_numeric():
            if self.cde.max_value is not None:
                validate_max = make_validation_func(ValidationType.MAX, self.cde)
                validators.append(validate_max)

            if self.cde.min_value is not None:
                validate_min = make_validation_func(ValidationType.MIN, self.cde)
                validators.append(validate_min)

        if self._is_string():
            if self.cde.pattern:
                try:
                    validate_pattern = make_validation_func(ValidationType.PATTERN, self.cde)
                    if validate_pattern is not None:
                        validators.append(validate_pattern)
                except Exception as ex:
                    logger.error(
                        "Could not pattern validator for string field of cde %s pattern %s: %s" %
                        (self.cde.name, self.cde.pattern, ex))

            if self.cde.max_length:
                validate_length = make_validation_func(ValidationType.LENGTH, self.cde)
                validators.append(validate_length)

        return validators
