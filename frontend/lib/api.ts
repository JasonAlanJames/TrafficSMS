// Browser code always talks to a same-origin API path.
// In development, Next.js rewrites proxy `/api/*` to the backend service.
const API_BASE_URL = '/api';

export type RegisterPayload = {
  email: string;
  password: string;
  phone_number: string;
  sms_consent: boolean;
  marketing_consent: boolean;
};

export type LoginPayload = {
  email: string;
  password: string;
  remember_me: boolean;
};

export type UpdateProfilePayload = {
  home_location?: string | null;
  work_location?: string | null;
  gym_location?: string | null;
  school_location?: string | null;
  default_state?: string | null;
  default_country?: string | null;
};

export type ChangePasswordPayload = {
  current_password: string;
  new_password: string;
};

export type ChangeEmailPayload = {
  new_email: string;
  current_password: string;
};

export type ChangePhonePayload = {
  phone_number: string;
  current_password: string;
};

export type AuthenticatedUser = {
  id: number;
  email: string;
  phone_e164: string | null;
  subscription_status: string;
  subscription_plan: string | null;
  email_verified: boolean;
  phone_verified: boolean;
  is_active: boolean;
  home_location: string | null;
  work_location: string | null;
  gym_location: string | null;
  school_location: string | null;
  default_state: string | null;
  default_country: string;
  pending_email: string | null;
  phone_verification_requested_at: string | null;
  created_at: string;
};

export type TokenResponse = {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  token_type: string;
};

export type AuthenticationResponse = TokenResponse & {
  user: AuthenticatedUser;
};

export type MessageResponse = {
  message: string;
};

export type BillingPlan = 'standard' | 'unlimited';

export type PricingPlan = {
  plan: string;
  product_id: string;
  price_id: string;
  name: string;
  description: string | null;
  price: number;
  currency: string;
  interval: string;
  sms_allowance: number;
};

export type CheckoutSessionResponse = {
  url: string;
};

export type CustomerPortalResponse = {
  url: string;
};

export type UsageSummary = {
  plan: string;
  sms_used: number;
  sms_allowance: number;
  remaining_sms: number;
  progress_ratio: number;
  period_start: string;
  period_end: string;
  reset_at: string;
};

export type SubscriptionSummary = {
  plan: string;
  status: string;
  stripe_customer_id: string | null;
  stripe_subscription_id: string | null;
  stripe_price_id: string | null;
  web_access_enabled: boolean;
  cancel_at_period_end: boolean;
  current_period_start: string | null;
  current_period_end: string | null;
  renewal_date: string | null;
  grace_period_end: string | null;
  trial_end: string | null;
  email_verified: boolean;
  phone_verified: boolean;
  saved_home_location: string | null;
  saved_work_location: string | null;
  saved_gym_location: string | null;
  saved_school_location: string | null;
  usage: UsageSummary;
};

export type BillingEvent = {
  event_type: string;
  status: string | null;
  source: string;
  amount_cents: number | null;
  currency: string | null;
  message: string | null;
  occurred_at: string;
};

export type SessionInfo = {
  id: string;
  ip_address: string | null;
  user_agent: string | null;
  device_name: string | null;
  created_at: string;
  last_used_at: string | null;
  expires_at: string;
  is_current: boolean;
};

export type ReconcileSubscriptionResponse = {
  message: string;
  subscription: SubscriptionSummary;
};

export type ValidationIssue = {
  field: string;
  message: string;
  type: string;
};

