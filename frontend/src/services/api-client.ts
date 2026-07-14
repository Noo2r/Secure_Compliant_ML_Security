import axios from "axios";

/**
 * Base Axios client for the real FastAPI backend (Milestone 3,
 * app/main.py). Every feature service below is written against this client
 * so that flipping VITE_USE_MOCKS=false switches the whole app from mock
 * data to the live API without touching component code — only the service
 * layer (src/services/*.ts) knows whether it's talking to a mock or the
 * real backend.
 */
export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000",
  timeout: 15_000,
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const USE_MOCKS = import.meta.env.VITE_USE_MOCKS !== "false";

/** Simulates realistic network latency for mock services. */
export function mockDelay<T>(value: T, ms = 350): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), ms));
}
