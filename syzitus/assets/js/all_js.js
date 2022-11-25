function formkey() {
      return $('#formkey_element').data('formkey');
}

//avoid console errors
$(document).on('click', 'a[href="javascript:void(0)"]', function(event){event.preventDefault()})

// Using mouse

document.body.addEventListener('mousedown', function() {
  document.body.classList.add('using-mouse');
});

document.body.addEventListener('keydown', function(event) {
  if (event.keyCode === 9) {
    document.body.classList.remove('using-mouse');
  }
});

// 2FA toggle modal

$('#2faModal').on('hidden.bs.modal', function () {

  var box = document.getElementById("2faToggle");
  
  box.checked = !box.checked;

});

//email change

// Show confirm password field when user clicks email box

$('#new_email').on('input', function () {

  var id = document.getElementById("email-password");
  var id2 = document.getElementById("email-password-label");
  var id3 = document.getElementById("emailpasswordRequired");

  id.classList.remove("d-none");
  id2.classList.remove("d-none");
  id3.classList.remove("d-none");

});

//GIFS

  // Identify which comment form to insert GIF into

  var commentFormID;

$('.btn-open-inserters').click(function(){
  //this is actually a <textarea> ID, not a comment or a <form> idea
  //blame the ruqqus devs not me
  commentFormID=$(this).data('form-id')
})



$('#gifModal #gifSearch').change(function(){

  var searchTerm = $(this).val();

  //handle blank search
  if (searchTerm=="" || searchTerm==undefined) {
    $('#default-GIFs').removeClass('d-none');
    $('#GIFs').addClass('d-none');
    $('#no-GIFs').addClass('d-none');
    return;
  }

  postformtoast($('#gif-search-form'), callback=function(xhr){
    var resp=JSON.parse(xhr.response);
    //console.log(data)
    var data = resp['data']

    if (data.length==0) {
      $('#default-GIFs').addClass('d-none');
      $('#no-GIFs').removeClass('d-none');
      $('#GIFs').addClass('d-none');
      return;
    }

    output=""

    for (i=0; i<data.length; i++){
      output += '<div class="card bg-white gif-insert-btn" data-dismiss="modal" aria-label="Close" data-gif-url="' + data[i]['images']['original']['url'] + '" data-comment-form-id="' + commentFormID + '"><div class="gif-cat-overlay"></div><img class="img-fluid" src="' + data[i]['images']['fixed_width_downsampled']['url'] + '/100.gif"></div>'
    }

    $('#default-GIFs').addClass('d-none');
    $('#no-GIFs').addClass('d-none');
    $('#GIFs').removeClass('d-none');
    $('#GIFs').html(output)

  })

})

$('.clear-gif-form').click(function(){
  $('#gifSearch').val('');
  $('#gifSearch').change()
})

$('#gifModal .searchcard').click(function(){
  $('#gifSearch').val($(this).data('gif-search-term'));
  $('#gifSearch').change();

})

$('#gifSearch').on('keypress', function(event){
  if (event.key==="Enter"){
    event.preventDefault();
    $('#gifSearch').change();
  }
})

$(document).on('click', '.gif-insert-btn', function(){
  var textbox= $('#'+$(this).data('comment-form-id'))
  textbox.val(textbox.val()+"![]("+$(this).data('gif-url')+")")
})


$(document).on('click', '.comment-collapse', function() {
  $("#comment-"+$(this).data('comment-id')).toggleClass("collapsed");
})

// Commenting form

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

// Comment edit form
$('.btn-toggle-comment-edit').click(function(){
  id=$(this).data('comment-id')
  $("#comment-text-"+id).toggleClass('d-none');
  $("#comment-edit-"+id).toggleClass('d-none');
  $('#comment-' + id +'-actions').toggleClass('d-none');

  box=document.getElementById('comment-edit-body-'+id);
  autoExpand(box);
})

// Post edit form

$(document).on('click', ".btn-edit-post", function(){
  id=$(this).data("target-id")
  box=document.getElementById("post-edit-box-"+id);

  $('#post-body').toggleClass("d-none");
  $('#edit-post-body-'+$(this).data('target-id')).toggleClass("d-none");
  autoExpand(box);
}
)

//comment modding
$('.btn-mod-comment').click(function () {

  var url;

  if ($("#comment-"+$(this).data('comment-id')+"-only").hasClass("banned")) {
    url="/api/unban_comment/"+$(this).data('comment-id');
    callback=function(){
      $("#comment-"+$(this).data('comment-id')+"-only").removeClass("banned");
      $('.btn-mod-comment-text-'+$(this).data('comment-id')).text("Approve")
    }
  } else {
    url="/api/ban_comment/"+$(this).data('comment-id');
    callback=function(){
      $("#comment-"+$(this).data('comment-id')+"-only").addClass("banned");
      $('.btn-mod-comment-text-'+$(this).data('comment-id')).text("Remove")
    }
  }
  post_toast(url, callback)
})


$(document).on('click', '.btn-distinguish-comment', function(){

  var comment_id=$(this).data('comment-id');

  var xhr = new XMLHttpRequest();
  xhr.open("post", "/api/distinguish_comment/"+comment_id);

  var form = new FormData();

  form.append('formkey', formkey());

  xhr.withCredentials=true;
  xhr.onload=function(){
    if (xhr.status==200) {
      $('#comment-'+comment_id+'-only').html(JSON.parse(xhr.response)["html"]);
    }
    else {
      $('#toast-success').toast('dispose');
      $('#toast-error').toast('dispose');
      $('#toast-error').toast('show');
      $('#toast-error.toast-text').text(JSON.parse(xhr.response)["error"]);
    }
  }
  xhr.send(form)
})



//comment replies

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


//Autoexpand textedit comments

function autoExpand (field) {

  //get current scroll position
  xpos=window.scrollX;
  ypos=window.scrollY;

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

  //keep window position from changing
  window.scrollTo(xpos,ypos);

};

document.addEventListener('input', function (event) {
  if (event.target.tagName.toLowerCase() !== 'textarea') return;
  autoExpand(event.target);
}, false);

//dark mode

$(".dark-switch").click(function () {

  if ($('#css-link-light').attr("rel")=="stylesheet") {
    post("/settings/dark_mode/1",
      callback=function(){
        $('#css-link-dark').attr("rel", "stylesheet");
        $('#css-link-light').attr("rel", "");
        $('body').toggleClass('light');
        $('body').toggleClass('dark');
        $('.dark-switch-icon').removeClass('fa-toggle-off')
        $('.dark-switch-icon').addClass('fa-toggle-on')
      }
      );
  }
  else {
    post("/settings/dark_mode/0",
      callback=function(){
        $('#css-link-dark').attr("rel", "");
        $('#css-link-light').attr("rel", "stylesheet");
        $('body').toggleClass('light');
        $('body').toggleClass('dark');
        $('.dark-switch-icon').removeClass('fa-toggle-on')
        $('.dark-switch-icon').addClass('fa-toggle-off')
      }
      );
  }
})

