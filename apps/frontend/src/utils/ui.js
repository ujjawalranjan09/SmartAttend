export function toast(msg,type='info',ms=4000){const c=document.getElementById('toast-container');const el=document.createElement('div');el.className=`toast ${type}`;const icons={success:'check-circle',error:'x-circle',info:'info'};el.innerHTML=`<i data-lucide="${icons[type]||'info'}"></i><span>${msg}</span>`;c.appendChild(el);if(window.lucide)lucide.createIcons({el});setTimeout(()=>el.remove(),ms);}
export const showModal=id=>document.getElementById(id)?.classList.remove('hidden');
export const hideModal=id=>document.getElementById(id)?.classList.add('hidden');
export function setLoading(btn,on){if(on){btn._orig=btn.innerHTML;btn.innerHTML='<span style="opacity:.5">Loading...</span>';btn.disabled=true;}else{btn.innerHTML=btn._orig||'Submit';btn.disabled=false;}}
export const fmtPct=n=>`${Math.round(n)}%`;
export const fmtDate=d=>new Date(d).toLocaleDateString('en-IN',{day:'numeric',month:'short',year:'numeric'});
export const fmtTime=d=>new Date(d).toLocaleTimeString('en-IN',{hour:'2-digit',minute:'2-digit'});
export const attClass=p=>p>=75?'success':p>=60?'warning':'error';
export const attBarClass=p=>p>=75?'':p>=60?'medium':'low';

export function formatDate(d){return new Date(d).toLocaleDateString('en-IN',{day:'numeric',month:'short',year:'numeric'});}
export function formatTime(d){return new Date(d).toLocaleTimeString('en-IN',{hour:'2-digit',minute:'2-digit'});}
export function formatPercent(n){return `${Math.round(n)}%`;}

export function renderError(container,message,onRetry){
  container.innerHTML=`<div class="empty-state"><i data-lucide="alert-triangle" style="width:48px;height:48px;color:var(--color-error)"></i><h3>Something went wrong</h3><p>${message}</p>${onRetry?'<button class="btn btn-primary" id="retry-btn"><i data-lucide="refresh-cw"></i> Retry</button>':''}</div>`;
  if(window.lucide)lucide.createIcons({nodes:[container]});
  if(onRetry){const btn=container.querySelector('#retry-btn');if(btn)btn.addEventListener('click',onRetry);}
}

export function renderLoading(container,count=4){
  container.innerHTML=`<div class="skeleton-grid">${Array.from({length:count},()=>`<div class="skeleton-card"><div class="skeleton" style="height:16px;width:60%;margin-bottom:12px"></div><div class="skeleton" style="height:12px;width:80%;margin-bottom:8px"></div><div class="skeleton" style="height:12px;width:40%"></div></div>`).join('')}</div>`;
}

export function renderEmpty(container,icon,title,subtitle){
  container.innerHTML=`<div class="empty-state"><i data-lucide="${icon}" class="empty-icon"></i><h3>${title}</h3><p>${subtitle}</p></div>`;
  if(window.lucide)lucide.createIcons({nodes:[container]});
}

export const skeleton=(n=4)=>Array.from({length:n},()=>'<div class="skeleton skeleton-text" style="height:48px;margin-bottom:8px"></div>').join('');
export const emptyState=(icon,title,body,action='')=>`<div class="empty-state"><i data-lucide="${icon}" style="width:48px;height:48px"></i><h3>${title}</h3><p>${body}</p>${action}</div>`;
