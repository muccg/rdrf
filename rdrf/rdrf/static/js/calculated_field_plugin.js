(function ( $ ) {
    $.fn.add_calculation = function( options ) {
        var settings = $.extend({
            // These are the defaults.
            calculation: function (context) { context.result = "???"; },
            subjects: '', // E.g. "CDE01,CDE02" comma separated list of inputs to the calculation
            prefix: '',//  formcode^^sectioncode^^
            target: "value",
            observer: ''  // the cde code of the output e,g, CDE03
        }, options );

        var subject_codes_string  = _.map(settings.subjects.split(","), function(code){return "#id_" + settings.prefix + code;}).join()

        $(subject_codes_string).on("input, change",function () {
            var context = {};
            var subject_codes = settings.subjects.split(",");

            for(var i=0;i<subject_codes.length;i++) {
                // Note how we use the prefix to map from the page to the context variable names
                // and reverse map to update the output
                context[subject_codes[i]] = $("#id_" + settings.prefix + subject_codes[i]).val();
            }

            try {
                settings.calculation(context);
            }
            catch(err) {
                context.result = "#ERROR";
            }

            $("#id_" + settings.prefix + settings.observer).val(context.result);
        });
    };

}( jQuery ));