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
