// Plumbing code tp launch a constructor form for a DE value and return it back to the main form


function goodValue(element) {
    $(element).next(".validationindicator").html("<span class='validationindicator'>VALID</span>");
}

function badValue(element) {
    $(element).next(".validationindicator").html("<span class='validationindicator'>INVALID</span>");
}

function generic_constructor(element, constructorName, constructorFormUrl) {

   function updateValue(value) {
       $(element).closest("td").find("input[type='text']").val(value);
   }
   var w = window.open(constructorFormUrl, "Construct " + constructorName, "location=no,width=200,height=200,scrollbars=yes,top=100,left=100,resizable = no");
   // NB this function is/must be called on the child form to allow the constructed data value to be passed back to the form
   w.updateParentForm = updateValue;
}

function generic_validate(element, rpcEndPoint, rpcCommand) {

    var value = $(element).val();
    var csrfToken = $("input[name='csrfmiddlewaretoken']").val();

    var rpc = new RPC.RPC(rpcEndPoint, csrfToken);
    rpc.send(rpcCommand, [value], function (response) {
        var isValid = response.result;
        if (isValid) {
            goodValue(element);
        }
        else {
            badValue(element);
        }
    });
}