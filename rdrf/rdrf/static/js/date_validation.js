function setUpDatePickers() {
        var dateOptions = {
            'dateFormat': 'yy-mm-dd',
            'showAnim': 'blind',
            'changeMonth': true,
            'changeYear': true,
            'minDate': '-100Y',
            'maxDate': '0',
            'yearRange': '-100:+0',
            'defaultDate': '-30Y',
            onSelect: function(date, inst) {
                $(this).valid();
            }
        };

        $.each(arguments, function(_, id) {
            $(id).datepicker(dateOptions);
        });

        // Avoid Google Translate to translate the widget
        // This would set the value NaN-NaN-NaN when you select a date in the widget
        $(".ui-datepicker").addClass("notranslate");
};


function addExtraValidationMethods() {
        jQuery.validator.addMethod("selectcheck", function (value) {
            return (value != '0');
        }, gettext("This field is required."));

        jQuery.validator.addMethod("validdateformat", function (value) {
            return value.match(/\s*(\d{4})-(\d{1,2})-(\d{1,2})\s*/);
        }, gettext("The date format should be YYYY-MM-DD."));

        jQuery.validator.addMethod("validdate", function (value) {
            var m = value.match(/\s*(\d{4})-(\d{1,2})-(\d{1,2})\s*/);
            if (m == null) {
                return false;
            }
            var year = parseInt(m[1]);
            var month = parseInt(m[2]);
            var day = parseInt(m[3]);

            function isLeapYear(year) {
                return ((year % 4 == 0) && (year % 100 != 0)) || (year % 400 == 0);
            }

            function daysInMonth(year, month) {
                if (month === 2 && isLeapYear(year)) {
                    return 29;
                }
                return [31,28,31,30,31,30,31,31,30,31,30,31][month - 1];
            }

            return year >= 1900 && month >= 1 && month <= 12 && day >=1 && day <= daysInMonth(year, month);
        }, gettext("Please enter a valid date"));


        jQuery.validator.addMethod("dateinpast", function (value) {
            return dateInPast(new Date(value));
        }, gettext("The date of birth should be in the past."));

        jQuery.validator.addMethod("adultpatientonly", function (value) {
            if ($("#id_is_parent").val() == "true") {
                $("#underage_msg").hide("blind");
                return true;
            }
            var isAdult = dateDiffInYears(new Date(), new Date(value)) >= 18;
            if (isAdult) {
                $("#underage_msg").hide("blind");
            } else {
                $("#underage_msg").show();
            }
            return isAdult;
        }, gettext("Please register child as Parent/Guardian"));

        jQuery.validator.addMethod("adultonly", function (value) {
            var isAdult = dateDiffInYears(new Date(), new Date(value)) >= 18;
            return isAdult;
        }, gettext("Parent/Guardian must be an adult."));

        jQuery.validator.addMethod("containsnumber", function (value) {
            return value.match(/\d+/);
        }, gettext("Password must contain at least 1 number"));

        jQuery.validator.addMethod("matchespassword1", function (value) {
            return value === $("#id_password1").val();
        }, gettext("Password must contain at least 1 number"));
    };
