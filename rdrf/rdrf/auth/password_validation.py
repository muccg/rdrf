import re

from django.core.exceptions import ValidationError
from django.utils.translation import ungettext


class BaseHasCharacterValidator():
    name = None
    pattern = None

    def __init__(self, min_occurences=1):
        self.min_occurences = min_occurences

    @property
    def msg(self):
        return 'The password must contain at least %(min_occurences)s ' + self.name + '.'

    @property
    def msg_plural(self):
        return 'The password must contain at least %(min_occurences)s ' + self.name + 's.'

    @property
    def help_text(self):
        return 'Your password must contain at least %(min_occurences)s ' + self.name + '.'

    @property
    def help_text_plural(self):
        return 'Your password must contain at least %(min_occurences)s ' + self.name + 's.'

    def validate(self, password, user=None):
        if len(self.pattern.findall(password)) < self.min_occurences:
            raise ValidationError(
                ungettext(self.msg, self.msg_plural, self.min_occurences),
                code='password_does_not_have_enough_%ss' % self.name,
                params={'min_occurences': self.min_occurences},
            )

    def get_help_text(self):
        return ungettext(self.help_text, self.help_text_plural, self.min_occurences) % {
            'min_occurences': self.min_occurences}


class HasNumberValidator(BaseHasCharacterValidator):
    name = 'number'
    pattern = re.compile(r'\d')


class HasUppercaseLetterValidator(BaseHasCharacterValidator):
    name = 'uppercase letter'
    pattern = re.compile(r'[A-Z]')


class HasLowercaseLetterValidator(BaseHasCharacterValidator):
    name = 'lowercase letter'
    pattern = re.compile(r'[a-z]')


class HasSpecialCharacterValidator(BaseHasCharacterValidator):
    name = 'special character'
    pattern = re.compile(r'[!@#\$%\^&\*]')
