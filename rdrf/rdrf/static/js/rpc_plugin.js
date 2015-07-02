(function($) {
    $.fn.addRPCHandler = function(options) {
        var settings = $.extend({
           // These are the defaults.
           command: null,
           inputIds: [],
           rpcEndPointUrl: null,
           csrfToken: "",
           successCallBack: function() {}
        }, options);

        var getInputs = function() {
            var inputData = [];
            for (var i = 0; i < settings.inputIds.length; i++) {
                var value = $("#" + settings.inputIds[i]).val();
                console.log("got input " + settings.inputIds[i] + " = " + value.toString());
                inputData.push(value);
            }
            return inputData;
        };

        var RPC = function(endPointUrl) {
            this.endPoint = endPointUrl;
            this.send = function(commandName, commandData, successCallBack) {
                console.log('sending rpc command: ' + commandName + ' data: ' + commandData.toString());
                var packet = {
                                 rpc_command: commandName,
                                 args: commandData
                };
                var packetJSON = JSON.stringify(packet);
                $.ajaxSetup({beforeSend: function(xhr) {
                                 xhr.setRequestHeader('X-CSRFToken', settings.csrfToken);
                }});
                $.post(this.endPoint, packetJSON, successCallBack, 'json');
            };
        };

        this.click(function() {
            var rpc = new RPC(settings.rpcEndPointUrl);
            var inputs = getInputs();
            rpc.send(settings.command, inputs, settings.successCallBack);
        });

        return this;
    };

}(jQuery));
