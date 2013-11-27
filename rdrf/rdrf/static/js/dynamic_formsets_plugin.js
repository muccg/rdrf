// JQuery plugin to allow dynamic formset creation in the section form

(function ( $ ) {
    $.fn.allow_dynamic_formsets = function( options ) {
        var settings = $.extend({
            // These are the defaults.
           table_id: '',
           cde_codes: '', // csv codes of fields that comprise one form in the formset
           add_button_id: 'add',
           remove_button_id: 'remove'
        }, options );

       function new_specifier(num_cdes, old_value, new_row_index) {
           /*
           <input id="id_form-0-CDEAge" name="form-0-CDEAge" type="text">
           We return "form-1-CDEAge" for example  - there are num_cdes rows per form
           */
           var form_number = Math.floor(new_row_index / num_cdes);
           var new_form_string = "-" + form_number.toString() + "-";
           var s = old_value.replace(/-\d+-/, new_form_string);
           return s;

       }

       var cdes = [];
       var added_cdes = [];

       _.map(settings.cde_codes.split(","), function(code){cdes.push(code);});

       // bind the add button
       function get_row_count() {
           return $("#" + settings.table_id + " > tbody > tr").length;
       }
       // current length of table
       $("#"+settings.add_button_id).on("click", function (){
            for (var i=0;i<cdes.length;i++){
                var cde_code = cdes[i];
                // locate the first row with this code, clone it , modify it and add to table
                var row_selector = "#"+ settings.table_id + " > tbody > tr:has(label[for='id_form-0-" + cde_code + "'])";
                $(row_selector)
                    .clone()            // create a copy
                    .find("label")      // update the clone's for attr to the new value
                    .each(function() {
                        $(this).attr({
                            'for': function(_, old_for) { return new_specifier(cdes.length, old_for, get_row_count())}
                        })
                    })
                    .end()
                    .find(":input")     // change the ids of inputs
                    .each(function() {

                        $(this).attr({
                            'id': function(_, old_id) { return new_specifier(cdes.length, old_id, get_row_count())},
                            'name': function(_, old_name) { return new_specifier(cdes.length, old_name, get_row_count())}
                        });
                        $(this).val("");
                    })
                    .end()
                    .insertAfter("#" + settings.table_id + " tr:last")


            }
        });

       // bind the remove button
        $("#"+settings.remove_button_id).on("click", function (){
            var num_rows = get_row_count();
            if (num_rows > cdes.length) {
                neg_index = -cdes.length - 1;

                $("#"+ settings.table_id + " > tbody > tr").slice(neg_index,-1).remove();
            }
        });

    }
}( jQuery ));
