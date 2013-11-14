var ComboBox = function (element, forceInit) {
    var self = this;

    self.choices = [];
    self.container = element.parentNode;
    self.element = element;
    self.dropdown = null;
    self.focused = false;
    self.ie6 = (window.navigator.userAgent.indexOf("MSIE 6.0") != -1);
    self.ie7 = (window.navigator.userAgent.indexOf("MSIE 7.0") != -1);
    self.iframe = null;
    self.inTable = false;
    self.rows = [];
    self.table = null;
    self.timeout = null;


    // Element initialisation: first we need to parse the provided options.
    var options = self.element.getAttribute("options");
    if (options) {
        if (JSON.parse) {
            /* This throws a SyntaxError on error. We could wrap this, but
             * since the only logical thing to do is rethrow anyway, there's
             * not much point. */
            self.choices = JSON.parse(options);
        }
        else {
            /* If you're getting this exception, something's gone wrong, since
             * Django should be trying to load json2.js as well to provide JSON
             * emulation for browsers that don't have it as a native object. */
            throw new ComboBox.JSONException("No JSON parser available");
        }
    }

    if (forceInit) {
        if (!self.choices) {
            self.choices = [];
        }

        // Disable autocomplete to avoid conflicts when showing the dropdown.
        self.element.setAttribute("autocomplete", "off");
    }
    else if (self.choices && self.choices.length > 0) {
        // Disable autocomplete to avoid conflicts when showing the dropdown.
        self.element.setAttribute("autocomplete", "off");
    }
    else {
        /* No options; no need to augment the input element. Let's just bail
         * and let the user enjoy his or her text input element as the
         * browser intended. */
        return;
    }


    self.onRowClick = function (id, row) {
        self.element.value = id;
    };

    self.addRow = function (id, cells) {
        if (typeof cells == "string") {
            cells = [cells];
        }

        var row = self.table.insertRow(self.table.rows.length);

        var handler = function (e) {
            return self.onRowClick(id, row);
        };
        
        for (var i = 0; i < cells.length; i++) {
            (function () {
                var cell = row.insertCell(row.cells.length);
                cell.appendChild(document.createTextNode(cells[i]));
                cell.onclick = handler;
            })();
        }

        row.onclick = handler;

        /* This is a little bit of a hack, but it helps with
         * findRowByName. */
        row.value = id;
        self.rows.push(row);

        /* We can't just use the :hover pseudo class for a couple of reasons:
         * firstly because we want to be able to control the "selected" item
         * with key presses as well as mouse hovers, and secondly because we
         * need to fiddle with other attributes upon selection. We don't need
         * an onmouseout handler because we cover deselection in onmouseover
         * and onkeypress. */
        row.onmouseover = function (e) {
            self.selectRow(row);
            return true;
        };
    };


    self.hideDropdown = function () {
        if (self.dropdown) {
            document.body.removeChild(self.dropdown);
            self.dropdown = null;

            if (self.iframe) {
                document.body.removeChild(self.iframe);
                self.iframe = null;
            }
        }
    };

    self.showDropdown = function () {
        self.dropdown = document.createElement("div");
        self.dropdown.className = "combo-dropdown";

        self.table = document.createElement("table");

        self.rows = [];

        for (var i = 0; i < self.choices.length; i++) {
            if (typeof self.choices[i] == "object") {
                self.addRow(self.choices[i][0], self.choices[i]);
            }
            else {
                self.addRow(self.choices[i], self.choices[i]);
            }
        }

        // Append the dropdown elements to the DOM.
        self.dropdown.appendChild(self.table);
        document.body.appendChild(self.dropdown);

        /* We want to capture all clicks on the document -- if they've bubbled
         * this far, then we can hide the dropdown. This has to be wrapped in a
         * timeout to avoid it firing immediately if the user clicked into the
         * input box. */
        window.setTimeout(function () {
            var remover;

            var handler = function () {
                self.hideDropdown();
                remover();
            };

            if (document.body.addEventListener) {
                remover = function () {
                    document.body.removeEventListener("click", handler, false);
                };

                document.body.addEventListener("click", handler, false);
            }
            else if (document.body.attachEvent) {
                remover = function () {
                    document.body.detachEvent("onclick", handler);
                };

                document.body.attachEvent("onclick", handler);
            }

            /* Place a click handler on the input box so that we don't hide a
             * shown dropdown when the input box is double clicked. */
            if (self.element.addEventListener) {
                self.element.addEventListener("click", function (e) {
                    e.stopPropagation();
                }, false);
            }
            else if (self.element.attachEvent) {
                self.element.attachEvent("onclick", function () {
                    window.event.cancelBubble = true;
                });
            }
        }, 100);

        /* In the beginning, there was a truly gorgeous piece of code here to
         * handle positioning the dropdown that did most of the hard work in
         * CSS and just did a couple of nice to haves here, like work out an
         * appropriate max-height to avoid needing to scroll the browser
         * window.
         *
         * Unfortunately, on the seventh day, this code met IE 6 and 7, and
         * this approach quickly turned out not to work so well. Nesting an
         * absolutely positioned element within a relatively positioned one
         * with a z-index triggered one of IE's most spectacular (well,
         * infamous, at least) bugs, and the usual workarounds didn't work
         * because of the double nesting of non-static positioned elements.
         *
         * After bashing my head against the wall for several hours, I have
         * decided to cut my losses and handle all of the positioning in
         * Javascript, and instead attach the element to the document body.
         * There is precisely one advantage to doing this apart from IE
         * support: we get rid of one non-semantic div that was being
         * dynamically created anyway. There are numerous disadvantages: the
         * code is now uglier, it's prone to random breakage in new browser
         * versions if the semantics of the various positioning properties that
         * are being used change, and it's probably slower to boot.
         *
         * Basically, I would like to curse everyone involved in developing
         * Trident, the rendering engine used in IE. You have cost me most of a
         * day, some precious sanity, and reminded me just how much you suck.
         */

        /* Calculate the position of the input element within the document so
         * that we can set the appropriate positioning styles on the dropdown
         * element. */
        var x = 0;
        var y = 0;
        if (self.element.offsetParent) {
            (function () {
                var element = self.element;
                y = element.offsetHeight;
                do {
                    x += element.offsetLeft;
                    y += element.offsetTop;
                } while (element = element.offsetParent);
            })();
        }

        self.dropdown.style.position = "absolute";
        self.dropdown.style.left = x + "px";
        self.dropdown.style.top = y + "px";

        /* Now we want to calculate the maximum possible height the dropdown
         * can take without forcing scrolling. */

        // Calculate the viewport height in a vaguely cross browser way.
        var viewportHeight;
        if (window.innerHeight) {
            viewportHeight = window.innerHeight;
        }
        else if (document.documentElement.clientHeight && document.documentElement.clientHeight > 0) {
            viewportHeight = document.documentElement.clientHeight;
        }

        // Calculate the current scroll position of the page.
        var scrollY = window.scrollY ? window.scrollY : document.documentElement.scrollTop;

        /* To work out the maximum height, we now look at where the input
         * element is within the viewport and do some basic maths. The 5 pixel
         * offset in the maxHeight calculation is basically a fudge for
         * browsers that don't include border sizes within offsetHeight. 
         *
         * As a minimum, the maximum height will always be able to cover one
         * row within the dropdown, even if there isn't enough room in the
         * viewport.
         */
        var posInViewport = y - scrollY;
        var maxHeight = Math.max(viewportHeight - posInViewport - 5, self.rows[0].offsetHeight);

        self.dropdown.style.maxHeight = maxHeight + "px";

        /* In general, I don't advocate browser sniffing, but this is one of
         * those rare times when we really do need to deliver a hack
         * specifically to IE 6 to emulate max-height. */
        if (self.ie6) {
            if (self.dropdown.scrollHeight > maxHeight) {
                self.dropdown.style.height = maxHeight + "px";
            }
            else {
                self.dropdown.style.height = "auto";
            }
        }

        /* Set the minimum width of the dropdown to the actual width of the
         * text box, and the maximum width to what can be displayed within the
         * viewport. */
        var availableWidth = document.documentElement.clientWidth - x;

        self.dropdown.style.minWidth = self.element.offsetWidth + "px";
        self.dropdown.style.maxWidth = availableWidth + "px";

        /* Similarly, we have to override the proprietary overflow-x and
         * overflow-y style properties on IE 6 and 7 to get sane scrollbar
         * behaviour. */
        if (self.ie6 || self.ie7) {
            self.dropdown.style.overflowX = "hidden";
            self.dropdown.style.overflowY = "auto";

            /* This is also a quick and dirty way of suggesting to IE that it
             * not use a tonne of horizontal space for the dropdown. */
            var maxWidth = self.element.offsetWidth * 2;

            // The - 10 is a complete fudge. Does seem to help, though.
            self.dropdown.style.width = Math.min(maxWidth, availableWidth - 10) + "px";

            /* Background iframe hack for IE 6. We have to do this after
             * everything else so we can reuse the styles we've previously
             * applied. */
            if (self.ie6) {
                self.iframe = document.createElement("iframe");
                self.iframe.style.width = self.dropdown.style.width;
                self.iframe.style.height = self.dropdown.style.height;
                self.iframe.style.position = "absolute";
                self.iframe.style.top = self.dropdown.style.top;
                self.iframe.style.left = self.dropdown.style.left;
                self.iframe.style.filter = "alpha(opacity=0)";
                
                document.body.insertBefore(self.iframe, self.dropdown);
            }
        }

        /* Finally, if the input element already has a value, we'll find the
         * row it matches in the dropdown (if one exists) and "select" it,
         * thereby highlighting it and ensuring the dropdown scrolls to a point
         * where it can be seen. */
        if (self.element.value) {
            var currentRow = self.findRowByName(self.element.value);
            if (currentRow) {
                self.selectRow(currentRow);
            }
        }
    };

    self.findRowByName = function (name) {
        for (var i = 0; i < self.rows.length; i++) {
            if (self.rows[i].value == name) {
                return self.rows[i];
            }
        }

        return null;
    };

    /* Note that this returns an object with both the currently selected row
     * and the row's position within the rows array, largely to make the code
     * in moveSelection simpler. */
    self.getSelected = function () {
        for (var i = 0; i < self.rows.length; i++) {
            if (self.rows[i].getAttribute("selected")) {
                return {
                    row: self.rows[i],
                    position: i
                };
            }
        }

        return null;
    };

    self.moveSelection = function (offset) {
        if (self.rows) {
            var current = self.getSelected();

            if (current) {
                var position = current.position + offset;

                // Handle negative wraparound.
                while (position < 0) {
                    position += self.rows.length;
                }

                /* The modulo handles positive wraparound by constraining the
                 * position to an actual valid value. */
                self.selectRow(self.rows[position % self.rows.length]);
            }
            else {
                // No current row; figure out what to select instead.
                if (offset > 0) {
                    self.selectRow(self.rows[offset - 1]);
                }
                else if (offset < 0) {
                    self.selectRow(self.rows[self.rows.length + offset]);
                }
                else {
                    self.selectRow(self.rows[offset]);
                }
            }
        }
    };

    self.selectRow = function (row) {
        if (row) {
            // Remove the selected style off the current selection.
            var current = self.getSelected();
            if (current) {
                current.row.removeAttribute("selected");
                current.row.className = current.row.className.replace(/\bselected\b/, " ").replace(/\s*$/, "");
            }

            /* Select the row. Originally, this would only have applied the
             * attribute, but since IE 6 can't style based on an arbitrary
             * attribute selector, we need to give it a class as well. Since
             * it's possible (albeit unlikely) that a class "selected" might
             * exist outside of the combo box widget context, the "selected"
             * attribute is being used as the canonical way of indicating that
             * the row is actually selected. */
            row.setAttribute("selected", "selected");
            row.className = row.className.replace(/\s*$/, " selected");

            /* Move the dropdown's scroll position to ensure the selected row
             * is in view. */
            var rowTop = row.offsetTop;
            var rowBottom = row.offsetTop + row.offsetHeight;

            var currentTop = self.dropdown.scrollTop;
            var currentBottom = self.dropdown.scrollTop + self.dropdown.clientHeight;

            if (rowTop < currentTop) {
                self.dropdown.scrollTop = rowTop;
            }
            else if (rowBottom > currentBottom) {
                self.dropdown.scrollTop = rowBottom - self.dropdown.clientHeight;
            }
        }
    };

    element.onfocus = function (e) {
        if (self.timeout) {
            window.clearTimeout(self.timeout);
            self.timeout = null;
        }

        self.showDropdown();
    };

    element.onkeydown = function (e) {
        var keyCode = window.event ? window.event.keyCode : e.keyCode;

        /* We have to handle tab keys here since the keyup event never actually
         * reaches the element (which makes sense when you think about what tab
         * does). */
        if (keyCode == 9) {
            self.hideDropdown();
        }
    };

    element.onkeyup = function (e) {
        // Fuck you, IE.
        var keyCode = window.event ? window.event.keyCode : e.keyCode;

        /* I did consider also trying to catch the Enter key here, but since it
         * still triggers the onsubmit for the form, there's not really much
         * point. Escape is close enough, and works reasonably well across
         * browsers. */
        if (keyCode == 38) {
            // Up.
            self.moveSelection(-1);
            self.element.value = self.getSelected().row.value;
            return false;
        }
        else if (keyCode == 40) {
            // Down.
            self.moveSelection(1);
            self.element.value = self.getSelected().row.value;
            return false;
        }
        else if (keyCode == 27) {
            // Escape.
            self.hideDropdown();
            return false;
        }

        return true;
    };
};


ComboBox.exceptionToString = function () {
    return this.name + ": " + this.message;
};

ComboBox.JSONException = function (message) {
    this.message = message;
    this.name = "JSONException";
    this.toString = ComboBox.exceptionToString;
};


// Initialise the combo box widgets.
(function () {
    var init = function () {
        var boxes;

        if (document.querySelectorAll) {
            boxes = document.querySelectorAll("input.combo");
        }
        else {
            boxes = [];
            var inputs = document.getElementsByTagName("input");

            for (var i = 0; i < inputs.length; i++) {
                if (inputs[i].className.indexOf("combo") != -1) {
                    boxes.push(inputs[i]);
                }
            }
        }

        for (var i = 0; i < boxes.length; i++) {
            new ComboBox(boxes[i]);
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
