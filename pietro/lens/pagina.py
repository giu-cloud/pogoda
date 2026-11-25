"""La carta del vento per Pietro: un solo file HTML, ore da scorrere, vento con le scie animate, raffiche, pioggia e
temporali, viste sui golfi e sulla sua casa. Nessun riferimento a chi l'ha fatta."""
import json
import os

QUI = os.path.dirname(os.path.abspath(__file__))

CSS = """
:root{color-scheme:light;--bg:#f2f1ec;--card:#fdfdfb;--ink:#14171c;--ink2:#5a5d63;--line:#e2e0d8;--acc:#1f5fa8}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.45 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
main{max-width:860px;margin:0 auto;padding:18px 12px 40px}
header{margin:0 2px 14px}h1{font-family:'Garamond Stara',Georgia,serif;font-weight:500;font-size:2.3rem;letter-spacing:.5px;margin:0;line-height:1.1}
.motto{font-family:'Garamond Stara',Georgia,serif;font-style:italic;font-size:1.2rem;color:#3d4450;margin:2px 0 6px}
.agg{font-size:.8rem;color:var(--ink2);margin:0}
.card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:10px;margin:0 0 12px;box-shadow:0 1px 2px rgba(0,0,0,.04),0 6px 18px rgba(0,0,0,.05)}
.riga{display:flex;gap:6px;overflow-x:auto;padding-bottom:8px;scrollbar-width:none}.riga::-webkit-scrollbar{display:none}
button{font:inherit;font-size:.84rem;border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:999px;padding:6px 12px;cursor:pointer;white-space:nowrap}
button[aria-pressed=true]{background:var(--ink);color:#fff;border-color:var(--ink)}
.mw{position:relative;border-radius:12px;overflow:hidden;box-shadow:inset 0 0 0 1px rgba(0,0,0,.12);background:#cfe3ec}
.mw canvas{display:block;width:100%}#p{position:absolute;inset:0;height:100%;pointer-events:none}
#flx{position:absolute;right:8px;bottom:10px;width:38px;height:38px;padding:0;border-radius:50%;border:1px solid rgba(0,0,0,.15);background:rgba(255,255,255,.9);font:700 18px/1 system-ui;color:#333}
#flx[aria-pressed=true]{background:#1e2a44;color:#fff}
.nord{position:absolute;top:8px;right:9px;width:20px;height:27px;pointer-events:none;filter:drop-shadow(0 1px 1px rgba(0,0,0,.25))}
.sb{position:absolute;left:10px;bottom:10px;pointer-events:none}.sb span{display:block;height:5px;border:1.5px solid #222;border-top:0;background:linear-gradient(90deg,#222 50%,#fff 50%);box-shadow:0 0 0 1.5px rgba(255,255,255,.8)}
.sb b{font:600 11px system-ui,sans-serif;color:#222;text-shadow:0 0 3px #fff,0 0 3px #fff}
.tempo{display:flex;align-items:center;gap:6px;margin:12px 0 0}
.tb{width:34px;height:34px;padding:0;border-radius:50%;flex:none;display:grid;place-items:center}
#play{width:40px;height:40px;background:var(--ink);color:#fff;border-color:var(--ink)}#play.on{background:var(--acc);border-color:var(--acc)}
.cursore{flex:1;min-width:0;position:relative;padding-bottom:16px}.cursore input{width:100%;accent-color:var(--acc);margin:0}
#gg{position:absolute;left:8px;right:8px;bottom:0;height:16px;font-size:.68rem;color:var(--ink2)}
#gg i{position:absolute;top:-14px;width:1px;height:8px;background:var(--line)}#gg em{position:absolute;transform:translateX(-50%);font-style:normal}
.tl{font-variant-numeric:tabular-nums;font-weight:650;font-size:.95rem;text-align:center;margin:4px 0 2px}
.leg{margin-top:8px;padding:10px 12px;border-radius:12px;background:#f6f5f1;border:1px solid var(--line)}
.leg .lt{font-weight:650;font-size:.9rem}.leg p{margin:6px 0 0;font-size:.82rem;line-height:1.4;color:var(--ink2)}
.bande{display:grid;grid-template-columns:repeat(9,1fr);gap:2px;margin:6px 0 2px;text-align:center;font-size:.7rem;line-height:1.2;font-variant-numeric:tabular-nums}
.bande i{display:block;height:10px;border-radius:3px;margin-bottom:2px;box-shadow:inset 0 0 0 1px rgba(0,0,0,.06)}.bande small{display:block;color:var(--ink2);font-size:.64rem}
.info{margin-top:8px}.ig{display:grid;grid-template-columns:auto 1fr;gap:3px 12px;font-size:.88rem;padding:10px 12px;border:1px solid var(--line);border-radius:12px}
.ig span{color:var(--ink2)}.ig b{font-weight:600;font-variant-numeric:tabular-nums}.vuoto{font-size:.85rem;color:var(--ink2);margin:0}
.note{font-size:.8rem;color:var(--ink2);line-height:1.45}.note p{margin:.4em 0}
"""

