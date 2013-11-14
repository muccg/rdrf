from datetime import date

from django import forms
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext
from registry.utils import get_static_url


class DateFormatError(ValueError):
    pass


class DateWidget(forms.Widget):
    class Media:
        css = {"all": [get_static_url("date/date.css")]}
        js = [get_static_url("js/json2.js"),
              get_static_url("date/date.js")]

    def __init__(self, attrs={}, format="%d %B %Y", popup=False, today=False, years=None, required=True):
        self.attrs = dict(attrs)

        if "class" in self.attrs:
            self.attrs["class"] += " date"
        else:
            self.attrs["class"] = "date"

        # We'll handle the today and popup links mostly in Javascript, but we
        # still need to tell it that we want them. I went back and forth a bit
        # as to whether the "today" link should actually set the date to the
        # server's date or the client's, but have decided to go with the
        # client's for now: there's less WTF for the user that way.
        if popup:
            # We need to send the translated versions of the day names down.
            from django.utils.dates import WEEKDAYS_ABBR
            from json import dumps

            popup = {
                "image": get_static_url("images/icon_calendar.gif"),
                "weekdays": [(id, unicode(name)) for (id, name) in WEEKDAYS_ABBR.items()],
            }

            self.attrs["popup"] = dumps(popup)

        if today:
            self.attrs["today"] = ugettext("Today")

        super(DateWidget, self).__init__(self.attrs)

        self.format = format

        # Work out the range of years that we need to show in the dropdown.
        if type(years) is int:
            # This is the number of years to go back/forward from this year.
            now = date.today().year
            other = now + years

            if now < other:
                self.years = range(now, other + 1)
            else:
                self.years = range(other, now + 1)
        else:
            self.years = years

        self.formats = {
            "%b": AbbreviatedMonthName(),
            "%B": MonthName(),
            "%d": DayOfMonth(),
            "%m": Month(),
            "%y": AbbreviatedYear(self.years),
            "%Y": Year(self.years),
        }

    def render(self, name, value, attrs=None):
        import re

        # If value is a string, we need to parse it. For now, we'll just let
        # the exception bubble up if parsing fails.
        if type(value) is str:
            year, month, day = [int(part) for part in value.split("-")]

            class Value:
                year = month = day = None

            value = Value()
            value.year, value.month, value.day = year, month, day

        formats = re.findall(r"(%[A-Za-z])([^%]*)", self.format)

        # Start by plonking whatever text was before the first % into the
        # output.
        try:
            pos = self.format.index("%")
            output = [self.format[0:pos]]
        except ValueError:
            output = []

        # Now work through the format strings and output the relevant controls.
        for format in formats:
            format, trail = format

            if format in self.formats:
                formatter = self.formats[format]
                output.append(formatter.render(name, value, attrs))
            else:
                raise DateFormatError("Unknown format: " + format)

            output.append(trail)

        # Set up the div container.
        def make_attribute(name, value):
            from cgi import escape
            return u'%s="%s"' % (escape(name), escape(value, True))

        container_attrs = [make_attribute(name, value) for (name, value) in attrs.iteritems()]
        container_attrs += [make_attribute(name, value) for (name, value) in self.attrs.iteritems()]

        container = u"<div " + " ".join(container_attrs) + ">"

        return mark_safe(container + u"\n".join(output) + u"</div>")

    def value_from_datadict(self, data, files, name):
        today = date.today()

        # If the year's blank, we'll assume that the user wants None and let
        # the usual validation routines figure it out from there.
        year = data.get(name + "_year")
        if year == "" or year is None:
            return None

        # Look for the relevant values in the dict.  We're wrapping this so
        # that we can handle blank strings appropriately.
        def dict_value_as_int(name, default):
            try:
                return int(data.get(name, default))
            except ValueError:
                return default

        year = dict_value_as_int(name + "_year", today.year)
        month = dict_value_as_int(name + "_month", today.month)
        day = dict_value_as_int(name + "_day", today.day)

        if year is None or month is None or day is None:
            return None

        return "%04d-%02d-%02d" % (year, month, day)


class Formatter(object):
    def render(self):
        raise NotImplemented


class Month(Formatter):
    def render(self, name, value, attrs):
        choices = [(month, month) for month in range(1, 13)]
        return self.render_choices(name, value, attrs, choices)

    def render_choices(self, name, value, attrs, choices):
        attrs = dict(attrs)

        attrs["parent"] = name
        attrs["type"] = "month"
        attrs["id"] = name = name + "_month"

        select = forms.Select(choices=choices)
        return select.render(name, self.value(value), attrs)

    def value(self, value):
        try:
            return value.month
        except AttributeError:
            return None


class AbbreviatedMonthName(Month):
    def render(self, name, value, attrs):
        from django.utils.dates import MONTHS_3

        choices = [(id, name.title()) for id, name in MONTHS_3.items()]
        return self.render_choices(name, value, attrs, choices)


class MonthName(Month):
    def render(self, name, value, attrs):
        from django.utils.dates import MONTHS
        return self.render_choices(name, value, attrs, MONTHS.items())


class DayOfMonth(Formatter):
    def render(self, name, value, attrs):
        attrs = dict(attrs)

        attrs["parent"] = name
        attrs["type"] = "day"
        attrs["id"] = name = name + "_day"

        try:
            default = value.day
        except AttributeError:
            default = None

        choices = [(day, day) for day in range(1, 32)]
        select = forms.Select(choices=choices)
        return select.render(name, default, attrs)


class Year(Formatter):
    def __init__(self, years):
        self.years = years

    def render(self, name, value, attrs):
        choices = [(year, ) for year in self.years]
        return self.render_choices(name, value, attrs, choices)

    def render_choices(self, name, value, attrs, choices):
        attrs = dict(attrs)

        attrs["parent"] = name
        attrs["type"] = "year"
        attrs["id"] = name = name + "_year"

        try:
            default = value.year
        except AttributeError:
            default = None

        from widgets import ComboWidget
        widget = ComboWidget(attrs={"size": 5}, options=choices)
        return widget.render(name, default, attrs)


class AbbreviatedYear(Year):
    def render(self, name, value, attrs):
        choices = [(year, ("%02d" % (year % 100))) for year in self.years]
        return self.render_choices(name, value, attrs, choices)
