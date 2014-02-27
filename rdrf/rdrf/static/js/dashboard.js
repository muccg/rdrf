function check_for_btn(id1, id2, element_id) {
    if (id1 != -1 && id2 != -1 ) {
        $(element_id).prop('disabled', false);
    } else {
        $(element_id).prop('disabled', true);
    }
}