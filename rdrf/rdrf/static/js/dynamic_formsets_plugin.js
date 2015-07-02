// JQuery plugin to allow dynamic formset creation in the section form

(function($) {
    $.fn.allow_dynamic_formsets = function(options) {
        var settings = $.extend({
            // These are the defaults.
           table_id: '',
           cde_codes: '', // csv codes of fields that comprise one form in the formset
           add_button_id: 'add',
           total_forms_id: 'id_form-TOTAL_FORMS',
           initial_forms_id: 'id_form_INITIAL_FORMS',
           formset_prefix: 'form',
           metadata_json: '' // easier to pass a string in the template
        }, options);

       var metadata = {};
       try {

           metadata = jQuery.parseJSON(settings.metadata_json);
       }

       catch (err) {
           metadata = {};
       }

       function new_specifier(num_cdes, old_value, new_row_index) {
           /*
           <input id="id_form-0-CDEAge" name="form-0-CDEAge" type="text">
           We return "form-1-CDEAge" for example  - there are num_cdes rows per form
           complication is that a remove button is included when we add - hence
           the + 1 to the num_cdes
           */
           var form_number = Math.floor(new_row_index / (num_cdes + 1));
           var new_form_string = "-" + form_number.toString() + "-";
           var s = old_value.replace(/-\d+-/, new_form_string);
           return s;

       }

       function update_form_total(value) {
           // total forms
           var old_value = parseInt($("#" + settings.total_forms_id).val());
           $("#" + settings.total_forms_id).val(old_value + value);
           // initial forms
           var old_initial_value = parseInt($("#" + settings.initial_forms_id).val());
           $("#" + settings.initial_forms_id).val(old_initial_value + value);

       }

       function get_form_total() {
           return parseInt($("#" + settings.total_forms_id).val());
       }

       function get_initial_count() {
           return $("#" + settings.initial_forms_id).val();
       }

       var cdes = [];
       var added_cdes = [];

       _.map(settings.cde_codes.split(","), function(code) {cdes.push(code);});

       // bind the add button
       function get_row_count() {
           // return the number of input rows
           return $("#" + settings.table_id + " > tbody > tr:has(:input)").length;
       }

       function get_row_selector(cde_code) {
           // check settings for any overrides
           // e.g. for date cdes we use  <cde_code>_month to locate the row not just cde_code
           if (metadata[cde_code] && metadata[cde_code].row_selector) {
               return metadata[cde_code].row_selector;
           }
           else {
               return cde_code;
           }
       }

       function dump_state(msg) {
           console.log("****************************************************");
           console.log("state " + msg);
           console.log("row count = " + get_row_count());
           console.log("django form total = " + get_form_total().toString());
           console.log("initial form count = " + get_initial_count());
           console.log("****************************************************");
       }
       // current length of table
       $("#" + settings.add_button_id).on("click", function() {
            dump_state("before add");
            for (var i = 0; i < cdes.length; i++) {
                var cde_code = cdes[i];
                // locate the first row with this code, clone it , modify it and add to table

                // Most cdes use standard input widgets which are locatable with cde code directly
                // complex fields ( multiwidgets ) will modify the id so we use settings to pass
                // metadata about overrides to the plugin to allow location
                var row_selector = "#" + settings.table_id + " > tbody > tr:has(label[for='id_" + settings.formset_prefix + "-0-" + get_row_selector(cde_code) + "'])";
                $(row_selector)
                    .clone(true)            // create a copy
                    .find("label")      // update the clone's for attr to the new value
                    .each(function() {
                        $(this).attr({
                            'for': function(_, old_for) { return new_specifier(cdes.length, old_for, get_row_count())}
                        });
                    })
                    .end()
                    .find(":input")     // change the ids of inputs
                    .each(function() {

                        $(this).attr({
                            'id': function(_, old_id) { return new_specifier(cdes.length, old_id, get_row_count())},
                            'name': function(_, old_name) { return new_specifier(cdes.length, old_name, get_row_count())}
                        });
                        $(this).val("");
                        console.log("updated input : " + $(this).text());
                    })
                    .end()
                    .insertAfter("#" + settings.table_id + " tr:last");


            }
            // copy the last remove button row and modify it
            // this row should look like:
            //<tr id="remove_formset_STest_0" class="actionbutton"><td onclick="do_remove(this,'section_table_STest',2,'id_formset_STest-TOTAL_FORMS');">Remove</td></tr>

            var remove_button_selector = "#" + settings.table_id + " > tbody > tr[id^='remove_" + settings.formset_prefix + "']";
            $(remove_button_selector + ":last")
                .clone(true)
                .attr({
                        'id' : function(_, old_id) {
                                var parts = old_id.split("_");
                                var last_el = parts[parts.length - 1];
                                var new_num = parseInt(last_el) + 1;
                                return "remove_button_" + settings.formset_prefix + "_" + new_num.toString();
                        }
                    })
                .find("td")
                .each(function() {
                    $(this).attr({
                        "onclick" : function(_, old_onclick) { return old_onclick;}
                    });
                })
                .end()
                .insertAfter("#" + settings.table_id + " tr:last");
            update_form_total(1);
            dump_state("after add");
        });

    };
}(jQuery));
