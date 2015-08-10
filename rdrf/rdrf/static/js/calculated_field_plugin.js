(function($) {
    $.fn.add_calculation = function(options) {
        var settings = $.extend({
            // These are the defaults.
            calculation: function(context) { context.result = "???"; },
            subjects: '', // E.g. "CDE01,CDE02" comma separated list of inputs to the calculation
            prefix: '',//  formcode^^sectioncode^^
            target: "value",
            observer: '',  // the cde code of the output e,g, CDE03
            // Stuff below added to allow calculations to retrieve remote model properties
            injected_model: "",  // e.g. Patient  ( model class name)
            injected_model_id: null,  // the id of the injected model instance to retrieve
            tastypie_url: ""  //the url to request model data on eg /api/v1/patient/1

        }, options);



        // locate the codes anywhere on the page ( we assume only one occurance of given cde for now
        function locate_code(code) {
            var id = $('[id*=' + code + ']').attr("id");
            return "#" + id;
        }

        var subject_codes_string = _.map(settings.subjects.split(","), function(code)
            { return locate_code(code);}).join();

        function get_object(model, model_id) {
            var d = $.Deferred();
             if (model_id == -1) {
                 d.resolve([]);
                 return;
            }

            $.get(settings.tastypie_url)
                .done(function(object) {
                    d.resolve(object);
                })
                .fail(d.reject);

            return d.promise();
        }

        var update_function = function() {
            var context = {};
            var subject_codes = settings.subjects.split(",");

            for (var i = 0; i < subject_codes.length; i++) {
                // Note how we use the prefix to map from the page to the context variable names
                // and reverse map to update the output
                var subject_code_id_on_page = locate_code(subject_codes[i]);
                context[subject_codes[i]] = $(subject_code_id_on_page).val();
            }

            var model_promise = get_object(settings.injected_model.toLowerCase(),
                                           settings.injected_model_id);

            $.when(model_promise)
             .done(function(injected_models) {
                        try {
                            settings.calculation.apply(null, [context].concat(injected_models));
                        }
                        catch (err) {
                            context.result = "ERROR";
                        }
                        $("#id_" + settings.prefix + settings.observer).val(context.result);
                        $("#id_" + settings.prefix + settings.observer).trigger("rdrf_calculation_performed");
             });
        };

        $(subject_codes_string).on("input change", update_function);
        $(subject_codes_string).on("rdrf_calculation_performed", update_function);

        try {
            // call on initial page load
            update_function(); //call it to ensure if calculation changes on server
                               // we are always in sync(RDR-426 )
        }
        catch (err) {
            alert(err);
        }
    };

}(jQuery));
