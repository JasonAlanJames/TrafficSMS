const NON_DIGIT_PATTERN = /\D/g;

function getUsPhoneDigits(value: string): string {
  const digits = value.replace(NON_DIGIT_PATTERN, '');

  if (digits.length === 11 && digits.startsWith('1')) {
    return digits.slice(1, 11);
  }

  return digits.slice(0, 10);
}

export function formatPhoneInput(value: string): string {
  const digits = getUsPhoneDigits(value);

  if (digits.length <= 3) {
    return digits ? `(${digits}` : '';
  }

  if (digits.length <= 6) {
    return `(${digits.slice(0, 3)}) ${digits.slice(3)}`;
  }

  return `(${digits.slice(0, 3)}) ${digits.slice(3, 6)}-${digits.slice(6, 10)}`;
}

export function normalizeUsPhoneNumber(value: string): string | null {
  const digits = getUsPhoneDigits(value);

  if (digits.length !== 10) {
    return null;
  }

  return `+1${digits}`;
}
