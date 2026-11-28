"""Pistrice Sailing · Weather Lab: la carta del vento a tutto schermo, da allargare con le dita come Windy.
Tessere in rilievo (t/{z}/{x}/{y}.webp) sotto, il campo di Lens sopra, scie animate, cassetto in basso."""
import json
import os

QUI = os.path.dirname(os.path.abspath(__file__))


def _leggi(*p):
    return open(os.path.join(QUI, *p), encoding="utf-8").read()


def fonti():
    import base64
    cart = os.path.join(QUI, "lens", "fonti")
    gamme = {"latin": "U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+2000-206F,U+20AC,U+2122,U+2212",
             "latin-ext": "U+0100-02BA,U+02BD-02C5,U+02C7-02CC,U+02CE-02D7,U+02DD-02FF,U+1E00-1E9F,U+2C60-2C7F,U+A720-A7FF"}
    out = ""
    for sub, gamma in gamme.items():
        for stile in ("normal", "italic"):
            f = os.path.join(cart, f"eb-garamond-{sub}-500-{stile}.woff2")
            if os.path.exists(f):
                b = base64.b64encode(open(f, "rb").read()).decode()
                out += (f"@font-face{{font-family:'Garamond Stara';font-style:{stile};font-weight:500;font-display:swap;"
                        f"src:url(data:font/woff2;base64,{b}) format('woff2');unicode-range:{gamma}}}")
    return out


