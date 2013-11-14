/* This object basically encapsulates the Javascript functionality required to
 * make the LiveComboWidget Django widget work. This is, in essence, an
 * extension of the combo box widget to get the dropdown contents from a live
 * data source via AJAX rather than having them pre-baked into the input
 * element. */
var LiveComboBox = function (element) {
    var self = this;

    /* The number of milliseconds to wait after a key is pressed in the input
     * box before launching an AJAX request. The default could probably be
     * increased a touch. */
    self.keyTimeout = element.getAttribute("keytimeout");
    if (!self.keyTimeout) {
        self.keyTimeout = 500;
    }

    /* The minimum number of characters that need to be entered before
     * requesting search results. */
    self.minCharacters = element.getAttribute("minchars");
    if (!self.minCharacters) {
        self.minCharacters = 3;
    }

    /* Boolean representing if the input element is currently focused, since we
     * don't want to show the dropdown if it isn't. Controlled via onfocus and
     * onblur handlers to avoid any odd behaviour in older versions of IE with
     * regards to their inconsistent handling of the :focus pseudo-class and
     * focusing non-link elements in general. */
    self.focused = false;

    /* Timeout that gets set in situations where we may want to show the
     * dropdown after a delay. This is usually after a keypress within the
     * input element. */
    self.showingTimeout = null;

    /* Most of the hard work is being done within the ComboBox object, so we'll
     * instantiate one of those and just override its behaviour as we need to.
     * */
    var combo = new ComboBox(element, true);


    // Override the onblur handler to set self.focused.
    (function () {
        combo.element.onblur = function (e) {
            self.focused = false;
        };
    })();

    /* Override the onfocus handler to set self.focused and use LiveComboBox's
     * internal method for determining whether the dropdown should be shown,
     * rather than unconditionally showing it per ComboBox. (Specifically, if
     * the number of characters in the input element are less than the minimum,
     * we don't want to show the dropdown or, more importantly, load the
     * backend by performing the search. */
    combo.element.onfocus = function (e) {
        self.focused = true;
        self.considerShowing();
    };

    /* Override the combo box onkeyup handler so that we can trigger the AJAX
     * dropdown after the appropriate delay. */
    (function () {
        var comboBoxKeyUp = combo.element.onkeyup;
        combo.element.onkeyup = function (e) {
            /* If we're already showing the dropdown, then we need to use
             * ComboBox's onkeyup handler first, since there's no point calling
             * considerShowing() if it's a navigation keypress. */
            if (combo.dropdown) {
                if (comboBoxKeyUp(e)) {
                    /* ComboBox didn't handle it internally, so let's think
                     * about whether we need to show the dropdown. */
                    self.considerShowing();
                    return true;
                }

                return false;
            }

            if (self.focused) {
                self.considerShowing();
            }

            return true;
        };
    })();

    /* Override the default ComboBox.showDropdown() to ensure the dropdown is
     * always hidden before showing. This isn't an issue in ComboBox because
     * there's only ever one case where the dropdown is actually shown
     * (onfocus), whereas here there are many, as it's controlled by AJAX
     * requests. */
    (function () {
        var comboShowDropdown = combo.showDropdown;
        combo.showDropdown = function () {
            combo.hideDropdown();
            comboShowDropdown();
        };
    })();


    // Utility function to clear the loading class from the input element.
    self.clearLoading = function () {
        element.className = element.className.replace(/\bloading\b/, " ");
    };

    /* Function to both clear any pending timeout for issuing a search request
     * and also to cancel any searches that are currently in progress. This
     * function will also call clearLoading() if required. */
    self.clearShowingTimeout = function () {
        if (self.showingTimeout) {
            window.clearTimeout(self.showingTimeout);
            self.showingTimeout = null;
        }

        if (self.xhr && (self.xhr.readyState == 2 || self.xhr.readyState == 3)) {
            self.xhr.abort();
            self.clearLoading();
        }
    };

    // Starts (or at least resets) the clock on a key timeout.
    self.considerShowing = function () {
        /* Get rid of any pending timeouts and requests, since we're about to
         * subsume them. */
        self.clearShowingTimeout();

        if (element.value.length >= self.minCharacters) {
            var searchTerm = element.value;

            self.showingTimeout = window.setTimeout(function () {
                self.xhr = XHR.create();

                if (self.xhr) {
                    self.setLoading();

                    self.xhr.onreadystatechange = function (e) {
                        if (self.xhr.readyState == 4) {
                            if (self.xhr.status == 200) {
                                var results = JSON.parse(self.xhr.responseText);
                                if (results.length > 0) {
                                    combo.choices = [];
                                    for (var i = 0; i < results.length; i++) {
                                        combo.choices.push(results[i]);
                                    }
                                    combo.showDropdown();
                                }
                            }
                            else {
                                /* It might be nice to have an unobtrusive way
                                 * of signalling these errors to the user, but
                                 * since there's probably nothing the user can
                                 * do about them anyway, let's just hide the
                                 * dropdown for now. Firebug or the
                                 * Safari/Chrome Developer Tools are going to
                                 * highlight the HTTP error in the AJAX pane
                                 * anyway, so the developer's at least aware of
                                 * what's going on. */
                                self.hideDropdown();
                            }

                            self.clearLoading();
                        }
                    };

                    self.xhr.open("GET", element.getAttribute("backend") + escape(searchTerm), true);
                    self.xhr.setRequestHeader("X-Requested-With", "XMLHttpRequest");
                    self.xhr.send();
                }
            }, self.keyTimeout);
        }
        else {
            combo.hideDropdown();
        }
    };

    /* Sets the loading class on the input element so the UI can display
     * whatever's appropriate: by default, that's a little animated GIF that
     * acts as a throbber. (Or spinner, if you prefer. I just like the word
     * throbber.) */
    self.setLoading = function () {
        element.className = element.className.replace(/\s*$/, " loading");
    };
};


// Hook up all live combo boxes on the page with the required functionality.
(function () {
    var init = function () {
        var boxes;

        if (document.querySelectorAll) {
            boxes = document.querySelectorAll("input.live-combo");
        }
        else {
            boxes = [];
            var inputs = document.getElementsByTagName("input");

            for (var i = 0; i < inputs.length; i++) {
                if (inputs[i].className.indexOf("live-combo") != -1) {
                    boxes.push(inputs[i]);
                }
            }
        }

        for (var i = 0; i < boxes.length; i++) {
            new LiveComboBox(boxes[i]);
        }
    };

    // Handle existing onload handlers gracefully.
    if (window.onload) {
        var onload = window.onload;

        window.onload = function () {
            onload();
            init();
        };
    }
    else {
        window.onload = init;
    }
})();


// vim: set cin ai et ts=4 sw=4:
