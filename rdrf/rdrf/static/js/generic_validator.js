// Plumbing code tp launch a constructor form for a DE value and return it back to the main form



function goodValue(element) {
    var indicator = $(element).next(".validationindicator");
    if (indicator.hasClass("validity invalid")) {
        indicator.removeClass('validity invalid');
    }
    indicator.addClass("validity valid");
}

function badValue(element) {
    var indicator = $(element).next(".validationindicator");
    if (indicator.hasClass("validity valid")) {
        indicator.removeClass('validity valid');
    }
    indicator.addClass("validity invalid");
}

function noValue(element) {
    var indicator = $(element).next(".validationindicator");
    if(indicator.hasClass("validity valid")) {
        indicator.removeClass('validity valid');
    }
    if(indicator.hasClass("validity invalid")) {
        indicator.removeClass('validity invalid');
    }
}

function generic_constructor(element, constructorName, constructorFormUrl) {
   // element here is the constructor button next to the input field - we have
   // to use navigate via jquery traversal as the field may be in a multisection and have been cloned

   function updateValue(value) {
       var textField = $(element).closest("div").find("input[type='text']");
       textField.val(value);  // we assume that the DE is text input field
       textField.trigger("keyup");
   }
   // NB IE 8 doesn't like spaces in window name
   var w = window.open(constructorFormUrl, constructorName.replace(/ /g, ''), "location=no,width=800,height=600,scrollbars=yes,top=100,left=700,resizable = no");
   // NB this function is/must be called on the child form to allow the constructed data value to be passed back to the form
   w.updateParentForm = updateValue;

}

function generic_validate(element, rpcEndPoint, rpcCommand) {
    // element is the text box
    var value = $(element).val();

    var csrfToken = $("input[name='csrfmiddlewaretoken']").val(); // this will/must appear on our django form
    var rpc = new RPC.RPC(rpcEndPoint, csrfToken);

    // If the user has entered text and cleared the input field, remove any prior validation icon as there is nothing to validate.
    // This is also used on the initial page load as the text fields are empty and there is nothing to validate.
    if(value.length == 0) {
        noValue(element);
        return;
    }

    rpc.send(rpcCommand, [value], function(response) {
        var isValid = response.result;
        if (isValid) {
            goodValue(element);
        }
        else {
            badValue(element);
        }
    });
}