// Delete Post
$('.btn-delete-post').click(function() {
  $('.btn-delete-post-confirm').data('delete-url', '/delete_post/'+$(this).data('post-id'))
})


$('.btn-delete-post-confirm').click(function(){  

  this.innerHTML='<span class="spinner-border spinner-border-sm mr-2" role="status" aria-hidden="true"></span>Deleting post';  
  this.disabled = true; 
  post($(this).data('delete-url'),
    callback = function() {
      location.reload();
    }
    )
  }
)

// Delete Comment

$(document).on('click', '.btn-delete-comment', function() {
  $("#deleteCommentButton").data('delete-url', '/delete/comment/' + $(this).data('comment-id'))
})


$('#deleteCommentButton').click(function() {  
    this.innerHTML='<span class="spinner-border spinner-border-sm mr-2" role="status" aria-hidden="true"></span>Deleting comment';  
    this.disabled = true; 
    post($(this).data('delete-url'),
      callback = function() {
        location.reload();
      }
      )
  }
)

//Email verification text

//flagging
// Flag Comment
$('.btn-report-comment').click(function() {

  $("#comment-author").text($(this).data('target-author'));

  //offtopic.disabled=true;

  $("#reportCommentButton").data('report-url', '/api/flag/comment/'+$(this).data('comment-id'))
  })

$("#reportCommentButton").click(function() {

  this.innerHTML='<span class="spinner-border spinner-border-sm mr-2" role="status" aria-hidden="true"></span>Reporting comment';
  this.disabled = true;
  post($(this).data('report-url'),
    callback = function() {
      $("#reportCommentFormBefore").addClass('d-none');
      $("#reportCommentFormAfter").removeClass('d-none');
    }
  )
})

$('#reportCommentModal').on('hidden.bs.modal', function () {

  var button = document.getElementById("reportCommentButton");

  var beforeModal = document.getElementById("reportCommentFormBefore");
  var afterModal = document.getElementById("reportCommentFormAfter");

  button.innerHTML='Report comment';
  button.disabled= false;
  afterModal.classList.add('d-none');

  if ( beforeModal.classList.contains('d-none') ) {
    beforeModal.classList.remove('d-none');
  }

});


// Flag Submission
$('.btn-report-post').click(function() {

  $("#post-author").text($(this).data('target-author'));

  $('#report-post-to-guild-dropdown-option').text('This post is off-topic for +' + $(this).data('target-board'));

  if (board=='general') {
    $('#report-post-to-guild-dropdown-option').prop('disabled', true);
  }
  else {
    $('#report-post-to-guild-dropdown-option').prop('disabled', false);
  }

  $('#report-type-dropdown').val('reason_not_selected');

  $("#reportPostButton").prop('disabled',true)
  $("#reportPostButton").data('report-url', $(this).data('report-url'))
  })

$('#reportPostButton').click(function() {
  post_toast($(this).data('report-url'))
})

$('#reportPostModal').on('hidden.bs.modal', function () {

  var button = document.getElementById("reportPostButton");

  var beforeModal = document.getElementById("reportPostFormBefore");
  var afterModal = document.getElementById("reportPostFormAfter");

  button.innerHTML='Report post';
  button.disabled= false;

  afterModal.classList.add('d-none');

  if ( beforeModal.classList.contains('d-none') ) {
    beforeModal.classList.remove('d-none');
  }

});

//enlarge thumbs
// Enlarge submissionlisting thumbnail

enlarge_thumb = function(post_id) {

  document.getElementById(post_id).classList.toggle("enlarged");

};

//iOS webapp stuff

(function(document,navigator,standalone) {
            // prevents links from apps from oppening in mobile safari
            // this javascript must be the first script in your <head>
            if ((standalone in navigator) && navigator[standalone]) {
              var curnode, location=document.location, stop=/^(a|html)$/i;
              document.addEventListener('click', function(e) {
                curnode=e.target;
                while (!(stop).test(curnode.nodeName)) {
                  curnode=curnode.parentNode;
                }
                    // Condidions to do this only on links to your own app
                    // if you want all links, use if('href' in curnode) instead.
                    if('href' in curnode && ( curnode.href.indexOf('http') || ~curnode.href.indexOf(location.host) ) ) {
                      e.preventDefault();
                      location.href = curnode.href;
                    }
                  },false);
            }
          })(document,window.navigator,'standalone');


//KC easter egg

$(function(){
  var kKeys = [];
  function Kpress(e){
    kKeys.push(e.keyCode);
    if (kKeys.toString().indexOf("38,38,40,40,37,39,37,39,66,65") >= 0) {
      $(this).unbind('keydown', Kpress);
      kExec();
    }
  }
  $(document).keydown(Kpress);
});
function kExec(){
 $('body').append ('<iframe width="0" height="0" src="https://www.youtube.com/embed/xoEEOrTctpA?rel=0&amp;controls=0&amp;showinfo=0&autoplay=1" frameborder="0" allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>');
 $('a').addClass('ruckus');
 $('p').addClass('ruckus');
 $('img').addClass('ruckus');
 $('span').addClass('ruckus');
 $('button').addClass('ruckus');
 $('i').addClass('ruckus');
 $('input').addClass('ruckus');
};

//Post kick

kick_postModal = function(id) {

  document.getElementById("kickPostButton").onclick = function() {

    this.innerHTML='<span class="spinner-border spinner-border-sm mr-2" role="status" aria-hidden="true"></span>kicking post';
    this.disabled = true;
    post('/api/flag/post/' + id,
      callback = function() {

        location.reload();
      }
      )
  }
};

$('#kickPostModal').on('hidden.bs.modal', function () {

  var button = document.getElementById("kickPostButton");

  var beforeModal = document.getElementById("kickPostFormBefore");
  var afterModal = document.getElementById("kickPostFormAfter");

  button.innerHTML='kick post';
  button.disabled= false;

  afterModal.classList.add('d-none');

  if ( beforeModal.classList.contains('d-none') ) {
    beforeModal.classList.remove('d-none');
  }

});

$('.kick-button-listing').click(function(event) {
  if (event.which != 1) {return}

  boardname=$(this).data('boardname')
  pid=$(this).data('pid')

  post_response('/mod/kick/'+ boardname+'/'+pid, callback=function(xhr){
    $("#post-"+pid).replaceWith(JSON.parse(xhr.response)['data'])
      }
    )
  }
)

//POST

function post(url, callback=function(){console.log('.')}, errortext="") {
  var xhr = new XMLHttpRequest();
  xhr.open("POST", url, true);
  var form = new FormData()
  form.append("formkey", formkey());
  xhr.withCredentials=true;
  xhr.onerror=function() { alert(errortext); };
  xhr.onload = function() {
    if (xhr.status >= 200 && xhr.status < 300) {
      callback();
    } else {
      xhr.onerror();
    }
  };
  xhr.send(form);
};

