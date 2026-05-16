import {sessionsAPI} from './api.js';
let _t=null;
export async function renderQR(sessionId,canvas,labelEl,expiryEl){async function draw(){try{const d=await sessionsAPI.qr(sessionId);const p=JSON.stringify({session_id:sessionId,token:d.token,ts:Date.now()});QRCode.toCanvas(canvas,p,{width:240,margin:2,color:{dark:'#ffffff',light:'#1c1b19'},errorCorrectionLevel:'M'});if(labelEl)labelEl.textContent=d.course_name||`Session ${sessionId}`;if(expiryEl)expiryEl.textContent=`Expires ${new Date(d.expires_at).toLocaleTimeString()}`;}catch{const p=JSON.stringify({session_id:sessionId,ts:Date.now()});QRCode.toCanvas(canvas,p,{width:240,margin:2});}}
await draw();_t=setInterval(draw,30000);}
export function stopQR(){if(_t){clearInterval(_t);_t=null;}}
