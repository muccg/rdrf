
var j = jQuery.noConflict();


function show_hide_data() {
    if (j("#id_include_all").is(":checked")){
        j("#id_data").val("{}");
        j("#id_data").parent().children().hide();
    } else {
        j("#id_data").parent().children().show();
    }
}

function show_hide_include_all() {
    // "SR" is Patient Status Report
    if (j("#id_action_type").val()=="SR"){
        j("#id_include_all").parent().children().show();
    } else {
        j("#id_include_all").parent().children().hide();
    }
}

j(document).ready(function() {
    j("#id_action_type").change(function() {
        show_hide_include_all();
    });
    j("#id_include_all").change(function() {
        show_hide_data();
    });
    show_hide_data();
    show_hide_include_all()
});

