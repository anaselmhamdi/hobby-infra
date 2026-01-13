# Hobby Infrastructure Architecture

Infrastructure for deploying hobby projects on Civo Kubernetes (k3s).

## Stack Overview

```
Cloudflare (DNS + R2 State)
         │
         ▼
Civo Load Balancer (FRA1)
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│              Civo Kubernetes Cluster (k3s)              │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │   Traefik   │  │ cert-manager │  │ cluster-      │  │
│  │  (Ingress)  │  │ (TLS certs)  │  │ autoscaler    │  │
│  └─────────────┘  └──────────────┘  └───────────────┘  │
│                                                         │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │   External  │  │   Grafana    │  │  Uptime Kuma  │  │
│  │   Secrets   │  │    Alloy     │  │  (status page)│  │
│  └─────────────┘  └──────────────┘  └───────────────┘  │
│         │                │                              │
│         ▼                ▼                              │
│  ┌─────────────┐  ┌──────────────┐                     │
│  │  Infisical  │  │   Grafana    │                     │
│  │  Cloud EU   │  │    Cloud     │                     │
│  └─────────────┘  └──────────────┘                     │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │                 App Namespace                    │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐         │   │
│  │  │  app1   │  │  app2   │  │  app3   │   ...   │   │
│  │  └─────────┘  └─────────┘  └─────────┘         │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

## Components

### Civo Cluster
- **Runtime**: k3s (Civo's managed Kubernetes)
- **Region**: FRA1 (Frankfurt)
- **Node pool**: Autoscaled (1-5 nodes, g4s.kube.medium)
- **Default apps disabled**: `-Traefik` (we self-host)

### Traefik Ingress
- Self-hosted via Helm (not Civo's bundled Traefik)
- DaemonSet mode for HA
- Configured for Cloudflare proxy compatibility
- Exposes ports 80 (HTTP) and 443 (HTTPS)

### cert-manager
- Manages TLS certificates automatically
- ClusterIssuer: Let's Encrypt production
- Challenge type: DNS-01 via Cloudflare API
- Supports wildcard certificates

### External Secrets Operator (ESO)
- Syncs secrets from Infisical Cloud to Kubernetes
- SecretStore per namespace
- Configurable sync interval (default: 1h)
- Apps reference ExternalSecret CRDs

### Cluster Autoscaler
- Civo-native autoscaler
- Scales based on pending pods
- Scale-down delay: 10m after add
- Expander strategy: least-waste

### Monitoring
- **Grafana Cloud** (free tier): Metrics, logs, traces
- **Grafana Alloy**: Ships telemetry to Grafana Cloud
- **Uptime Kuma**: Simple uptime checks and status page

## Repository Structure

```
hobby-infra/
├── docs/                    # Documentation
├── terraform/
│   ├── production/          # Main environment
│   │   ├── main.tf          # Cluster, firewall
│   │   ├── providers.tf     # Provider configs
│   │   ├── apps.tf          # Module instantiations
│   │   ├── ingress.tf       # DNS + Ingress resources
│   │   ├── external_secrets.tf
│   │   ├── cert_manager.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   └── modules/             # Reusable modules
│       ├── traefik/
│       ├── cluster-autoscaler/
│       ├── grafana-alloy/
│       └── uptime-kuma/
├── apps/                    # Helm charts for apps
│   ├── _template/           # Copy for new apps
│   └── [app-name]/
├── scripts/
└── .github/workflows/       # CI/CD
```

## Secrets Flow

```
Infisical Cloud EU
        │
        │ (Universal Auth)
        ▼
┌──────────────────┐
│ External Secrets │
│    Operator      │
└────────┬─────────┘
         │
         │ SecretStore (per namespace)
         │ ExternalSecret (per app)
         ▼
┌──────────────────┐
│  Kubernetes      │
│  Secret          │
└────────┬─────────┘
         │
         │ envFrom / volumeMount
         ▼
┌──────────────────┐
│    App Pod       │
└──────────────────┘
```

## Traffic Flow

```
User Request
      │
      ▼
Cloudflare (DNS + optional proxy)
      │
      ▼
Civo Load Balancer
      │
      ▼
Traefik Ingress
      │
      ├─► TLS termination (cert-manager certs)
      │
      ▼
Kubernetes Service
      │
      ▼
App Pod
```

## External Services

| Service | Purpose | Region |
|---------|---------|--------|
| Civo | Kubernetes cluster | FRA1 |
| Cloudflare | DNS, R2 (state), optional CDN | Global |
| Infisical | Secrets management | EU |
| Grafana Cloud | Monitoring | EU |
| Neon | PostgreSQL databases | EU |
| GitHub | Code, container registry, CI/CD | Global |

## CI/CD

### Terraform Workflows
- **On PR**: `terraform plan` runs, posts diff as comment
- **Manual dispatch**: `terraform apply` with approval

### App Deployment
Apps are deployed via Terraform `helm_release`. To deploy:
1. Update image tag in app's `values.yaml`
2. PR → plan → merge → apply

### App Repo CI
Each app repo builds and pushes images:
1. Build Docker image
2. Push to ghcr.io
3. (Optional) Trigger hobby-infra workflow

## Key Design Decisions

1. **Unified infra repo**: All deployment config lives here, app repos are code-only
2. **Terraform over ArgoCD**: Simpler for hobby scale, one less component
3. **Grafana Cloud over self-hosted**: Zero maintenance monitoring
4. **External Secrets over Infisical Operator**: Already proven in xingzap
5. **Cloudflare over Route53**: Consolidate DNS with CDN/R2 capabilities
