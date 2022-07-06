var inactivityTimeoutSetup = function (config) {
    var time;
    window.onload = resetTimer;
    document.onmousemove = resetTimer;
    document.onkeydown = resetTimer;
    var messageUpdate;
    var timeLeft = config.warning;
    var modal = getModal();
    const loginUrl = config.login; 

    $(document).on('hide.bs.modal','#timeout_warning_modal', function () {
	console.log("sending rpc to reset session timeout ...");
	config.rpc.send("reset_session_timeout",[], function(data) {
	    console.log("reset session!");
	});

    });


    function warning() {
	modal.show();
	messageUpdate = setInterval(update_timeout_message, 1000);
    }

    function getModal() {
	return new bootstrap.Modal(document.getElementById("timeout_warning_modal"));
    }

    function resetTimer() {
	modal.hide();
        clearTimeout(time);
	clearInterval(messageUpdate);
	timeLeft = config.warning;
	const message = $("#timeout_warning_message");
	message.text("");

	var startWarning = 1000 * ( config.timeout - config.warning );
        time = setTimeout(warning, startWarning);
    }

    function update_timeout_message() {
	const message = $("#timeout_warning_message");
	timeLeft -= 1; 
	if (timeLeft === 0) {
	    window.onbeforeunload = function () {
		return null;
	    };
	    window.location = loginUrl;
	}
	var msg = "You will be logged out in " + timeLeft.toString() + " seconds.";
	message.text(msg);
    }
};


