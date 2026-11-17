(function () {
 'use strict';
 var tiles=document.querySelectorAll('.tile'), rows=[[0,1],[2,3,4],[5,6,7]], selected=0, bridges=[], busy=false;
 var status=document.getElementById('status');
 function focus(i){selected=Math.max(0,Math.min(tiles.length-1,i));for(var j=0;j<tiles.length;j++){tiles[j].className=tiles[j].className.replace(/ selected/g,'');tiles[j].setAttribute('tabindex',j===selected?'0':'-1');}tiles[selected].className+=' selected';tiles[selected].focus();}
 function open(i){if(busy)return;busy=true;status.textContent='Opening...';var id=tiles[i].getAttribute('data-id');
  if(typeof PalmServiceBridge==='undefined'){status.textContent='TV launch service unavailable';busy=false;return;}
  var b=new PalmServiceBridge();bridges.push(b);b.onservicecallback=function(raw){busy=false;var r;try{r=JSON.parse(raw);}catch(e){r={returnValue:false};}status.textContent=r.returnValue?'':('Could not open: '+(r.errorText||'please try again'));var n=bridges.indexOf(b);if(n!==-1)bridges.splice(n,1);};
  b.call('luna://com.webos.applicationManager/launch',JSON.stringify({id:id}));setTimeout(function(){busy=false;},3000);
 }
 function move(code){var r=0,c=0;for(var a=0;a<rows.length;a++){var n=rows[a].indexOf(selected);if(n!==-1){r=a;c=n;break;}}
  if(code===37)c=Math.max(0,c-1);if(code===39)c=Math.min(rows[r].length-1,c+1);if(code===38)r=Math.max(0,r-1);if(code===40)r=Math.min(rows.length-1,r+1);focus(rows[r][Math.min(c,rows[r].length-1)]);
 }
 for(var i=0;i<tiles.length;i++){(function(n){tiles[n].onclick=function(){focus(n);open(n);};tiles[n].onmouseover=function(){focus(n);};})(i);}
 document.addEventListener('keydown',function(e){var k=e.keyCode;if(k>=37&&k<=40){move(k);e.preventDefault();}else if(k===13){open(selected);e.preventDefault();}else if(k===461||k===27){window.close();e.preventDefault();}});
 var backgroundFile='';
 function background(){
  var photo=homeBackgroundForDate(new Date());
  if(photo.file===backgroundFile)return;
  var img=new Image();
  img.onload=function(){document.body.style.backgroundImage='linear-gradient(rgba(8,16,24,0.22),rgba(8,16,24,0.52)),url("'+photo.file+'")';document.getElementById('photo-credit').textContent=photo.title+' / USFWS';backgroundFile=photo.file;};
  img.src=photo.file;
 }
 function clock(){background();var d=new Date(),h=d.getHours(),m=d.getMinutes();document.getElementById('clock').textContent=(h%12||12)+':'+(m<10?'0':'')+m+' '+(h<12?'AM':'PM');}
 document.addEventListener('webOSRelaunch',function(){busy=false;status.textContent='';if(window.PalmSystem&&PalmSystem.activate)PalmSystem.activate();clock();focus(selected);});
 document.addEventListener('visibilitychange',function(){if(!document.hidden){busy=false;status.textContent='';clock();}});
 clock();setInterval(clock,60000);focus(0);
}());
