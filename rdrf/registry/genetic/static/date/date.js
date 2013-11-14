var CalendarTable = function (container, d, months, weekdays) {
    var self = this;

    if (d) {
        self.date = d;
    }
    else {
        self.date = new Date();
    }

    if (months) {
        self.months = months;
    }
    else {
        // Fallback to English.
        self.months = [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December"
        ];
    }

    if (weekdays) {
        self.weekdays = weekdays;
    }
    else {
        // Fallback to English again.
        self.weekdays = [
            "Mon",
            "Tue",
            "Wed",
            "Thu",
            "Fri",
            "Sat",
            "Sun"
        ];
    }

    // Build the basic elements for the table.
    self.table = document.createElement("table");
    self.table.className = "calendar-table";
    self.head = self.table.createTHead();
    self.body = document.createElement("tbody");
    self.table.appendChild(self.body);

    
    self.buildHeader = function () {
        while (self.head.rows.length > 0) {
            self.head.deleteRow(0);
        }

        // Set up the first header row.
        (function () {
            var Spinner = function (element, defaultValue) {
                element.className += " spinner";
                this.value = +defaultValue;

                this.previous = document.createElement("a");
                this.previous.className = "previous";
                this.previous.href = "#";
                this.previous.appendChild(document.createTextNode("<"));

                this.next = document.createElement("a");
                this.next.className = "next";
                this.next.href = "#";
                this.next.appendChild(document.createTextNode(">"));

                this.display = document.createElement("span");
                this.text = document.createTextNode("");
                this.display.appendChild(this.text);

                element.appendChild(this.previous);
                element.appendChild(this.next);
                element.appendChild(this.display);
            };

            var row = self.head.insertRow(0);

            var monthContainer = document.createElement("th");
            monthContainer.colSpan = 4;
            var yearContainer = document.createElement("th");
            yearContainer.colSpan = 3;

            var month = new Spinner(monthContainer, self.date.getMonth());
            var year = new Spinner(yearContainer, self.date.getFullYear());

            row.appendChild(monthContainer);
            row.appendChild(yearContainer);

            year.update = function () {
                year.text.data = year.value.toString();
                self.date.setFullYear(year.value);
                self.update();
            };

            year.previous.onclick = function () {
                year.value--;
                year.update();
                return false;
            };

            year.next.onclick = function () {
                year.value++;
                year.update();
                return false;
            };

            month.update = function () {
                month.text.data = self.months[month.value];
                self.date.setMonth(month.value);
                self.update();
            };

            month.previous.onclick = function () {
                month.value--;

                if (month.value == -1) {
                    month.value = 11;
                    year.value--;
                    year.update();
                }

                month.update();
                return false;
            };

            month.next.onclick = function () {
                month.value++;
                
                if (month.value == 12) {
                    month.value = 0;
                    year.value++;
                    year.update();
                }

                month.update();
                return false;
            };

            month.update();
            year.update();
        })();

        // Set up the days of the week.
        (function () {
            var row = self.head.insertRow(1);

            for (var i in self.weekdays) {
                if (self.weekdays.hasOwnProperty(i)) {
                    var weekday = self.weekdays[i];
                    var cell = document.createElement("th");

                    cell.appendChild(document.createTextNode(weekday));
                    row.appendChild(cell);
                }
            }
        })();
    };

    self.update = function (highlight) {
        while (self.body.rows.length > 0) {
            self.body.deleteRow(0);
        }

        /* Utility function to convert the Sunday-based day Javascript dates
         * use to the Monday-based day we're using here (which lines up with
         * Django and hence our day names). */
        var convertDay = function (day) {
            if (--day < 0) {
                day += 7;
            }
            return day % 7;
        };

        // Get the start of the month.
        var start = new Date(self.date.getTime());
        start.setDate(1);
        var month = start.getMonth();

        // Insert whatever cells we need before the first day of the month.
        var row = document.createElement("tr");
        self.body.appendChild(row);

        for (var i = 0; i < convertDay(start.getDay()); i++) {
            var cell = document.createElement("td");
            cell.className = "empty";
            row.appendChild(cell);
        }

        // Now loop through the month and append cells for each day.
        for (var day = start; day.getMonth() == month; day = new Date(day.getTime() + 86400000)) {
            (function () {
                if (row.cells.length == 7) {
                    row = document.createElement("tr");
                    self.body.appendChild(row);
                }

                var cell = document.createElement("td");
                cell.appendChild(document.createTextNode(day.getDate()));
                row.appendChild(cell);

                if (highlight) {
                    if (day.toDateString() == highlight.toDateString()) {
                        cell.className = "highlight";
                    }
                }

                cell.date = new Date(day.getTime());
                cell.onclick = function () {
                    if (self.ondate) {
                        self.ondate(cell.date);
                    }

                    return false;
                };
            })();
        }

        // Finally, add the required cells to avoid the table being ragged.
        while (row.cells.length < 7) {
            var cell = document.createElement("td");
            cell.className = "empty";
            row.appendChild(cell);
        }
    };


    self.buildHeader();
    self.update(self.date);

    container.appendChild(self.table);
};


