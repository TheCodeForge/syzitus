

function vote(post_id, direction) {
url="/api/vote/post/"+post_id+"/"+direction;

callback=function(){
thing = document.getElementById("post-"+post_id);
uparrow1=document.getElementById("post-"+post_id+"-up");
downarrow1=document.getElementById("post-"+post_id+"-down");
scoreup1=document.getElementById("post-"+post_id+"-score-up");
scorenone1=document.getElementById("post-"+post_id+"-score-none");
scoredown1=document.getElementById("post-"+post_id+"-score-down");

thing2=document.getElementById("voting-"+post_id+"-mobile")
uparrow2=document.getElementById("arrow-"+post_id+"-mobile-up");
downarrow2=document.getElementById("arrow-"+post_id+"-mobile-down");
scoreup2=document.getElementById("post-"+post_id+"-score-mobile-up");
scorenone2=document.getElementById("post-"+post_id+"-score-mobile-none");
scoredown2=document.getElementById("post-"+post_id+"-score-mobile-down");

if (direction=="1") {
thing.classList.add("upvoted");
thing.classList.remove("downvoted");
uparrow1.onclick=function(){vote(post_id, 0)};
downarrow1.onclick=function(){vote(post_id, -1)};
scoreup1.classList.remove("d-none");
scorenone1.classList.add("d-none");
scoredown1.classList.add("d-none");

thing2.classList.add("upvoted");
thing2.classList.remove("downvoted");
uparrow2.onclick=function(){vote(post_id, 0)};
downarrow2.onclick=function(){vote(post_id, -1)};
scoreup2.classList.remove("d-none");
scorenone2.classList.add("d-none");
scoredown2.classList.add("d-none");
}
else if (direction=="-1"){
thing.classList.remove("upvoted");
thing.classList.add("downvoted");
uparrow1.onclick=function(){vote(post_id, 1)};
downarrow1.onclick=function(){vote(post_id, 0)};
scoreup1.classList.add("d-none");
scorenone1.classList.add("d-none");
scoredown1.classList.remove("d-none");

thing2.classList.remove("upvoted");
thing2.classList.add("downvoted");
uparrow2.onclick=function(){vote(post_id, 1)};
downarrow2.onclick=function(){vote(post_id, 0)};
scoreup2.classList.add("d-none");
scorenone2.classList.add("d-none");
scoredown2.classList.remove("d-none");

}
else if (direction=="0"){
thing.classList.remove("upvoted");
thing.classList.remove("downvoted");
uparrow1.onclick=function(){vote(post_id, 1)};
downarrow1.onclick=function(){vote(post_id, -1)};
scoreup1.classList.add("d-none");
scorenone1.classList.remove("d-none");
scoredown1.classList.add("d-none");

thing2.classList.remove("upvoted");
thing2.classList.remove("downvoted");
uparrow2.onclick=function(){vote(post_id, 1)};
downarrow2.onclick=function(){vote(post_id, -1)};
scoreup2.classList.add("d-none");
scorenone2.classList.remove("d-none");
scoredown2.classList.add("d-none");

}
}

post(url, callback, "Unable to vote at this time. Please try again later.");
}


function vote_comment(comment_id, direction) {
url="/api/vote/comment/"+ comment_id +"/"+direction;

callback=function(){
thing = document.getElementById("comment-"+ comment_id+"-actions");
uparrow1=document.getElementById("comment-"+ comment_id +"-up");
downarrow1=document.getElementById("comment-"+ comment_id +"-down");
scoreup1=document.getElementById("comment-"+ comment_id +"-score-up");
scorenone1=document.getElementById("comment-"+ comment_id +"-score-none");
scoredown1=document.getElementById("comment-"+ comment_id +"-score-down");

if (direction=="1") {
thing.classList.add("upvoted");
thing.classList.remove("downvoted");
uparrow1.onclick=function(){vote_comment(comment_id, 0)};
downarrow1.onclick=function(){vote_comment(comment_id, -1)};
scoreup1.classList.remove("d-none");
scorenone1.classList.add("d-none");
scoredown1.classList.add("d-none");
}
else if (direction=="-1"){
thing.classList.remove("upvoted");
thing.classList.add("downvoted");
uparrow1.onclick=function(){vote_comment(comment_id, 1)};
downarrow1.onclick=function(){vote_comment(comment_id, 0)};
scoreup1.classList.add("d-none");
scorenone1.classList.add("d-none");
scoredown1.classList.remove("d-none");
}
else if (direction=="0"){
thing.classList.remove("upvoted");
thing.classList.remove("downvoted");
uparrow1.onclick=function(){vote_comment(comment_id, 1)};
downarrow1.onclick=function(){vote_comment(comment_id, -1)};
scoreup1.classList.add("d-none");
scorenone1.classList.remove("d-none");
scoredown1.classList.add("d-none");
}
}

post(url, callback, "Unable to vote at this time. Please try again later.");
}