//no jquery allowed here.... sad!

var frames = document.getElementsByClassName('syzitus-embed');
for (let i=0; i<frames.length; i++){
  frame=frames[i];
  frame.addEventListener('message' function(event){
    var data= event.data;
    if (data.height) {
      frame.height=data.height;
    }
  })
}