JS = r"""
(async function(){
const D=__DATI__,Q=id=>document.getElementById(id);
function dec(b){const s=atob(b),a=new Uint8Array(s.length);for(let i=0;i<s.length;i++)a[i]=s.charCodeAt(i);return a}
let P;
try{P=JSON.parse(await new Response(new Blob([dec(D.gz)]).stream().pipeThrough(new DecompressionStream('gzip'))).text())}
catch(e){Q('info').innerHTML='<p class="vuoto">Questo browser è troppo vecchio per aprire la carta: aggiornalo e riprova.</p>';return}
const ORE=P.ore,nx=D.nx,ny=D.ny,KB=D.kb,N=nx*ny;
const MAR=new Uint8Array(N);{const m=dec(P.mare);for(let k=0;k<N;k++)MAR[k]=(m[k>>3]>>(7-(k&7)))&1}
// valore di un campo del modello (griglia grossa su tutto il dominio) nel punto i,j della carta, bilineare
function bl(a,i,j){const gx=(i+D.m+.5)/D.NX*(D.gx-1),gy=(j+D.m+.5)/D.NY*(D.gy-1),x0=Math.min(D.gx-2,Math.floor(gx)),y0=Math.min(D.gy-2,Math.floor(gy)),wx=gx-x0,wy=gy-y0,q=y0*D.gx+x0;
 return(a[q]*(1-wx)+a[q+1]*wx)*(1-wy)+(a[q+D.gx]*(1-wx)+a[q+D.gx+1]*wx)*wy}
function ora(n){const o=ORE[n];if(o.S)return o;
 const V=dec(o.v),Dd=dec(o.d),G=o.g?dec(o.g):V;
 o.S=new Float32Array(N);o.G=new Float32Array(N);o.U=new Float32Array(N);o.W=new Float32Array(N);
 for(let k=0;k<N;k++){const s=V[k]/4,a=Dd[k]*Math.PI/128;o.S[k]=s;o.G[k]=G[k]/4;o.U[k]=-s*Math.sin(a);o.W[k]=-s*Math.cos(a)}
 return o}
// scala del vento in nodi (come in Shift) e forza Beaufort
const WS=[[0,[150,190,228]],[5,[76,175,80]],[10,[192,202,51]],[15,[255,179,0]],[20,[255,112,67]],[25,[229,57,53]],[32,[142,36,170]],[40,[90,20,110]]];
function sfuma(S,v){if(v<=S[0][0])return S[0][1];for(let i=1;i<S.length;i++)if(v<=S[i][0]){const a=S[i-1],b=S[i],t=(v-a[0])/(b[0]-a[0]);return[a[1][0]+(b[1][0]-a[1][0])*t,a[1][1]+(b[1][1]-a[1][1])*t,a[1][2]+(b[1][2]-a[1][2])*t]}return S[S.length-1][1]}
const SP=[[0.1,[190,215,245]],[0.5,[120,170,235]],[1,[60,130,220]],[3,[25,85,190]],[8,[15,45,140]]];
const rgb=c=>'rgb('+Math.round(c[0])+','+Math.round(c[1])+','+Math.round(c[2])+')';
const LIM=[1,3.5,6.5,10.5,16.5,21.5,27.5,33.5,40.5],BF=['0','1','2','3','4','5','6','7','8','9+'];
function forza(v){let b=0;while(b<LIM.length&&v>=LIM[b])b++;return BF[b]}
const num=(x,n)=>x.toFixed(n||0).replace('.',',').replace('-','−');
const ROSA=['N','NNE','NE','ENE','E','ESE','SE','SSE','S','SSO','SO','OSO','O','ONO','NO','NNO'];
const NOMI=['tramontana','grecale','levante','scirocco','ostro','libeccio','ponente','maestrale'];
const rosa=d=>ROSA[Math.round(d/22.5)%16],nome=d=>NOMI[Math.round(d/45)%8];
const VISTE=Object.keys(D.viste);
let h=0,strato='vento',vista=VISTE.includes('Due golfi')?'Due golfi':VISTE[0],sel=null,giro=null,flusso=null;
const cv=Q('c'),cx=cv.getContext('2d'),pc=Q('p'),px=pc.getContext('2d'),img=new Image(),off=document.createElement('canvas');
const casa=D.casa?[(D.casa[1]-D.interno[2])/(D.interno[3]-D.interno[2])*nx,(D.interno[1]-D.casa[0])/(D.interno[1]-D.interno[0])*ny]:null;
function pioggia(o,i,j){return o.pr?Math.max(0,bl(o.pr,i,j)):0}
function temporale(o,i,j){if(!o.ca)return 0;const c=bl(o.ca,i,j),p=pioggia(o,i,j);return Math.max(0,Math.min(1,(c-300)/700))*Math.min(1,0.3+p/0.6)}
function colore(o,k,i,j){
 if(strato==='vento'){const c=sfuma(WS,o.S[k]);return[c[0],c[1],c[2],140]}
 if(strato==='raff'){const c=sfuma(WS,o.G[k]);return[c[0],c[1],c[2],150]}
 const p=pioggia(o,i,j),t=temporale(o,i,j);
 if(t>0.15)return[150,60,190,Math.min(210,60+150*t)];
 if(p>=0.1){const c=sfuma(SP,p);return[c[0],c[1],c[2],Math.min(220,90+p*60)]}
 return[0,0,0,0]}
function sovrapposizione(o,v){const x0=v[0],y0=v[1],sw=v[2],sh=v[3],KO=Math.max(1,Math.min(4,Math.floor(800/sw))),w=sw*KO,hh=sh*KO;
 off.width=w;off.height=hh;const oc=off.getContext('2d'),im=oc.createImageData(w,hh),d=im.data;
 // colori calcolati sulla griglia della vista, poi resi morbidi dal ridimensionamento
 const C=new Uint8ClampedArray(sw*sh*4);for(let j=0;j<sh;j++)for(let i=0;i<sw;i++){const c=colore(o,(y0+j)*nx+x0+i,x0+i,y0+j),q=4*(j*sw+i);C[q]=c[0];C[q+1]=c[1];C[q+2]=c[2];C[q+3]=c[3]}
 const t=document.createElement('canvas');t.width=sw;t.height=sh;t.getContext('2d').putImageData(new ImageData(C,sw,sh),0,0);
 oc.imageSmoothingEnabled=true;oc.imageSmoothingQuality='high';oc.drawImage(t,0,0,w,hh);return off}
__ETICHETTE__
function scalaGrafica(v){const km=v[2]*D.dx/1000,pas=[0.5,1,2,5,10];let s=pas[0];for(const p of pas)if(p<=km/5)s=p;
 Q('sb').innerHTML='<span style="width:'+(s/km*cv.clientWidth).toFixed(0)+'px"></span><b>'+num(s,s<1?1:0)+' km</b>'}
function disegna(){const v=D.viste[vista],x0=v[0],y0=v[1],sw=v[2],sh=v[3],o=ora(h);
 const css=cv.clientWidth,dpr=Math.min(3,window.devicePixelRatio||1),W=Math.round(css*dpr),H=Math.round(css*sh/sw*dpr);
 if(cv.width!==W||cv.height!==H){cv.width=W;cv.height=H;pc.width=W;pc.height=H;part=[]}
 cx.lineJoin='round';cx.imageSmoothingEnabled=true;cx.imageSmoothingQuality='high';cx.drawImage(img,x0*KB,y0*KB,sw*KB,sh*KB,0,0,W,H);
 cx.drawImage(sovrapposizione(o,v),0,0,W,H);
 const pxs=W/sw;etichette(v,pxs,W,H,dpr);
 if(casa){const X=(casa[0]-x0)*pxs,Y=(casa[1]-y0)*pxs;if(X>0&&Y>0&&X<W&&Y<H){
  cx.beginPath();cx.arc(X,Y,5.5*dpr,0,7);cx.fillStyle='#c0392b';cx.fill();cx.lineWidth=2.5*dpr;cx.strokeStyle='#fffdf5';cx.stroke();
  cx.font='italic 500 '+(15*dpr)+"px 'Garamond Stara',Georgia,serif";cx.textBaseline='middle';cx.lineWidth=3.5*dpr;cx.strokeStyle='rgba(255,253,245,.95)';
  cx.strokeText("Pietro's Place",X+9*dpr,Y-1*dpr);cx.fillStyle='#7d1f16';cx.fillText("Pietro's Place",X+9*dpr,Y-1*dpr)}}
 if(sel!=null){const si=sel%nx-x0,sj=Math.floor(sel/nx)-y0;if(si>=0&&sj>=0&&si<sw&&sj<sh){const X=(si+.5)*pxs,Y=(sj+.5)*pxs;
  cx.lineWidth=4*dpr;cx.strokeStyle='#fffdf5';cx.beginPath();cx.arc(X,Y,9*dpr,0,7);cx.stroke();cx.lineWidth=2*dpr;cx.strokeStyle='#14171c';cx.stroke()}}
 scalaGrafica(v);testi();aggiornaFlusso()}
// scie del vento: particelle che seguono il vento calcolato, sopra la carta
let part=[],anim=null;
function flussoAttivo(){return flusso==null?strato!=='pioggia':flusso}
function aggiornaFlusso(){const on=flussoAttivo();Q('flx').setAttribute('aria-pressed',on);
 if(!on){if(anim){cancelAnimationFrame(anim);anim=null}px.clearRect(0,0,pc.width,pc.height);return}
 if(!part.length){const n=Math.round(Math.min(1500,pc.width*pc.height/((window.devicePixelRatio||1)**2)/80));for(let i=0;i<n;i++)part.push(nuova(true))}
 if(!anim)anim=requestAnimationFrame(passo)}
function nuova(a){return{x:Math.random()*pc.width,y:Math.random()*pc.height,e:a?Math.floor(Math.random()*80):0}}
function passo(){const v=D.viste[vista],o=ora(h),w=pc.width,hh=pc.height,dpr=window.devicePixelRatio||1;
 px.globalCompositeOperation='destination-in';px.fillStyle='rgba(0,0,0,0.92)';px.fillRect(0,0,w,hh);px.globalCompositeOperation='source-over';
 px.lineWidth=1.3*dpr;px.strokeStyle=strato==='pioggia'?'rgba(20,23,28,.7)':'rgba(255,255,255,.9)';px.beginPath();
 const kv=0.05*w/400*Math.min(1,180/v[2]+0.35);
 for(const p of part){const i=Math.min(v[2]-1,Math.max(0,Math.floor(p.x/w*v[2]))),j=Math.min(v[3]-1,Math.max(0,Math.floor(p.y/hh*v[3]))),k=(v[1]+j)*nx+v[0]+i;
  const dx=o.U[k]*kv,dy=-o.W[k]*kv;if(Math.abs(dx)+Math.abs(dy)>0.02){px.moveTo(p.x,p.y);px.lineTo(p.x+dx,p.y+dy)}
  p.x+=dx;p.y+=dy;p.e++;if(p.e>80||p.x<0||p.y<0||p.x>w||p.y>hh||o.S[k]<0.4)Object.assign(p,nuova(false))}
 px.stroke();anim=requestAnimationFrame(passo)}
document.addEventListener('visibilitychange',()=>{if(document.hidden&&anim){cancelAnimationFrame(anim);anim=null}else if(!document.hidden)aggiornaFlusso()});
function giorni(){let s='';for(let n=0;n<ORE.length;n++){const t=new Date(ORE[n].t+':00Z'),hr=+new Intl.DateTimeFormat('en-GB',{hour:'numeric',hourCycle:'h23',timeZone:'Europe/Rome'}).format(t);
  const x=(n/(ORE.length-1)*100).toFixed(2);if(hr===0&&n>0)s+='<i style="left:'+x+'%"></i>';if(hr===12)s+='<em style="left:'+x+'%">'+new Intl.DateTimeFormat('it',{weekday:'short',timeZone:'Europe/Rome'}).format(t)+'</em>'}
 Q('gg').innerHTML=s}
function testi(){const o=ora(h),t=new Date(o.t+':00Z');
 Q('tl').textContent=new Intl.DateTimeFormat('it',{weekday:'long',day:'numeric',hour:'2-digit',minute:'2-digit',timeZone:'Europe/Rome'}).format(t);
 const reg=o.a2>=1?"Aria rimescolata: il vento scavalca i monti.":o.a2>=0.25?"Aria poco stabile: il vento in parte scavalca, in parte aggira i monti.":"Aria stabile: il vento aggira i monti e lascia ridossi lunghi.";
 if(strato==='pioggia'){Q('leg').innerHTML='<div class="lt">Pioggia e temporali</div><div class="bande">'+SP.map(s=>'<div><i style="background:'+rgb(s[1])+'"></i>'+num(s[0],s[0]<1?1:0)+'</div>').join('')+'<div><i style="background:rgb(150,60,190)"></i>⚡</div></div><p>Pioggia in mm all\'ora. Viola: possibili temporali, dove c\'è energia nell\'aria (CAPE) e piove.</p>'}
 else{const b=[[0,'calma'],[5,'debole'],[10,'moderato'],[15,'teso'],[20,'fresco'],[25,'forte'],[32,'burrasca'],[40,'']];
  Q('leg').innerHTML='<div class="lt">'+(strato==='vento'?'Vento a 10 m':'Raffiche')+' · nodi</div><div class="bande" style="grid-template-columns:repeat(7,1fr)">'+b.slice(0,7).map(s=>'<div><i style="background:'+rgb(sfuma(WS,s[0]+2.5))+'"></i>'+s[0]+'+<small>'+s[1]+'</small></div>').join('')+'</div><p>'+reg+(o.q?' A 750 m: '+o.q[0]+' nodi da '+rosa(o.q[1])+'.':'')+(strato==='raff'?' Le raffiche sono più forti dove il vento esce da terra o dalla scia di un monte.':'')+'</p>'}
 if(sel==null){Q('info').innerHTML='<p class="vuoto">Tocca la carta: nel punto compaiono vento, raffiche e pioggia.</p>';return}
 const i=sel%nx,j=Math.floor(sel/nx),u=o.U[sel],w=o.W[sel],d=(Math.atan2(-u,-w)*180/Math.PI+360)%360,p=pioggia(o,i,j),tt=temporale(o,i,j);
 Q('info').innerHTML='<div class="ig"><span>Vento</span><b>'+num(o.S[sel],0)+' nodi · forza '+forza(o.S[sel])+'</b><span>Da</span><b>'+rosa(d)+' · '+nome(d)+' ('+Math.round(d)+'°)</b><span>Raffiche</span><b>'+num(o.G[sel],0)+' nodi</b><span>Pioggia</span><b>'+(p>=0.1?num(p,1)+' mm/h':'niente')+(tt>0.15?' · temporale possibile':'')+'</b><span>Dove</span><b>'+(MAR[sel]?'mare':'terra')+'</b></div>'}
function premi(g,v){document.querySelectorAll('#'+g+' button[data-v]').forEach(b=>b.setAttribute('aria-pressed',b.dataset.v===v))}
Q('viste').innerHTML=VISTE.map(v=>'<button type="button" data-v="'+v+'">'+v+'</button>').join('');
Q('viste').addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;vista=b.dataset.v;premi('viste',vista);part=[];sel=null;disegna()});
Q('strati').addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;strato=b.dataset.v;premi('strati',strato);disegna()});
Q('flx').addEventListener('click',()=>{flusso=!flussoAttivo();aggiornaFlusso()});
Q('cur').max=ORE.length-1;Q('cur').addEventListener('input',e=>{h=+e.target.value;disegna()});
function vai(d){h=Math.max(0,Math.min(ORE.length-1,h+d));Q('cur').value=h;disegna()}
Q('prima').addEventListener('click',()=>vai(-1));Q('dopo').addEventListener('click',()=>vai(1));
Q('play').addEventListener('click',()=>{if(giro){clearInterval(giro);giro=null;Q('play').classList.remove('on');Q('play').textContent='▶';return}
 Q('play').classList.add('on');Q('play').textContent='❚❚';giro=setInterval(()=>{h=(h+1)%ORE.length;Q('cur').value=h;disegna()},900)});
cv.addEventListener('click',e=>{const r=cv.getBoundingClientRect(),v=D.viste[vista],i=Math.min(v[2]-1,Math.max(0,Math.floor((e.clientX-r.left)/r.width*v[2]))),j=Math.min(v[3]-1,Math.max(0,Math.floor((e.clientY-r.top)/r.height*v[3])));sel=(v[1]+j)*nx+v[0]+i;disegna()});
window.addEventListener('resize',()=>{part=[];disegna()});
premi('viste',vista);premi('strati',strato);giorni();
{const ore_=(Date.now()-new Date(D.generato).getTime())/3600e3;if(ore_>20)Q('vecchio').textContent='Attenzione: la carta non si aggiorna da '+Math.floor(ore_)+' ore.'}
let ap=Date.now();document.addEventListener('visibilitychange',()=>{if(!document.hidden&&Date.now()-ap>60*60e3)location.reload()});
img.onload=disegna;img.src=Q('base').src;
})();
"""


