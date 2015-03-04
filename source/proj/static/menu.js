
//blatantly ripped and minorly modified from http://www.tjkdesign.com/articles/new_drop_down/TJK_dropDown.js

function swap(){this.className="msieFix"}
function swapBack(){this.className="trigger"}
function swapfocus() {this.parentNode.parentNode.parentNode.className="msieFix"}
function swapblur() {this.parentNode.parentNode.parentNode.className="trigger"}
function menu(){// v1.0 Copyright (c) 2006 TJKDesign - Thierry Koblentz
	if (document.getElementById){	
	var LI = document.getElementsByTagName("li");
	var zLI= LI.length;
		for(var k=0;k<zLI;k++){
			if(LI[k].id){
//			LI[k].firstChild.href="#";
			LI[k].className="trigger";
			}
			if(LI[k].parentNode.parentNode.className=="trigger"){LI[k].firstChild.onfocus=swapfocus;LI[k].firstChild.onblur = swapblur}
			if(LI[k].className=="trigger"){LI[k].onmouseover=swap;LI[k].onmouseout=swapBack}
		}
	}
}
window.onload=function(){menu();}