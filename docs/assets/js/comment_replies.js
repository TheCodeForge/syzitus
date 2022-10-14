// https://stackoverflow.com/a/42183824/11724748

/*
function toggleDropdown(e) {
    const _d = $(e.target).closest('.dropdown'),
        _m = $('.dropdown-menu', _d);
    setTimeout(function () {
        const shouldOpen = e.type !== 'click' && _d.is(':hover');
        _m.toggleClass('show', shouldOpen);
        _d.toggleClass('show', shouldOpen);
        $('[data-toggle="dropdown"]', _d).attr('aria-expanded', shouldOpen);
    }, e.type === 'mouseleave' ? 150 : 0);
}

// Display profile card on hover

$('body')
    .on('mouseenter mouseleave', '.user-profile', toggleDropdown)
    .on('click', '.dropdown-menu a', toggleDropdown);

// Toggle comment collapse

$(".toggle-collapse").click(function (event) {
    event.preventDefault();

    var id = $(this).parent().attr("id");

    document.getElementById(id).classList.toggle("collapsed");
});
*/
// Reply to parent comment

function addReplyForm(commentId, postId) {

    var id = "reply-to-" + commentId;

    document.getElementById(id).innerHTML = '<div class="comment-write collapsed child"> <form id="reply-to-t3_'+commentId+'" action="/api/comment" method="post" class="input-group"> <input type="hidden" name="formkey" value="'+formkey()+'"> <input type="hidden" name="parent_fullname" value="t3_'+commentId+'"> <input type="hidden" name="submission" value="'+postId+'"> <textarea name="body" form="reply-to-t3_'+commentId+'" class="comment-box form-control rounded" id="reply-form" aria-label="With textarea" placeholder="Add your comment..." rows="3"></textarea> <div class="comment-format"> <small class="format pl-0"><i class="fas fa-bold" aria-hidden="true" onclick="makeReplyBold()" data-toggle="tooltip" data-placement="bottom" title="Bold"></i></small> <small class="format"><i class="fas fa-italic" aria-hidden="true" onclick="makeReplyItalics()" data-toggle="tooltip" data-placement="bottom" title="Italicize"></i></small> <small class="format"><i class="fas fa-quote-right" aria-hidden="true" onclick="makeReplyQuote()" data-toggle="tooltip" data-placement="bottom" title="Quote"></i></small> <small class="format"><span class="font-weight-bold text-uppercase" style="font-size: 16px" aria-hidden="true" data-toggle="modal" data-target="#gifModal" data-toggle="tooltip" data-placement="bottom" data-delay='{"show":"700", "hide":"300"}' title="Add GIF">GIF</span></small> <small class="format d-none"><i class="fas fa-link" aria-hidden="true"></i></small> <a href="javascript:void(0)" onclick="delReplyForm(\''+commentId+'\')" class="btn btn-secondary ml-auto cancel-form">Cancel</a> <button form="reply-to-t3_'+commentId+'" class="btn btn-primary ml-2">Comment</button> </div> </form> </div>';

}

    // Removes reply form innerHTML on click

function delReplyForm(commentId) {

    var id = "reply-to-" + commentId;

    document.getElementById(id).innerHTML = '';

};

//Autoexpand textedit comments

var autoExpand = function (field) {

	// Reset field height
	field.style.height = 'inherit';

	// Get the computed styles for the element
	var computed = window.getComputedStyle(field);

	// Calculate the height
	var height = parseInt(computed.getPropertyValue('border-top-width'), 10)
	             + parseInt(computed.getPropertyValue('padding-top'), 10)
	             + field.scrollHeight
	             + parseInt(computed.getPropertyValue('padding-bottom'), 10)
	             + parseInt(computed.getPropertyValue('border-bottom-width'), 10)
		     + 32;

	field.style.height = height + 'px';

};

document.addEventListener('input', function (event) {
	if (event.target.tagName.toLowerCase() !== 'textarea') return;
	autoExpand(event.target);
}, false);