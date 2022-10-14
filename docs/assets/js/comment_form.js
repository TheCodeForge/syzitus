
// Expand comment box on focus, hide otherwise

$('.comment-box').focus(function (event) {
    event.preventDefault();

    $(this).parent().parent().addClass("collapsed");

});


/*
$('.comment-box').blur(function () {
    event.preventDefault();

    $(this).parent().parent().removeClass("collapsed");
});

*/

//Comment edit form

toggleEdit=function(id){
    comment=document.getElementById("comment-text-"+id);
    form=document.getElementById("comment-edit-"+id);
    box=document.getElementById('edit-box-comment-'+id);

    comment.classList.toggle("d-none");
    form.classList.toggle("d-none");
    autoExpand(box);
}

togglePostEdit=function(){

    body=document.getElementById("post-body");
    form=document.getElementById("edit-post-body");
    box=document.getElementById("post-edit-box");

    body.classList.toggle("d-none");
    form.classList.toggle("d-none");
    autoExpand(box);
}