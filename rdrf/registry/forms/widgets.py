from django import forms
from django.utils.html import escape
from django.utils.safestring import mark_safe
from registry.utils import get_static_url

from django.forms.widgets import RadioFieldRenderer
from django.utils.encoding import force_unicode
from django.forms.widgets import RadioSelect

class ComboWidget(forms.TextInput):
    class Media:
        css = {"all": [get_static_url("combo/combo.css")]}
        js = [get_static_url("combo/combo.js"), get_static_url("js/json2.js"), get_static_url("js/xhr.js")]

    def __init__(self, attrs={}, options=[]):
        """
        This widget requires the options within the dropdown to be provided via
        the options parameter. This is expected to be an array of either
        strings or nested arrays -- in the latter case, the elements within the
        nested array will be rendered as cells within a dropdown row.
        """

        import json

        if "class" in attrs:
            attrs["class"] += " combo"
        else:
            attrs["class"] = "combo"

        attrs["options"] = json.dumps(options)

        super(ComboWidget, self).__init__(attrs)


class LiveComboWidget(ComboWidget):
    class Media:
        css = {"all": ComboWidget.Media.css["all"] + [get_static_url("combo/live.css")]}
        js = ComboWidget.Media.js + [get_static_url("combo/live.js")]

    def __init__(self, attrs={}, backend=""):
        """
        The backend parameter is the URL used for retrieving dropdown results
        via AJAX. The search term will be appended to whatever is given. For
        example: given a backend of "/search/", searching for "foo" would
        result in the URL "/search/foo" being requested. Similarly, a backend
        "/search?query=" would result in search requests being made to
        "/search?query=foo".

        The backend is expected to return an array encoded in JSON form. The
        array can contain either strings (which will simply be presented to the
        user as a dropdown), or nested arrays, in which case each array element
        will be presented as a cell in a row within the dropdown, and the first
        element will also be used as the value when the row is selected.

        Errors from the backend should be signalled via the HTTP status: if 200
        OK is returned, then the content is expected to be valid JSON
        conforming to the aforementioned standard. 4xx and 5xx status codes
        will result in no dropdown being displayed, although no further error
        message will be shown to the user.

        This widget also supports two optional attributes: keytimeout, which is
        the number of milliseconds after a key press that an AJAX search should
        take place (by default, this is 500 milliseconds, or half a second --
        you don't want it to be too short, since it will unduly load the
        server), and minchars, which is the minimum numbers of characters that
        need to be entered into the input box before a search will be executed
        (by default this is 3, since large result sets would slow the browser
        down).
        """

        attrs["backend"] = backend

        # We need to do the __init__ first, then munge attrs later to avoid
        # the basic combo JS firing.
        super(LiveComboWidget, self).__init__(attrs)

        self.attrs["class"] = self.attrs["class"].replace("combo", "live-combo")
        del self.attrs["options"]

    #def render(self, name, value, attrs=None):
        #print 'rendering ', value
        #super(LiveComboWidget, self).render(name, value, attrs=attrs)


class StaticWidget(forms.HiddenInput):
    def __init__(self, attrs=None, text=None):
        self.text = text
        super(StaticWidget, self).__init__(attrs)

    def render(self, name, value, attrs=None):
        if self.text:
            text = self.text
        else:
            text = value
        return mark_safe(super(StaticWidget, self).render(name, value, attrs) + escape(unicode(text)))

    def _has_changed(self, initial, data):
        # Static input fields never change.
        return False


class PercentageWidget(forms.TextInput):
    def __init__(self, attrs={}, *args, **kwargs):
        '''
        if attrs:
            attrs["size"] = 3
        else:
            attrs = {"size": 3}
        '''
        if not attrs:
            attrs = {"size": "3"}

        super(PercentageWidget, self).__init__(attrs, *args, **kwargs)

    def render(self, name, value, attrs=None):
        return mark_safe(super(PercentageWidget, self).render(name, value, attrs) + " %")


# to add the text after the input field
class FVCPercentageWidget(forms.TextInput):
    def __init__(self, attrs={}, *args, **kwargs):
        if attrs:
            attrs["size"] = 3
        else:
            attrs = {"size": 3}

        super(FVCPercentageWidget, self).__init__(attrs, *args, **kwargs)

    def render(self, name, value, attrs=None):
        return super(FVCPercentageWidget, self).render(name, value, attrs) + "% (to 2 decimal places based on last spirometer reading)"

class NoDotsRadioFieldRenderer(RadioFieldRenderer):
    """
    Produces a list of radio buttons without dots to the left of each
    option.
    """
    def render(self):
        """Outputs a <ul> for this set of radio fields."""
        return mark_safe(u'<ul class="no-dots">\n%s\n</ul>' % u'\n'.join([u'<li>%s</li>'
                % force_unicode(w) for w in self]))

class NoDotsRadioSelect(RadioSelect):
    renderer = NoDotsRadioFieldRenderer
    

class TextWidget(forms.HiddenInput):
    def __init__(self, attrs=None, text=None, label=None):
        self.text = text
        self.label = label
        super(TextWidget, self).__init__(attrs)

    def render(self, name, value, attrs=None):
        value = self.text
        return mark_safe(super(TextWidget, self).render(name, value, attrs) + escape(unicode(self.label)))

    def _has_changed(self, initial, data):
        return False
