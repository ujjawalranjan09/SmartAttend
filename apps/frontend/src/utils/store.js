export function createStore(init){let s={...init};const ls=new Set();return{getState:()=>s,setState(p){s={...s,...(typeof p==='function'?p(s):p)};ls.forEach(f=>f(s));},subscribe(f){ls.add(f);return()=>ls.delete(f);}};}
export const appStore=createStore({user:null,role:null,currentView:'dashboard',notifications:[],isOnline:navigator.onLine,sidebarCollapsed:false});
