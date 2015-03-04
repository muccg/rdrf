from django.forms import widgets
import logging
import hashlib
import random
from django.core.urlresolvers import reverse

logger = logging.getLogger("registry_log")


class PatientRelativeLinkWidget(widgets.Widget):
    """
    This provides a link to the patient created from the relative
    Before the patient is created , it provides a checkbox ( Similar to the delete checkbox provided against other inlines )
    - checking it signals  that a patient should be created from the patient relative data supplied.
    There is also javascript to hide the green plus symbol to avoid the popup
    """
    def render(self, name, value, attrs=None):
        script = """<script>
                        function setupCreatePatientCheckBox(id) {
                            var checkBox = $("#" + id);
                            checkBox.hide();
                            checkBox.closest("tr").find(":input[type='hidden']").each(function () {
                                var inputName = $(this).attr("name");
                                if (inputName.match(/^relatives-\d+-id$/)) {
                                    var value = $(this).attr("value");
                                    if (value != null) checkBox.show();
                                };
                            });
                        }

                        $(document).ready(function() {
                            $("#" + "%s").siblings(".add-another").hide();
                            setupCreatePatientCheckBox("%s");
                        });
                    </script>
                """
        if value is None:
            control_id = attrs['id']
            html = """<input type="checkbox" id="%s" name="%s">""" % (attrs['id'], name)
            return html + script % (control_id, control_id)
        else:

            control_id = hashlib.sha1(str(random.random())).hexdigest()  # random guid for id ensures we can locate the link to hide the + easily
            script = """
            <script>
            $(document).ready(function() {
                            $("#" + "%s").siblings(".add-another").hide();
            });
            </script>
            """ % control_id
            hidden_field = """<input type=hidden id="%s" name="%s" value="%s">""" % (attrs['id'], name, value)  # ensure that the link to patient not lost on submission!
            patient_url = reverse("admin:patients_patient_change", args=[value,])
            html = """<a id="%s" href='%s'>Patient in registry</a>%s""" % (control_id, patient_url, hidden_field)
            return html + script
