export interface PasswordRequirement {
  id: string;
  label: string;
  test: (value: string) => boolean;
}

export const passwordRequirements: PasswordRequirement[] = [
  {
    id: "length",
    label: "Minimum 8 characters",
    test: (value) => value.length >= 8,
  },
  {
    id: "uppercase",
    label: "Uppercase letter",
    test: (value) => /[A-Z]/.test(value),
  },
  {
    id: "lowercase",
    label: "Lowercase letter",
    test: (value) => /[a-z]/.test(value),
  },
  {
    id: "number",
    label: "Number",
    test: (value) => /\d/.test(value),
  },
  {
    id: "special",
    label: "Special character",
    test: (value) => /[^A-Za-z0-9]/.test(value),
  },
];

export interface PasswordStrength {
  label: "Too weak" | "Weak" | "Fair" | "Good" | "Strong";
  score: number;
}

export function getPasswordChecks(password: string) {
  return passwordRequirements.map((requirement) => ({
    ...requirement,
    passed: requirement.test(password),
  }));
}

export function getPasswordStrength(password: string): PasswordStrength {
  const score = getPasswordChecks(password).filter((item) => item.passed).length;

  if (score <= 1) {
    return { label: "Too weak", score };
  }

  if (score === 2) {
    return { label: "Weak", score };
  }

  if (score === 3) {
    return { label: "Fair", score };
  }

  if (score === 4) {
    return { label: "Good", score };
  }

  return { label: "Strong", score };
}

export function formatPhoneInput(value: string) {
  const digits = getNormalizedUsDigits(value);

  if (digits.length === 0) {
    return "";
  }

  if (digits.length < 4) {
    return `(${digits}`;
  }

  if (digits.length < 7) {
    return `(${digits.slice(0, 3)}) ${digits.slice(3)}`;
  }

  return `(${digits.slice(0, 3)}) ${digits.slice(3, 6)}-${digits.slice(6, 10)}`;
}

export function normalizePhoneNumber(value: string) {
  const digits = getNormalizedUsDigits(value);

  if (digits.length !== 10) {
    return null;
  }

  return `+1${digits}`;
}

export function isValidEmail(value: string) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}

function getNormalizedUsDigits(value: string) {
  const rawDigits = value.replace(/\D/g, "");
  const digits =
    rawDigits.length === 11 && rawDigits.startsWith("1")
      ? rawDigits.slice(1)
      : rawDigits;

  return digits.slice(0, 10);
}
