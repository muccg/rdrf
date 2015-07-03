var RPC = (function() {

    var rpcObject = function(endPointUrl, csrfToken) {
        this.endPoint = endPointUrl;
        this.send = function(commandName, commandData, successCallBack) {
            var packet = {
                             rpc_command: commandName,
                             args: commandData
            };
            var packetJSON = JSON.stringify(packet);
            $.ajaxSetup({beforeSend: function(xhr) {
                             xhr.setRequestHeader('X-CSRFToken', csrfToken);
            }});
            $.post(this.endPoint, packetJSON, successCallBack, 'json');
        };
    };

    return {
        RPC: rpcObject
    };
})();