function post_response(url, callback=function(){console.log('.')}, errortext) {
  var xhr = new XMLHttpRequest();
  xhr.open("POST", url, true);
  var form = new FormData()
  form.append("formkey", formkey());
  xhr.withCredentials=true;
  xhr.onerror=function() { alert(errortext); };
  xhr.onload = function() {
    if (xhr.status >= 200 && xhr.status < 300) {
      callback(xhr);
    } else {
      xhr.onerror();
    }
  };
  xhr.send(form);
};

// sub/unsub

function toggleSub(thing_id){
  $('#button-unsub-'+thing_id).toggleClass('d-none');
  $('#button-sub-'+thing_id).toggleClass('d-none');
  $('#button-unsub-modal-'+thing_id).toggleClass('d-none');
  $('#button-sub-modal-'+thing_id).toggleClass('d-none');
  $('#button-unsub-mobile-'+thing_id).toggleClass('d-none');
  $('#button-sub-mobile-'+thing_id).toggleClass('d-none');
}

function post_toast(url, callback=function(){}) {
  var xhr = new XMLHttpRequest();
  xhr.open("POST", url, true);
  var form = new FormData()
  form.append("formkey", formkey());
  xhr.withCredentials=true;

  xhr.onload = function() {
    if (xhr.status==204){
      return
    }
    data=JSON.parse(xhr.response);
    if (xhr.status >= 200 && xhr.status < 300) {
      $('#toast-success .toast-text').text(data['message']);
      $('#toast-success').toast('show');
      callback();
    } else if (xhr.status >= 300 && xhr.status < 400 ) {
      window.location.href=data['redirect']
    } else {
      $('#toast-error .toast-text').text(data['error']);
      $('#toast-error').toast('show')
    }
  };

  xhr.send(form);

  }

// Bell Notifications

$('.bell-button').click(function (event) {

  if (event.which != 1) {
    return
  }

  $('.bell-icon').toggleClass('fa-bell')
  $('.bell-icon').toggleClass('fa-bell-on')
  $('.bell-icon').toggleClass('text-purple')

  post_toast($(this).data('url'))

});


//Admin post modding

$('.admin-remove-post').click(function() {
  post_id=$(this).data('post-id')
  url="/api/ban_post/"+post_id

  callback=function(){
    document.getElementById("post-"+post_id).classList.add("banned");

    $('.admin-approve-post-'+post_id).removeClass('d-none')
    $('.admin-remove-post-'+post_id).addClass('d-none')
  }
  post(url, callback, "Unable to remove post at this time. Please try again later.")
})

$('.admin-approve-post').click(function() {
  post_id=$(this).data('post-id')
  url="/api/unban_post/"+post_id

  callback=function(){
    document.getElementById("post-"+post_id).classList.remove("banned");

    $('.admin-approve-post-'+post_id).addClass('d-none')
    $('.admin-remove-post-'+post_id).removeClass('d-none')
  }

  post(url, callback, "Unable to approve post at this time. Please try again later.")
})

//Element deleter

function deleteElement(eid) {
  x=document.getElementById(eid)
  x.parentElement.removeChild(x)

}


//Signup js
// Display username and password requirements on input

$('#password-register').on('input', function () {

  var charCount = document.getElementById("password-register").value;
  var id = document.getElementById("passwordHelpRegister");
  var successID = document.getElementById("passwordHelpSuccess");

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

  var ruqqusAPI = '/api/is_available/' + charCount;

  if (charCount.length >= 3) {

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

    if (charCount.length < 3) {
      id.innerHTML = '<span class="form-text font-weight-bold text-muted mt-1">Username must be at least 3 characters long.';
    }
    else if (charCount.length > 25) {
      id.innerHTML = '<span class="form-text font-weight-bold text-danger mt-1">Username must be 25 characters or less.';
    }
  }
  else {
    id.innerHTML = '<span class="form-text font-weight-bold text-danger mt-1">No special characters or spaces allowed.</span>';
  };

});

// Search Icon
// Change navbar search icon when form is in focus, active states

$(".form-control").focus(function () {
  $(this).prev('.input-group-append').removeClass().addClass('input-group-append-focus');
  $(this).next('.input-group-append').removeClass().addClass('input-group-append-focus');
});

$(".form-control").focusout(function () {
  $(this).prev('.input-group-append-focus').removeClass().addClass('input-group-append');
  $(this).next('.input-group-append-focus').removeClass().addClass('input-group-append');
});

//spinner effect

$(document).ready(function() {
  $('#login').submit(function() {
      // disable button
      $("#login_button").prop("disabled", true);
      // add spinner to button
      $("#login_button").html('<span class="spinner-border spinner-border-sm mr-2" role="status" aria-hidden="true"></span>Signing in');
    });
});

$(document).ready(function() {
  $('#signup').submit(function() {
      // disable button
      $("#register_button").prop("disabled", true);
      // add spinner to button
      $("#register_button").html('<span class="spinner-border spinner-border-sm mr-2" role="status" aria-hidden="true"></span>Registering');
    });
});

$(document).ready(function() {
  $('#submitform').submit(function() {
      // disable button
      $("#create_button").prop("disabled", true);
      // add spinner to button
      $("#create_button").html('<span class="spinner-border spinner-border-sm mr-2" role="status" aria-hidden="true"></span>Creating post');
    });
});

// Sidebar collapsing

// Desktop

if (document.getElementById("sidebar-left") && localStorage.sidebar_pref == 'collapsed') {

  document.getElementById('sidebar-left').classList.add('sidebar-collapsed');

};

$('.toggle_sidebar_collapse').click(function() {

  // Store Pref
  localStorage.setItem('sidebar_pref', 'collapsed');

  document.getElementById('sidebar-left').classList.toggle('sidebar-collapsed');

})

$('.toggle_sidebar_expand').click(function() {

  // Remove Pref
  localStorage.removeItem('sidebar_pref');

  document.getElementById('sidebar-left').classList.toggle('sidebar-collapsed');

})

// Voting

$(document).on('click', '.upvote-button , .downvote-button', function(){

  type=$(this).data('type');
  id=$(this).data('id');
  var direction=0;

  if ($(this).hasClass('active')){
    direction=0;
  } else if ($(this).hasClass('upvote-button')) {
    direction=1;
  } else if ($(this).hasClass('downvote-button')) {
    direction=-1;
  }

  var new_score = Number($('.'+type+'-score-'+id)[0].innerText)

  if ($('.'+type+'-score-'+id).hasClass('score-up')){
    new_score--
  }
  else if ($('.'+type+'-score-'+id).hasClass('score-down')){
    new_score++
  }


  if ($(this).hasClass('downvote-button') && !$(this).hasClass('active')){
    new_score--
  }
  else if ($(this).hasClass('upvote-button') && !$(this).hasClass('active')){
    new_score++
  }

  $('.'+type+'-score-'+id).text(new_score)

  if (direction==1){

    $('.'+type+'-'+id+'-up').addClass('active')
    $('.'+type+'-'+id+'-down').removeClass('active')
    $('.'+type+'-score-'+id).addClass('score-up')
    $('.'+type+'-score-'+id).removeClass('score-down')

  } 
  else if (direction==0) {

    $('.'+type+'-'+id+'-up').removeClass('active')
    $('.'+type+'-'+id+'-down').removeClass('active')
    $('.'+type+'-score-'+id).removeClass('score-up')
    $('.'+type+'-score-'+id).removeClass('score-down')

  } 
  else if (direction==-1) {

    $('.'+type+'-'+id+'-up').removeClass('active')
    $('.'+type+'-'+id+'-down').addClass('active')
    $('.'+type+'-score-'+id).removeClass('score-up')
    $('.'+type+'-score-'+id).addClass('score-down')

  }

  url='/api/vote/' + type + "/" + id + "/" + direction;

  post_toast(url);

})


