# Runbooks

Common operations for managing the hobby infrastructure.

## Prerequisites

```bash
# Install CLIs
brew install civo terraform kubectl helm

# Authenticate to Civo
civo apikey add hobby-infra YOUR_API_KEY
civo apikey current hobby-infra
civo region use FRA1

# Get kubeconfig
civo kubernetes config hobby-cluster --save
```

## Terraform Operations

### Initialize (first time)
```bash
cd terraform/production
terraform init
```

### Plan changes
```bash
terraform plan -var-file=secrets.tfvars
```

### Apply changes
```bash
terraform apply -var-file=secrets.tfvars
```

### View state
```bash
terraform state list
terraform state show module.traefik.helm_release.traefik
```

## Cluster Operations

### Get cluster info
```bash
civo kubernetes show hobby-cluster
kubectl get nodes
kubectl get pods -A
```

### View cluster events
```bash
kubectl get events -A --sort-by='.lastTimestamp'
```

### Check resource usage
```bash
kubectl top nodes
kubectl top pods -A
```

### Scale node pool manually
```bash
# Via Civo CLI (autoscaler will adjust)
civo kubernetes node-pool scale hobby-cluster POOL_ID --nodes 3
```

## Traefik Operations

### Check Traefik status
```bash
kubectl get pods -n kube-system -l app.kubernetes.io/name=traefik
kubectl logs -n kube-system -l app.kubernetes.io/name=traefik -f
```

### View ingress routes
```bash
kubectl get ingressroute -A
kubectl get ingress -A
```

### Get LoadBalancer IP
```bash
kubectl get svc -n kube-system traefik -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
```

## Certificate Operations

### Check cert-manager
```bash
kubectl get pods -n cert-manager
kubectl get clusterissuer
```

### View certificates
```bash
kubectl get certificates -A
kubectl get certificaterequests -A
```

### Debug certificate issues
```bash
kubectl describe certificate <name> -n <namespace>
kubectl describe certificaterequest <name> -n <namespace>
kubectl logs -n cert-manager -l app=cert-manager -f
```

### Force certificate renewal
```bash
kubectl delete secret <cert-secret-name> -n <namespace>
# cert-manager will recreate it
```

## Secrets Operations

### Check External Secrets Operator
```bash
kubectl get pods -n external-secrets
kubectl get secretstores -A
kubectl get externalsecrets -A
```

### View sync status
```bash
kubectl get externalsecret <name> -n <namespace> -o yaml
```

### Force secret sync
```bash
kubectl annotate externalsecret <name> -n <namespace> \
  force-sync=$(date +%s) --overwrite
```

### Debug secret issues
```bash
kubectl describe externalsecret <name> -n <namespace>
kubectl logs -n external-secrets -l app.kubernetes.io/name=external-secrets -f
```

## App Operations

### Deploy an app
```bash
cd apps/<app-name>
helm upgrade --install <app-name> . -n <namespace> --create-namespace
```

### View app status
```bash
kubectl get pods -n <namespace>
kubectl get svc -n <namespace>
kubectl get ingress -n <namespace>
```

### View app logs
```bash
kubectl logs -n <namespace> -l app=<app-name> -f
```

### Restart app
```bash
kubectl rollout restart deployment/<app-name> -n <namespace>
```

### Scale app
```bash
kubectl scale deployment/<app-name> -n <namespace> --replicas=2
```

### Debug app issues
```bash
kubectl describe pod <pod-name> -n <namespace>
kubectl exec -it <pod-name> -n <namespace> -- /bin/sh
```

## Monitoring Operations

### Check Grafana Alloy
```bash
kubectl get pods -n monitoring -l app.kubernetes.io/name=alloy
kubectl logs -n monitoring -l app.kubernetes.io/name=alloy -f
```

### Check Uptime Kuma
```bash
kubectl get pods -n monitoring -l app=uptime-kuma
kubectl port-forward -n monitoring svc/uptime-kuma 3001:3001
# Open http://localhost:3001
```

## Autoscaler Operations

### Check autoscaler status
```bash
kubectl get pods -n kube-system -l app.kubernetes.io/name=cluster-autoscaler
kubectl logs -n kube-system -l app.kubernetes.io/name=cluster-autoscaler -f
```

### View scaling activity
```bash
kubectl get events -n kube-system --field-selector reason=ScaledUpGroup
kubectl get events -n kube-system --field-selector reason=ScaleDown
```

## Troubleshooting

### Pod won't start
```bash
kubectl describe pod <pod-name> -n <namespace>
kubectl get events -n <namespace> --sort-by='.lastTimestamp'
```

### Service not accessible
```bash
# Check service exists
kubectl get svc -n <namespace>

# Check endpoints
kubectl get endpoints -n <namespace>

# Check ingress
kubectl get ingress -n <namespace>
kubectl describe ingress <ingress-name> -n <namespace>

# Check Traefik logs
kubectl logs -n kube-system -l app.kubernetes.io/name=traefik | grep <hostname>
```

### Certificate not issuing
```bash
kubectl describe certificate <name> -n <namespace>
kubectl describe certificaterequest <name> -n <namespace>
kubectl describe challenge -A
kubectl logs -n cert-manager -l app=cert-manager
```

### Secrets not syncing
```bash
kubectl describe externalsecret <name> -n <namespace>
kubectl describe secretstore <name> -n <namespace>
kubectl logs -n external-secrets -l app.kubernetes.io/name=external-secrets
```

## Emergency Procedures

### Rollback Terraform
```bash
# View previous state versions in R2
# Restore from R2 console if needed

# Or use terraform state
terraform state pull > backup.tfstate
```

### Rollback app deployment
```bash
helm rollback <app-name> <revision> -n <namespace>
helm history <app-name> -n <namespace>
```

### Cluster recovery
```bash
# If cluster is accessible
civo kubernetes show hobby-cluster

# If cluster is unreachable, recreate
# (All state is in Terraform, apps redeploy automatically)
terraform apply -var-file=secrets.tfvars
```