CSS = r"""
html,body{margin:0;height:100%;overflow:hidden;background:#cfe3ec;font:15px/1.4 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;color:#14171c;-webkit-tap-highlight-color:transparent}
#map{position:fixed;inset:0;height:100dvh;background:#cfe3ec}
#pc,#oc{position:fixed;inset:0;width:100%;height:100%;pointer-events:none;z-index:450}
.campo{mix-blend-mode:multiply}
.brand{position:fixed;top:calc(8px + env(safe-area-inset-top));left:8px;z-index:800;display:flex;align-items:center;gap:8px;background:rgba(255,255,255,.88);backdrop-filter:blur(6px);-webkit-backdrop-filter:blur(6px);border-radius:14px;padding:5px 10px 5px 6px;box-shadow:0 2px 10px rgba(0,0,0,.18)}
.brand img{height:30px;display:block}
.brand b{display:block;font-family:'Garamond Stara',Georgia,serif;font-weight:500;font-size:15px;line-height:1.05;letter-spacing:.3px}
.brand em{display:block;font-size:10px;line-height:1.25;color:#55585e;font-family:'Garamond Stara',Georgia,serif}.brand em.cr{font-style:normal;font-family:inherit;font-size:9px;color:#8a8d93;letter-spacing:.3px}
.brand small{display:block;font-size:10.5px;color:#9c1a24;letter-spacing:1.6px;text-transform:uppercase;font-weight:700}
.strati{position:fixed;top:calc(8px + env(safe-area-inset-top));right:8px;z-index:800;display:flex;flex-direction:column;gap:6px}
.strati button,.tondo{font:inherit;font-size:12px;font-weight:650;border:0;background:rgba(255,255,255,.9);backdrop-filter:blur(6px);-webkit-backdrop-filter:blur(6px);color:#14171c;border-radius:12px;padding:7px 10px;box-shadow:0 2px 8px rgba(0,0,0,.18);cursor:pointer;min-width:74px;text-align:center}
.strati button[aria-pressed=true]{background:#14171c;color:#fff}
#flx[aria-pressed=true]{background:#1f3a66;color:#fff}
.leaflet-container{background:#cfe3ec;font:inherit}
.leaflet-control-attribution{font-size:9px!important;background:rgba(255,255,255,.6)!important;margin-bottom:var(--cassetto,118px)!important}
.leaflet-control-zoom{display:none}
.nome{white-space:nowrap;font-family:'Garamond Stara',Georgia,serif;font-weight:500;color:#2a2118;text-shadow:0 0 3px #f6efdc,0 0 3px #f6efdc,0 0 2px #f6efdc;pointer-events:none;transform:translate(-50%,-50%);font-size:14px}
.nome.c{font-size:16px;font-variant:small-caps;letter-spacing:1.2px}
.nome.p{font-style:italic;color:#5a3d1e;font-size:13px}
.nome.p:before{content:'▲ ';font-size:9px;font-style:normal}
.pt{position:relative}
.pt i{position:absolute;left:-9px;top:-9px;width:18px;height:18px;border-radius:50%;border:2.5px solid #fff;box-shadow:0 0 0 2px #14171c,0 2px 6px rgba(0,0,0,.4)}
.bolla{position:absolute;left:12px;bottom:12px;background:rgba(20,23,28,.92);color:#fff;border-radius:12px;padding:6px 8px;display:flex;gap:2px;box-shadow:0 4px 14px rgba(0,0,0,.35);white-space:nowrap}
.bolla.sx{left:auto;right:12px}.bolla.giu{bottom:auto;top:12px}
.bolla div{text-align:center;min-width:46px;padding:0 3px}
.bolla div+div{border-left:1px solid rgba(255,255,255,.15)}
.bolla em{display:block;font-style:normal;font-size:9.5px;opacity:.7;letter-spacing:.4px;text-transform:uppercase}
.bolla b{display:block;font-size:17px;line-height:1.1}
.bolla small{display:block;font-size:10.5px;opacity:.85;font-variant-numeric:tabular-nums}
.bolla svg{width:14px;height:14px;vertical-align:-2px;margin-right:2px}
.bolla small.w{margin-top:2px;color:#9fd0ff}
#cas{position:fixed;left:0;right:0;bottom:0;z-index:900;background:rgba(253,253,251,.97);backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);border-radius:18px 18px 0 0;box-shadow:0 -4px 20px rgba(0,0,0,.18);padding:0 12px calc(10px + env(safe-area-inset-bottom));max-height:75dvh;overflow:hidden;touch-action:none}
#cas.anima{transition:transform .25s ease}
#cas.aperto{overflow-y:auto;touch-action:pan-y}
.maniglia{display:block;width:100%;border:0;background:none;padding:8px 0 4px;cursor:pointer}
.maniglia span{display:block;margin:0 auto;width:42px;height:5px;border-radius:3px;background:#c9c6bd}
.riga{display:flex;align-items:center;gap:8px}
.tb{width:34px;height:34px;border-radius:50%;border:1px solid #e2e0d8;background:#fff;font:inherit;font-size:15px;display:grid;place-items:center;padding:0;flex:none;cursor:pointer;color:#14171c}
#play{width:40px;height:40px;background:#14171c;color:#fff;border-color:#14171c}#play.on{background:#9c1a24;border-color:#9c1a24}
.cursore{flex:1;min-width:0;position:relative;padding-bottom:15px}.cursore input{width:100%;margin:0;accent-color:#9c1a24}
#gg{position:absolute;left:8px;right:8px;bottom:0;height:14px;font-size:10.5px;color:#6b6e74}
#gg i{position:absolute;top:-13px;width:1px;height:8px;background:#d8d5cc}#gg em{position:absolute;transform:translateX(-50%);font-style:normal}
.ora{display:flex;justify-content:space-between;align-items:baseline;margin:2px 2px 6px}
.ora b{font-size:16px;font-variant-numeric:tabular-nums;text-transform:capitalize}.ora span{font-size:11.5px;color:#6b6e74}
.scala{display:grid;grid-template-columns:repeat(8,1fr);gap:2px;margin:6px 0 0;text-align:center;font-size:10.5px;color:#55585e;font-variant-numeric:tabular-nums}
.scala i{display:block;height:8px;border-radius:3px;margin-bottom:1px}
.altro{margin-top:12px;font-size:13px;color:#3a3d43}
.altro h3{font-size:12px;letter-spacing:1px;text-transform:uppercase;color:#9c1a24;margin:16px 0 6px}
.tab{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums;font-size:13px}
.tab th{font-weight:600;font-size:11px;color:#6b6e74;text-align:center;padding:2px}
.tab td{text-align:center;padding:4px 2px;border-top:1px solid #ecebe6}
.tab td:first-child,.tab th:first-child{text-align:left}
.vuoto{color:#6b6e74}
.firma{display:flex;align-items:center;gap:10px;margin-top:18px;padding-top:12px;border-top:1px solid #ecebe6}
.firma img{height:44px}.firma p{margin:0;font-size:12px;color:#55585e}
.altro p{margin:.45em 0}
"""

