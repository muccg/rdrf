
function get_fields_per_form(table_id) {
    var num_inputs = 0;
    $("#" + table_id).find(":input[id*='-0-").each(function () {
        num_inputs += 1;
    });
    return num_inputs;
}

function renumber_section_table(table_id) {
    // we need to ensure sequential order of form ids in case of removal from inside formset ...
    // re-number the ids of the form ...
    var fields_per_form = get_fields_per_form(table_id);

    function form_index_generator(fields_per_form) {
        // e,g if there are three fields per form
        // we return 0,0,0,1,1,1,2,2,2,3,3,3,...  for successive calls
        var i = 0;
        var form_num = 0;
        return function () {
            if (i > (fields_per_form - 1) ){
                i = 0;
                form_num += 1;
            }
            else {
                i = i + 1;
            }

            return form_num.toString();
        }
    }

    var label_gen = form_index_generator(fields_per_form);
    var input_id_gen = form_index_generator(fields_per_form);
    var input_name_gen = form_index_generator(fields_per_form);

    $("#" + table_id + " > tbody > tr ").each(function () {
        $(this)
                // update labels
                .find("label")
                .each(function () {
                    $(this).attr({
                        // <label for="id_formset_STest-1-CDEName">
                        'for': function (_, old_for) {
                            var new_index_string = label_gen();
                            var new_for = old_for.replace(/-\d+-/, "-" + new_index_string + "-");
                            return new_for;
                           }
            })
        });

        $(this)
                // update ids for inputs
                .find(":input").each(function () {
                    $(this).attr({
                        'id': function (_, old_id){
                            var new_index_string = input_id_gen();
                            var new_id = old_id.replace(/-\d+-/, "-" + new_index_string + "-");
                            return new_id;
                        },
                        'name': function (_, old_name) {
                            var new_index_string = input_name_gen();
                            var new_name = old_name.replace(/-\d+-/, "-" + new_index_string + "-");
                            return new_name;
                        }
                    })
                });

    })
}
function do_remove(el,table_id, num_rows, total_forms_id, initial_forms_id) {
    var num_rows_left = $("#" + table_id + " > tbody > tr").length;
    var min_rows_to_keep = 1 + num_rows;
    if (num_rows_left <= min_rows_to_keep) {
        // do nothing

        return;
    }
    var tr = $(el).parent();
    var current_row = tr;
    var rows_to_remove = [];
    for (var i=0;i<=num_rows;i++) {
        rows_to_remove.push(current_row);
        current_row = current_row.prev();
    }
    _.map(rows_to_remove, function (row) {row.remove();});

    // decrement total forms counter on management form
    var old_value = parseInt($('#' + total_forms_id).val());
    var new_value = old_value - 1;
    $('#' + total_forms_id).val(new_value.toString());

    // decrement initial forms counter on management form
    var old_initial_forms_value = parseInt($('#' + initial_forms_id).val());
    var new_initial_forms_value = old_initial_forms_value - 1;
    $('#' + initial_forms_id).val(new_initial_forms_value.toString());

    // renumber all the fields ( labels + inputs ) in case
    // we have removed a field set from inside the formset and have
    // destroyed the sequential ordering

    renumber_section_table(table_id);
}