function hgvsValidation(element) {
    if (element.val().length > 2) {
        $('#result_' + element.attr('id')).html('<i>Please wait...</i>');
        $.get('/hgvs/' + element.val(), function(data) {
            result = data['parse_result'];
            if (result == true) {
                result_text = '<font color="green">Correct</font>';
            } else {
                result_text = '<font color="red">Incorrect</font>';
            }
            $('#result_' + element.attr('id')).html(result_text);
        });
    }
}