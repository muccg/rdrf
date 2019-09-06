(function ($) {

    let required_cde_inputs = {};
    let calculated_cde_inputs = {}
    let patient_date_of_birth = '';
    let patient_sex = '';
    let wsurl = '';
    let cde_data_type = "";
    let do_fetch = true;

    const update_function = function (calculated_cdes) {

        calculated_cdes.forEach(cde_code => {
            do_fetch = true;
            // Retrieve all values of input
            let calculated_cde_inputs_json_values = {};
            calculated_cde_inputs[cde_code].forEach((required_input_cde) => {

                let cde_value = $(`[id$=__${required_input_cde}]`).val();

                // check if it is a date like dd-mm-yyyy and convert it in yyyy-mm-dd
                if (moment(cde_value, "D-M-YYYY", true).isValid()) {
                    cde_value = moment(cde_value, "D-M-YYYY", true).format('YYYY-MM-DD');
                }

                if (cde_data_type === "calculated") {
                    if (!moment(cde_value, "YYYY-MM-DD", true).isValid()) {
                        do_fetch = false;
                    }
                }

                // check if it is a number and convert it in a number
                if ($(`[id$=__${required_input_cde}]`).attr('type') === 'number') {
                    cde_value = parseFloat(cde_value);
                }

                calculated_cde_inputs_json_values[required_input_cde] = cde_value;
            });

            const body = {
                'cde_code': cde_code,
                'patient_date_of_birth': patient_date_of_birth,
                'patient_sex': patient_sex,
                'form_values': calculated_cde_inputs_json_values,
                'cde_data_type': cde_data_type
            };

            if (do_fetch) {
                fetch(wsurl, {
                    method: 'post',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': $("[name=csrfmiddlewaretoken]").val()
                    },
                    body: JSON.stringify(body)
                })
                    .then(function (response) {
                        return response.json();
                    })
                    .then(function (myJson) {
                        $(`[id$=__${cde_code}]`).val(myJson)
                        $(`[id$=__${cde_code}]`).trigger("change");
                    });
            }
        });
    }

    $.fn.add_calculation = function (options) {

        patient_date_of_birth = options.patient_date_of_birth;
        patient_sex = options.patient_sex;
        cde_data_type = options.cde_data_type;
        wsurl = options.wsurl;

        calculated_cde_inputs[options.observer] = options.cde_inputs;

        options.cde_inputs.forEach((input_cde_code) => {
            required_cde_inputs[input_cde_code] = required_cde_inputs[input_cde_code] != undefined ?
                [...required_cde_inputs[input_cde_code], options.observer] : [options.observer];
        });

        try {
            // call on initial page load
            update_function([options.observer]); //call it to ensure if calculation changes on server

            //update the onchange
            Object.keys(required_cde_inputs).forEach(function (cde_input) {
                $(`[id$=__${cde_input}]`).off("change");
                $(`[id$=__${cde_input}]`).on('change keyup', _.debounce((e) => { update_function(required_cde_inputs[cde_input]) }, 250))
            });

        } catch (err) {
            alert(err);
        }
    };
}
    (jQuery)
)
    ;
