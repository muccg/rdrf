from django import forms
from django.core.urlresolvers import reverse_lazy, get_script_prefix

from registry.forms.widgets import ComboWidget, LiveComboWidget, StaticWidget
from registry.genetic.models import *
from registry.utils import get_static_url

from models import *


class GeneChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        print 'doing label from instance %i', obj.id
        return obj.symbol

    def prepare_value(self, value):
        print 'preparing value: ', str(value)
        #newval = ""
        #try:
        #    newval = Gene.objects.get(symbol=value).id
        #except:
        #    pass

        return super(GeneChoiceField, self).prepare_value(value)


    def validate(self, value):
        print 'validating model: ', value, str(dir(value))
        return super(GeneChoiceField, self).validate(value)


class VariationWidget(forms.TextInput):
    class Media:
        css = {"all": [get_static_url("css/variation.css")]}
        js = [get_static_url("js/json2.js"),
              get_static_url("js/xhr.js"),
              get_static_url("variation/variation.js")
              ]

    def __init__(self, attrs={}, backend=None, popup=None):
        """
        The backend will have genetic variation strings POSTed to it as plain
        text, and is expected to respond with a 204 No Content if the string is
        valid, or 400 Bad Request if the string isn't valid. In the latter
        case, a JSON array of strings containing the relevant errors should be
        returned.
        """

        attrs["backend"] = backend

        if popup:
            attrs["variation-popup"] = popup

        if "class" in attrs:
            attrs["class"] += " variation"
        else:
            attrs["class"] = "variation"

        self.popup=reverse_lazy("registry:entry") # do not think this is required, have left in case needed under wsgi
        super(VariationWidget, self).__init__(attrs)


class MolecularDataForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(MolecularDataForm, self).__init__(*args, **kwargs)
        # make the patient field static if not a new molecular data record
        if "instance" in kwargs:
            self.fields["patient"] = forms.ModelChoiceField(Patient.objects.all(), widget=StaticWidget(text=unicode(kwargs["instance"])))

    class Meta:
        model = MolecularData


class MolecularDataSmaForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(MolecularDataSmaForm, self).__init__(*args, **kwargs)
        # make the patient field static if not a new molecular data record
        if "instance" in kwargs:
            self.fields["patient"] = forms.ModelChoiceField(Patient.objects.all(), widget=StaticWidget(text=unicode(kwargs["instance"])))

    class Meta:
        model = MolecularDataSma


class VariationForm(forms.ModelForm):
    gene = GeneChoiceField(queryset=Gene.objects.all(), label="Gene", widget=LiveComboWidget(backend=reverse_lazy("admin:gene_search", args=("",))))
    exon = forms.CharField(label="Exon", required=False, widget=VariationWidget(backend=reverse_lazy("admin:validate_exon"), attrs={"minchars": "0"}))
    protein_variation = forms.CharField(label="Protein variation", required=False, widget=VariationWidget(backend=reverse_lazy("admin:validate_protein")))
    dna_variation = forms.CharField(label="DNA variation", required=False, widget=VariationWidget(backend=reverse_lazy("admin:validate_sequence"), popup=get_script_prefix()+'genetic/variation/'))
    rna_variation = forms.CharField(label="RNA variation", required=False, widget=VariationWidget(backend=reverse_lazy("admin:validate_sequence"), popup=get_script_prefix()+'genetic/variation/'))
    technique = forms.CharField(label="Technique", widget=ComboWidget(options=["MLPA", "Genomic DNA sequencing", "cDNA sequencing", "Array"]))

    class Meta:
        model = Variation

class VariationSmaForm(forms.ModelForm):
    technique = forms.CharField(label="Technique", widget=ComboWidget(options=["MLPA", "Genomic DNA sequencing", "cDNA sequencing", "Array"]))

    class Meta:
        model = VariationSma