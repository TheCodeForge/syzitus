$(document).ready(function() {
	$('#login').submit(function() {
      // disable button
      $("#login_button").prop("disabled", true);
      // add spinner to button
      $("#login_button").html(
        `<span class="spinner-border spinner-border-sm mr-2" role="status" aria-hidden="true"></span>Signing in`
      );
    });
});

$(document).ready(function() {
	$('#signup').submit(function() {
      // disable button
      $("#register_button").prop("disabled", true);
      // add spinner to button
      $("#register_button").html(
        `<span class="spinner-border spinner-border-sm mr-2" role="status" aria-hidden="true"></span>Registering`
      );
    });
});

$(document).ready(function() {
	$('#submitform').submit(function() {
      // disable button
      $("#create_button").prop("disabled", true);
      // add spinner to button
      $("#create_button").html(
        `<span class="spinner-border spinner-border-sm mr-2" role="status" aria-hidden="true"></span>Creating post`
      );
    });
});