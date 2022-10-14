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
