const API_BASE_URL = (process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000').replace(/\/+$/, '');

export type RegisterPayload = {
  email: string;
  password: string;
  phone_number: string;
  sms_consent: boolean;
  marketing_consent: boolean;
};

type ApiErrorPayload = {
  detail?: string;
  message?: string;
  error?: string;
};

export class ApiError extends Error {
  status: number;
  payload: ApiErrorPayload | null;

  constructor(message: string, status: number, payload: ApiErrorPayload | null = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.payload = payload;
  }
}

async function readErrorPayload(response: Response): Promise<ApiErrorPayload | null> {
  const contentType = response.headers.get('content-type') ?? '';

  if (contentType.includes('application/json')) {
    return (await response.json()) as ApiErrorPayload;
  }

  const text = await response.text();
  return text ? { detail: text } : null;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, init);

  if (!response.ok) {
    const payload = await readErrorPayload(response);
    const message =
      payload?.detail ??
      payload?.message ??
      payload?.error ??
      'Something went wrong. Please try again.';

    throw new ApiError(message, response.status, payload);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const contentType = response.headers.get('content-type') ?? '';

  if (!contentType.includes('application/json')) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export async function register(payload: RegisterPayload): Promise<void> {
  await request<void>('/auth/register', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });
}
