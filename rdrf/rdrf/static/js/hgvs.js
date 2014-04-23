function hgvsValidation(element) {
    if (element.val().length > 2) {
        $('#result_' + element.attr('id')).html('<i>Please wait...</i>');
        $.get(window.HGVS_URL, { 'code': element.val() }, function(data) {
            result = data['parse_result'];
            if (result == true) {
                result_text = "<img src='"+ window.STATIC_URL +"images/tick.png'>";
            } else {
                result_text = "<img src='"+ window.STATIC_URL +"images/cross.png'>";
            }
            $('#result_' + element.attr('id')).html(result_text);
        });
    } else {
        $('#result_' + element.attr('id')).html('<i>No input to validate</i>');
    }
}