// Yank Post
$('#yank-type-dropdown').change(function(){
  $('#yankPostButton').prop('disabled',false);
})
$('.btn-yank-post').click(function(){
  $("#post-author-url").text($(this).data('post-author'));

  $("#post-comments").text($(this).data('comment-count'));

  $("#post-title").text($(this).data('title'));

  $("#post-author-url").attr('href', $(this).data('author-link'));

  $("#post-domain").text($(this).data('domain'));

  $("#post-timestamp").text($(this).data('timestamp'));


  $("#yankPostButton").data('yank-url', "/mod/take/"+$(this).data('post-id'));
})

$("#yankPostButton").click(function() {  


    var yankError = document.getElementById("toast-error-message");



    var xhr = new XMLHttpRequest();
    xhr.open("post", $(this).data('yank-url'));
    xhr.withCredentials=true;
    f=new FormData();
    f.append("formkey", formkey());
    f.append("board_id", document.getElementById('yank-type-dropdown').value)
    xhr.onload=function(){
      if (xhr.status==204) {
        window.location.reload(true);
      }
      else {
        $('#toast-invite-error').toast('dispose');
        $('#toast-invite-error').toast('show');
        yankError.textContent = JSON.parse(xhr.response)["error"];
      }
    }
    xhr.send(f);
  })

//yt embed

