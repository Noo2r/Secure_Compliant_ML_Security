import { mockDelay } from "./api-client";
import { COMPLIANCE_SUMMARY } from "@/data/real-facts";
import type { ComplianceControl } from "@/types/domain";

export const COMPLIANCE_CONTROLS: ComplianceControl[] = [
  { id: "c1", framework: "GDPR", control: "Data minimization", status: "implemented", evidence: "150 selected features vs. 434 raw columns; feature selection funnel documented" },
  { id: "c2", framework: "GDPR", control: "Integrity & confidentiality (Art. 32)", status: "implemented", evidence: "Field-level Fernet encryption on PII columns, re-verified independently by Module 1" },
  { id: "c3", framework: "GDPR", control: "Storage limitation", status: "partial", evidence: "No automated retention/deletion policy implemented for encrypted data" },
  { id: "c4", framework: "GDPR", control: "Data-subject access/erasure rights", status: "not_implemented", evidence: "No API or process exists to fulfill access/erasure requests", gap: "Recommended future work — no current implementation" },
  { id: "c5", framework: "GDPR", control: "Privacy by design", status: "implemented", evidence: "Differential privacy module, fairness audits, and encryption built into the pipeline from Module 1 onward" },
  { id: "c6", framework: "GDPR", control: "Breach notification readiness", status: "partial", evidence: "Structured audit logging exists; no formal incident-response runbook committed" },
  { id: "c7", framework: "HIPAA", control: "Applicability determination", status: "not_implemented", evidence: "This dataset is payment-card transaction data, not protected health information", gap: "HIPAA applicability is not established for this project — included for completeness only" },
  { id: "c8", framework: "HIPAA", control: "Access controls", status: "partial", evidence: "JWT-based API auth exists; not HIPAA-scoped since PHI applicability is unestablished" },
  { id: "c9", framework: "ISO 27001", control: "A.8 Asset management", status: "implemented", evidence: "Dataset manifest with version hashing (e457d0eb2c3b9e45) tracks data lineage" },
  { id: "c10", framework: "ISO 27001", control: "A.9 Access control", status: "implemented", evidence: "OAuth2 JWT auth, rate limiting, RBAC target design for Key Vault/AKS" },
  { id: "c11", framework: "ISO 27001", control: "A.12 Operations security", status: "partial", evidence: "CI/CD tests exist (178/178); no SAST/DAST/container/IaC scanning integrated yet" },
  { id: "c12", framework: "ISO 27001", control: "A.13 Communications security", status: "implemented", evidence: "TLS termination at WAF (target), strict CSP, security headers on every response" },
  { id: "c13", framework: "ISO 27001", control: "A.14 System acquisition/development", status: "implemented", evidence: "178 automated tests, requirements traceability matrix, documented threat model" },
  { id: "c14", framework: "ISO 27001", control: "A.18 Compliance", status: "not_implemented", evidence: "No formal legal compliance certification obtained or claimed", gap: "Explicitly out of scope for this project" },
];

export interface DocumentationInconsistency {
  id: string;
  claim: string;
  actualState: string;
  remediationPriority: "High" | "Medium" | "Low";
}

export const INCONSISTENCIES: DocumentationInconsistency[] = [
  {
    id: "i1",
    claim: "Milestone 4 documentation states field-level encryption uses AES-256",
    actualState: "The implementation uses Fernet, which is AES-128-CBC with HMAC authentication — a real, working scheme, but not AES-256 as documented",
    remediationPriority: "Medium",
  },
  {
    id: "i2",
    claim: "Security architecture documentation describes a validated, live AKS deployment",
    actualState: "Terraform for AKS/Key Vault/WAF/networking is designed and passes `terraform validate`, but has never been applied to a live Azure subscription",
    remediationPriority: "High",
  },
  {
    id: "i3",
    claim: "Compliance materials imply continuous WORM audit-log protection is active",
    actualState: "worm_storage.py has only been verified via --dry-run; no Azure Storage account is provisioned or credentialed in this repository",
    remediationPriority: "Medium",
  },
];

export async function getComplianceControls() {
  return mockDelay(COMPLIANCE_CONTROLS, 300);
}

export async function getComplianceSummary() {
  return mockDelay(COMPLIANCE_SUMMARY, 300);
}
