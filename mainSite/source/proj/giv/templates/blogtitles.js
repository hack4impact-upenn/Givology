




function splitblogtitles(){
    var i;
    var titles = [];
    var monthl = [];
    var monthd = {};
    $('.blogtitle').each(function(ix,te){
        titles.push(te);
        //console.log($(te).children());
        var m = $(te).children('.titlemonth').val();
        var t = {'e':te,'m':m};
        if(monthd[m]){
            monthl[monthl.length-1].push(t);
        }else{
            monthd[m] = 1;
            monthl.push([t]);
        }
    });
    
    for(i in monthl){
        monthl[i] = (function(){
            var l = monthl[i];
            var ms = l[0].m
            var id = 'blogtitlemonth'+i;
            var html = '<div id="'+id+'" class="blogtitlesmonth"><a id="' + id + 'a" href="#">' + ms + ' ('+l.length+')</a></div>';
            $('#blogtitles').append(html);
            var e = $('#'+id);
            //console.log(e);
            var a = $('#'+id+'a');
            for(var j in l){
                e.append(l[j].e);
            }
            a.click(function(){
                //console.log($('#'+id).children('.blogtitle'));
                e.children('.blogtitle').toggleClass('hidden');
                return false;
            });
            return {'e':e,'l':l};
        })();
    }

}

$(splitblogtitles)


