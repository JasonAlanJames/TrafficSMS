export type PasswordRequirement = {
  key: 'length' | 'uppercase' | 'lowercase' | 'number' | 'special';
  label: string;
  satisfied: boolean;
};

export function getPasswordRequirements(password: string): PasswordRequirement[] {
  return [
    {
      key: 'length',
      label: 'At least 8 characters',
      satisfied: password.length >= 8,
    },
    {
      key: 'uppercase',
      label: 'One uppercase letter',
      satisfied: /[A-Z]/.test(password),
    },
    {
      key: 'lowercase',
      label: 'One lowercase letter',
      satisfied: /[a-z]/.test(password),
    },
    {
      key: 'number',
      label: 'One number',
      satisfied: /\d/.test(password),
    },
    {
      key: 'special',
      label: 'One special character',
      satisfied: /[^A-Za-z0-9]/.test(password),
    },
  ];
}

export function getPasswordStrength(password: string): {
  label: 'Too weak' | 'Weak' | 'Fair' | 'Strong';
  score: 0 | 1 | 2 | 3 | 4;
} {
  if (!password) {
    return { label: 'Too weak', score: 0 };
  }

  const score = getPasswordRequirements(password).filter((requirement) => requirement.satisfied).length as 0 | 1 | 2 | 3 | 4 | 5;

  if (score <= 2) {
    return { label: 'Weak', score: Math.max(1, score) as 1 | 2 };
  }

  if (score === 3 || password.length < 10) {
    return { label: 'Fair', score: 3 };
  }

  return { label: 'Strong', score: 4 };
}
