function removePost(post_id) {
url="/api/ban_post/"+post_id

callback=function(){
document.getElementById("post-"+post_id).classList.add("banned");

var button=document.getElementById("moderate-post-"+post_id);
button.onclick=function(){approvePost(post_id)};
button.classList.remove("removeDropdownItem");
button.classList.add("approveDropdownItem");
button.innerHTML='<i class="fas fa-clipboard-check"></i>Approve'
}
post(url, callback, "Unable to remove post at this time. Please try again later.")
}

function approvePost(post_id) {
url="/api/unban_post/"+post_id

callback=function(){
document.getElementById("post-"+post_id).classList.remove("banned");

var button=document.getElementById("moderate-post-"+post_id);
button.onclick=function(){removePost(post_id)};
button.classList.remove("approveDropdownItem");
button.classList.add("removeDropdownItem");
button.innerHTML='<i class="fas fa-trash-alt"></i>Remove'
}

post(url, callback, "Unable to approve post at this time. Please try again later.")
}