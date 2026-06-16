export const validators = {
  required(value) {
    if (value === null || value === undefined) return 'This field is required';
    if (typeof value === 'string' && value.trim() === '') return 'This field is required';
    return null;
  },

  email(value) {
    if (!value) return null;
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(value) ? null : 'Please enter a valid email address';
  },

  minLength(n) {
    return (value) => {
      if (!value) return null;
      return value.length >= n ? null : `Must be at least ${n} characters`;
    };
  },

  maxLength(n) {
    return (value) => {
      if (!value) return null;
      return value.length <= n ? null : `Must be at most ${n} characters`;
    };
  },

  match(fieldName) {
    return (value, values) => {
      if (!value) return null;
      return value === values[fieldName] ? null : `Fields do not match`;
    };
  },

  pattern(re, msg) {
    return (value) => {
      if (!value) return null;
      return re.test(value) ? null : msg || 'Invalid format';
    };
  },
};

export function validateForm(fields, values) {
  const errors = {};

  for (const [name, rules] of Object.entries(fields)) {
    for (const rule of rules) {
      const error = rule(values[name], values);
      if (error) {
        errors[name] = error;
        break;
      }
    }
  }

  return { valid: Object.keys(errors).length === 0, errors };
}

export function showFieldError(el, msg) {
  el.classList.add('has-error');
  let errorEl = el.querySelector('.field-error');
  if (!errorEl) {
    errorEl = document.createElement('span');
    errorEl.className = 'field-error';
    el.appendChild(errorEl);
  }
  errorEl.textContent = msg;
}

export function clearFieldError(el) {
  el.classList.remove('has-error');
  const errorEl = el.querySelector('.field-error');
  if (errorEl) errorEl.remove();
}