type ApiErrorPayload = {
  detail?: string;
  message?: string;
  error?: string;
  status_code?: number;
  errors?: ValidationIssue[];
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

function buildJsonHeaders(accessToken?: string): HeadersInit {
  return {
    'Content-Type': 'application/json',
    ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
  };
}

function buildAuthHeaders(accessToken: string): HeadersInit {
  return {
    Authorization: `Bearer ${accessToken}`,
  };
}

export async function register(payload: RegisterPayload): Promise<void> {
  await request<void>('/auth/register', {
    method: 'POST',
    headers: buildJsonHeaders(),
    body: JSON.stringify(payload),
  });
}

export async function login(payload: LoginPayload): Promise<AuthenticationResponse> {
  return request<AuthenticationResponse>('/auth/login', {
    method: 'POST',
    headers: buildJsonHeaders(),
    body: JSON.stringify(payload),
  });
}

export async function refreshAccessToken(refreshToken: string): Promise<TokenResponse> {
  return request<TokenResponse>('/auth/refresh', {
    method: 'POST',
    headers: buildJsonHeaders(),
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
}

export async function logout(refreshToken: string): Promise<MessageResponse> {
  return request<MessageResponse>('/auth/logout', {
    method: 'POST',
    headers: buildJsonHeaders(),
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
}

export async function logoutAll(accessToken: string): Promise<MessageResponse> {
  return request<MessageResponse>('/auth/logout-all', {
    method: 'POST',
    headers: buildJsonHeaders(accessToken),
  });
}

export async function listSessions(accessToken: string): Promise<SessionInfo[]> {
  return request<SessionInfo[]>('/auth/sessions', {
    method: 'GET',
    headers: buildAuthHeaders(accessToken),
  });
}

export async function revokeSession(accessToken: string, sessionId: string): Promise<MessageResponse> {
  return request<MessageResponse>(`/auth/sessions/${sessionId}`, {
    method: 'DELETE',
    headers: buildAuthHeaders(accessToken),
  });
}

export async function resendVerification(email: string): Promise<MessageResponse> {
  return request<MessageResponse>('/auth/resend-verification', {
    method: 'POST',
    headers: buildJsonHeaders(),
    body: JSON.stringify({ email }),
  });
}

export async function forgotPassword(email: string): Promise<MessageResponse> {
  return request<MessageResponse>('/auth/forgot-password', {
    method: 'POST',
    headers: buildJsonHeaders(),
    body: JSON.stringify({ email }),
  });
}

export async function confirmEmailChange(token: string): Promise<MessageResponse> {
  return request<MessageResponse>('/auth/confirm-email-change', {
    method: 'POST',
    headers: buildJsonHeaders(),
    body: JSON.stringify({ token }),
  });
}

export async function getCurrentUser(accessToken: string): Promise<AuthenticatedUser> {
  return request<AuthenticatedUser>('/users/me', {
    method: 'GET',
    headers: buildAuthHeaders(accessToken),
  });
}

export async function updateCurrentUserProfile(
  accessToken: string,
  payload: UpdateProfilePayload,
): Promise<AuthenticatedUser> {
  return request<AuthenticatedUser>('/users/me', {
    method: 'PATCH',
    headers: buildJsonHeaders(accessToken),
    body: JSON.stringify(payload),
  });
}

export async function changePassword(
  accessToken: string,
  payload: ChangePasswordPayload,
): Promise<MessageResponse> {
  return request<MessageResponse>('/users/me/change-password', {
    method: 'POST',
    headers: buildJsonHeaders(accessToken),
    body: JSON.stringify(payload),
  });
}

export async function changeEmail(
  accessToken: string,
  payload: ChangeEmailPayload,
): Promise<MessageResponse> {
  return request<MessageResponse>('/users/me/change-email', {
    method: 'POST',
    headers: buildJsonHeaders(accessToken),
    body: JSON.stringify(payload),
  });
}

export async function changePhone(
  accessToken: string,
  payload: ChangePhonePayload,
): Promise<AuthenticatedUser> {
  return request<AuthenticatedUser>('/users/me/change-phone', {
    method: 'POST',
    headers: buildJsonHeaders(accessToken),
    body: JSON.stringify(payload),
  });
}

export async function getPricing(): Promise<PricingPlan[]> {
  return request<PricingPlan[]>('/billing/pricing', {
    method: 'GET',
  });
}

export async function createCheckoutSession(
  accessToken: string,
  plan: BillingPlan,
): Promise<CheckoutSessionResponse> {
  return request<CheckoutSessionResponse>('/billing/create-checkout-session', {
    method: 'POST',
    headers: buildJsonHeaders(accessToken),
    body: JSON.stringify({ plan }),
  });
}

export async function createCustomerPortal(accessToken: string): Promise<CustomerPortalResponse> {
  return request<CustomerPortalResponse>('/billing/customer-portal', {
    method: 'POST',
    headers: buildJsonHeaders(accessToken),
  });
}

export async function getBillingSubscription(accessToken: string): Promise<SubscriptionSummary> {
  return request<SubscriptionSummary>('/billing/subscription', {
    method: 'GET',
    headers: buildAuthHeaders(accessToken),
  });
}

export async function getBillingUsage(accessToken: string): Promise<UsageSummary> {
  return request<UsageSummary>('/billing/usage', {
    method: 'GET',
    headers: buildAuthHeaders(accessToken),
  });
}

export async function getBillingHistory(accessToken: string): Promise<BillingEvent[]> {
  return request<BillingEvent[]>('/billing/history', {
    method: 'GET',
    headers: buildAuthHeaders(accessToken),
  });
}

export async function reconcileSubscription(accessToken: string): Promise<ReconcileSubscriptionResponse> {
  return request<ReconcileSubscriptionResponse>('/billing/reconcile', {
    method: 'POST',
    headers: buildJsonHeaders(accessToken),
  });
}

export async function changePlan(
  accessToken: string,
  plan: BillingPlan,
): Promise<SubscriptionSummary> {
  return request<SubscriptionSummary>('/billing/change-plan', {
    method: 'POST',
    headers: buildJsonHeaders(accessToken),
    body: JSON.stringify({ plan }),
  });
}

export async function cancelSubscription(
  accessToken: string,
  cancelAtPeriodEnd = true,
): Promise<SubscriptionSummary> {
  return request<SubscriptionSummary>('/billing/cancel', {
    method: 'POST',
    headers: buildJsonHeaders(accessToken),
    body: JSON.stringify({ cancel_at_period_end: cancelAtPeriodEnd }),
  });
}
