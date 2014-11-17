from django.forms import widgets
import logging
import hashlib
import random
logger = logging.getLogger("registry_log")


class PatientRelativeLinkWidget(widgets.Widget):
    def render(self, name, value, attrs=None):
        script = """<script>
                        function setupCreatePatientCheckBox(id) {
                            var checkBox = $("#" + id);
                            checkBox.closest("tr").find(":input[type='hidden']").each(function () {
                                var inputName = $(this).attr("name");
                                if (inputName.match(/^patientrelative_set.*-id$/)) {
                                    var value = $(this).attr("value");
                                    if (value != null) {
                                        checkBox.prop("disabled", false);
                                    }
                                    else {
                                        checkBox.prop("disabled", true);
                                    }
                                }
                            })
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
        else:
            control_id = hashlib.sha1(str(random.random())).hexdigest()  # random guid for id ensures we can locate the link to hide the + easily
            hidden_field = """<input type=hidden id="%s" name="%s" value="%s">""" % (attrs['id'], name, value)  # ensure that the link to patient not lost on submission!
            html = """<a id="%s" href='/admin/patients/patient/%s/'>Patient in registry</a>%s""" % (control_id, value, hidden_field)
        return html + script % (control_id, control_id)