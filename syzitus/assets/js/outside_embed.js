//no jquery allowed here.... sad!

var divs = document.getElementsByClassName('syzitus-embed');
for (let i=0; i<divs.length; i++){
  div=divs[i];
  div.addEventListener('load', function(){
    div.height = divcontentWindow.document.body.offsetHeight + 'px';
  })
}

window.addEventListener('resize', function(){
  var divs = document.getElementsByClassName('syzitus-embed');
  for (let i=0; i<divs.length; i++){
    div=divs[i];
    div.height = divcontentWindow.document.body.offsetHeight + 'px';
    }
  }
);