def fonti():
    import base64
    cart = os.path.join(QUI, "fonti")
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


ETICHETTE = open(os.path.join(QUI, "etichette.js"), encoding="utf-8").read()


def pagina(dati, base, mime="image/webp"):
    import datetime as dt
    from zoneinfo import ZoneInfo
    gen = dt.datetime.fromisoformat(dati["generato"]).astimezone(ZoneInfo("Europe/Rome"))
    modello = dati.get("nome_modello") or dati["modello"]
    l2 = " e corretto con le misure del radar satellitare sul mare" if dati.get("lens2") else ""
    nord = ('<svg class="nord" viewBox="0 0 26 34"><path d="M13 2L20 22L13 18L6 22Z" fill="#222" stroke="#fff" stroke-width="1.5" stroke-linejoin="round"/>'
            '<text x="13" y="32" text-anchor="middle" style="font:700 10px system-ui;fill:#222;stroke:#fff;stroke-width:3px;paint-order:stroke">N</text></svg>')
    return f"""<!DOCTYPE html>
<html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow"><title>Pietro</title>
<link rel="manifest" href="manifest.webmanifest"><link rel="icon" type="image/png" href="icona_192.png"><link rel="apple-touch-icon" href="icona_180.png">
<meta name="theme-color" content="#1f5fa8"><meta name="mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-title" content="Pietro">
<style>{fonti()}{CSS}</style></head><body><main>
<header><h1>Pietro</h1><p class="motto">«Mi piace la forma della vela»</p>
<p class="agg">Vento sui golfi di Palermo e Mondello · aggiornato {gen:%d/%m alle %H:%M}</p><p class="agg" id="vecchio" style="color:#9a5b00;font-weight:600"></p></header>
<div class="card">
<div class="riga" id="viste"></div>
<div class="riga" id="strati"><button type="button" data-v="vento">Vento</button><button type="button" data-v="raff">Raffiche</button><button type="button" data-v="pioggia">Pioggia e temporali</button></div>
<div class="mw"><canvas id="c" width="600" height="600"></canvas><canvas id="p"></canvas>{nord}<div class="sb" id="sb"></div><button type="button" id="flx" aria-pressed="true" title="Scie del vento">≋</button></div>
<div class="tempo"><button type="button" class="tb" id="prima" aria-label="ora prima">‹</button><button type="button" class="tb" id="play" aria-label="scorri">▶</button><button type="button" class="tb" id="dopo" aria-label="ora dopo">›</button>
<div class="cursore"><input type="range" id="cur" min="0" value="0" aria-label="ora"><div id="gg"></div></div></div>
<div class="tl" id="tl"></div><div class="leg" id="leg"></div><div class="info" id="info"></div></div>
<div class="card note"><p>Vento e raffiche a 10 m, in nodi, quadretti di {dati['dx']:.0f} m. Il vento di {modello} è ricalcolato sul rilievo vero{l2}: si vedono ridossi, accelerazioni e il vento che si incanala tra i monti. Le scie bianche mostrano il flusso. Pioggia e temporali vengono da ICON-2I.</p>
<p>Fonti: ECMWF e ICON-2I via Open-Meteo.com (CC BY 4.0); radar Sentinel-1, Copernicus; rilievo Copernicus DEM GLO-30; copertura del suolo ESA WorldCover 2021 (CC BY 4.0); nomi © OpenStreetMap (ODbL).</p></div>
<img id="base" alt="" hidden src="data:{mime};base64,{base}">
</main><script>{JS.replace("__ETICHETTE__", ETICHETTE).replace("__DATI__", json.dumps(dati, separators=(",", ":"), ensure_ascii=False))}</script></body></html>"""
