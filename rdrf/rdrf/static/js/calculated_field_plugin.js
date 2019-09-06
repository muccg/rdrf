"use strict";

function _toConsumableArray(arr) {
  return (
    _arrayWithoutHoles(arr) || _iterableToArray(arr) || _nonIterableSpread()
  );
}

function _nonIterableSpread() {
  throw new TypeError("Invalid attempt to spread non-iterable instance");
}

function _iterableToArray(iter) {
  if (
    Symbol.iterator in Object(iter) ||
    Object.prototype.toString.call(iter) === "[object Arguments]"
  )
    return Array.from(iter);
}

function _arrayWithoutHoles(arr) {
  if (Array.isArray(arr)) {
    for (var i = 0, arr2 = new Array(arr.length); i < arr.length; i++) {
      arr2[i] = arr[i];
    }
    return arr2;
  }
}

(function($) {
  var required_cde_inputs = {};
  var calculated_cde_inputs = {};
  var patient_date_of_birth = "";
  var patient_sex = "";
  var wsurl = "";

  var update_function = function update_function(calculated_cdes) {
    calculated_cdes.forEach(function(cde_code) {
      // Retrieve all values of input
      var calculated_cde_inputs_json_values = {};
      calculated_cde_inputs[cde_code].forEach(function(required_input_cde) {
        var cde_value = $("[id$=__".concat(required_input_cde, "]")).val(); // check if it is a date like dd-mm-yyyy and convert it in yyyy-mm-dd

        if (moment(cde_value, "D-M-YYYY", true).isValid()) {
          cde_value = moment(cde_value, "D-M-YYYY", true).format("YYYY-MM-DD");
        } // check if it is a number and convert it in a number

        if (
          $("[id$=__".concat(required_input_cde, "]")).attr("type") === "number"
        ) {
          cde_value = parseFloat(cde_value);
        }

        calculated_cde_inputs_json_values[required_input_cde] = cde_value;
      });
      var body = {
        cde_code: cde_code,
        patient_date_of_birth: patient_date_of_birth,
        patient_sex: patient_sex,
        form_values: calculated_cde_inputs_json_values
      };
      fetch(wsurl, {
        method: "post",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": $("[name=csrfmiddlewaretoken]").val()
        },
        body: JSON.stringify(body)
      })
        .then(function(response) {
          if (!response.ok) {
            throw new Error(response.statusText);
          }

          return response.json();
        })
        .then(function(result) {
          if (result.stat === "fail") {
            throw new Error(result.message);
          }

          $("[id$=__".concat(cde_code, "]")).val(result);
          $("[id$=__".concat(cde_code, "]")).trigger("change");
        })
        .catch(function(errormsg) {
          console.log(errormsg);
        });
    });
  };

  $.fn.add_calculation = function(options) {
    patient_date_of_birth = options.patient_date_of_birth;
    patient_sex = options.patient_sex;
    wsurl = options.wsurl;
    calculated_cde_inputs[options.observer] = options.cde_inputs;
    options.cde_inputs.forEach(function(input_cde_code) {
      required_cde_inputs[input_cde_code] =
        required_cde_inputs[input_cde_code] != undefined
          ? [].concat(_toConsumableArray(required_cde_inputs[input_cde_code]), [
              options.observer
            ])
          : [options.observer];
    });

    try {
      // call on initial page load
      update_function([options.observer]); //call it to ensure if calculation changes on server
      //update the onchange

      Object.keys(required_cde_inputs).forEach(function(cde_input) {
        $("[id$=__".concat(cde_input, "]")).off("change");
        $("[id$=__".concat(cde_input, "]")).on(
          "change keyup",
          _.debounce(function(e) {
            update_function(required_cde_inputs[cde_input]);
          }, 250)
        );
      });
    } catch (err) {
      alert(err);
    }
  };
})(jQuery);
