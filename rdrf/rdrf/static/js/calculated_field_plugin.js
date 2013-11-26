(function ( $ ) {
    $.fn.add_calculation = function( options ) {
        var settings = $.extend({
            // These are the defaults.
            calculation: function (context) { context.result = "???"; },
            subjects: '', // E.g. "CDE01,CDE02" comma separated list of inputs to the calculation
            target: "value",
            observer: ''  // the cde code of the output e,g, CDE03
        }, options );

        var subject_codes_string  = _.map(settings.subjects.split(","), function(code){return "#id_" + code;}).join()

        $(subject_codes_string).on("input, change",function () {
            var context = {};
            var subject_codes = settings.subjects.split(",");
            // replace
            for(var i=0;i<subject_codes.length;i++) {
                context[subject_codes[i]] = $("#id_" + subject_codes[i]).val();
            }

            try {
                settings.calculation(context);
            }
            catch(err) {
                context.result = "#ERROR";
            }

            $("#id_" + settings.observer).val(context.result);
        });
    };

}( jQuery ));