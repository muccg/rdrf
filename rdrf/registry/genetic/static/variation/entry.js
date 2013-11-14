var Entry = {
    asString: function () {
        var s = document.getElementById("sequence-type").value + ".";

        var rangeStart = document.getElementById("range-start").value;
        var rangeEnd = document.getElementById("range-end").value;
        if (rangeEnd.length > 0 && rangeEnd != rangeStart) {
            s += rangeStart + "_" + rangeEnd;
        }
        else {
            s += rangeStart;
        }

        var oldSequence = document.getElementById("sequence").value;
        var newSequence = document.getElementById("new-sequence").value;

        switch (document.getElementById("mutation-type").value) {
            case "substitution":
                s += oldSequence + ">" + newSequence;
                break;

            case "deletion":
                s += "del" + oldSequence;
                break;

            case "insertion":
                s += "ins" + newSequence;
                break;

            case "duplication":
                s += "dup" + oldSequence;
                break;

            case "indel":
                s += "del" + oldSequence + "ins" + newSequence;
                break;

            case "inversion":
                s += "inv";
                break;

            default:
                s += "(=)";
        }

        return s;
    }
};

(function () {
    var hideRangeEnd = function () {
        document.getElementById("range-end").value = "";
        document.getElementById("range-end-container").style.display = "none";
    };

    var queueUpdatePreview = (function () {
        var timeout = null;

        return function () {
            if (timeout) {
                window.clearTimeout(timeout);
            }

            timeout = window.setTimeout(function () {
                timeout = null;
                updatePreview();
            }, 100);
        };
    })();

    var setSequenceLabel = function (label) {
        var element = document.getElementById("sequence-label");

        while (element.childNodes.length > 0) {
            element.removeChild(element.firstChild);
        }

        element.appendChild(document.createTextNode(label));
    };

    var showSequences = function (oldSequence, newSequence) {
        if (oldSequence) {
            document.getElementById("sequence-container").style.display = "block";
        }
        else {
            document.getElementById("sequence-container").style.display = "none";
            document.getElementById("sequence").value = "";
        }

        if (newSequence) {
            document.getElementById("new-sequence-container").style.display = "block";
            setSequenceLabel("Old sequence:");
        }
        else {
            document.getElementById("new-sequence-container").style.display = "none";
            document.getElementById("new-sequence").value = "";
            setSequenceLabel("Sequence:");
        }
    };

    var showRangeEnd = function () {
        document.getElementById("range-end-container").style.display = "inline";
    };

    var updateForm = function () {
        var type = document.getElementById("mutation-type").value;

        if (type == "substitution") {
            // Substitutions always apply to a single point only.
            hideRangeEnd();
            showSequences(true, true);
        }
        else {
            showRangeEnd();

            if (type == "deletion") {
                showSequences(true, false);
                setSequenceLabel("Deleted sequence: (optional)");
            }
            else if (type == "insertion") {
                showSequences(false, true);
            }
            else if (type == "duplication") {
                showSequences(true, false);
                setSequenceLabel("Duplicated sequence: (optional)");
            }
            else if (type == "indel") {
                showSequences(true, true);
                setSequenceLabel("Old sequence: (optional)");
            }
            else if (type == "inversion") {
                showSequences(false, false);
            }
            else {
                // Dunno!
                showSequences(true, true);
            }
        }
    };

    var updatePreview = (function () {
        var timeout = null;
        var validity = document.getElementById("validity");

        var clearValidity = function () {
            while (validity.childNodes.length > 0) {
                validity.removeChild(self.validity.firstChild);
            }

            validity.className = "validity";
        };

        var checkValidity = function (s) {
            var xhr = XHR.create();

            xhr.onreadystatechange = function (e) {
                if (xhr.readyState == 4) {
                    var validity = document.getElementById("validity");
                    if (xhr.status == 1223 || (xhr.status >= 200 && xhr.status <= 299)) {
                        validity.className = "validity valid";
                    }
                    else if (xhr.status == 400 && xhr.getResponseHeader("Content-Type") == "application/json") {
                        validity.className = "validity invalid";
                    }
                    else {
                        validity.className = "validity hell-if-i-know";
                    }
                }
            };

            xhr = prepare_xhr(xhr, {"method":"POST", "url" : validate_sequence_url});
            xhr.send(s);
        };

        return function () {
            var preview = document.getElementById("preview");

            while (preview.childNodes.length > 0) {
                preview.removeChild(preview.firstChild);
            }

            var s = Entry.asString();
            if (s.length > 0) {
                document.getElementById("preview-container").style.display = "block";
                preview.appendChild(document.createTextNode(s));

                if (timeout) {
                    window.clearTimeout(timeout);
                }
                
                timeout = window.setTimeout(function () {
                    checkValidity(s);
                }, 500);
            }
            else {
                document.getElementById("preview-container").style.display = "none";
            }

            return true;
        };
    })();

    var init = function () {
        document.getElementById("mutation-type").onchange = function (e) {
            updateForm();
            updatePreview();
            return true;
        };

        document.getElementById("sequence-type").onchange = updatePreview;
        document.getElementById("range-start").onchange = updatePreview;
        document.getElementById("range-end").onchange = updatePreview;
        document.getElementById("sequence").onchange = updatePreview;
        document.getElementById("new-sequence").onchange = updatePreview;

        document.getElementById("sequence-type").onkeyup = queueUpdatePreview;
        document.getElementById("range-start").onkeyup = queueUpdatePreview;
        document.getElementById("range-end").onkeyup = queueUpdatePreview;
        document.getElementById("sequence").onkeyup = queueUpdatePreview;
        document.getElementById("new-sequence").onkeyup = queueUpdatePreview;

        updateForm();
    };

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