var DateWidget = function (element) {
    var find = function (type) {
        var elements = element.getElementsByTagName("*");

        for (var i = 0; i < elements.length; i++) {
            if (elements[i].getAttribute("type") == type) {
                return elements[i];
            }
        }

        return null;
    };

    // Utility function to set the broken down elements to a Date object.
    var set = function (d) {
        var day = find("day");
        var month = find("month");
        var year = find("year");

        if (day) {
            day.value = d.getDate();
        }

        if (month) {
            month.value = d.getMonth() + 1;
        }

        if (year) {
            year.value = d.getFullYear();
        }
    };

    if (element.getAttribute("popup")) {
        (function () {
            var popup = JSON.parse(element.getAttribute("popup"));

            var link = document.createElement("a");
            link.className = "calendar-popup";
            link.href = "#";

            var image = document.createElement("img");
            image.src = popup.image;

            link.appendChild(image);
            element.appendChild(link);

            link.onclick = function () {
                var d = new Date();
                
                // Set the initial date value based on the current input value.
                var day = find("day");
                var month = find("month");
                var year = find("year");

                if (year.value) {
                    d.setFullYear(year.value);
                }

                if (month.value) {
                    d.setMonth(month.value - 1);
                }

                if (day.value) {
                    d.setDate(day.value);
                }

                var container = document.createElement("div");
                var iframe = null;
                
                container.style.position = "absolute";
                container.style.background = "white";

                // Calculate our position.
                var x = 0;
                var y = 0;
                if (link.offsetParent) {
                    (function () {
                        var e = link;
                        x = e.offsetWidth;
                        do {
                            x += e.offsetLeft;
                            y += e.offsetTop;
                        } while (e = e.offsetParent);
                    })();
                }

                container.style.left = x + "px";
                container.style.top = y + "px";

                var months = [];
                for (var i = 0; i < month.options.length; i++) {
                    months.push(month.options[i].text);
                }

                var weekdays = [];
                for (var i = 0; i < popup.weekdays.length; i++) {
                    weekdays.push(popup.weekdays[i][1]);
                }

                var table = new CalendarTable(container, d, months, weekdays);

                var hidePopup = function () {
                    if (container) {
                        document.body.removeChild(container);
                        container = null;
                        table = null;
                        if (iframe) {
                            document.body.removeChild(iframe);
                            iframe = null;
                        }
                    }
                };

                table.ondate = function (d) {
                    set(d);
                    hidePopup();
                };

                window.setTimeout(function () {
                    container.onclick = function (e) {
                        if (!e) {
                            e = window.event;
                        }

                        e.cancelBubble = true;

                        if (e.stopPropagation) {
                            e.stopPropagation();
                        }
                    };

                    document.body.onclick = function (e) {
                        hidePopup();
                    };
                }, 250);

                container.appendChild(table.table);
                document.body.appendChild(container);

                // IE 6 background iframe hack.
                if (window.navigator.userAgent.indexOf("MSIE 6.0") != -1) {
                    var iframe = document.createElement("iframe");
                    iframe.style.width = container.offsetWidth + "px";
                    iframe.style.height = container.offsetHeight + "px";
                    iframe.style.position = "absolute";
                    iframe.style.left = x + "px";
                    iframe.style.top = y + "px";
                    iframe.style.filter = "alpha(opacity=0)";
                    document.body.insertBefore(iframe, container);
                }

                return false;
            };
        })();
    }

    if (element.getAttribute("today")) {
        (function () {
            var today = document.createElement("a");
            today.href = "#";
            today.appendChild(document.createTextNode(element.getAttribute("today")));

            today.onclick = function () {
                set(new Date());
                return false;
            };

            element.appendChild(today);
        })();
    }
};


// Initialise the date widgets.
(function () {
    var init = function () {
        var boxes;

        if (document.querySelectorAll) {
            boxes = document.querySelectorAll("div.date");
        }
        else {
            boxes = [];
            var inputs = document.getElementsByTagName("div");

            for (var i = 0; i < inputs.length; i++) {
                if (inputs[i].className.indexOf("date") != -1) {
                    boxes.push(inputs[i]);
                }
            }
        }

        for (var i = 0; i < boxes.length; i++) {
            new DateWidget(boxes[i]);
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
