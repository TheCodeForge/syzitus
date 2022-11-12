//no jquery allowed here.... sad!
window.addEventListener('message', function(event){
  var data = event.data;
  if (data.height && data.frame) {
    document.getElementById(data.frame).height=data.height;
  }
})