function localIsoDate(value) {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, '0');
  const day = String(value.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

export function todayIso() {
  return localIsoDate(new Date());
}

export function latestAdultDobIso() {
  const today = new Date();
  const adult = new Date(today.getFullYear() - 18, today.getMonth(), today.getDate());
  return localIsoDate(adult);
}

export function eighteenthBirthdayIso(dobValue) {
  const dob = new Date(`${dobValue}T00:00:00`);
  if (Number.isNaN(dob.getTime())) return '';
  dob.setFullYear(dob.getFullYear() + 18);
  return localIsoDate(dob);
}

export function isoToDmy(isoValue) {
  const match = String(isoValue || '').match(/^(\d{4})-(\d{2})-(\d{2})$/);
  return match ? `${match[3]}-${match[2]}-${match[1]}` : '';
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

export function bindImmediateEmailValidation(input, message) {
  if (!input) return;
  const validate = () => {
    const invalid = input.value.trim() && !isValidEmail(input.value);
    input.setCustomValidity(invalid ? message : '');
    input.setAttribute('aria-invalid', invalid ? 'true' : 'false');
    if (invalid) input.reportValidity();
  };
  input.addEventListener('input', validate);
  input.addEventListener('blur', validate);
}

export function bindNidaMatchedDobValidation({
  input,
  nidaInput,
  invalidDateMessage,
  mismatchMessage,
  underageMessage,
} = {}) {
  if (!input) return;

  const message = document.createElement('p');
  message.className = 'field-validation-error';
  message.setAttribute('role', 'alert');
  message.hidden = true;
  input.insertAdjacentElement('afterend', message);

  const showMessage = (text) => {
    input.setCustomValidity(text);
    input.setAttribute('aria-invalid', 'true');
    message.textContent = text;
    message.hidden = false;
  };
  const clearMessage = () => {
    input.setCustomValidity('');
    input.setAttribute('aria-invalid', 'false');
    message.textContent = '';
    message.hidden = true;
  };

  const validate = ({ showIncomplete = false } = {}) => {
    if (!input.value) {
      clearMessage();
      return;
    }
    const dobIso = dmyToIso(input.value);
    if (!dobIso) {
      if (showIncomplete || input.value.length === 10) showMessage(invalidDateMessage);
      else clearMessage();
      return;
    }
    if (dobIso > latestAdultDobIso()) {
      showMessage(underageMessage(dobIso));
      return;
    }
    const nida = String(nidaInput?.value || '');
    if (/^\d{20}$/.test(nida) && nida.slice(0, 8) !== dobIso.replaceAll('-', '')) {
      showMessage(mismatchMessage);
      return;
    }
    clearMessage();
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

  const message = document.createElement('p');
  message.className = 'field-validation-error';
  message.setAttribute('role', 'alert');
  message.hidden = true;
  input.insertAdjacentElement('afterend', message);

  const showMessage = (text) => {
    input.setCustomValidity(text);
    input.setAttribute('aria-invalid', 'true');
    message.textContent = text;
    message.hidden = false;
  };

  const clearMessage = () => {
    input.setCustomValidity('');
    input.setAttribute('aria-invalid', 'false');
    message.textContent = '';
    message.hidden = true;
  };

  input.addEventListener('input', () => {
    const original = input.value;
    const digits = original.replace(/\D/g, '').slice(0, length);
    input.value = digits;
    if (original !== digits) {
      showMessage(digitsOnlyMessage);
    } else {
      clearMessage();
    }
  });

  input.addEventListener('blur', () => {
    if (input.value && input.value.length !== length) {
      showMessage(exactLengthMessage);
    } else if (/^\d+$/.test(input.value) || !input.value) {
      clearMessage();
    }
  });
}
