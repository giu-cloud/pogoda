(function(){
const MM=__DATI__,TXT=__TXT__;
let lang='pl';
const box=document.getElementById('mappa');
function lingua(l){lang=l;document.body.dataset.l=l;
 document.querySelectorAll('.lsw button').forEach(b=>b.setAttribute('aria-pressed',b.dataset.l===l));
 if(box){const d=document.querySelector('.lng[data-l="'+l+'"] [data-mappa]');if(d)d.appendChild(box);testi()}}
document.querySelectorAll('.lsw button').forEach(b=>b.addEventListener('click',()=>lingua(b.dataset.l)));
if(!box||!MM){lingua(lang);return}
const Q=id=>document.getElementById(id),G=13;
const pul=a=>a.map(x=>x==null?0:x);
// strati: 0 terreno, 1 nube, 2 pioggia, 3 neve, 4 neve accumulata, 5 vento, 6 temperatura (gruppo principale)
// 7 raffiche, 8 percepita, 9 umidita', 10 visibilita', 11 nuvolosita', 12 sole, 13 pressione, 14 temporali, 15 1500 m
const PRINC=[0,1,2,3,4,5,6],ALTRI=[7,8,9,10,11,12,13,14,15];
let C,N,H,dem,I,WX,AT,scalaK=null,im,ora=0,strato=0,sel=null,giro=null,ACC=null,flusso=null,altri=false;
const cv=Q('ov'),cx=cv.getContext('2d'),lc=Q('lc'),lx=lc.getContext('2d'),pc=Q('pc'),px=pc.getContext('2d');
const VENTO={},UV={};
function carica(k){const m=MM.m[k];scalaK=k;
 if(!m.pronto){m.c.z=pul(m.c.z);['T','Td','pr','low','nuv','ws','wd','wg'].forEach(q=>{m.c[q]=m.c[q].map(pul)});
  ['p','cape','sw','vis','T850'].forEach(q=>{m.c[q]=(m.c[q]&&m.c[q].length&&m.c[q][0].some(x=>x!=null))?m.c[q].map(pul):null});
  const n=m.n,bin=atob(m.dem),d=new Uint16Array(n*n);for(let i=0;i<n*n;i++)d[i]=bin.charCodeAt(2*i)|(bin.charCodeAt(2*i+1)<<8);
  // interpolazione bicubica (Catmull-Rom) della griglia del modello: campi morbidi, senza quadretti
  const gi=new Uint16Array(16*n*n),gw=new Float32Array(16*n*n);
  const cr=t=>{const t2=t*t,t3=t2*t;return[(-t3+2*t2-t)/2,(3*t3-5*t2+2)/2,(-3*t3+4*t2+t)/2,(t3-t2)/2]};
  const cl=v=>Math.max(0,Math.min(G-1,v));
  for(let r=0;r<n;r++)for(let c=0;c<n;c++){const gx=(c+.5)/n*(G-1),gy=(r+.5)/n*(G-1),x0=Math.min(G-2,Math.floor(gx)),y0=Math.min(G-2,Math.floor(gy)),q=16*(r*n+c);
   const ax=cr(gx-x0),ay=cr(gy-y0);let j=0;
   for(let a=0;a<4;a++)for(let b=0;b<4;b++){gi[q+j]=cl(y0-1+a)*G+cl(x0-1+b);gw[q+j]=ay[a]*ax[b];j++}}
  // atlante del vento: risposte del rilievo a un vento unitario, riportate sulla griglia della carta
  let at=null;
  if(m.v){const nv=m.v.n,bv=atob(m.v.f),nf=bv.length/2/(nv*nv),raw=new Float32Array(nf*nv*nv);
   for(let i=0;i<raw.length;i++){let x=bv.charCodeAt(2*i)|(bv.charCodeAt(2*i+1)<<8);if(x>32767)x-=65536;raw[i]=x/100}
   at=[];for(let f=0;f<nf;f++){const a=new Float32Array(n*n);
    for(let r=0;r<n;r++)for(let c=0;c<n;c++){const fx=Math.max(0,Math.min(nv-1.001,(c+.5)/n*nv-.5)),fy=Math.max(0,Math.min(nv-1.001,(r+.5)/n*nv-.5)),x0=Math.floor(fx),y0=Math.floor(fy),wx=fx-x0,wy=fy-y0,o=f*nv*nv;
     a[r*n+c]=(raw[o+y0*nv+x0]*(1-wx)+raw[o+y0*nv+x0+1]*wx)*(1-wy)+(raw[o+(y0+1)*nv+x0]*(1-wx)+raw[o+(y0+1)*nv+x0+1]*wx)*wy}
    at.push(a)}}
  m.d=d;m.gi=gi;m.gw=gw;m.at=at;m.pronto=true;VENTO[k]={};UV[k]={}}
 C=m.c;N=m.n;H=C.ore;dem=m.d;I=m.gi;WX=m.gw;AT=m.at;ACC=m.acc||null;cv.width=N;cv.height=N;im=cx.createImageData(N,N);
 if(ora>H-1)ora=H-1;Q('cur').max=H-1;Q('cur').value=ora;sel=null;
 document.querySelectorAll('#mw [data-k]').forEach(e=>{e.style.display=e.dataset.k===k?'':'none'});
 document.querySelectorAll('#scale button').forEach(b=>b.setAttribute('aria-pressed',b.dataset.k===k));
 giorni();scalaGrafica()}
function bl(a,k){const q=16*k;let v=0;for(let j=0;j<16;j++)v+=a[I[q+j]]*WX[q+j];return v}
// vento del modello come componenti (verso est, verso nord), km/h, sulla griglia del modello
function uvModello(h){const c=UV[scalaK];if(c[h])return c[h];
 const u=C.ws[h].map((v,i)=>-v*Math.sin(C.wd[h][i]*Math.PI/180)),v=C.ws[h].map((v,i)=>-v*Math.cos(C.wd[h][i]*Math.PI/180));return c[h]=[u,v]}
// stabilita' dell'ora: numero di Froude dal vento medio e dal gradiente termico tra le celle del modello
function froude(h){const m=MM.m[scalaK];if(!m.v)return 1;
 const U=Math.max(0.5,C.ws[h].reduce((a,b)=>a+b,0)/C.ws[h].length/3.6),T=C.T[h].reduce((a,b)=>a+b,0)/C.T[h].length/10;
 const N2=9.81/(273.15+T)*(C.gamma[h]/1000+0.0098);if(N2<=1e-6)return 4;
 const fr=U/(Math.sqrt(N2)*Math.max(100,m.v.rilievo));return fr*fr}
function pesiClassi(h){const cl=MM.m[scalaK].v.classi,f2=froude(h);
 if(f2>=cl[0])return[[0,1]];if(f2<=cl[cl.length-1])return[[cl.length-1,1]];
 for(let i=0;i<cl.length-1;i++)if(f2<=cl[i]&&f2>=cl[i+1]){const w=Math.log(cl[i]/f2)/Math.log(cl[i]/cl[i+1]);return[[i,1-w],[i+1,w]]}
 return[[0,1]]}
// vento sul rilievo (metodo Lens): combinazione delle risposte unitarie pesata con il vento del modello in ogni punto
function vento(h){const c=VENTO[scalaK];if(c[h])return c[h];
 const [mu,mv]=uvModello(h),u=new Float32Array(N*N),v=new Float32Array(N*N),s=new Float32Array(N*N),r=new Float32Array(N*N);
 const pc_=AT?pesiClassi(h):null;
 for(let k=0;k<N*N;k++){const U=bl(mu,k),V=bl(mv,k);let a=U,b=V;
  if(AT){a=0;b=0;for(const [ci,w] of pc_){const o=4*ci;a+=w*(U*AT[o][k]+V*AT[o+2][k]);b+=w*(U*AT[o+1][k]+V*AT[o+3][k])}}
  u[k]=a;v[k]=b;s[k]=Math.hypot(a,b);r[k]=Math.max(0.5,Math.min(1.9,s[k]/Math.max(3,Math.hypot(U,V))))}
 return c[h]={u:u,v:v,s:s,r:r,fr:AT?froude(h):null}}
const sat=x=>Math.exp(17.625*x/(243.04+x));
function tw(t,u){u=Math.max(5,Math.min(99,u));return t*Math.atan(0.151977*Math.sqrt(u+8.313659))+Math.atan(t+u)-Math.atan(u-1.676331)+0.00391838*Math.pow(u,1.5)*Math.atan(0.023101*u)-4.686035}
function punto(k,h){const z0=bl(C.z,k),T0=bl(C.T[h],k)/10,D0=bl(C.Td[h],k)/10,g=C.gamma[h],dz=dem[k]-z0;
 const T=T0+g*dz/1000,Td=Math.min(T,D0-0.002*dz),ur=Math.min(100,100*sat(Td)/sat(T));
 const base=z0+125*Math.max(0,T0-D0),low=Math.max(0,bl(C.low[h],k)),nube=ur>=96||(g<-2&&base<=dem[k]&&low>=50);
 // precipitazione che cresce con la quota rispetto alla cella del modello (circa +6% ogni 100 m, valore tipico dei Carpazi)
 const pr=Math.max(0,bl(C.pr[h],k)/10)*Math.max(0.6,Math.min(1.6,1+0.0006*dz));
 const sn=Math.max(Math.min(1,Math.max(0,(ur-94)/3)),(g<-2&&low>=50)?Math.min(1,Math.max(0,(dem[k]-base+40)/80)):0);
 const w=tw(T,ur);
 return{z:dem[k],T:T,Td:Td,ur:ur,nube:nube,sn:sn,mgla:nube&&g>=-2&&dz<0,low:low,pr:pr,tw:w,neve:pr>=0.1&&w<=1.0,cm:pr<0.1?0:(w<=0.5?pr:(w<=1.5?pr*0.5:0)),base:base}}
function percepita(T,v){return(T<=10&&v>4.8)?13.12+0.6215*T-11.37*Math.pow(v,0.16)+0.3965*T*Math.pow(v,0.16):T}
function visib(p,k,h){const v=C.vis?Math.max(0.05,bl(C.vis[h],k)/10):null;const f=p.sn>0.5?0.15+0.5*(1-p.sn):null;
 return v==null?f:(f==null?v:Math.min(v,f))}
// neve fresca che resta al suolo, ora per ora e punto per punto: quella che cade meno quella che fonde (gradi-ora)
function accumula(){const m=MM.m[scalaK];if(m.acc){ACC=m.acc;return}
 const a=new Float32Array(H*N*N);for(let h=0;h<H;h++){const o=h*N*N,q=(h-1)*N*N;for(let k=0;k<N*N;k++){const p=punto(k,h);
  const fusione=p.T>0?p.T*(0.15+(p.tw>1.5?0.12*p.pr:0)):0;a[o+k]=Math.max(0,(h?a[q+k]:0)+p.cm-fusione)}}
 m.acc=a;ACC=a}
// scale di colore: [valore, [r,g,b]] sfumate, oppure a gradini per la neve
const SF=[[0.1,[214,218,252],'0,1'],[0.5,[160,155,235],'0,5'],[1,[118,98,210],'1'],[2,[78,42,160],'2+']];
const SA=[[0.5,[232,236,255],'0,5'],[2,[196,200,248],'2'],[5,[160,155,235],'5'],[10,[125,105,215],'10'],[20,[95,65,185],'20'],[40,[65,30,135],'40+']];
const ST=[[-20,[40,30,110]],[-14,[49,54,149]],[-7,[69,117,180]],[-2,[116,173,209]],[0,[205,232,243]],[2,[255,250,200]],[6,[254,217,118]],[11,[253,160,80]],[17,[240,101,60]],[24,[212,45,38]],[32,[150,0,38]]];
const SW=[[0,[214,226,236]],[5,[170,205,226]],[10,[118,180,212]],[20,[86,170,150]],[30,[150,200,90]],[40,[245,210,80]],[55,[244,150,60]],[70,[218,70,64]],[90,[160,40,120]]];
const SU=[[30,[168,120,70]],[50,[222,196,140]],[70,[200,226,214]],[85,[96,180,190]],[100,[30,110,160]]];
const SV=[[0.1,[250,250,252]],[0.5,[225,228,234]],[1,[190,196,210]],[3,[150,160,180]],[10,[120,130,150]]];
const SP=[[985,[70,110,190]],[1000,[150,180,225]],[1013,[240,240,240]],[1025,[240,190,150]],[1040,[200,100,80]]];
const SC=[[50,[255,245,170]],[300,[253,200,90]],[1000,[240,110,50]],[2500,[190,30,60]]];
const SS=[[0,[60,70,90]],[100,[150,140,110]],[300,[250,214,120]],[600,[255,180,40]]];
function sfuma(S,t){if(t<=S[0][0])return S[0][1];for(let i=1;i<S.length;i++)if(t<=S[i][0]){const a=S[i-1],b=S[i],w=(t-a[0])/(b[0]-a[0]);return[a[1][0]+(b[1][0]-a[1][0])*w,a[1][1]+(b[1][1]-a[1][1])*w,a[1][2]+(b[1][2]-a[1][2])*w]}return S[S.length-1][1]}
function classe(S,v){let c=S[0][1];for(const x of S)if(v>=x[0])c=x[1];return c}
const num=(x,n)=>(x==null||isNaN(x))?'–':x.toFixed(n||0).replace('.',',').replace('-','−');
const MANCA={12:'sw',13:'p',14:'cape',15:'T850'};
function disegna(){const d=im.data;if(strato==4)accumula();const vuoto=MANCA[strato]&&!C[MANCA[strato]];
 const W=(strato==5||strato==7||strato==8)?vento(ora):null;
 for(let k=0;k<N*N;k++){let c=null,a=0;
  if(strato&&!vuoto){const p=punto(k,ora);
   switch(strato){
   case 1:{const q=p.sn;c=[95+155*q,102+148*q,118+135*q];a=Math.max(222*q,p.low*1.15*(1-q));break}
   case 2:if(p.pr>=0.1&&p.tw>0.5){c=p.tw<=1.5?[120,170,235]:[30,100,210];a=Math.min(235,90+p.pr*90)}break;
   case 3:if(p.cm>=0.05){c=classe(SF,p.cm);a=210*Math.min(1,(p.cm-0.05)/0.1)}break;
   case 4:{const v=ACC[ora*N*N+k];if(v>=0.3){c=classe(SA,v);a=210*Math.min(1,(v-0.3)/0.4)}break}
   case 5:c=sfuma(SW,W.s[k]);a=165;break;
   case 6:c=sfuma(ST,p.T);a=155;break;
   case 7:c=sfuma(SW,bl(C.wg[ora],k)*W.r[k]);a=165;break;
   case 8:c=sfuma(ST,percepita(p.T,W.s[k]));a=155;break;
   case 9:c=sfuma(SU,p.ur);a=150;break;
   case 10:{const v=visib(p,k,ora);if(v!=null&&v<10){c=sfuma(SV,v);a=Math.min(225,60+165*Math.max(0,1-Math.log10(v*10)/2))}break}
   case 11:{const v=Math.max(0,Math.min(100,bl(C.nuv[ora],k)));c=[248,249,252];a=v*2.0;break}
   case 12:{const v=Math.max(0,bl(C.sw[ora],k));c=sfuma(SS,v);a=v<5?120:150;break}
   case 13:c=sfuma(SP,bl(C.p[ora],k)/10);a=110;break;
   case 14:{const v=Math.max(0,bl(C.cape[ora],k));if(v>=50){c=sfuma(SC,v);a=Math.min(200,80+v/10)}break}
   case 15:c=sfuma(ST,bl(C.T850[ora],k)/10);a=155;break}}
  const o=4*k;if(c){d[o]=c[0];d[o+1]=c[1];d[o+2]=c[2];d[o+3]=a}else{d[o+3]=0}}
 cx.putImageData(im,0,0);linee();aggiornaFlusso();tempo();info()}
// ---- linee: isobare, isoterma di zero gradi (quadrati in marcia sulla griglia della carta)
function campoLinea(){if(MANCA[strato]&&!C[MANCA[strato]])return null;if(strato==13){const a=new Float32Array(N*N);for(let k=0;k<N*N;k++)a[k]=bl(C.p[ora],k)/10;return{a:a,passo:2,fmt:v=>num(v,0)}}
 if(strato==6||strato==8){const a=new Float32Array(N*N);const W=strato==8?vento(ora):null;for(let k=0;k<N*N;k++){const p=punto(k,ora);a[k]=W?percepita(p.T,W.s[k]):p.T}return{a:a,livelli:[0],fmt:()=>'0°'}}
 if(strato==15){const a=new Float32Array(N*N);for(let k=0;k<N*N;k++)a[k]=bl(C.T850[ora],k)/10;return{a:a,passo:2,fmt:v=>num(v,0)+'°'}}
 return null}
function linee(){const r=window.devicePixelRatio||1,w=lc.clientWidth*r,h=lc.clientHeight*r;if(lc.width!==w)lc.width=w;if(lc.height!==h)lc.height=h;
 lx.clearRect(0,0,w,h);const L=campoLinea();if(!L)return;const a=L.a;let lo=1e9,hi=-1e9;for(const v of a){if(v<lo)lo=v;if(v>hi)hi=v}
 const liv=L.livelli||(()=>{const o=[];for(let v=Math.ceil(lo/L.passo)*L.passo;v<=hi;v+=L.passo)o.push(v);return o})();
 const sx=w/N,sy=h/N,P=(c,r)=>[(c+.5)*sx,(r+.5)*sy];
 lx.lineJoin='round';lx.lineCap='round';
 for(const v of liv){const seg=[];
  for(let r=0;r<N-1;r++)for(let c=0;c<N-1;c++){const q=[a[r*N+c],a[r*N+c+1],a[(r+1)*N+c+1],a[(r+1)*N+c]];
   const idx=(q[0]>v?8:0)|(q[1]>v?4:0)|(q[2]>v?2:0)|(q[3]>v?1:0);if(idx===0||idx===15)continue;
   const e=[(()=>{const t=(v-q[0])/(q[1]-q[0]);return[c+t,r]})(),(()=>{const t=(v-q[1])/(q[2]-q[1]);return[c+1,r+t]})(),(()=>{const t=(v-q[3])/(q[2]-q[3]);return[c+t,r+1]})(),(()=>{const t=(v-q[0])/(q[3]-q[0]);return[c,r+t]})()];
   const T={1:[[2,3]],2:[[1,2]],3:[[1,3]],4:[[0,1]],5:[[0,3],[1,2]],6:[[0,2]],7:[[0,3]],8:[[0,3]],9:[[0,2]],10:[[0,1],[2,3]],11:[[0,1]],12:[[1,3]],13:[[1,2]],14:[[2,3]]}[idx];
   for(const [i,j] of T)seg.push([e[i],e[j]])}
  if(!seg.length)continue;
  const zero=L.livelli;
  lx.strokeStyle='rgba(255,255,255,.8)';lx.lineWidth=(zero?3.6:3.2)*r;lx.beginPath();for(const [p,q] of seg){const A=P(p[0],p[1]),B=P(q[0],q[1]);lx.moveTo(A[0],A[1]);lx.lineTo(B[0],B[1])}lx.stroke();
  lx.strokeStyle=zero?'#1b3f8f':'rgba(30,34,48,.8)';lx.lineWidth=(zero?1.6:1.3)*r;if(zero)lx.setLineDash([5*r,4*r]);lx.stroke();lx.setLineDash([]);
  // etichetta: sul tratto piu' vicino al centro di ogni quarto di carta in cui la linea passa
  const usati=[];for(const [qx,qy] of [[.3,.3],[.7,.7],[.7,.3],[.3,.7]]){let best=null,bd=1e9;
   for(const [p] of seg){const dd=Math.hypot(p[0]/N-qx,p[1]/N-qy);if(dd<bd){bd=dd;best=p}}
   if(!best||bd>.22||usati.some(u=>Math.hypot(u[0]-best[0],u[1]-best[1])<N*.25))continue;usati.push(best);
   const A=P(best[0],best[1]),t=L.fmt(v);lx.font=(600*1)+' '+(11*r)+'px system-ui,sans-serif';lx.textAlign='center';lx.textBaseline='middle';
   lx.lineWidth=3.5*r;lx.strokeStyle='rgba(255,255,255,.95)';lx.strokeText(t,A[0],A[1]);lx.fillStyle=zero?'#1b3f8f':'#1e2230';lx.fillText(t,A[0],A[1])}}}
// ---- flusso del vento: particelle che seguono il vento sul rilievo
let part=[],anim=null;
function flussoAttivo(){return flusso==null?strato==5||strato==7:flusso}
function aggiornaFlusso(){const on=flussoAttivo();Q('flx').setAttribute('aria-pressed',on);
 if(!on){if(anim){cancelAnimationFrame(anim);anim=null}px.clearRect(0,0,pc.width,pc.height);return}
 const r=window.devicePixelRatio||1,w=pc.clientWidth*r,h=pc.clientHeight*r;if(pc.width!==w||pc.height!==h){pc.width=w;pc.height=h;part=[]}
 if(!part.length){const n=Math.round(Math.min(1400,w*h/(r*r)/90));for(let i=0;i<n;i++)part.push(nuova(w,h,true))}
 if(!anim)anim=requestAnimationFrame(passo)}
function nuova(w,h,a){return{x:Math.random()*w,y:Math.random()*h,e:a?Math.floor(Math.random()*90):0}}
function passo(){const r=window.devicePixelRatio||1,w=pc.width,h=pc.height,W=vento(ora);
 px.globalCompositeOperation='destination-in';px.fillStyle='rgba(0,0,0,0.92)';px.fillRect(0,0,w,h);px.globalCompositeOperation='source-over';
 px.lineWidth=1.25*r;px.strokeStyle=strato==5||strato==7?'rgba(255,255,255,.88)':'rgba(25,30,45,.75)';px.beginPath();
 const k_=0.03*w/370;
 for(const p of part){const c=Math.min(N-1,Math.max(0,Math.floor(p.x/w*N))),rr=Math.min(N-1,Math.max(0,Math.floor(p.y/h*N))),k=rr*N+c;
  const dx=W.u[k]*k_,dy=-W.v[k]*k_,x2=p.x+dx,y2=p.y+dy;
  if(Math.abs(dx)+Math.abs(dy)>0.02){px.moveTo(p.x,p.y);px.lineTo(x2,y2)}
  p.x=x2;p.y=y2;p.e++;
  if(p.e>90||p.x<0||p.y<0||p.x>w||p.y>h||W.s[k]<0.7)Object.assign(p,nuova(w,h,false))}
 px.stroke();anim=requestAnimationFrame(passo)}
document.addEventListener('visibilitychange',()=>{if(document.hidden&&anim){cancelAnimationFrame(anim);anim=null}else if(!document.hidden)aggiornaFlusso()});
// ---- scala grafica e giorni sotto il cursore del tempo
function scalaGrafica(){const lato=+scalaK,tgt=lato/5,pas=[0.5,1,2,5,10,20,25,50];let km=pas[0];for(const v of pas)if(v<=tgt)km=v;
 Q('sb').innerHTML='<span style="width:'+(km/lato*100).toFixed(1)+'%"></span><b>'+num(km,km<1?1:0)+' km</b>'}
function giorni(){const t0=new Date(C.t0+':00Z');let s='';
 for(let h=0;h<H;h++){const t=new Date(t0.getTime()+h*3600e3);const ore=+new Intl.DateTimeFormat('en-GB',{hour:'numeric',hourCycle:'h23',timeZone:'Europe/Warsaw'}).format(t);
  if(ore===0&&h>0)s+='<i style="left:'+(h/(H-1)*100).toFixed(2)+'%"></i>';
  if(ore===12){let g;try{g=new Intl.DateTimeFormat(lang,{weekday:'short',timeZone:'Europe/Warsaw'}).format(t)}catch(e){g=''}s+='<em style="left:'+(h/(H-1)*100).toFixed(2)+'%">'+g+'</em>'}}
 Q('gg').innerHTML=s}
function tempo(){const t=new Date(C.t0+':00Z');t.setUTCHours(t.getUTCHours()+ora);
 let s;try{s=new Intl.DateTimeFormat(lang,{weekday:'short',day:'numeric',hour:'2-digit',minute:'2-digit',timeZone:'Europe/Warsaw'}).format(t)}catch(e){s=t.toISOString().slice(5,16)}
 Q('tl').textContent=s}
function rosa(u,v){const d=(Math.atan2(-u,-v)*180/Math.PI+360)%360;return(lang=='pl'?['N','NE','E','SE','S','SW','W','NW']:['N','NE','E','SE','S','SO','O','NO'])[Math.round(d/45)%8]}
function info(){const T=TXT[lang],mk=Q('mk');if(sel==null){Q('info').innerHTML='<p class="vuoto">'+T.tocca+'</p>';mk.style.display='none';return}
 const p=punto(sel,ora),W=vento(ora),x=(sel%N+.5)/N*100,y=(Math.floor(sel/N)+.5)/N*100;
 mk.style.display='block';mk.style.left=x+'%';mk.style.top=y+'%';
 const vis=visib(p,sel,ora),pr=p.pr>=0.1?(p.tw<=0.5?T.f_neve:(p.tw<=1.5?T.f_mista:T.f_pioggia)):T.asciutto;
 const righe=[[T.quota,p.z+' m'],[T.temp,num(p.T,1)+' °C'],[T.percepita,num(percepita(p.T,W.s[sel]),0)+' °C'],
  [T.vento,num(W.s[sel],0)+' km/h '+rosa(W.u[sel],W.v[sel])],[T.raffica,num(bl(C.wg[ora],sel)*W.r[sel],0)+' km/h'],
  [T.precip,num(p.pr,1)+' mm/h · '+pr],[T.ur,num(p.ur,0)+' %'],[T.cielo,p.mgla?T.nebbia:(p.nube?T.in_nube:T.fuori_nube)],
  [T.visib,vis==null?'–':(vis<1?num(vis*1000,0)+' m':num(vis,vis<10?1:0)+' km')],[T.pressione,C.p?num(bl(C.p[ora],sel)/10,0)+' hPa':'–']];
 if(ACC)righe.push([T.nuova,num(ACC[ora*N*N+sel],0)+' cm']);
 Q('info').innerHTML='<div class="ig">'+righe.map(r=>'<span>'+r[0]+'</span><b>'+r[1]+'</b>').join('')+'</div>'}
function scalaHtml(S,a,b,tacche,unita){return '<div class="scala" style="background:linear-gradient(90deg,'+S.filter(s=>s[0]>=a&&s[0]<=b).map(s=>'rgb('+s[1].map(Math.round).join(',')+') '+((s[0]-a)/(b-a)*100).toFixed(0)+'%').join(',')+')"></div><div class="tacche">'+tacche.map(t=>'<span>'+t+'</span>').join('')+'<span class="u">'+unita+'</span></div>'}
function scalaClassi(S,unita){return '<div class="classi">'+S.map(x=>'<div><i style="background:rgb('+x[1].join(',')+')"></i>'+x[2]+'</div>').join('')+'<div class="u">'+unita+'</div></div>'}
function testi(){const T=TXT[lang];
 const bott=ids=>ids.map(i=>'<button type="button" data-s="'+i+'" aria-pressed="'+(i==strato)+'">'+T.strati[i]+'</button>').join('');
 Q('strati').innerHTML=bott(PRINC)+'<button type="button" class="piu" data-piu aria-expanded="'+altri+'">'+(altri?T.meno:T.piu)+'</button>';
 Q('strati2').innerHTML=bott(ALTRI);Q('strati2').hidden=!altri&&!ALTRI.includes(strato);
 document.querySelectorAll('#mw .casa-t').forEach(e=>{e.textContent=MM.casa[lang]+' '+MM.quota+' m'});
 let lg=T.leg[strato],h='';
 if(strato==3)h=scalaClassi(SF,'cm/h');
 if(strato==4){h=scalaClassi(SA,'cm');if(MM.suolo!=null)lg+=' '+T.suolo+': '+MM.suolo+' cm.'}
 if(strato==5||strato==7)h=scalaHtml(SW,0,90,['0','10','20','40','70','90'],'km/h');
 if(strato==6||strato==8||strato==15)h=scalaHtml(ST,-20,24,['−20','−10','0','10','24'],'°C');
 if(strato==9)h=scalaHtml(SU,30,100,['30','50','70','85','100'],'%');
 if(strato==10)h=scalaHtml(SV,0.1,10,['0,1','1','3','10'],'km');
 if(strato==12)h=scalaHtml(SS,0,600,['0','100','300','600'],'W/m²');
 if(strato==13)h=scalaHtml(SP,985,1040,['985','1000','1013','1025','1040'],'hPa');
 if(strato==14)h=scalaHtml(SC,50,2500,['50','300','1000','2500'],'J/kg');
 let st='';if(AT&&(strato==5||strato==7||strato==8)){const f=froude(ora),fr=Math.sqrt(f);st=' '+(fr>1?T.fr_alto:fr>0.4?T.fr_medio:T.fr_basso).replace('#',num(fr,fr<1?2:1))}
 Q('leg').innerHTML='<div class="lt">'+T.strati[strato]+'</div>'+h+'<p>'+lg+st+'</p><p class="src">'+T.modello+': '+MM.modello+(AT&&(strato==5||strato==7||strato==8)?' · '+T.lens:'')+'</p>';
 Q('flx').title=T.flusso;giorni();tempo();info()}
document.getElementById('mappa').addEventListener('click',e=>{const b=e.target.closest('#strati button,#strati2 button');if(!b)return;
 if(b.dataset.piu!=null){altri=!altri;testi();return}strato=+b.dataset.s;testi();disegna()});
Q('scale').addEventListener('click',e=>{const b=e.target.closest('button');if(!b||b.dataset.k===scalaK)return;carica(b.dataset.k);part=[];testi();disegna()});
Q('cur').addEventListener('input',e=>{ora=+e.target.value;disegna();if(strato==5||strato==7||strato==8)testi()});
Q('flx').addEventListener('click',e=>{e.stopPropagation();flusso=!flussoAttivo();aggiornaFlusso()});
function avanti(d){ora=Math.max(0,Math.min(H-1,ora+d));Q('cur').value=ora;disegna()}
Q('pr').addEventListener('click',()=>avanti(-1));Q('nx').addEventListener('click',()=>avanti(1));
Q('play').addEventListener('click',()=>{if(giro){clearInterval(giro);giro=null;Q('play').classList.remove('on');return}
 Q('play').classList.add('on');giro=setInterval(()=>{ora=(ora+1)%H;Q('cur').value=ora;disegna()},700)});
Q('mw').addEventListener('click',e=>{if(e.target.closest('#flx'))return;const r=Q('mw').getBoundingClientRect(),c=Math.min(N-1,Math.max(0,Math.floor((e.clientX-r.left)/r.width*N))),w=Math.min(N-1,Math.max(0,Math.floor((e.clientY-r.top)/r.height*N)));sel=w*N+c;info()});
window.addEventListener('resize',()=>{part=[];linee();aggiornaFlusso()});
carica(MM.k[MM.k.length>2?1:0]);lingua(lang);disegna();
})();
