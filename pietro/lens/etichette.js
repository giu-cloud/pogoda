function etichette(v,px,W,H,dpr){const x0=v[0],y0=v[1],sw=v[2],presi=[];
 cx.textBaseline='middle';
 const libero=r=>presi.every(q=>r[2]<q[0]||r[0]>q[2]||r[3]<q[1]||r[1]>q[3]);
 const minuti=sw<nx*0.35;
 for(const l of D.luoghi){if(l[3]>=4&&!minuti)continue;const X=(l[1]*nx-x0)*px,Y=(l[2]*ny-y0)*px;if(X<6||Y<10||X>W-6||Y>H-10)continue;
  const picco=l[4]==='p',fs=(l[3]<=1?12.5:11.5)*dpr;cx.font=(l[3]<=2?'600 ':'500 ')+fs+'px system-ui,sans-serif';
  // la scritta prova a destra, a sinistra, sopra e sotto il punto; se non trova posto libero non si scrive
  const tw=cx.measureText(l[0]).width,g=7*dpr,v1=fs*1.15,pos=[[g,0],[-tw-g,0],[-tw/2,-v1],[-tw/2,v1],[-g,-v1],[-tw+g,-v1],[-g,v1],[-tw+g,v1]];let dx=null,dy=0,r=null;
  for(const p of pos){let tx=X+p[0];const ty=Y+p[1];
   if(p[1]!==0)tx=Math.max(2*dpr,Math.min(W-tw-2*dpr,tx));   // sopra e sotto la scritta puo' scorrere per restare dentro la carta
   if(tx<2*dpr||tx+tw>W-2*dpr||ty<fs*0.8||ty>H-fs*0.8)continue;
   const rr=[Math.min(X,tx)-3*dpr,Math.min(Y,ty)-fs*0.75,Math.max(X,tx+tw)+3*dpr,Math.max(Y,ty)+fs*0.75];if(libero(rr)){dx=tx-X;dy=p[1];r=rr;break}}
  if(dx===null)continue;presi.push(r);
  if(picco){cx.fillStyle='#5a3d1e';cx.beginPath();cx.moveTo(X,Y-5*dpr);cx.lineTo(X+4.5*dpr,Y+3*dpr);cx.lineTo(X-4.5*dpr,Y+3*dpr);cx.closePath();cx.fill()}
  else{cx.fillStyle='#c0392b';cx.beginPath();cx.arc(X,Y,2.6*dpr,0,7);cx.fill()}
  cx.lineWidth=3.2*dpr;cx.strokeStyle='rgba(255,253,245,.92)';cx.strokeText(l[0],X+dx,Y+dy);cx.fillStyle=picco?'#4a3420':'#14140f';cx.fillText(l[0],X+dx,Y+dy)}}