JS = r"""
(async function(){
const D=__DATI__,Q=id=>document.getElementById(id);
function dec(b){const s=atob(b),a=new Uint8Array(s.length);for(let i=0;i<s.length;i++)a[i]=s.charCodeAt(i);return a}
async function gunzip(b,txt){const r=new Response(new Blob([dec(b)]).stream().pipeThrough(new DecompressionStream('gzip')));return txt?r.text():new Uint8Array(await r.arrayBuffer())}
let P,BIN;
try{P=JSON.parse(await gunzip(D.gz,true));BIN=await gunzip(D.bin,false)}
catch(e){document.body.insertAdjacentHTML('beforeend','<p style="position:fixed;top:40%;left:10%;right:10%;background:#fff;padding:16px;border-radius:12px;z-index:2000">Questo browser è troppo vecchio per aprire la carta: aggiornalo e riprova.</p>');return}
const ORE=P.ore,NH=ORE.length,nx=D.nx,ny=D.ny,N=nx*ny,[S0,N0,O0,E0]=D.interno;
{const acc=new Uint8Array(N);for(let f=0;f<3;f++){acc.fill(0);for(let n=0;n<NH;n++){const o=(f*NH+n)*N;for(let k=0;k<N;k++){acc[k]=(acc[k]+BIN[o+k])&255;BIN[o+k]=acc[k]}}}}
const MAR=new Uint8Array(N);{const m=dec(P.mare);for(let k=0;k<N;k++)MAR[k]=(m[k>>3]>>(7-(k&7)))&1}
const CAMPO={};
function ora(n){if(CAMPO[n])return CAMPO[n];const V=BIN.subarray(n*N,n*N+N),G=BIN.subarray((NH+n)*N,(NH+n)*N+N),Dd=BIN.subarray((2*NH+n)*N,(2*NH+n)*N+N);
 const o={S:new Float32Array(N),G:new Float32Array(N),U:new Float32Array(N),W:new Float32Array(N),m:ORE[n]};
 for(let k=0;k<N;k++){const s=V[k]/2,a=Dd[k]*Math.PI/64;o.S[k]=s;o.G[k]=G[k]/2;o.U[k]=-s*Math.sin(a);o.W[k]=-s*Math.cos(a)}
 const ks=Object.keys(CAMPO);if(ks.length>6)delete CAMPO[ks[0]];return CAMPO[n]=o}
// pioggia e CAPE: griglia del modello su tutto il dominio di calcolo
function blm(a,i,j){if(!a)return 0;const gx=(i+D.m+.5)/D.NX*(D.gx-1),gy=(j+D.m+.5)/D.NY*(D.gy-1),x0=Math.max(0,Math.min(D.gx-2,Math.floor(gx))),y0=Math.max(0,Math.min(D.gy-2,Math.floor(gy))),wx=gx-x0,wy=gy-y0,q=y0*D.gx+x0;
 return(a[q]*(1-wx)+a[q+1]*wx)*(1-wy)+(a[q+D.gx]*(1-wx)+a[q+D.gx+1]*wx)*wy}
const OD=D.onde;
function onda(n,lat,lon){if(!OD)return null;const [bs,bn,bo,be]=OD.box,fy=(bn-lat)/(bn-bs)*(OD.gy-1),fx=(lon-bo)/(be-bo)*(OD.gx-1);
 if(fx<0||fy<0||fx>OD.gx-1||fy>OD.gy-1)return null;const x0=Math.min(OD.gx-2,Math.floor(fx)),y0=Math.min(OD.gy-2,Math.floor(fy)),wx=fx-x0,wy=fy-y0,q=y0*OD.gx+x0,G=OD.gx;
 const H=OD.h[n],Dd=OD.d[n],T=OD.p[n];if(!H||H[q]==null)return null;
 const b=a=>(a[q]*(1-wx)+a[q+1]*wx)*(1-wy)+(a[q+G]*(1-wx)+a[q+G+1]*wx)*wy;
 let su=0,cu=0;for(const [k,w] of [[q,(1-wx)*(1-wy)],[q+1,wx*(1-wy)],[q+G,(1-wx)*wy],[q+G+1,wx*wy]]){const r=Dd[k]*Math.PI/180;su+=w*Math.sin(r);cu+=w*Math.cos(r)}
 return{h:b(H),d:(Math.atan2(su,cu)*180/Math.PI+360)%360,p:T&&T[q]!=null?b(T):null}}
const SO=[[0,[225,238,246]],[0.25,[175,212,236]],[0.5,[118,174,228]],[1,[64,124,212]],[1.5,[72,84,192]],[2,[122,62,172]],[3,[172,52,122]],[4,[205,42,62]]];
const pioggia=(m,i,j)=>Math.max(0,blm(m.pr,i,j)),temporale=(m,i,j)=>{if(!m.ca)return 0;const c=blm(m.ca,i,j),p=pioggia(m,i,j);return Math.max(0,Math.min(1,(c-300)/700))*Math.min(1,0.3+p/0.6)};
// posizione -> cella (frazionaria) della griglia
const ij=(lat,lon)=>[(lon-O0)/(E0-O0)*nx-.5,(N0-lat)/(N0-S0)*ny-.5];
function campo(a,fi,fj){if(fi<-.5||fj<-.5||fi>nx-.5||fj>ny-.5)return null;const i0=Math.max(0,Math.min(nx-2,Math.floor(fi))),j0=Math.max(0,Math.min(ny-2,Math.floor(fj))),wx=Math.min(1,Math.max(0,fi-i0)),wy=Math.min(1,Math.max(0,fj-j0)),k=j0*nx+i0;
 return(a[k]*(1-wx)+a[k+1]*wx)*(1-wy)+(a[k+nx]*(1-wx)+a[k+nx+1]*wx)*wy}
const WS=[[0,[150,190,228]],[5,[76,175,80]],[10,[192,202,51]],[15,[255,179,0]],[20,[255,112,67]],[25,[229,57,53]],[32,[142,36,170]],[40,[90,20,110]]];
const SP=[[0.1,[190,215,245]],[0.5,[120,170,235]],[1,[60,130,220]],[3,[25,85,190]],[8,[15,45,140]]];
function sfuma(S,v){if(v<=S[0][0])return S[0][1];for(let i=1;i<S.length;i++)if(v<=S[i][0]){const a=S[i-1],b=S[i],t=(v-a[0])/(b[0]-a[0]);return[a[1][0]+(b[1][0]-a[1][0])*t,a[1][1]+(b[1][1]-a[1][1])*t,a[1][2]+(b[1][2]-a[1][2])*t]}return S[S.length-1][1]}
const rgb=c=>'rgb('+c.map(Math.round).join(',')+')';
const num=(x,n)=>(x==null?'–':x.toFixed(n||0).replace('.',','));
const ROSA=['N','NNE','NE','ENE','E','ESE','SE','SSE','S','SSO','SO','OSO','O','ONO','NO','NNO'],NOMI=['tramontana','grecale','levante','scirocco','ostro','libeccio','ponente','maestrale'];
const LIM=[1,3.5,6.5,10.5,16.5,21.5,27.5,33.5,40.5];const forza=v=>{let b=0;while(b<LIM.length&&v>=LIM[b])b++;return b};
const fmtOra=t=>new Intl.DateTimeFormat('it',{weekday:'short',day:'numeric',hour:'2-digit',minute:'2-digit',timeZone:'Europe/Rome'}).format(new Date(t+':00Z'));
const soloOra=t=>new Intl.DateTimeFormat('it',{hour:'2-digit',minute:'2-digit',timeZone:'Europe/Rome'}).format(new Date(t+':00Z'));
// prima ora: quella in corso
let h=0;{const ad=Date.now();for(let n=0;n<NH;n++)if(new Date(ORE[n].t+':00Z').getTime()<=ad)h=n}
let strato='vento',flusso=null,giro=null,sel=null;
// ---- carta
const lim=[[S0-0.03,O0-0.04],[N0+0.03,E0+0.04]];
const map=L.map('map',{zoomControl:false,minZoom:10,maxZoom:16,maxBounds:L.latLngBounds(lim).pad(0.15),maxBoundsViscosity:0.8,attributionControl:true,zoomSnap:0.25,wheelPxPerZoomLevel:90});
L.tileLayer('t/{z}/{x}/{y}.webp',{minZoom:10,maxZoom:16,maxNativeZoom:14,bounds:lim,attribution:'Rilievo Copernicus DEM · ESA WorldCover · © OpenStreetMap · '+D.modello+' via Open-Meteo · Copernicus Sentinel-1'}).addTo(map);
map.fitBounds([[38.04,13.17],[38.25,13.56]]);
{const zmin=map.getBoundsZoom([[S0,O0],[N0,E0]],false);map.setMinZoom(Math.max(10,Math.floor(zmin*4)/4));map.setMaxBounds(L.latLngBounds([[S0,O0],[N0,E0]]).pad(0.08));map.options.maxBoundsViscosity=1}
map.createPane('costa').style.zIndex=430;
fetch('costa.json').then(r=>r.json()).then(c=>{L.polyline(c,{pane:'costa',color:'#2c3e50',weight:1.4,opacity:.9,interactive:false,smoothFactor:1}).addTo(map)}).catch(()=>{});
// campo colorato: un'immagine a griglia, ridisegnata solo quando cambiano ora o strato
const cvF=document.createElement('canvas');cvF.width=nx;cvF.height=ny;const cxF=cvF.getContext('2d');let ovl=null;
function immagine(){const o=ora(h),im=cxF.createImageData(nx,ny),d=im.data;
 for(let j=0;j<ny;j++)for(let i=0;i<nx;i++){const k=j*nx+i;let c=null,a=0;
  if(strato==='vento'){c=sfuma(WS,o.S[k]);a=MAR[k]?190:110}else if(strato==='raff'){c=sfuma(WS,o.G[k]);a=MAR[k]?200:120}
  else if(strato==='onde'){if(MAR[k]){const w=onda(h,N0-(j+.5)/ny*(N0-S0),O0+(i+.5)/nx*(E0-O0));if(w){c=sfuma(SO,w.h);a=200}}}
  else{const p=pioggia(o.m,i,j),t=temporale(o.m,i,j);if(t>0.15){c=[150,60,190];a=Math.min(210,60+150*t)}else if(p>=0.1){c=sfuma(SP,p);a=Math.min(220,90+p*60)}}
  const q=4*k;if(c){d[q]=c[0];d[q+1]=c[1];d[q+2]=c[2];d[q+3]=a}}
 cxF.putImageData(im,0,0);const url=cvF.toDataURL('image/png');
 if(!ovl)ovl=L.imageOverlay(url,[[S0,O0],[N0,E0]],{opacity:1,interactive:false,className:'campo'}).addTo(map);else ovl.setUrl(url)}
// nomi, nitidi a ogni zoom; si tengono solo quelli che non si sovrappongono
const nomi=L.layerGroup().addTo(map);let LU=[];
fetch('luoghi.json').then(r=>r.json()).then(j=>{LU=j.luoghi||[];disponi()}).catch(()=>{});
function disponi(){nomi.clearLayers();const z=map.getZoom(),presi=[],b=map.getBounds().pad(0.1);
 const soglia=z<11?1:z<12?2:z<13?3:z<14?4:9;
 for(const [n,la,lo,pri,t] of LU){if(pri>soglia||!b.contains([la,lo]))continue;const p=map.latLngToContainerPoint([la,lo]);
  const cl=t==='p'?'p':(pri<=1?'c':''),w=(n.length*(cl==='c'?8.5:7))+8,hh=18,r=[p.x-w/2,p.y-hh/2,p.x+w/2,p.y+hh/2];
  if(presi.some(q=>!(r[2]<q[0]||r[0]>q[2]||r[3]<q[1]||r[1]>q[3])))continue;presi.push(r);
  nomi.addLayer(L.marker([la,lo],{interactive:false,keyboard:false,icon:L.divIcon({className:'',html:'<div class="nome '+cl+'">'+n+'</div>',iconSize:[0,0]})}))}}
map.on('zoomend moveend',disponi);
// ---- frecce delle onde (direzione verso cui vanno, lunghezza con l'altezza)
const oc=Q('oc'),ox=oc.getContext('2d');
function frecceOnde(){const r=window.devicePixelRatio||1;oc.width=innerWidth*r;oc.height=innerHeight*r;ox.clearRect(0,0,oc.width,oc.height);
 if(strato!=='onde'||!OD)return;const passo=56;ox.lineCap='round';
 for(let y=passo/2;y<innerHeight;y+=passo)for(let x=passo/2;x<innerWidth;x+=passo){const ll=map.containerPointToLatLng([x,y]),[fi,fj]=ij(ll.lat,ll.lng),i=Math.round(fi),j=Math.round(fj);
  if(i<0||j<0||i>=nx||j>=ny||!MAR[j*nx+i])continue;const w=onda(h,ll.lat,ll.lng);if(!w)continue;
  const a=(w.d+180)*Math.PI/180,L=(10+Math.min(14,w.h*7))*r,dx=Math.sin(a)*L/2,dy=-Math.cos(a)*L/2,X=x*r,Y=y*r;
  ox.strokeStyle='rgba(15,25,45,.8)';ox.lineWidth=2*r;ox.beginPath();ox.moveTo(X-dx,Y-dy);ox.lineTo(X+dx,Y+dy);
  const pa=a+Math.PI,hl=5*r;ox.moveTo(X+dx,Y+dy);ox.lineTo(X+dx+Math.sin(pa-0.5)*hl,Y+dy-Math.cos(pa-0.5)*hl);ox.moveTo(X+dx,Y+dy);ox.lineTo(X+dx+Math.sin(pa+0.5)*hl,Y+dy-Math.cos(pa+0.5)*hl);ox.stroke()}}
map.on('moveend zoomend',frecceOnde);map.on('movestart zoomstart',()=>ox.clearRect(0,0,oc.width,oc.height));addEventListener('resize',frecceOnde);
// ---- scie del vento
const pc=Q('pc'),px=pc.getContext('2d');let part=[],anim=null,fermo=false;
function flussoOn(){return flusso==null?(strato!=='pioggia'&&strato!=='onde'):flusso}
function misura(){const r=window.devicePixelRatio||1;pc.width=innerWidth*r;pc.height=innerHeight*r;part=[]}
function nuova(a){return{x:Math.random()*pc.width,y:Math.random()*pc.height,e:a?Math.floor(Math.random()*70):0}}
function passo(){anim=requestAnimationFrame(passo);if(fermo)return;const r=window.devicePixelRatio||1,w=pc.width,hh=pc.height,o=ora(h);
 if(!part.length){const n=Math.round(Math.min(2200,w*hh/(r*r)/110));for(let i=0;i<n;i++)part.push(nuova(true))}
 px.globalCompositeOperation='destination-in';px.fillStyle='rgba(0,0,0,0.92)';px.fillRect(0,0,w,hh);px.globalCompositeOperation='source-over';
 px.lineWidth=1.4*r;px.strokeStyle=strato==='pioggia'?'rgba(20,23,28,.65)':'rgba(255,255,255,.9)';px.beginPath();
 const kv=0.07*r;
 for(const p of part){const ll=map.containerPointToLatLng([p.x/r,p.y/r]),[fi,fj]=ij(ll.lat,ll.lng),u=campo(o.U,fi,fj),v=campo(o.W,fi,fj);
  if(u==null||p.e>70){Object.assign(p,nuova(false));continue}
  const dx=u*kv,dy=-v*kv;px.moveTo(p.x,p.y);px.lineTo(p.x+dx,p.y+dy);p.x+=dx;p.y+=dy;p.e++;
  if(p.x<0||p.y<0||p.x>w||p.y>hh||Math.abs(u)+Math.abs(v)<0.3)Object.assign(p,nuova(false))}
 px.stroke()}
function aggiornaFlusso(){const on=flussoOn();Q('flx').setAttribute('aria-pressed',on);
 if(!on){if(anim){cancelAnimationFrame(anim);anim=null}px.clearRect(0,0,pc.width,pc.height);return}if(!anim)anim=requestAnimationFrame(passo)}
map.on('movestart zoomstart',()=>{fermo=true;px.clearRect(0,0,pc.width,pc.height)});
map.on('moveend zoomend',()=>{fermo=false;part=[]});
addEventListener('resize',()=>{misura()});
document.addEventListener('visibilitychange',()=>{if(document.hidden&&anim){cancelAnimationFrame(anim);anim=null}else if(!document.hidden)aggiornaFlusso()});
// ---- punto toccato: adesso, tra 1 ora e tra 2 ore, accanto al dito
let mk=null;
function freccia(d){return '<svg viewBox="0 0 20 20"><path d="M10 2 L15 16 L10 13 L5 16 Z" fill="#fff" transform="rotate('+((d+180)%360)+' 10 10)"/></svg>'}
function valori(n,ll){const o=ora(n),[fi,fj]=ij(ll.lat,ll.lng),s=campo(o.S,fi,fj);if(s==null)return null;
 const u=campo(o.U,fi,fj),w=campo(o.W,fi,fj),d=(Math.atan2(-u,-w)*180/Math.PI+360)%360,i=Math.round(fi),j=Math.round(fj);
 const mare=MAR[Math.max(0,Math.min(ny-1,j))*nx+Math.max(0,Math.min(nx-1,i))];
 return{s:s,g:campo(o.G,fi,fj),d:d,p:pioggia(o.m,i,j),t:temporale(o.m,i,j),mare:mare,w:mare?onda(n,ll.lat,ll.lng):null}}
function bolla(){if(!sel){if(mk){map.removeLayer(mk);mk=null}return}
 const col=[];for(const [dh,et] of [[0,'ora'],[1,'+1 h'],[2,'+2 h']]){const n=Math.min(NH-1,h+dh),v=valori(n,sel);if(!v)continue;
  const val=strato==='raff'?v.g:v.s,on=v.w?'<small class="w">≈ '+num(v.w.h,1)+' m '+freccia(v.w.d)+'</small>':'';
  col.push('<div><em>'+(dh?et:soloOra(ORE[n].t))+'</em><b>'+num(val,0)+'</b><small>'+freccia(v.d)+String(Math.round(v.d)).padStart(3,'0')+'°</small>'+on+'</div>')}
 if(!col.length){sel=null;bolla();return}
 const p=map.latLngToContainerPoint(sel),cls='bolla'+(p.x+215>innerWidth?' sx':'')+(p.y<130?' giu':'');
 const html='<div class="pt"><i></i><div class="'+cls+'">'+col.join('')+'</div></div>';
 if(!mk)mk=L.marker(sel,{interactive:false,keyboard:false,icon:L.divIcon({className:'',html:html,iconSize:[0,0]})}).addTo(map);else{mk.setLatLng(sel);mk.setIcon(L.divIcon({className:'',html:html,iconSize:[0,0]}))}}
map.on('click',e=>{if(sel){sel=null}else{const v=valori(h,e.latlng);sel=v?e.latlng:null}bolla();dettagli()});
map.on('zoomend',()=>{if(sel)bolla()});
// ---- cassetto
function giorni(){let s='';for(let n=0;n<NH;n++){const t=new Date(ORE[n].t+':00Z'),hr=+new Intl.DateTimeFormat('en-GB',{hour:'numeric',hourCycle:'h23',timeZone:'Europe/Rome'}).format(t),x=(n/(NH-1)*100).toFixed(2);
 if(hr===0&&n>0)s+='<i style="left:'+x+'%"></i>';if(hr===12)s+='<em style="left:'+x+'%">'+new Intl.DateTimeFormat('it',{weekday:'short',timeZone:'Europe/Rome'}).format(t)+'</em>'}Q('gg').innerHTML=s}
function legenda(){if(strato==='onde'){Q('sc').style.gridTemplateColumns='repeat(8,1fr)';Q('sc').innerHTML=SO.map(s=>'<div><i style="background:'+rgb(s[1])+'"></i>'+num(s[0],s[0]%1?(s[0]<1?2:1):0)+'</div>').join('');Q('un').textContent='onda, metri'+(OD?' · '+OD.modello:'');return}
 if(strato==='pioggia'){Q('sc').style.gridTemplateColumns='repeat(6,1fr)';Q('sc').innerHTML=SP.map(s=>'<div><i style="background:'+rgb(s[1])+'"></i>'+num(s[0],s[0]<1?1:0)+'</div>').join('')+'<div><i style="background:rgb(150,60,190)"></i>⚡</div>';Q('un').textContent='mm/h'}
 else{Q('sc').style.gridTemplateColumns='repeat(8,1fr)';Q('sc').innerHTML=WS.map(s=>'<div><i style="background:'+rgb(sfuma(WS,s[0]+2))+'"></i>'+s[0]+'</div>').join('');Q('un').textContent=strato==='raff'?'raffiche, nodi':'vento, nodi'}}
function dettagli(){const m=ORE[h];
 const reg=m.a2==null?'':m.a2>=1?'Aria rimescolata: il vento scavalca i monti.':m.a2>=0.25?'Aria poco stabile: il vento in parte scavalca, in parte aggira i monti.':'Aria stabile: il vento aggira i monti e lascia ridossi lunghi.';
 Q('aria').textContent=reg+(m.q?' A 750 m: '+m.q[0]+' nodi da '+ROSA[Math.round(m.q[1]/22.5)%16]+'.':'');
 if(!sel){Q('punto').innerHTML='<p class="vuoto">Tocca la carta in un punto: accanto al dito compaiono vento e direzione adesso, tra 1 e tra 2 ore. Qui sotto, le prossime ore.</p>';return}
 let r='';for(let dh=0;dh<8;dh++){const n=h+dh;if(n>=NH)break;const v=valori(n,sel);if(!v)break;
  r+='<tr><td>'+soloOra(ORE[n].t)+'</td><td><b>'+num(v.s,0)+'</b></td><td>'+num(v.g,0)+'</td><td>'+ROSA[Math.round(v.d/22.5)%16]+' '+String(Math.round(v.d)).padStart(3,'0')+'°</td><td>'+forza(v.s)+'</td><td>'+(v.t>0.15?'⚡':(v.p>=0.1?num(v.p,1):'–'))+'</td><td>'+(v.w?num(v.w.h,1)+' m'+(v.w.p?' '+num(v.w.p,0)+'s':''):'–')+'</td></tr>'}
 const v0=valori(h,sel);
 Q('punto').innerHTML='<p><b>'+sel.lat.toFixed(4)+'° N, '+sel.lng.toFixed(4)+'° E</b> · '+(v0&&v0.mare?'mare':'terra')+(v0?' · '+NOMI[Math.round(v0.d/45)%8]:'')+'</p><table class="tab"><tr><th>ora</th><th>nodi</th><th>raffica</th><th>da</th><th>Bft</th><th>pioggia</th><th>onda</th></tr>'+r+'</table>'}
function tutto(){Q('tl').textContent=fmtOra(ORE[h].t);immagine();bolla();dettagli();legenda();frecceOnde()}
document.querySelectorAll('.strati button[data-v]').forEach(b=>b.addEventListener('click',()=>{strato=b.dataset.v;document.querySelectorAll('.strati button[data-v]').forEach(x=>x.setAttribute('aria-pressed',x===b));tutto();aggiornaFlusso()}));
Q('flx').addEventListener('click',()=>{flusso=!flussoOn();aggiornaFlusso()});
const cur=Q('cur');cur.max=NH-1;cur.value=h;cur.addEventListener('input',()=>{h=+cur.value;tutto()});
const vai=d=>{h=Math.max(0,Math.min(NH-1,h+d));cur.value=h;tutto()};Q('prima').onclick=()=>vai(-1);Q('dopo').onclick=()=>vai(1);
Q('play').onclick=()=>{if(giro){clearInterval(giro);giro=null;Q('play').classList.remove('on');Q('play').textContent='▶';return}
 Q('play').classList.add('on');Q('play').textContent='❚❚';giro=setInterval(()=>{h=(h+1)%NH;cur.value=h;tutto()},1100)};
// cassetto: tocco sulla maniglia o trascinamento verso l'alto
const cas=Q('cas');let aperto=false;
function chiuso(){return Math.max(0,cas.offsetHeight-Q('man').offsetHeight-Q('base').offsetHeight-14)}
function posa(){cas.classList.toggle('aperto',aperto);cas.style.transform=aperto?'translateY(0)':'translateY('+chiuso()+'px)';cas.scrollTop=0;
 document.documentElement.style.setProperty('--cassetto',(Q('base').offsetHeight+24)+'px')}
Q('man').onclick=()=>{aperto=!aperto;posa()};Q('brand').onclick=()=>{aperto=true;posa()};
let y0=null;cas.addEventListener('touchstart',e=>{y0=e.touches[0].clientY},{passive:true});
cas.addEventListener('touchend',e=>{if(y0==null)return;const dy=e.changedTouches[0].clientY-y0;if(!aperto&&dy<-30){aperto=true;posa()}else if(aperto&&dy>40&&cas.scrollTop<=0){aperto=false;posa()}y0=null},{passive:true});
addEventListener('resize',posa);
// dati vecchi
{const vec=(Date.now()-new Date(D.generato).getTime())/3600e3;if(vec>20)Q('vecchio').textContent='Attenzione: la carta non si aggiorna da '+Math.floor(vec)+' ore.'}
let ap=Date.now();document.addEventListener('visibilitychange',()=>{if(!document.hidden&&Date.now()-ap>60*60e3)location.reload()});
misura();giorni();tutto();aggiornaFlusso();posa();setTimeout(()=>{posa();cas.classList.add('anima')},300);
})();
"""


