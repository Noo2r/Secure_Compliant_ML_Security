import { mockDelay } from "./api-client";
import type { ThreatRow } from "@/types/domain";

export const THREATS: ThreatRow[] = [
  { id: "t1", category: "Spoofing", asset: "Auth endpoint", attackVector: "Credential stuffing against /api/v1/auth/token", existingControl: "bcrypt-hashed password check + rate limiting", residualRisk: "Medium", status: "locally_tested" },
  { id: "t2", category: "Spoofing", asset: "JWT bearer tokens", attackVector: "Forged/replayed tokens", existingControl: "HS256-signed JWT, 15-minute expiry", residualRisk: "Low", status: "locally_tested" },
  { id: "t3", category: "Tampering", asset: "Inference request payload", attackVector: "Malformed/oversized/injected fields", existingControl: "Pydantic strict schema (extra='forbid'), bounded fields", residualRisk: "Low", status: "verified" },
  { id: "t4", category: "Tampering", asset: "Model artifact (joblib bundle)", attackVector: "Supply-chain tampering of the trained model file", existingControl: "Not currently signed or checksummed at load time", residualRisk: "High", status: "future_work" },
  { id: "t5", category: "Repudiation", asset: "Inference requests", attackVector: "Denial of having made a fraudulent-flagged request", existingControl: "Structured, PII-free audit logging with request_id", residualRisk: "Low", status: "locally_tested" },
  { id: "t6", category: "Repudiation", asset: "Audit trail", attackVector: "Tampering with logs after the fact", existingControl: "WORM upload script (dry-run verified only)", residualRisk: "Medium", status: "dry_run" },
  { id: "t7", category: "Information Disclosure", asset: "PII / sensitive fields", attackVector: "Data exfiltration from storage", existingControl: "Fernet field-level encryption (AES-128-CBC + auth)", residualRisk: "Medium", status: "verified" },
  { id: "t8", category: "Information Disclosure", asset: "Error responses", attackVector: "Stack traces leaking internals", existingControl: "Global exception handler returns generic 500 only", residualRisk: "Low", status: "locally_tested" },
  { id: "t9", category: "Information Disclosure", asset: "Secrets (JWT key, DB creds)", attackVector: "Secret leakage via env files or logs", existingControl: "Azure Key Vault target architecture; local .env for dev only", residualRisk: "Medium", status: "designed_not_deployed" },
  { id: "t10", category: "Denial of Service", asset: "Inference & auth endpoints", attackVector: "Request flooding / brute force", existingControl: "SlowAPI global rate limiter, stricter on auth", residualRisk: "Medium", status: "locally_tested" },
  { id: "t11", category: "Elevation of Privilege", asset: "Kubernetes namespace", attackVector: "Lateral movement between pods", existingControl: "Default-deny NetworkPolicy + explicit allow rules", residualRisk: "Medium", status: "designed_not_deployed" },
  { id: "t12", category: "Elevation of Privilege", asset: "AKS control plane", attackVector: "Unauthorized cluster admin access", existingControl: "Private cluster, Azure AD RBAC, authorized IP ranges (target)", residualRisk: "High", status: "designed_not_deployed" },
];

export const TRUST_BOUNDARIES = [
  { name: "Internet → WAF/Application Gateway", description: "Public entry point; TLS termination, OWASP CRS 3.2 rule set (target architecture, not deployed)." },
  { name: "WAF → AKS private cluster", description: "NSG-restricted, HTTPS only. AKS control plane has no public endpoint in the target design." },
  { name: "Inference pods → Key Vault", description: "Private endpoint only, public network access disabled, RBAC secrets-reader role (target architecture)." },
  { name: "CI/CD → Repository secrets", description: "GitHub Actions secrets scoped per-job; WORM upload job requires 6 Azure secrets, none configured in this repository." },
];

export async function getThreats(): Promise<ThreatRow[]> {
  return mockDelay(THREATS, 300);
}
