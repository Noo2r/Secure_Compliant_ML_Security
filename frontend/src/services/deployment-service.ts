import { mockDelay } from "./api-client";
import type { TerraformResource, K8sResource } from "@/types/domain";

export const TERRAFORM_RESOURCES: TerraformResource[] = [
  { module: "network", logicalName: "vnet-fraud-ml-prod", resourceType: "azurerm_virtual_network", securityNote: "10.20.0.0/16, 3 subnets (WAF DMZ, AKS, private endpoints)" },
  { module: "network", logicalName: "nsg-appgw", resourceType: "azurerm_network_security_group", securityNote: "Only inbound 443 allowed to the WAF subnet" },
  { module: "aks", logicalName: "aks-fraud-ml-prod", resourceType: "azurerm_kubernetes_cluster", securityNote: "Private cluster, Azure AD RBAC, authorized IP ranges" },
  { module: "aks", logicalName: "fraud-inference-sa", resourceType: "kubernetes_service_account (Workload Identity)", securityNote: "OIDC-federated, no stored client secret" },
  { module: "keyvault", logicalName: "kv-fraud-ml-prod", resourceType: "azurerm_key_vault", securityNote: "Public network access disabled, private endpoint only" },
  { module: "keyvault", logicalName: "kv-access-policy-aks", resourceType: "azurerm_key_vault_access_policy", securityNote: "Secrets: Get + List only, scoped to the AKS workload identity" },
  { module: "monitoring", logicalName: "law-fraud-ml-prod", resourceType: "azurerm_log_analytics_workspace", securityNote: "Audit logs, Key Vault access logs, AKS diagnostics, Defender alerts" },
  { module: "monitoring", logicalName: "defender-plan", resourceType: "azurerm_security_center_subscription_pricing", securityNote: "Defender for Cloud continuous scanning" },
  { module: "waf", logicalName: "appgw-fraud-ml-prod", resourceType: "azurerm_application_gateway", securityNote: "WAF_v2 tier, OWASP CRS 3.2, TLS 1.2+ termination" },
  { module: "waf", logicalName: "waf-policy-custom-rules", resourceType: "azurerm_web_application_firewall_policy", securityNote: "Custom rate-limit and geo-block rules (docs/WAF_Rules.md)" },
];

export const K8S_RESOURCES: K8sResource[] = [
  { kind: "Namespace", name: "fraud-inference", purpose: "Isolated namespace for the inference service" },
  { kind: "ServiceAccount", name: "fraud-inference-sa", purpose: "Workload Identity binding, no long-lived credentials" },
  { kind: "Deployment", name: "fraud-inference-api", purpose: "3 replicas of the FastAPI service container" },
  { kind: "Service", name: "fraud-inference-svc", purpose: "ClusterIP service fronting the deployment" },
  { kind: "NetworkPolicy", name: "default-deny-all", purpose: "Deny-by-default baseline for the namespace" },
  { kind: "NetworkPolicy", name: "allow-appgw-ingress", purpose: "Explicit allow from the Application Gateway subnet only" },
];

export async function getTerraformResources(): Promise<TerraformResource[]> {
  return mockDelay(TERRAFORM_RESOURCES, 300);
}

export async function getK8sResources(): Promise<K8sResource[]> {
  return mockDelay(K8S_RESOURCES, 300);
}
