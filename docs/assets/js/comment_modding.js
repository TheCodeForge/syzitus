function removeComment(post_id) {
url="/api/ban_comment/"+post_id

callback=function(){
document.getElementById("comment-"+post_id+"-only").classList.add("banned");

button=document.getElementById("moderate-"+post_id);
button.onclick=function(){approveComment(post_id)};
button.innerHTML="approve"
}
post(url, callback, "Unable to remove post at this time. Please try again later.")
}

function approveComment(post_id) {
url="/api/unban_comment/"+post_id

callback=function(){
document.getElementById("comment-"+post_id+"-only").classList.remove("banned");

button=document.getElementById("moderate-"+post_id);
button.onclick=function(){removeComment(post_id)};
button.innerHTML="remove"
}

post(url, callback, "Unable to approve post at this time. Please try again later.")
}

function distinguishModComment(post_id) {
url="/api/distinguish_comment/"+post_id

callback=function(){
document.getElementById("comment-"+post_id+"-only").classList.add("distinguish-mod");

button=document.getElementById("distinguish-"+post_id);
button.onclick=function(){undistinguishModComment(post_id)};
button.innerHTML="undistinguish"
}

post(url, callback, "Unable to distinguish comment at this time. Please try again later.")
}

function undistinguishModComment(post_id) {
url="/api/undistinguish_comment/"+post_id

callback=function(){
document.getElementById("comment-"+post_id+"-only").classList.remove("distinguish-mod");

button=document.getElementById("distinguish-"+post_id);
button.onclick=function(){distinguishModComment(post_id)};
button.innerHTML="distinguish"
}
post(url, callback, "Unable to undistinguish comment at this time. Please try again later.")
}

function distinguishAdminComment(post_id) {
url="/api/distinguish_comment/"+post_id

callback=function(){
document.getElementById("comment-"+post_id+"-only").classList.add("distinguish-admin");

button=document.getElementById("distinguish-"+post_id);
button.onclick=function(){undistinguishAdminComment(post_id)};
button.innerHTML="undistinguish"
}
post(url, callback, "Unable to distinguish comment at this time. Please try again later.")
}

function undistinguishAdminComment(post_id) {
url="/api/undistinguish_comment/"+post_id

callback=function(){
document.getElementById("comment-"+post_id+"-only").classList.remove("distinguish-admin");

button=document.getElementById("distinguish-"+post_id);
button.onclick=function(){distinguishAdminComment(post_id)};
button.innerHTML="distinguish"
}
post(url, callback, "Unable to undistinguish post at this time. Please try again later.")
}