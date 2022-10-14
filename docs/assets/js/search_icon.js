// Change navbar search icon when form is in focus, active states

$(".form-control").focus(function () {
    $(this).prev('.input-group-append').removeClass().addClass('input-group-append-focus');
    $(this).next('.input-group-append').removeClass().addClass('input-group-append-focus');
});

$(".form-control").focusout(function () {
    $(this).prev('.input-group-append-focus').removeClass().addClass('input-group-append');
    $(this).next('.input-group-append-focus').removeClass().addClass('input-group-append');
});