function getId(url) {
  var regExp = /^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|\&v=)([^#\&\?]*).*/;
  var match = url.match(regExp);

  if (match && match[2].length == 11) {
    return match[2];
  } else {
    return 'error';
  }
}

var myUrl = $('#embedURL').text();

myId = getId(myUrl);

$('#ytEmbed').html('<iframe width="100%" height="475" src="//www.youtube.com/embed/' + myId + '" frameborder="0" allowfullscreen></iframe>');


// Expand Images on Desktop



// When image modal is closed

$('#expandImageModal').on('hidden.bs.modal', function (e) {

    // // attribution div

    // var attribution = document.getElementById("modal-image-attribution");

    // // remove the attribution

    // attribution.innerHTML = null;

  // remove image src and link

  document.getElementById("desktop-expanded-image").src = '';

  document.getElementById("desktop-expanded-image-link").href = '';

});

// Text Formatting

// Bold Text

$('.btn-make-bold').click(function () {
  form=$(this).data('form-id')
  var text = document.getElementById(form);
  var startIndex = text.selectionStart,
  endIndex = text.selectionEnd;
  var selectedText = text.value.substring(startIndex, endIndex);

  var format = '**'

  if (selectedText.includes('**')) {
    text.value = selectedText.replace(/\*/g, '');
    
  }
  else if (selectedText.length == 0) {
    text.value = text.value.substring(0, startIndex) + selectedText + text.value.substring(endIndex);
  }
  else {
    text.value = text.value.substring(0, startIndex) + format + selectedText + format + text.value.substring(endIndex);
  }
})

// Italicize Comment Text

$('.btn-make-italic').click(function () {
  form=$(this).data('form-id')
  var text = document.getElementById(form);
  var startIndex = text.selectionStart,
  endIndex = text.selectionEnd;
  var selectedText = text.value.substring(startIndex, endIndex);

  var format = '*'

  if (selectedText.includes('*')) {
    text.value = selectedText.replace(/\*/g, '');
    
  }
  else if (selectedText.length == 0) {
    text.value = text.value.substring(0, startIndex) + selectedText + text.value.substring(endIndex);
  }
  else {
    text.value = text.value.substring(0, startIndex) + format + selectedText + format + text.value.substring(endIndex);
  }
})

// Quote Comment Text

$('.btn-make-quote').click(function () {
  form=$(this).data('form-id')
  var text = document.getElementById(form);
  var startIndex = text.selectionStart,
  endIndex = text.selectionEnd;
  var selectedText = text.value.substring(startIndex, endIndex);

  var format = '>'

  if (selectedText.includes('>')) {
    text.value = text.value.substring(0, startIndex) + selectedText.replace(/\>/g, '') + text.value.substring(endIndex);
    
  }
  else if (selectedText.length == 0) {
    text.value = text.value.substring(0, startIndex) + selectedText + text.value.substring(endIndex);
  }
  else {
    text.value = text.value.substring(0, startIndex) + format + selectedText + text.value.substring(endIndex);
  }
})

// Character Count

$('.textarea-form-input').on('input', function() {

  var input = $(this);

  var text = $('#'+$(this).data('text'));

  var length = input.val().length;

  var maxLength = input.attr("maxlength");

  if (length >= maxLength) {
    text.addClass('text-danger');
    text.removeClass('text-warning');
    text.removeClass('text-muted');
  }
  else if (length >= maxLength * .72){
    text.addClass('text-warning');
    text.removeClass('text-danger');
    text.removeClass('text-muted');
  }
  else {
    text.addClass('text-muted');
    text.removeClass('text-danger');
    text.removeClass('text-warning');
  }

  text.text(maxLength - length);

})



// Mobile bottom navigation bar

window.onload = function () {
  var prevScrollpos = window.pageYOffset;
  window.onscroll = function () {
    var currentScrollPos = window.pageYOffset;

    var topBar = document.getElementById("fixed-bar-mobile");

    var bottomBar = document.getElementById("mobile-bottom-navigation-bar");

    var dropdown = document.getElementById("mobileSortDropdown");

    var navbar = document.getElementById("navbar");

    if (bottomBar != null) {
      if (prevScrollpos > currentScrollPos && (window.innerHeight + currentScrollPos) < (document.body.offsetHeight - 65)) {
        bottomBar.style.bottom = "0px";
      } 
      else if (currentScrollPos <= 125 && (window.innerHeight + currentScrollPos) < (document.body.offsetHeight - 65)) {
        bottomBar.style.bottom = "0px";
      }
      else if (prevScrollpos > currentScrollPos && (window.innerHeight + currentScrollPos) >= (document.body.offsetHeight - 65)) {
        bottomBar.style.bottom = "-50px";
      }
      else {
        bottomBar.style.bottom = "-50px";
      }
    }

    // Execute if bottomBar exists

    if (topBar != null && dropdown != null) {
      if (prevScrollpos > currentScrollPos) {
        topBar.style.top = "49px";
      } 
      else if (currentScrollPos <= 125) {
        topBar.style.top = "49px";
      }
      else {
        topBar.style.top = "-49px";
        dropdown.classList.remove('show');
      }
    }
    prevScrollpos = currentScrollPos;
  }
}

// Tooltips

$(document).ready(function(){
  $('[data-toggle="tooltip"]').tooltip(); 
});

// Paste to create submission

document.addEventListener('paste', function (event) {

  var nothingFocused = document.activeElement === document.body;

  if (nothingFocused) {

    if (document.getElementById('guild-name-reference')) {
      var guild = document.getElementById('guild-name-reference').innerText;
    }

    var clipText = event.clipboardData.getData('Text');

    var url = new RegExp('^(?:[a-z]+:)?//', 'i');

    if (url.test(clipText) && window.location.pathname !== '/submit' && guild == undefined) {
      window.location.href = '/submit?url=' + clipText;
    }
    else if (url.test(clipText) && window.location.pathname !== '/submit' && guild !== undefined) {
      window.location.href = '/submit?url=' + clipText + '&guild=' + guild;
    }
    else if (url.test(clipText) && window.location.pathname == '/submit' && guild == undefined) {

      document.getElementById("post-URL").value = clipText;

      autoSuggestTitle()

    }
  }
});

//  Submit Page Front-end Validation

function checkForRequired() {

  // Divs

  var title = $("#post-title");

  var url = $("#post-URL");

  var text = $("#post-text");

  var button = $("#create_button");

  var image = $("#file-upload");

  // Toggle reuqired attribute

  if (url.val().length > 0 || image.val().length > 0) {
    text.prop('required', false);
    url.prop('required', false);
  } else if (text.val().length > 0 || image.val().length > 0) {
    url.prop('required', false);
  } else {
    text.prop('required',true);
    url.prop('required', false);
  }

  // Validity check

  var isValidTitle = title[0].checkValidity();

  var isValidURL = url[0].checkValidity();

  var isValidText = text[0].checkValidity();

  // Disable submit button if invalid inputs

  if (isValidTitle && (isValidURL || image.val().length>0)) {
    button.prop('disabled',false);
  } else if (isValidTitle && isValidText) {
    button.prop('disabled',false);
  } else {
    button.prop('disabled',true);
  }
}

//attach the above function to Input and Change
$('.submit-form-input').on('input', checkForRequired);

// Auto-suggest title given URL
function autoSuggestTitle() {

  var urlField = $("#post-URL");
  var titleField = $("#post-title");
  var isValidURL = urlField[0].checkValidity();

  if (isValidURL && urlField.val().length > 0 && titleField.val() === "") {

    var x = new XMLHttpRequest();
    x.withCredentials=true;
    x.onload = function() {
      if (x.status == 200) {
        title=JSON.parse(x.responseText)["title"];
        titleField.val(title);
        checkForRequired()
      }
    }
    x.open('get','/submit/title?url=' + urlField.val());
    x.send();

  };
}

$("#post-URL").on("change", autoSuggestTitle )

// Run AutoSuggestTitle function on load

if (window.location.pathname=='/submit') {
  window.onload = autoSuggestTitle();
}

// Exile Member
$('#exileUserButton').click(function(){

  boardname=$(this).data('board-name')

  var exileForm = document.getElementById("exile-form");

  var exileError = document.getElementById("toast-error-message");

  var usernameField = document.getElementById("exile-username");

  var isValidUsername = usernameField.checkValidity();

  username = usernameField.value;

  if (isValidUsername) {

    var xhr = new XMLHttpRequest();
    xhr.open("post", "/mod/exile/"+boardname);
    xhr.withCredentials=true;
    f=new FormData();
    f.append("username", username);
    f.append("formkey", formkey());
    xhr.onload=function(){
      if (xhr.status==204) {
        window.location.reload(true);
      }
      else {
        $('#toast-exile-error').toast('dispose');
        $('#toast-exile-error').toast('show');
        exileError.textContent = JSON.parse(xhr.response)["error"];
      }
    }
    xhr.send(f)
  }

})

// Approve user
function approve_from_guild(boardid) {

  var approvalForm = document.getElementById("approve-form");

  var approveError = document.getElementById("toast-error-message");

  var usernameField = document.getElementById("approve-username");

  var isValidUsername = usernameField.checkValidity();

  username = usernameField.value;

  if (isValidUsername) {

    var xhr = new XMLHttpRequest();
    xhr.open("post", "/mod/approve/"+boardid);
    xhr.withCredentials=true;
    f=new FormData();
    f.append("username", username);
    f.append("formkey", formkey());
    xhr.onload=function(){
      if (xhr.status==204) {
        window.location.reload(true);
      }
      else {
        $('#toast-approve-error').toast('dispose');
        $('#toast-approve-error').toast('show');
        approveError.textContent = JSON.parse(xhr.response)["error"];
      }
    }
    xhr.send(f)
  }

}

// Invite user to mod
function invite_mod_to_guild(boardid) {

  var inviteForm = document.getElementById("invite-form");

  var inviteError = document.getElementById("toast-error-message");

  var usernameField = document.getElementById("invite-username");

  var isValidUsername = usernameField.checkValidity();

  username = usernameField.value;

  if (isValidUsername) {

    var xhr = new XMLHttpRequest();
    xhr.open("post", "/mod/invite_mod/"+boardid);
    xhr.withCredentials=true;
    f=new FormData();
    f.append("username", username);
    f.append("formkey", formkey());
    xhr.onload=function(){
      if (xhr.status==204) {
        window.location.reload(true);
      }
      else {
        $('#toast-invite-error').toast('dispose');
        $('#toast-invite-error').toast('show');
        inviteError.textContent = JSON.parse(xhr.response)["error"];
      }
    }
    xhr.send(f)
  }

}

block_user=function() {

  var exileForm = document.getElementById("exile-form");

  var exileError = document.getElementById("toast-error-message");

  var usernameField = document.getElementById("exile-username");

  var isValidUsername = usernameField.checkValidity();

  username = usernameField.value;

  if (isValidUsername) {

    var xhr = new XMLHttpRequest();
    xhr.open("post", "/settings/block");
    xhr.withCredentials=true;
    f=new FormData();
    f.append("username", username);
    f.append("formkey", formkey());
    xhr.onload=function(){
      if (xhr.status<300) {
        window.location.reload(true);
      }
      else {
        $('#toast-exile-error').toast('dispose');
        $('#toast-exile-error').toast('show');
        exileError.textContent = JSON.parse(xhr.response)["error"];
      }
    }
    xhr.send(f)
  }

}

$(document).on('click', '.btn-save-new-comment', function(){

  var form = new FormData($('#'+$(this).data('form-id'))[0]);

  var btn=$(this);

  var xhr = new XMLHttpRequest();
  xhr.open("post", "/api/comment");
  xhr.withCredentials=true;
  xhr.onload=function(){
    if (xhr.status==200) {
      $('#comment-form-space-'+btn.data('parent-fullname')).html(JSON.parse(xhr.response)["html"]);
      $('#toast-success').toast('dispose');
      $('#toast-error').toast('dispose');
      $('#toast-success').toast('show')
      $('#toast-success .toast-text').text("Comment posted!");
    }
    else {
      btn.prop('disabled', false);
      btn.removeClass('disabled')
      var commentError = document.getElementById("comment-error-text");
      $('#toast-success').toast('dispose');
      $('#toast-error').toast('dispose');
      $('#toast-error').toast('show');
      $('#toast-error .toast-text').text(JSON.parse(xhr.response)["error"]);
    }
  }
  xhr.send(form)

  $(this).prop('disabled', true)
  $(this).addClass('disabled');

})


$(document).on('click', '.btn-herald-comment', function(){

  var cid = $(this).data('comment-id')

  var xhr = new XMLHttpRequest();
  xhr.open("post", "/mod/distinguish_comment/"+$(this).data('board-name')+'/'+$(this).data('comment-id'));

  var form = new FormData();

  form.append('formkey', formkey());

  xhr.withCredentials=true;
  xhr.onload=function(){
    if (xhr.status==200) {
      comment=document.getElementById('comment-'+cid+'-only');
      comment.innerHTML=JSON.parse(xhr.response)["html"];
    }
    else {
      var commentError = document.getElementById("comment-error-text");
      $('#toast-comment-success').toast('dispose');
      $('#toast-comment-error').toast('dispose');
      $('#toast-comment-error').toast('show');
      commentError.textContent = JSON.parse(xhr.response)["error"];
    }
  }
  xhr.send(form)

})

$(document).on('click', ".btn-pin-comment", function(){


  var xhr = new XMLHttpRequest();
  xhr.open("post", "/mod/comment_pin/"+$(this).data('board-name')+'/'+$(this).data('comment-id'));

  var form = new FormData();

  form.append('formkey', formkey());

  xhr.withCredentials=true;
  xhr.onload=function(){
    if (xhr.status==200) {
      comment=document.getElementById('comment-'+$(this).data('comment-id')+'-only');
      comment.innerHTML=JSON.parse(xhr.response)["html"];
    }
    else {
      var commentError = document.getElementById("comment-error-text");
      $('#toast-comment-success').toast('dispose');
      $('#toast-comment-error').toast('dispose');
      $('#toast-comment-error').toast('show');
      commentError.textContent = JSON.parse(xhr.response)["error"];
    }
  }
  xhr.send(form)

})



//part of submit page js

$('#post-URL').on('input', function(){
  x=document.getElementById('image-upload-block');
  url=document.getElementById('post-URL').value;
  if (url.length>=1){
    x.classList.add('d-none');
  }
  else {
    x.classList.remove('d-none');
  }
})



$(document).on('click', '.btn-save-edit-comment', function() {

  id=$(this).data('comment-id')

  var commentError = document.getElementById("comment-error-text");

  var form = new FormData($('#'+$(this).data('form-id'))[0]);

  form.append('formkey', formkey());
  form.append('body', document.getElementById('comment-edit-body-'+id).value);


  var xhr = new XMLHttpRequest();
  xhr.open("post", "/edit_comment/"+id);
  xhr.withCredentials=true;
  xhr.onload=function(){
    if (xhr.status==200) {
      commentForm=document.getElementById('comment-text-'+id);
      commentForm.innerHTML=JSON.parse(xhr.response)["html"];
      document.getElementById('cancel-edit-'+id).click()
      $('#toast-success').toast('dispose');
      $('#toast-error').toast('dispose');
      $('#toast-success').toast('show');
      $('#toast-success .toast-text').text("Comment edit saved")
    }
    else {
      $('#toast-success').toast('dispose');
      $('#toast-error').toast('dispose');
      $('#toast-error').toast('show');
      $('#toast-error .toast-text').text(JSON.parse(xhr.response)["error"]);
    }
  }
  xhr.send(form)

})

coin_quote = function() {

  var coins = document.getElementById('select-coins');
  var btn = document.getElementById('buy-coin-btn')
  var promo=document.getElementById('promo-code')
  var promotext=document.getElementById('promo-text')

  coin_count = coins.selectedOptions[0].value

  var xhr = new XMLHttpRequest();
  xhr.open('get', '/shop/get_price?coins='+coin_count+'&promo='+promo.value)

  xhr.onload=function(){
    var s = 'Buy '+ coin_count + ' Coin';

    if (coin_count > 1){s = s+'s'};

    s=s+': $'+JSON.parse(xhr.response)["price"];

    btn.value=s;

    promotext.innerText=JSON.parse(xhr.response)["promo"];
  }
  xhr.send()
}
$('input#promo-code').on('input', coin_quote)
$('select#select-coins').on('change', coin_quote)


$(".btn-tip-modal-trigger").click(function() {
  console.log('opened modal, tipModal2 function triggered')

  $('#tip-recipient-pfp').attr('src',$(this).data('target-author-profile-url'));
  $("#tip-content-type").text($(this).data('target-type'));

  $("#tip-recipient-username").text($(this).data('target-author'));
  $("#sendTipButton").data('tip-url', $(this).data('tip-url'))
}
)

$("#sendTipButton").click(function() {
  post_toast($(this).data('tip-url'),
    callback = function() {
      window.location.reload()
    }
  )
}
);

var togglecat = function(sort, reload=false, delay=1000, page="/all") {
  var cbs = document.getElementsByClassName('cat-check');
  var l = []
  for (var i=0; i< cbs.length; i++) {
    l.push(cbs[i].checked)
  }
  setTimeout(function(){triggercat(sort, l, reload, page)}, delay)
  return l;
}

var triggercat=function(sort, cats, reload, page) {

  var cbs = document.getElementsByClassName('cat-check');
  var l = []
  for (var i=0; i< cbs.length; i++) {
    l.push(cbs[i].checked)
  }



  for (var i=0; i<l.length; i++){
    if (cats[i] != l[i]){
      console.log("triggerfail");
      return false;
    }
  }

  console.log("triggercat")

  var catlist=[]
  for (var i=0; i< cbs.length; i++) {
    if(cbs[i].checked){
      catlist.push(cbs[i].dataset.cat);
    }
  }

  var groups = document.getElementsByClassName('cat-group');
  var grouplist=[];
  for (i=0; i<groups.length; i++){
    if(groups[i].checked){
      grouplist.push(groups[i].dataset.group);
    }
  }

  var url='/inpage/all?sort='+ sort +'&cats=' + catlist.join(',') + '&groups=' + grouplist.join(',');
  

  xhr = new XMLHttpRequest();
  xhr.open('get', url);
  xhr.withCredentials=true;

  xhr.onload=function(){
    if (reload){
      document.location.href=page
    }
    else {
      var l = document.getElementById('posts');
      l.innerHTML=xhr.response;
      register_votes();
    }
  }
  xhr.send()
}


$('.btn-edit-mod-perms').click(function(){

  $('#permedit-user').text($(this).data('username'))
  $('#edit-perm-username').val($(this).data('username'))

  cbs=$('.perm-box')

  btn=$(this)

  cbs.prop('checked', function(index, currentvalue){
    return btn.data('permlist').includes($(this).data('perm')) || btn.data('permlist').includes('full')
  })
  
})

var permfull=function() {

  cbs = document.getElementsByClassName('perm-box')

  full = cbs[0]

  if (full.checked) {
    for (i=1; i< cbs.length; i++) {
      cbs[i].checked = true;
    }
  }
}
var permother=function() {

  cbs = document.getElementsByClassName('perm-box')

  full = cbs[0]

  for (i=1; i< cbs.length; i++) {
    if(cbs[i].checked == false) {
      full.checked=false;
    }
  }
}

var cattoggle=function(id){

  var check = document.getElementById('group-'+id);

  check.click()

  var x=document.getElementsByClassName('group-'+id);
  for (i=0;i<x.length;i++) {
    x[i].checked=check.checked
  }

  card=document.getElementById('cat-card-'+id)
  card.classList.toggle('selected');
}

$('#show-all-cats-btn').click(function(){
  $('.cat-check').prop('checked',true);
  $('.cat-group').prop('checked',true);
  togglecat('hot', reload=true, delay=0, page='/')
})


//mobile prompt
if (("standalone" in window.navigator) &&       // Check if "standalone" property exists
    window.navigator.standalone){               // Test if using standalone navigator

    // Web page is loaded via app mode (full-screen mode)
    // (window.navigator.standalone is TRUE if user accesses website via App Mode)

} else {
  if (window.innerWidth <= 737){
    try {
      $('#mobile-prompt').tooltip('show')
      $('.tooltip').on(
        'click',
        function(event){
          $('#mobile-prompt').tooltip('hide')
          var xhr = new XMLHttpRequest();
          xhr.withCredentials=true;
          xhr.open("POST", '/dismiss_mobile_tip', true);
          xhr.send();
        }
      )
    } catch (error) {
      console.error(error);
    }
  }
}

$('.mention-user').click(function (event) {

  if (event.which != 1) {
    return
  }

  event.preventDefault();

  window.location.href='/@' + $(this).data('original-name');

});


$(document).on('click', '.expandable-image', function(event) {

  if (event.which != 1) {
    return
  }
  event.preventDefault();

  var url= $(this).data('url');

  $('#desktop-expanded-image').attr('src', url)

  $('#desktop-expanded-image-link').attr('href', url);
  $('#desktop-expanded-image-wrap-link').attr('href', url)


  if (url.includes('giphy.com')) {
    $('#modal-image-attribution').removeClass('d-none');
  }
  else {
    $('#modal-image-attribution').addClass('d-none');
  }
})


$('.text-expand').click(function(event){
  if (event.which != 1) {
    return
  };
  id=$(this).data('id');


  $('#post-text-'+id).toggleClass('d-none');
  $('.text-expand-icon-'+id).toggleClass('fa-expand-alt');
  $('.text-expand-icon-'+id).toggleClass('fa-compress-alt');
  
})



function mod_post(url, type, id) {
  var xhr = new XMLHttpRequest();
  xhr.open("POST", url, true);
  var form = new FormData()
  form.append("formkey", formkey());
  item=document.getElementById(type);
  button=document.getElementById(id);
  if (item.type=="checkbox") {
    form.append(item.name, item.checked)
    if (item.checked) {
      form.append(item.name, true);
    } else {
      form.append(item.name, false);
    }
  }
  else {
    form.append(item.name, item.value);
  }
  xhr.withCredentials=true;
  xhr.onprogress=function(){
    button.classList.add("btn-primary");
    button.disabled = true;
    button.innerHTML = '<span class="spinner-border spinner-border-sm mr-2" role="status" aria-hidden="true"></span>Saving';
  }
  xhr.onload=function(){
    if (xhr.status >= 400)
    {
      button.classList.add("btn-primary");
      button.disabled=false;
      button.innerHTML="Save"
      data=JSON.parse(xhr.response);
      $('#toast-post-error').toast('dispose');
      $('#toast-post-error').toast('show');
      document.getElementById('toast-post-error-text').innerText = data["error"];
      return;
    }
    button.classList.remove("btn-danger");
    button.classList.add("btn-success");
    button.innerHTML = `<i class="fas fa-check mr-2"></i>Saved`;
  }
  xhr.send(form);
}


//post form toast utility function
function postformtoast(x, callback=function(data){}){

  var form_id
  if (x.prop('tagName')=='FORM') {
    form_id=x.prop('id')
  }
  else {
    form_id=x.data('form')
  }

  var xhr = new XMLHttpRequest();
  var url=$('#'+form_id).prop('action');
  var method=$('#'+form_id).prop('method')

  xhr.open("POST", url, true);
  var form = new FormData($('#'+form_id)[0]);
  xhr.withCredentials=true;
  xhr.onerror=function() { 
      $('#toast-error .toast-text').text("Something went wrong. Please try again later.");
      $('#toast-error').toast('show')
  };
  xhr.onload = function() {
    data=JSON.parse(xhr.response);
    if (xhr.status >= 200 && xhr.status < 300) {
      if (data['message']!=undefined) {
        $('#toast-success .toast-text').text(data['message']);
        $('#toast-success').toast('show');
      }
      callback(xhr);
    } 
    else if (xhr.status >= 300 && xhr.status < 400 ) {
      window.location.href=data['redirect']
    } 
    else if (xhr.status >=400 && xhr.status < 500) {
      $('#toast-error .toast-text').text(data['error']);
      $('#toast-error').toast('show')
    } 
    else {
      $('#toast-error .toast-text').text("Something went wrong. Please try again later.");
      $('#toast-error').toast('show')
    }
  };

  xhr.send(form);
}

$('.toast-form-submit').click(function(){postformtoast($(this))});
$('.toast-form-change-submit').change(function(){postformtoast($(this))});


//Transferring onclick garbage into this file

$(".btn-guild-block").click(function(){
  post_toast('/settings/block_guild?board='+$(this).data("board-name"))
})
$(".btn-guild-unblock").click(function(){
  post_toast('/settings/unblock_guild?board='+$(this).data("board-name"))
})

$(".btn-guild-sub").click(function(){
  id=$(this).data('thing-id');
  post('/api/subscribe/'+$(this).data('board-name'), callback=function(){toggleSub(id)})
})
$(".btn-guild-unsub").click(function(){
  id=$(this).data('thing-id');
  post('/api/unsubscribe/'+$(this).data('board-name'), callback=function(){toggleSub(id)})
})

$(document).on('click', ".post-url-reload", function(){
  post($(this).data('post-url'), callback=function(){window.location.reload()})
})

$(document).on('click', ".post-url", function(){
  post($(this).data('post-url'))
})

$(document).on('click', ".post-toast-url-reload", function(){
  post_toast($(this).data('post-url'), callback=function(){window.location.reload()})
})

$(document).on('click', ".post-toast-url", function(){
  post_toast($(this).data('post-url'))
})

$(".go-to-login").click(function(){window.location.href="/login?redirect="+window.location.pathname})

$(document). on('click', ".btn-cancel-comment", function(){
  $('.reply-to-'+$(this).data('comment-id')).addClass('d-none')
})

$(document).on('click', '.btn-reply-comment', function(){
  $('#reply-to-'+$(this).data('comment-id')).removeClass('d-none')
})

$('.btn-file-input').change(function(){
  $('#filename-show-reply-'+$(this).data('btn-id')).text(
    $('#file-upload-reply-'+$(this).data('parent-fullname'))[0].files[0].name
    );
})

$('.btn-block-user').click(function() {
  name=$(this).data('target-user');
  id=$(this).data('post-id');
  post_toast(
    '/settings/block?username='+name, 
    callback=function(){
    $('#block-user-'+id).toggleClass('d-none');
    $('#unblock-user-'+id).toggleClass('d-none');
  }
  )
})

$('.btn-unblock-user').click(function() {
  name=$(this).data('target-user');
  id=$(this).data('post-id');
  post_toast(
    '/settings/unblock?username='+name, 
    callback=function(){
    $('#block-user-'+id).toggleClass('d-none');
    $('#unblock-user-'+id).toggleClass('d-none');
  }
  )
})

$('.btn-demod-user').click(function(){
  $('#demod-user').toggleClass('d-none');
})

$('.btn-ban-user').click(function(){
  $('#btn-confirm-ban-user').toggleClass('d-none');
})

$('.btn-toggle-follow').click(function(){
  id=$(this).data('thing-id');
  post(
    $(this).data("post-url"),
    callback=function(){toggleSub(id)}
    )
})

$('.btn-cat-toggle').click(function(){
  cattoggle($(this).data('cat-id'))
})

$('#btn-all-cats').click(function(){
  togglecat('hot', reload=true, delay=0, page='/')
})

$('#report-type-dropdown').change(function(){
  $('#reportPostButton').prop('disabled', false)
})

$('#submit-image-div').on('dragover', function(event){
  event.preventDefault();
});
$('#submit-image-div').on('drop', function(event){
  event.preventDefault();
  let input=$('#file-upload');
  input[0].files=event.dataTransfer.files;
  input.change();
});

$('#title-selector').change(function(){
  post_toast('/settings/profile?title_id='+$(this).val())
})
$('#defaultsorting').change(function(){
  post_toast('/settings/profile?defaultsorting='+$(this).val())
})
$('#defaulttime').change(function(){
  post_toast('/settings/profile?defaulttime='+$(this).val())
})
$("#privateswitch").change(function(){
  post_toast('/settings/profile?private='+$(this).prop('checked'))
})
$("#nofollowswitch").change(function(){
  post_toast('/settings/profile?nofollow='+$(this).prop('checked'))
})

$('.onchange-form-submit').change(function(){form.submit()})

$('#2faToggle').change(function(){
  $('#2faModal').modal('toggle')
})

$('#over18').change(function(){
  post_toast('/settings/profile?over18='+$(this).prop('checked'));
  $('#filter-nsfw-option').toggleClass('d-none')
})

$('#filter-nsfw').change(function(){
  post_toast('/settings/profile?filter_nsfw='+$(this).prop('checked'))
})
$('#hidensfl').change(function(){
  post_toast('/settings/profile?show_nsfl='+$(this).prop('checked'))
})
$('#hideoffensive').change(function(){
  post_toast('/settings/profile?hide_offensive='+$(this).prop('checked'))
})
$('#hidebot').change(function(){
  post_toast('/settings/profile?hide_bot='+$(this).prop('checked'))
})

$('.btn-hide-guild').click(function(){
  id=$(this).data("post-id")
  post_toast(
    '/settings/block_guild?board='+$(this).data('board-name'), 
    callback=function(){
      $('#hide-guild-'+id).toggleClass('d-none');
      $('#unhide-guild-'+id).toggleClass('d-none');
    })
})
$('.btn-unhide-guild').click(function(){
  id=$(this).data("post-id")
  post_toast(
    '/settings/unblock_guild?board='+$(this).data('board-name'), 
    callback=function(){
      $('#hide-guild-'+id).toggleClass('d-none');
      $('#unhide-guild-'+id).toggleClass('d-none');
    })
})

$('.gm-approve-post').click(function(){
  name=$(this).data('board-name')
  pid =$(this).data('post-id')
  post(
    '/mod/accept/'+name+'/'+pid, 
    callback=function(){
      if (window.location.pathname.endsWith('/mod/queue')){
        deleteElement('post-'+pid)
      }
    }
    )
})

$("iframe.internal-embed").on('load', function() {
    $(this).attr('height', $(this)[0].contentWindow.document.body.offsetHeight + 'px');
});

$(window).resize(function(){
  var x=$("iframe.internal-embed");
  if (x[0] != undefined){
    x.attr('height',  x[0].contentWindow.document.body.offsetHeight+'px');
  }
})


$('.copy-outside-embed').click(function(){
  var xhr = new XMLHttpRequest();
  xhr.withCredentials=true;
  xhr.open(
    "GET", 
    '/embed_thing/'+$(this).data('thing-fullname'), 
    true
    );
  xhr.onload=function(){
    if (xhr.status==200){
      navigator.clipboard.writeText(JSON.parse(xhr.response)['html']);
      $('#toast-success').toast('show');
      $('#toast-success .toast-text').text('Embed HTML copied to clipboard.');
    } else {
      $('#toast-error').toast('show');
      $('#toast-error .toast-text').text(JSON.parse(xhr.response)["error"]);
    }

    }
  xhr.send();
  }
)

$('#btn-toggle-sidebar-collapse').click(function(){
  post(
    '/settings/toggle_collapse',
    callback=function(){
      $('#sidebar-left').toggleClass('sidebar-collapsed')
    })
})

$('#guild-ban-reason').on('input', function(){
  $('#guild-ban-submit').prop('disabled',false);
})
$('domain-ban-selector').change(function(){
  $('#domain-ban-submit').prop('disabled', false)
})


$('.app-secret-hider').click(function(){
  $(this).addClass('d-none');
  $('#edit-'+$(this).data('app-id')+'-client-secret').removeClass('d-none');
})

$('.btn-reroll-app-secret').click(function(){
  var app_id = $(this).data('app-id');
  post_toast(
    '/oauth/reroll/'+app_id,
    callback=function(xhr){
      $('#edit-'+app_id+'-client-id').val(JSON.parse(xhr.response)['id']);
      $('#edit-'+app_id+'-client-secret').val(JSON.parse(xhr.response)['secret']);
    }
    )
})