// Minimal reactive store — no external deps
const _listeners = new Map();
const state = {
  user: null,
  role: null,
  currentView: 'dashboard',
  notifications: [],
  isOffline: false,
};

export function getState() { return { ...state }; }

export function setState(patch) {
  Object.assign(state, patch);
  const keys = Object.keys(patch);
  keys.forEach(k => (_listeners.get(k) || []).forEach(fn => fn(state[k], state)));
  (_listeners.get('*') || []).forEach(fn => fn(state));
}

export function subscribe(key, fn) {
  if (!_listeners.has(key)) _listeners.set(key, []);
  _listeners.get(key).push(fn);
  return () => { _listeners.set(key, _listeners.get(key).filter(f => f !== fn)); };
}

export function subscribeAll(fn) { return subscribe('*', fn); }
