import { apiClient, USE_MOCKS, mockDelay } from "./api-client";
import { DATASET } from "@/data/real-facts";
import type { PredictionRequestPreview, PredictionResponsePreview } from "@/types/domain";

export const SAMPLE_REQUEST: PredictionRequestPreview & Record<string, unknown> = {
  TransactionID: 1000001,
  TransactionDT: 86400,
  TransactionAmt: 250.75,
  ProductCD: "W",
  card1: 13553,
  card2: 555,
  card3: 150,
  card4: "visa",
  card5: 226,
  card6: "debit",
  addr1: 315,
  P_emaildomain: "example.com",
  R_emaildomain: "example.com",
  DeviceType: "mobile",
  DeviceInfo: "generic-device",
  id_30: "Android 7.0",
  id_31: "chrome",
  id_33: "1920x1080",
};

export async function requestToken(username: string, password: string): Promise<string> {
  if (!USE_MOCKS) {
    const form = new URLSearchParams();
    form.set("username", username);
    form.set("password", password);
    const { data } = await apiClient.post("/api/v1/auth/token", form, {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });
    return data.access_token;
  }
  if (username !== "svc-ml-engineer" || password !== "CHANGE_ME_IN_PRODUCTION") {
    await mockDelay(null, 400);
    throw new Error("401 Unauthorized — invalid username or password");
  }
  await mockDelay(null, 400);
  return `mock.${btoa(username)}.${Date.now()}`;
}

export async function requestPrediction(token: string, payload: Record<string, unknown>): Promise<PredictionResponsePreview> {
  if (!USE_MOCKS) {
    const { data } = await apiClient.post<PredictionResponsePreview>("/api/v1/inference/predict", payload, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return data;
  }
  if (!token) {
    await mockDelay(null, 300);
    throw new Error("401 Unauthorized — missing or invalid bearer token");
  }
  const amt = Number(payload.TransactionAmt ?? 0);
  const isCredit = payload.card6 === "credit";
  const probability = Math.min(0.97, Math.max(0.005, (isCredit ? 0.045 : 0.012) + amt / 50_000));
  await mockDelay(null, 650);
  return {
    is_fraud: probability > 0.5976,
    fraud_probability: Number(probability.toFixed(4)),
    model_version: `lightgbm@${DATASET.datasetVersion}`,
    request_id: crypto.randomUUID(),
  };
}

export interface ApiEndpointRow {
  method: string;
  route: string;
  auth: boolean;
  input: string;
  output: string;
  purpose: string;
  security: string[];
}

export const API_ENDPOINTS: ApiEndpointRow[] = [
  {
    method: "POST",
    route: "/api/v1/auth/token",
    auth: false,
    input: "form: username, password",
    output: "{ access_token, token_type }",
    purpose: "OAuth2 password flow — issues a 15-minute JWT",
    security: ["Rate limited (stricter)", "bcrypt-hashed credential check"],
  },
  {
    method: "POST",
    route: "/api/v1/inference/predict",
    auth: true,
    input: "TransactionFeatures (strict schema, extra='forbid')",
    output: "{ is_fraud, fraud_probability, model_version, request_id }",
    purpose: "Real-time fraud-risk scoring using the LightGBM inference bundle",
    security: ["Bearer JWT required", "Rate limited", "Bounded/typed input validation"],
  },
  {
    method: "GET",
    route: "/health",
    auth: false,
    input: "—",
    output: "{ status, environment }",
    purpose: "Liveness/readiness probe (no sensitive information returned)",
    security: ["No auth required by design"],
  },
  {
    method: "GET",
    route: "/docs",
    auth: false,
    input: "—",
    output: "Swagger UI (self-hosted, not CDN-hosted)",
    purpose: "Interactive OpenAPI documentation",
    security: ["Disabled in production", "Scoped CSP (self + inline only)"],
  },
];