def pagina(dati):
    import datetime as dt
    from zoneinfo import ZoneInfo
    gen = dt.datetime.fromisoformat(dati["generato"]).astimezone(ZoneInfo("Europe/Rome"))
    return f"""<!DOCTYPE html>
<html lang="it"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="robots" content="noindex,nofollow"><title>Pistrice Sailing · Weather Lab</title>
<link rel="manifest" href="manifest.webmanifest"><link rel="icon" type="image/png" href="icona_192.png"><link rel="apple-touch-icon" href="icona_180.png">
<meta name="theme-color" content="#9c1a24"><meta name="mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Pistrice Lab"><meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<style>{_leggi('web', 'leaflet.css')}{fonti()}{CSS}</style></head><body>
<div id="map"></div><canvas id="oc"></canvas><canvas id="pc"></canvas>
<div class="brand" id="brand"><img src="logo.png" alt="Pistrice Sailing"><div><b>Pistrice Sailing</b><small>Weather Lab</small><em>I like the shape of the sail</em><em class="cr">Crafted by Giù Ferrarella</em></div></div>
<div class="strati"><button type="button" data-v="vento" aria-pressed="true">Vento</button><button type="button" data-v="raff" aria-pressed="false">Raffiche</button><button type="button" data-v="pioggia" aria-pressed="false">Pioggia</button><button type="button" data-v="onde" aria-pressed="false">Onde</button><button type="button" id="flx" aria-pressed="true" title="Scie del vento">≋ scie</button></div>
<div id="cas"><button type="button" class="maniglia" id="man" aria-label="apri il cassetto"><span></span></button>
<div id="base"><div class="ora"><b id="tl"></b><span id="un"></span></div>
<div class="riga"><button type="button" class="tb" id="prima" aria-label="ora prima">‹</button><button type="button" class="tb" id="play" aria-label="scorri">▶</button><button type="button" class="tb" id="dopo" aria-label="ora dopo">›</button>
<div class="cursore"><input type="range" id="cur" min="0" value="0" aria-label="ora"><div id="gg"></div></div></div>
<div class="scala" id="sc"></div></div>
<div class="altro"><h3>Nel punto</h3><div id="punto"></div>
<h3>L'aria adesso</h3><p id="aria"></p>
<h3>Informazioni</h3>
<p>Previsione ad alta risoluzione di vento, raffiche, pioggia e onde sui golfi di Palermo e Mondello, prodotta da Pistrice Sailing Weather Lab. Vento e raffiche a 10 m, in nodi; onde come altezza significativa, direzione e periodo.</p>
<p>Si allarga con due dita. Le scie bianche mostrano il flusso e si spengono con «≋ scie». Un tocco sulla carta mostra i valori del punto, un secondo tocco li toglie.</p>
<p>Aggiornata il {gen:%d/%m alle %H:%M}, due volte al giorno. Previsione indicativa: non sostituisce i bollettini ufficiali. <span id="vecchio" style="color:#9a5b00;font-weight:600"></span></p>
<p style="font-size:11.5px;color:#6b6e74">Fonti dei dati: ECMWF, ICON-2I e modelli del mare via Open-Meteo.com (CC BY 4.0); Copernicus Sentinel-1; Copernicus DEM GLO-30; ESA WorldCover 2021 (CC BY 4.0); © OpenStreetMap contributors (ODbL); Leaflet (BSD).</p>
<div class="firma"><img src="logo.png" alt=""><p><b>Pistrice Sailing · Weather Lab</b><br><i>I like the shape of the sail</i><br>Crafted by Giù Ferrarella</p></div>
</div></div>
<script>{_leggi('web', 'leaflet.js')}</script>
<script>{JS.replace("__DATI__", json.dumps(dati, separators=(",", ":"), ensure_ascii=False))}</script></body></html>"""
