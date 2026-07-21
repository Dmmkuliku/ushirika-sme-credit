function localIsoDate(value) {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, '0');
  const day = String(value.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

export function todayIso() {
  return localIsoDate(new Date());
}

export function dmyToIso(dmyValue) {
  const match = String(dmyValue || '').match(/^(\d{2})-(\d{2})-(\d{4})$/);
  if (!match) return '';
  const [, day, month, year] = match;
  const iso = `${year}-${month}-${day}`;
  const parsed = new Date(`${iso}T00:00:00`);
  return !Number.isNaN(parsed.getTime()) && localIsoDate(parsed) === iso ? iso : '';
}

function formatDmyInput(value) {
  const digits = String(value || '').replace(/\D/g, '').slice(0, 8);
  if (digits.length <= 2) return digits;
  if (digits.length <= 4) return `${digits.slice(0, 2)}-${digits.slice(2)}`;
  return `${digits.slice(0, 2)}-${digits.slice(2, 4)}-${digits.slice(4)}`;
}

export function normalizeTzPhone(localDigits) {
  const raw = String(localDigits || '').replace(/\D/g, '');
  let local = raw;
  if (raw.startsWith('255')) local = raw.slice(3);
  else if (raw.startsWith('0')) local = raw.slice(1);
  return /^[67]\d{8}$/.test(local) ? `+255${local}` : null;
}

export function phoneLocalDigits(phone) {
  const raw = String(phone || '').replace(/\D/g, '');
  if (raw.startsWith('255')) return raw.slice(3, 12);
  if (raw.startsWith('0')) return raw.slice(1, 10);
  return raw.slice(0, 9);
}

export function formatTzPhone(phone) {
  const normalized = normalizeTzPhone(phone);
  return normalized ? `(+255) ${normalized.slice(4)}` : String(phone || '');
}

export function phoneInputHtml({ id, name = 'phone', value = '', required = false } = {}) {
  return `
    <div class="phone-input-group">
      <span class="phone-prefix" aria-hidden="true">+255</span>
      <input id="${id}" name="${name}" type="tel" inputmode="numeric"
        minlength="9" maxlength="9" pattern="[67][0-9]{8}"
        placeholder="712345678" value="${phoneLocalDigits(value)}"${required ? ' required' : ''} />
    </div>`;
}

export function isValidEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(email || '').trim());
}

/**
 * Attach an inline error paragraph directly below a field and return
 * show/clear helpers. Keeps the browser validity state in sync so the
 * form cannot be submitted while the error is visible.
 */
function attachInlineError(input) {
  const message = document.createElement('p');
  message.className = 'field-validation-error';
  message.setAttribute('role', 'alert');
  message.hidden = true;
  const anchor = input.closest('.phone-input-group') || input;
  anchor.insertAdjacentElement('afterend', message);
  return {
    show(text) {
      input.setCustomValidity(text);
      input.setAttribute('aria-invalid', 'true');
      message.textContent = text;
      message.hidden = false;
    },
    clear() {
      input.setCustomValidity('');
      input.setAttribute('aria-invalid', 'false');
      message.textContent = '';
      message.hidden = true;
    },
  };
}

export function bindImmediateEmailValidation(input, message) {
  if (!input) return;
  const error = attachInlineError(input);
  const validate = () => {
    if (input.value.trim() && !isValidEmail(input.value)) error.show(message);
    else error.clear();
  };
  input.addEventListener('input', validate);
  input.addEventListener('blur', validate);
}

/** Show an error under the field as soon as the user leaves it empty. */
export function bindRequiredField(input, message) {
  if (!input) return;
  const error = attachInlineError(input);
  const validate = () => {
    if (!String(input.value || '').trim()) error.show(message);
    else error.clear();
  };
  input.addEventListener('blur', validate);
  input.addEventListener('change', validate);
  input.addEventListener('input', () => {
    if (String(input.value || '').trim()) error.clear();
  });
}

/** 4-digit PIN: strip non-digits while typing, flag wrong length on blur. */
export function bindPinField(input, message) {
  if (!input) return;
  const error = attachInlineError(input);
  input.addEventListener('input', () => {
    const digits = input.value.replace(/\D/g, '').slice(0, 4);
    if (digits !== input.value) {
      input.value = digits;
      error.show(message);
    } else if (digits.length === 4) {
      error.clear();
    }
  });
  input.addEventListener('blur', () => {
    if (input.value && !/^\d{4}$/.test(input.value)) error.show(message);
    else error.clear();
  });
}

/** Confirm-PIN must match the main PIN field as the user types. */
export function bindConfirmPinField(confirmInput, pinInput, mismatchMessage) {
  if (!confirmInput) return;
  const error = attachInlineError(confirmInput);
  const validate = () => {
    const value = confirmInput.value.replace(/\D/g, '').slice(0, 4);
    if (value !== confirmInput.value) confirmInput.value = value;
    if (value && pinInput && value !== pinInput.value) error.show(mismatchMessage);
    else error.clear();
  };
  confirmInput.addEventListener('input', validate);
  confirmInput.addEventListener('blur', validate);
  pinInput?.addEventListener('input', () => {
    if (confirmInput.value) validate();
  });
}

/** Tanzanian phone (9 local digits starting with 6 or 7) with instant feedback. */
export function bindPhoneField(input, message) {
  if (!input) return;
  const error = attachInlineError(input);
  input.addEventListener('input', () => {
    const digits = input.value.replace(/\D/g, '').slice(0, 9);
    if (digits !== input.value) {
      input.value = digits;
      error.show(message);
      return;
    }
    if (/^[67]\d{8}$/.test(digits) || !digits) error.clear();
  });
  input.addEventListener('blur', () => {
    if (input.value && !/^[67]\d{8}$/.test(input.value)) error.show(message);
    else error.clear();
  });
}

/**
 * DD-MM-YYYY date input, optionally cross-checked against a NIDA input
 * (first 8 NIDA digits must equal YYYYMMDD of the birth date).
 */
export function bindNidaMatchedDobValidation({
  input,
  nidaInput,
  invalidDateMessage,
  mismatchMessage,
} = {}) {
  if (!input) return;
  const error = attachInlineError(input);

  const validate = ({ showIncomplete = false } = {}) => {
    if (!input.value) {
      error.clear();
      return;
    }
    const dobIso = dmyToIso(input.value);
    if (!dobIso) {
      if (showIncomplete || input.value.length === 10) error.show(invalidDateMessage);
      else error.clear();
      return;
    }
    const nida = String(nidaInput?.value || '');
    if (mismatchMessage && /^\d{20}$/.test(nida) && nida.slice(0, 8) !== dobIso.replaceAll('-', '')) {
      error.show(mismatchMessage);
      return;
    }
    error.clear();
  };

  input.addEventListener('input', () => {
    input.value = formatDmyInput(input.value);
    validate();
  });
  input.addEventListener('blur', () => validate({ showIncomplete: true }));
  nidaInput?.addEventListener('input', () => validate());
}

export function bindExactDigitsValidation(input, {
  length,
  digitsOnlyMessage,
  exactLengthMessage,
} = {}) {
  if (!input) return;
  const error = attachInlineError(input);

  input.addEventListener('input', () => {
    const original = input.value;
    const digits = original.replace(/\D/g, '').slice(0, length);
    input.value = digits;
    if (original !== digits) {
      error.show(digitsOnlyMessage);
    } else {
      error.clear();
    }
  });

  input.addEventListener('blur', () => {
    if (input.value && input.value.length !== length) {
      error.show(exactLengthMessage);
    } else if (/^\d+$/.test(input.value) || !input.value) {
      error.clear();
    }
  });
}
