/* Stock function to create an XMLHttpRequest object in a cross-browser way:
 * for most browsers these days that just means instantiating the object, but
 * older IE versions require a little more magic. */
var XHR = {
    create: function () {
        if (typeof XMLHttpRequest == "undefined") {
            try {
                return new ActiveXObject("Msxml2.XMLHTTP.6.0");
            }
            catch (e) {}

            try {
                return new ActiveXObject("Msxml2.XMLHTTP.3.0");
            }
            catch (e) {}

            try {
                return new ActiveXObject("Msxml2.XMLHTTP");
            }
            catch (e) {}

            throw new Error("Cannot create an XMLHttpRequest object");
        }
        else {
            return new XMLHttpRequest();
        }
    }
};


function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie != '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = cookies[i];
            cookie = cookie.replace(/^\s+|\s+$/g,''); // trim whitespace

            // Does this cookie string begin with the name we want?
            if (cookie.search(name) != -1) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
};


function sameOrigin(url) {
    // url could be relative or scheme relative or absolute
    var host = document.location.host; // host + port
    var protocol = document.location.protocol;
    var sr_origin = '//' + host;
    var origin = protocol + sr_origin;
    // Allow absolute or scheme relative URLs to same origin
    return (url == origin || url.slice(0, origin.length + 1) == origin + '/') ||
        (url == sr_origin || url.slice(0, sr_origin.length + 1) == sr_origin + '/') ||
        // or any other URL that isn't scheme relative or absolute i.e relative.
        !(/^(\/\/|http:|https:).*/.test(url));
}
function safeMethod(method) {
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}

//this function prepares an xhr request,
//adding the correct headers for XHR and CSRF
//The name of the cookie that will be set for CSRF should have been
//set as a global JS var called CSRF_COOKIE_NAME, otherwise you can pass it in
//yourself as settings.csrfname
function prepare_xhr(xhr, settings){
    var method = settings.method;
    var url = settings.url;
    var cookiename = typeof(settings.csrfname) == "undefined" ? CSRF_COOKIE_NAME : settings.csrfname;
    xhr.open(method, url, true);
    if (!safeMethod(method) && sameOrigin(url)) {
        xhr.setRequestHeader("X-CSRFToken", getCookie(cookiename));
    }
    xhr.setRequestHeader("X-Requested-With", "XMLHttpRequest");
    return xhr;
}

// vim: set cin ai et ts=4 sw=4:
