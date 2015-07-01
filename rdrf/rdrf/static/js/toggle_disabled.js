(function($) {
    $.fn.disable = function() {
        return this.each(function() {
            this.disabled = true;
        });
    };

    $.fn.enable = function() {
        return this.each(function() {
            this.disabled = false;
        });
    };

})(jQuery);
