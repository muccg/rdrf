var inactivityTimeoutSetup = function (config) {
    var time;
    console.log(config.warning);
    console.log(config.timeout);
    window.onload = resetTimer;
    // DOM Events
    document.onmousemove = resetTimer;
    document.onkeydown = resetTimer;
    var messageUpdate;
    var timeLeft = config.warning;
    var modal = getModal();

    function warning() {
	modal.show();
	messageUpdate = setInterval(update_timeout_message, 1000);
    }

    function getModal() {
	return new bootstrap.Modal(document.getElementById("timeout_warning_modal"));
    }

    function updateTimerWidget() {
	console.log(time);
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
	    window.location = "/account/login?next=/router/";
	}
	var msg = "You will be logged out in " + timeLeft.toString() + " seconds.";
	message.text(msg);
    }
};


