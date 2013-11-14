var Variation = function (element) {
    var self = this;

    // Basic properties.
    self.element = element;
    self.id = new Number(django.jQuery(".original input[type='hidden']", self.element.parentNode.parentNode).val());
    self.ie6 = (window.navigator.userAgent.indexOf("MSIE 6.0") != -1);
    self.minChars = self.element.getAttribute("minchars") || 2;
    self.parent = element.parentNode;
    self.timeout = null;
    self.xhr = null;


    // Create the element that indicates the validity of the entered variation.

    self.validity = document.createElement("span");
    self.validity.className = "validity";

    self.parent.appendChild(self.validity);


    // Create the hook for the popup form to enter the variation.

    var popup = self.element.getAttribute("variation-popup");
    if (popup) {
        /* We need some extra CSS rules to make IE 6 behave like a real
         * browser. */
        if (self.ie6) {
            for (var i = 0; i < document.styleSheets.length; i++) {
                var sheet = document.styleSheets[i];

                if (sheet.href.indexOf("variation.css") != -1) {
                    var ieSheet = sheet.href.replace("variation.css", "variation-ie6.css");
                    sheet.addImport(ieSheet);
                    break;
                }
            }
        }

        self.showForm = document.createElement("span");
        self.showForm.className = "show-form";
        self.showForm.appendChild(document.createTextNode("+"));

        self.showForm.onclick = function (e) {
            var overlayContainer = document.createElement("div");
            overlayContainer.className = "overlay-container";

            var overlay = document.createElement("div");
            overlay.className = "overlay";

            var iframe = document.createElement("iframe");
            iframe.src = popup;

            var onLoad = function () {
                var doc;

                if (iframe.contentDocument) {
                    doc = iframe.contentDocument;
                }
                else {
                    doc = iframe.contentWindow.document;
                }

                doc.getElementById("variation-entry-form").onsubmit = function () {
                    self.element.value = iframe.contentWindow.Entry.asString();
                    self.setTimeout();

                    document.body.removeChild(overlayContainer);

                    return false;
                };

                doc.getElementById("close").onclick = function () {
                    document.body.removeChild(overlayContainer);
                    return false;
                };
            };

            if (iframe.attachEvent) {
                iframe.attachEvent("onload", onLoad);
            }
            else {
                iframe.addEventListener("load", onLoad, false);
            }

            overlayContainer.appendChild(overlay);
            overlayContainer.appendChild(iframe);
            document.body.appendChild(overlayContainer);

            return false;
        };

        self.parent.appendChild(self.showForm);
    }


    // Set up the event handlers we need on the element.

    self.element.onchange = function (e) {
        self.setTimeout();
    };

    self.element.onkeyup = function (e) {
        self.setTimeout();
    };


    self.clearTimeout = function () {
        if (self.timeout) {
            window.clearTimeout(self.timeout);
            self.timeout = null;
        }

        if (self.xhr && (self.xhr.readyState == 2 || self.xhr.readyState == 3)) {
            self.xhr.abort();
        }
    };

    self.clearValidity = function () {
        while (self.validity.childNodes.length > 0) {
            self.validity.removeChild(self.validity.firstChild);
        }

        self.validity.className = "validity";

        /* Remove any mouseover/out handlers we previously set up for :hover
         * emulation purposes. */
        if (self.ie6) {
            self.validity.onmouseover = null;
            self.validity.onmouseout = null;
        }

        self.validity.onclick = null;
    };

    self.getVariationType = function () {
        var TYPES = ["exon", "dna", "rna", "protein"];

        for (var i = 0; i < TYPES.length; i++) {
            if (self.element.id.indexOf(TYPES[i]) != -1) {
                return TYPES[i];
            }
        }

        // Should never fall through to here.
        throw "Unknown variation type";
    };

    self.isSavedVariation = function () {
        return (self.id != 0);
    };

    self.setInvalid = function (messages) {
        self.clearValidity();

        self.setValidityClass("invalid");

        /* Set up the elements we need to show the error message(s) from the
         * validator. */

        var popup = document.createElement("div");
        popup.className = "popup";

        var list = document.createElement("ul");
        for (var i = 0; i < messages.length; i++) {
            var item = document.createElement("li");
            item.appendChild(document.createTextNode(messages[i]));
            list.appendChild(item);
        }

        popup.appendChild(list);
        self.validity.appendChild(popup);

        // OK, quick hack to emulate :hover in IE 6.
        if (self.ie6) {
            self.validity.onmouseover = function () {
                self.validity.className = self.validity.className.replace(/\s*$/, " hover");
            };

            self.validity.onmouseout = function () {
                self.validity.className = self.validity.className.replace(/\bhover\b/, " ");
            };

            // Let's emulate :first-child while we're at it, too.
            list.firstChild.style.borderTop = "solid 1px #cccccc";
        }

        /* If the user can override validity checks and this is a saved
         * variation, let's hook up a handler. */
        if (ValidationOverrides.available && self.isSavedVariation()) {
            var item = document.createElement("li");
            item.className = "hint";
            item.appendChild(document.createTextNode("To override the automated validation, please click on the cross above"));
            list.appendChild(item);

            self.validity.onclick = function () {
                if (window.confirm("Are you sure you wish to override the validation for this variation?")) {
                    /* A local XHR instance is fine here, since it's not meant
                     * to be interruptable when the content changes. */
                    var xhr = XHR.create();

                    xhr.onreadystatechange = function (e) {
                        if (xhr.readyState == 4) {
                            if (xhr.status == 1223 || (xhr.status >= 200 && xhr.status <= 299)) {
                                ValidationOverrides.ids[self.id][self.type] = true;
                                self.setTimeout();
                            }
                            else {
                                window.alert("An error occurred while overriding the validation.");
                            }
                        }
                    };
                    xhr = prepare_xhr(xhr, {"method":"POST", "url" : "../override/" + self.type + "/" + self.id});
                    //xhr.open("POST", "../override/" + self.type + "/" + self.id, true);
                    //xhr.setRequestHeader("X-Requested-With", "XMLHttpRequest");
                    xhr.send();
                }
            };
        }
    };

    self.setLoading = function (messages) {
        self.clearValidity();

        self.setValidityClass("loading");
    };

    self.setTimeout = function () {
        self.clearTimeout();

        if (ValidationOverrides.contains(self.id, self.type)) {
            self.setValid();
            return;
        }

        if (self.element.value.length > self.minChars) {
            self.timeout = window.setTimeout(function () {
                // Check validity.
                self.setLoading();
                self.xhr = XHR.create();

                self.xhr.onreadystatechange = function (e) {
                    if (self.xhr.readyState == 4) {
                        /* We're testing for status code 1223 to work around
                         * yet another IE bug. I've reported the relevant bug
                         * to Microsoft Connect for them to ignore; the URL is
                         * https://connect.microsoft.com/IE/feedback/details/557310/xmlhttprequest-doesnt-handle-204-no-content-responses-properly
                         * */
                        if (self.xhr.status == 1223 || (self.xhr.status >= 200 && self.xhr.status <= 299)) {
                            self.setValid();
                        }
                        else if (self.xhr.status == 400 && self.xhr.getResponseHeader("Content-Type") == "application/json") {
                            self.setInvalid(JSON.parse(self.xhr.responseText));
                        }
                        else {
                            self.setUnknown();
                        }
                    }
                };

                //djan.ajaxSend(self.xhr, {"type": "POST", "url" : self.element.getAttribute("backend")});
               
                self.xhr = prepare_xhr(self.xhr, {"method":"POST", "url" : self.element.getAttribute("backend")});
                self.xhr.send(self.element.value);
            }, 1000);
        }
    };

    self.setUnknown = function () {
        self.clearValidity();

        self.setValidityClass("hell-if-i-know");
    };

    self.setValid = function () {
        self.clearValidity();

        self.setValidityClass("valid");
    };

    self.setValidityClass = function (className) {
        self.validity.className = "validity " + className;

        if (self.ie6) {
            // God, I want to stab everyone who worked on IE 6 sometimes.
            self.validity.style.cssText = "";
            var match = /url\((.*)\)/.exec(self.validity.currentStyle.backgroundImage);
            if (match) {
                self.validity.style.backgroundImage = "none";
                self.validity.style.filter = "progid:DXImageTransform.Microsoft.AlphaImageLoader(src=" + match[1] + ")";
            }
        }
    };


    self.type = self.getVariationType();
    self.setTimeout();
};


// Initialise variation widgets.
(function () {
    var init = function () {
        var boxes;

        if (document.querySelectorAll) {
            boxes = document.querySelectorAll("input.variation");
        }
        else {
            boxes = [];
            var inputs = document.getElementsByTagName("input");

            for (var i = 0; i < inputs.length; i++) {
                if (inputs[i].className.indexOf("variation") != -1) {
                    boxes.push(inputs[i]);
                }
            }
        }

        for (var i = 0; i < boxes.length; i++) {
            new Variation(boxes[i]);
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
