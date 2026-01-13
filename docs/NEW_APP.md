# Adding a New App

Guide for deploying a new hobby project to the cluster.

## Prerequisites

Before deploying, ensure your app repo has:
- `Dockerfile` with `EXPOSE` for the port
- `.env.example` listing required environment variables
- `README.md` with any special notes (health checks, dependencies)
- Secrets stored in Infisical under the project path

## Quick Start

### 1. Copy the template
```bash
cp -r apps/_template apps/my-app
```

### 2. Update Chart.yaml
```yaml
# apps/my-app/Chart.yaml
apiVersion: v2
name: my-app
version: 0.1.0
appVersion: "1.0.0"
```

### 3. Configure values.yaml
```yaml
# apps/my-app/values.yaml
replicaCount: 1

image:
  repository: ghcr.io/yourusername/my-app
  tag: latest
  pullPolicy: Always

service:
  port: 3000  # From Dockerfile EXPOSE

ingress:
  enabled: true
  host: my-app.yourdomain.com
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod

resources:
  requests:
    cpu: 50m
    memory: 128Mi
  limits:
    cpu: 200m
    memory: 256Mi

# Health checks (update paths for your app)
livenessProbe:
  path: /health
  port: 3000
readinessProbe:
  path: /health
  port: 3000

# Secrets from Infisical
externalSecret:
  enabled: true
  secretStoreName: infisical-secret-store
  refreshInterval: 1h
  # Keys to sync from Infisical
  data:
    - secretKey: DATABASE_URL
      remoteRef:
        key: MY_APP_DATABASE_URL
    - secretKey: API_KEY
      remoteRef:
        key: MY_APP_API_KEY
```

### 4. Add DNS record in ingress.tf
```hcl
# terraform/production/ingress.tf
resource "cloudflare_record" "my_app" {
  zone_id = var.cloudflare_zone_id
  name    = "my-app"
  value   = data.civo_loadbalancer.main.public_ip
  type    = "A"
  proxied = true  # or false for direct access
}
```

### 5. Add Helm release in apps.tf
```hcl
# terraform/production/apps.tf
resource "helm_release" "my_app" {
  name       = "my-app"
  namespace  = "apps"
  chart      = "${path.module}/../../apps/my-app"

  values = [
    file("${path.module}/../../apps/my-app/values.yaml")
  ]

  depends_on = [
    helm_release.external_secrets,
    kubernetes_manifest.secret_store
  ]
}
```

### 6. Deploy
```bash
cd terraform/production
terraform plan
terraform apply
```

## Template Files Explained

### templates/deployment.yaml
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ .Release.Name }}
spec:
  replicas: {{ .Values.replicaCount }}
  selector:
    matchLabels:
      app: {{ .Release.Name }}
  template:
    metadata:
      labels:
        app: {{ .Release.Name }}
    spec:
      containers:
        - name: {{ .Release.Name }}
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
          ports:
            - containerPort: {{ .Values.service.port }}
          envFrom:
            - secretRef:
                name: {{ .Release.Name }}-secrets
          {{- if .Values.livenessProbe }}
          livenessProbe:
            httpGet:
              path: {{ .Values.livenessProbe.path }}
              port: {{ .Values.livenessProbe.port }}
            initialDelaySeconds: 30
            periodSeconds: 10
          {{- end }}
          resources:
            {{- toYaml .Values.resources | nindent 12 }}
```

### templates/service.yaml
```yaml
apiVersion: v1
kind: Service
metadata:
  name: {{ .Release.Name }}
spec:
  type: ClusterIP
  ports:
    - port: {{ .Values.service.port }}
      targetPort: {{ .Values.service.port }}
  selector:
    app: {{ .Release.Name }}
```

### templates/ingress.yaml
```yaml
{{- if .Values.ingress.enabled }}
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {{ .Release.Name }}
  annotations:
    {{- toYaml .Values.ingress.annotations | nindent 4 }}
spec:
  ingressClassName: traefik
  tls:
    - hosts:
        - {{ .Values.ingress.host }}
      secretName: {{ .Release.Name }}-tls
  rules:
    - host: {{ .Values.ingress.host }}
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: {{ .Release.Name }}
                port:
                  number: {{ .Values.service.port }}
{{- end }}
```

### templates/external-secret.yaml
```yaml
{{- if .Values.externalSecret.enabled }}
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: {{ .Release.Name }}-secrets
spec:
  refreshInterval: {{ .Values.externalSecret.refreshInterval }}
  secretStoreRef:
    name: {{ .Values.externalSecret.secretStoreName }}
    kind: SecretStore
  target:
    name: {{ .Release.Name }}-secrets
    creationPolicy: Owner
  data:
    {{- range .Values.externalSecret.data }}
    - secretKey: {{ .secretKey }}
      remoteRef:
        key: {{ .remoteRef.key }}
    {{- end }}
{{- end }}
```

## Working with Claude

When adding a new app, you can ask Claude to generate the Helm chart by pointing to the app repo:

> "Add my-app from ~/Projects/my-app to hobby-infra"

Claude will read:
- `Dockerfile` for port and entrypoint
- `.env.example` for required secrets
- `README.md` for health checks and notes
- `CLAUDE.md` for specific instructions

And generate the appropriate chart in `apps/my-app/`.

## Checklist

- [ ] App repo has Dockerfile with EXPOSE
- [ ] Secrets are in Infisical
- [ ] Chart.yaml has correct name and version
- [ ] values.yaml has correct image, port, host
- [ ] DNS record added in ingress.tf
- [ ] Helm release added in apps.tf
- [ ] terraform plan shows expected changes
- [ ] terraform apply succeeds
- [ ] App is accessible at https://my-app.yourdomain.com
- [ ] TLS certificate is valid
- [ ] Secrets are properly injected

## Troubleshooting

### App not starting
```bash
kubectl describe pod -n apps -l app=my-app
kubectl logs -n apps -l app=my-app
```

### Secrets not available
```bash
kubectl get externalsecret -n apps my-app-secrets
kubectl describe externalsecret -n apps my-app-secrets
```

### Certificate not issuing
```bash
kubectl get certificate -n apps
kubectl describe certificate -n apps my-app-tls
```

### Ingress not working
```bash
kubectl get ingress -n apps
kubectl describe ingress -n apps my-app
kubectl logs -n kube-system -l app.kubernetes.io/name=traefik
```
