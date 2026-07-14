import { apiClient, USE_MOCKS, mockDelay } from "./api-client";

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface AuthUser {
  username: string;
  role: string;
}

interface TokenResponse {
  access_token: string;
  token_type: string;
}

/**
 * Matches the real backend's OAuth2 password flow at
 * POST /api/v1/auth/token (app/api/auth.py, form-encoded body). Falls back
 * to a mock token when VITE_USE_MOCKS is enabled (default) or when the
 * backend isn't reachable, so the UI is fully demoable without the FastAPI
 * service running.
 */
export async function login({ username, password }: LoginCredentials): Promise<AuthUser> {
  if (!USE_MOCKS) {
    const form = new URLSearchParams();
    form.set("username", username);
    form.set("password", password);
    const { data } = await apiClient.post<TokenResponse>("/api/v1/auth/token", form, {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });
    localStorage.setItem("access_token", data.access_token);
    const user = { username, role: "ml_engineer" };
    localStorage.setItem("auth_user", JSON.stringify(user));
    return user;
  }

  if (username !== "svc-ml-engineer" || password !== "CHANGE_ME_IN_PRODUCTION") {
    await mockDelay(null, 500);
    throw new Error("Invalid username or password.");
  }
  const mockToken = `mock.${btoa(username)}.${Date.now()}`;
  const user = { username, role: "ml_engineer" };
  await mockDelay(null, 600);
  localStorage.setItem("access_token", mockToken);
  localStorage.setItem("auth_user", JSON.stringify(user));
  return user;
}

export function logout() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("auth_user");
}

export function getStoredUser(): AuthUser | null {
  const raw = localStorage.getItem("auth_user");
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AuthUser;
  } catch {
    return null;
  }
}
