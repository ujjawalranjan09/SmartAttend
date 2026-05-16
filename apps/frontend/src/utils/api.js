// SmartAttend API Client
const BASE = window.SA_API || (location.hostname==='localhost'?'http://localhost:8000':'');
let _access=null,_refresh=null;
export const setTokens=(a,r)=>{_access=a;_refresh=r;};
export const clearTokens=()=>{_access=null;_refresh=null;};
export const getToken=()=>_access;
const offlineQueue=[];
async function req(method,path,body){const h={'Content-Type':'application/json'};if(_access)h['Authorization']=`Bearer ${_access}`;try{const r=await fetch(BASE+path,{method,headers:h,body:body?JSON.stringify(body):undefined});if(r.status===401&&_refresh){const ok=await tryRefresh();if(ok)return req(method,path,body);}const d=r.headers.get('content-type')?.includes('json')?await r.json():await r.text();if(!r.ok)throw{status:r.status,detail:d?.detail||d};return d;}catch(e){if(!navigator.onLine&&method==='POST'){offlineQueue.push({method,path,body,ts:Date.now()});return{queued:true};}throw e;}}
async function tryRefresh(){try{const r=await fetch(BASE+'/api/v1/auth/refresh',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({refresh_token:_refresh})});if(!r.ok)return false;const d=await r.json();_access=d.access_token;return true;}catch{return false;}}
export async function flushOfflineQueue(){const items=[...offlineQueue];offlineQueue.length=0;for(const i of items){try{await req(i.method,i.path,i.body);}catch{offlineQueue.push(i);}}}
export const api={get:(p)=>req('GET',p),post:(p,b)=>req('POST',p,b),put:(p,b)=>req('PUT',p,b),patch:(p,b)=>req('PATCH',p,b),del:(p)=>req('DELETE',p)};
export const authAPI={login:(e,p)=>api.post('/api/v1/auth/login',{email:e,password:p}),me:()=>api.get('/api/v1/auth/me'),logout:()=>api.post('/api/v1/auth/logout')};
export const sessionsAPI={list:(p={})=>api.get(`/api/v1/sessions?${new URLSearchParams(p)}`),create:(d)=>api.post('/api/v1/sessions',d),get:(id)=>api.get(`/api/v1/sessions/${id}`),start:(id)=>api.post(`/api/v1/sessions/${id}/start`),end:(id)=>api.post(`/api/v1/sessions/${id}/end`),qr:(id)=>api.get(`/api/v1/sessions/${id}/qr`),attendance:(id)=>api.get(`/api/v1/sessions/${id}/attendance`),override:(sId,stId,status)=>api.post(`/api/v1/sessions/${sId}/override`,{student_id:stId,status})};
export const attendanceAPI={mark:(d)=>api.post('/api/v1/attendance/mark',d)};
export const studentsAPI={list:(p={})=>api.get(`/api/v1/students?${new URLSearchParams(p)}`),get:(id)=>api.get(`/api/v1/students/${id}`),alerts:(id)=>api.get(`/api/v1/students/${id}/alerts`),attendance:(id)=>api.get(`/api/v1/students/${id}/attendance`)};
export const facultyAPI={list:()=>api.get('/api/v1/faculty'),get:(id)=>api.get(`/api/v1/faculty/${id}`),sessions:(id)=>api.get(`/api/v1/faculty/${id}/sessions`),analytics:(id)=>api.get(`/api/v1/faculty/${id}/analytics`)};
export const analyticsAPI={student:(id)=>api.get(`/api/v1/analytics/student/${id}`),course:(id)=>api.get(`/api/v1/analytics/course/${id}`),institution:()=>api.get('/api/v1/analytics/institution/summary'),atRisk:()=>api.get('/api/v1/analytics/institution/at-risk')};
export const reportsAPI={summary:(p)=>api.get(`/api/v1/reports/summary?${new URLSearchParams(p||{})}`),generate:(d)=>api.post('/api/v1/reports/generate',d),csvUrl:(p)=>`${BASE}/api/v1/reports/export/csv?${new URLSearchParams(p)}&token=${_access}`};
