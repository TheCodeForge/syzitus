// Display username and password requirements on input

$('#password-register').on('input', function () {

    var charCount = document.getElementById("password-register").value;
    var id = document.getElementById("passwordHelpRegister");
    var successID = document.getElementById("passwordHelpSuccess");

    console.log(charCount.length);

    if (charCount.length >= 8) {
        id.classList.add("d-none");
        successID.classList.remove("d-none");
    }
    else {
        id.classList.remove("d-none");
        successID.classList.add("d-none");
    };

});

// Check username length, special chars

$('#username-register').on('input', function () {

    var charCount = document.getElementById("username-register").value;
    var id = document.getElementById("usernameHelpRegister");
    var successID = document.getElementById("usernameHelpSuccess");

    var ruqqusAPI = 'https://www.ruqqus.com/api/is_available/' + charCount;

    if (charCount.length >= 5) {

    $.getJSON(ruqqusAPI, function(result) {
        $.each(result, function(i, field) {
          if (field == false) {
            id.innerHTML = '<span class="form-text font-weight-bold text-danger mt-1">Username already taken :(';
        }
    });
    });

}

    if (!/[^a-zA-Z0-9_$]/.test(charCount)) {
    // Change alert text
    id.innerHTML = '<span class="form-text font-weight-bold text-success mt-1">Username is a-okay!';

    if (charCount.length < 5) {
      id.innerHTML = '<span class="form-text font-weight-bold text-muted mt-1">Username must be at least 5 characters long.';
  }
  else if (charCount.length > 25) {
      id.innerHTML = '<span class="form-text font-weight-bold text-danger mt-1">Username must be 25 characters or less.';
  }
}
else {
    id.innerHTML = '<span class="form-text font-weight-bold text-danger mt-1">No special characters or spaces allowed.</span>';
};

});
