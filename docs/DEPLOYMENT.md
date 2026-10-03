# UGC Marketplace Deployment Guide

> Production deployment guide for Docker, Kubernetes, and Terraform.

**Last Updated**: 2024-03-15

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Architecture Overview](#architecture-overview)
- [Docker Deployment](#docker-deployment)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Terraform Infrastructure](#terraform-infrastructure)
- [Environment Variables](#environment-variables)
- [SSL/TLS Configuration](#tls-configuration)
- [Monitoring & Alerting](#monitoring--alerting)
- [Backup & Disaster Recovery](#backup--disaster-recovery)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Tools

| Tool | Version | Purpose |
|------|---------|---------|
| Docker | >= 24.0 | Container runtime |
| Docker Compose | >= 2.20 | Local orchestration |
| kubectl | >= 1.28 | Kubernetes CLI |
| Helm | >= 3.12 | K8s package manager |
| Terraform | >= 1.5 | Infrastructure as Code |
| AWS CLI | >= 2.13 | AWS operations |
| Helmfile | >= 0.155 | Helm release management |

### Cloud Provider Accounts

- [AWS Account](https://aws.amazon.com/) with appropriate IAM permissions
- [Stripe Account](https://stripe.com/) for payment processing
- [SendGrid Account](https://sendgrid.com/) for transactional email
- [Sentry Account](https://sentry.io/) for error tracking

---

## Architecture Overview

```mermaid
graph LR
    subgraph "Internet"
        USERS[Users]
    end

    subgraph "AWS Cloud"
        subgraph "Edge"
            CF[CloudFront CDN]
            WAF[AWS WAF]
            R53[Route 53]
        end

        subgraph "EKS Cluster"
            subgraph "Ingress"
                ALB[AWS ALB Ingress Controller]
                NGINX[NGINX Ingress]
            end

            subgraph "Apps"
                API[API Pods<br/>HPA: 3-20]
                WEB[Web Pods<br/>HPA: 2-10]
                WORKER[Worker Pods<br/>HPA: 2-10]
            end

            subgraph "Data"
                RDS[(RDS PostgreSQL<br/>Multi-AZ)]
                DOCDB[(DocumentDB)]
                ELASTICACHE[(ElastiCache Redis)]
                OPENSEARCH[(OpenSearch)]
                MSK[(MSK Kafka)]
            end

            subgraph "Storage"
                S3[(S3 Bucket<br/>Assets)]
                EBS[(EBS Volumes)]
            end
        end

        subgraph "Monitoring"
            CW[CloudWatch]
            PROM[Prometheus]
            GRAFANA[Grafana]
            SENTRY[Sentry]
        end
    end

    USERS --> R53 --> CF --> WAF --> ALB
    ALB --> NGINX
    NGINX --> API
    NGINX --> WEB
    API --> RDS
    API --> DOCDB
    API --> ELASTICACHE
    API --> OPENSEARCH
    API --> S3
    API --> MSK
    WORKER --> MSK
    WORKER --> S3
    API --> PROM
    API --> SENTRY
```

---

## Docker Deployment

### Quick Start (Development)

```bash
# Clone repository
git clone https://github.com/ugc-marketplace/ugc-marketplace.git
cd ugc-marketplace

# Copy environment file
cp .env.example .env

# Start all services
docker-compose up -d

# Run migrations
docker-compose exec api npm run migrate

# Seed database
docker-compose exec api npm run seed

# View logs
docker-compose logs -f api
```

### Production Docker Compose

```bash
# Use production compose file
docker-compose -f docker-compose.prod.yml up -d

# Scale API containers
docker-compose -f docker-compose.prod.yml up -d --scale api=4

# Rolling update
docker-compose -f docker-compose.prod.yml up -d --no-deps --build api
```

### Docker Compose Production Configuration

```yaml
# docker-compose.prod.yml
version: "3.9"

services:
  api:
    build:
      context: .
      dockerfile: apps/api/Dockerfile
      target: production
    image: ugc-marketplace/api:${VERSION:-latest}
    restart: always
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: "1.0"
          memory: 1G
        reservations:
          cpus: "0.5"
          memory: 512M
    environment:
      - NODE_ENV=production
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - ELASTICSEARCH_URL=${ELASTICSEARCH_URL}
      - S3_BUCKET=${S3_BUCKET}
      - JWT_SECRET=${JWT_SECRET}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    networks:
      - backend

  web:
    build:
      context: .
      dockerfile: apps/web/Dockerfile
    image: ugc-marketplace/web:${VERSION:-latest}
    restart: always
    deploy:
      replicas: 2
    networks:
      - backend

  worker:
    build:
      context: .
      dockerfile: apps/worker/Dockerfile
    image: ugc-marketplace/worker:${VERSION:-latest}
    restart: always
    deploy:
      replicas: 2
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - KAFKA_BROKERS=${KAFKA_BROKERS}
    networks:
      - backend

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./infrastructure/docker/nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./infrastructure/docker/nginx/ssl:/etc/nginx/ssl:ro
    depends_on:
      - api
      - web
    networks:
      - backend

networks:
  backend:
    driver: bridge
```

### Building Production Images

```bash
# Build all images
docker compose -f docker-compose.prod.yml build

# Build specific service
docker compose -f docker-compose.prod.yml build api

# Tag and push to registry
docker tag ugc-marketplace/api:latest ${REGISTRY}/ugc-marketplace/api:${VERSION}
docker push ${REGISTRY}/ugc-marketplace/api:${VERSION}
```

---

## Kubernetes Deployment

### Prerequisites

```bash
# Create EKS cluster
eksctl create cluster \
  --name ugc-marketplace-prod \
  --region us-east-1 \
  --node-type m5.xlarge \
  --nodes-min 3 \
  --nodes-max 10 \
  --managed

# Install AWS Load Balancer Controller
helm repo add eks https://aws.github.io/eks-charts
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  --set clusterName=ugc-marketplace-prod

# Install NGINX Ingress Controller
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm install nginx-ingress ingress-nginx/ingress-nginx \
  --set controller.service.annotations."service\.beta\.kubernetes\.io/aws-load-balancer-type"="nlb"

# Install cert-manager
helm repo add jetstack https://charts.jetstack.io
helm install cert-manager jetstack/cert-manager \
  --set installCRDs=true

# Install Prometheus Stack
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install kube-prometheus-stack prometheus-community/kube-prometheus-stack
```

### Namespace Setup

```yaml
# infrastructure/kubernetes/00-namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ugc-marketplace
  labels:
    app.kubernetes.io/name: ugc-marketplace
    app.kubernetes.io/component: namespace
---
apiVersion: v1
kind: ResourceQuota
metadata:
  name: ugc-marketplace-quota
  namespace: ugc-marketplace
spec:
  hard:
    requests.cpu: "20"
    requests.memory: 40Gi
    limits.cpu: "40"
    limits.memory: 80Gi
    pods: "100"
---
apiVersion: v1
kind: LimitRange
metadata:
  name: ugc-marketplace-limits
  namespace: ugc-marketplace
spec:
  limits:
    - default:
        cpu: 500m
        memory: 512Mi
      defaultRequest:
        cpu: 100m
        memory: 128Mi
      max:
        cpu: "4"
        memory: 8Gi
      min:
        cpu: 50m
        memory: 64Mi
      type: Container
```

### ConfigMap

```yaml
# infrastructure/kubernetes/01-configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: ugc-marketplace-config
  namespace: ugc-marketplace
data:
  NODE_ENV: "production"
  PORT: "3000"
  API_VERSION: "v1"
  CORS_ORIGIN: "https://ugc-marketplace.io"
  LOG_LEVEL: "info"
  S3_REGION: "us-east-1"
  S3_BUCKET: "ugc-marketplace-assets-prod"
  ELASTICSEARCH_INDEX: "ugc_content"
  KAFKA_CLIENT_ID: "ugc-marketplace-api"
```

### Secret

```yaml
# infrastructure/kubernetes/02-secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: ugc-marketplace-secrets
  namespace:ugc-marketplace
type: Opaque
stringData:
  DATABASE_URL: "postgresql://user:password@rds-endpoint:5432/ugc_marketplace"
  REDIS_URL: "rediss://:password@elasticache-endpoint:6379"
  ELASTICSEARCH_URL: "https://opensearch-endpoint:9200"
  JWT_SECRET: "<generate-with-openssl-rand-base64-32>"
  STRIPE_SECRET_KEY: "sk_live_..."
  STRIPE_WEBHOOK_SECRET: "whsec_..."
  S3_ACCESS_KEY: "AKIA..."
  S3_SECRET_KEY: "..."
  SENDGRID_API_KEY: "SG...."
  SENTRY_DSN: "https://..."
```

### API Deployment

```yaml
# infrastructure/kubernetes/03-api-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
  namespace: ugc-marketplace
  labels:
    app: api
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: api
  template:
    metadata:
      labels:
        app: api
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "3000"
        prometheus.io/path: "/metrics"
    spec:
      serviceAccountName: ugc-marketplace-api
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
      containers:
        - name: api
          image: ugc-marketplace/api:latest
          imagePullPolicy: Always
          ports:
            - containerPort: 3000
              protocol: TCP
          envFrom:
            - configMapRef:
                name: ugc-marketplace-config
            - secretRef:
                name: ugc-marketplace-secrets
          resources:
            requests:
              cpu: 500m
              memory: 512Mi
            limits:
              cpu: "2"
              memory: 2Gi
          livenessProbe:
            httpGet:
              path: /health/live
              port: 3000
            initialDelaySeconds: 30
            periodSeconds: 10
            timeoutSeconds: 5
            failureThreshold: 3
          readinessProbe:
            httpGet:
              path: /health/ready
              port: 3000
            initialDelaySeconds: 10
            periodSeconds: 5
            timeoutSeconds: 3
            failureThreshold: 3
          startupProbe:
            httpGet:
              path: /health/startup
              port: 3000
            initialDelaySeconds: 10
            periodSeconds: 5
            failureThreshold: 30
          volumeMounts:
            - name: tmp
              mountPath: /tmp
      volumes:
        - name: tmp
          emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: api
  namespace: ugc-marketplace
  labels:
    app: api
spec:
  type: ClusterIP
  ports:
    - port: 80
      targetPort: 3000
      protocol: TCP
  selector:
    app: api
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api-hpa
  namespace: ugc-marketplace
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api
  minReplicas: 3
  maxReplicas: 20
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
        - type: Pods
          value: 4
          periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
        - type: Pods
          value: 2
          periodSeconds: 120
```

### Web Deployment

```yaml
# infrastructure/kubernetes/04-web-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  namespace: ugc-marketplace
  labels:
    app: web
spec:
  replicas: 2
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
      containers:
        - name: web
          image: ugc-marketplace/web:latest
          imagePullPolicy: Always
          ports:
            - containerPort: 80
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 512Mi
          livenessProbe:
            httpGet:
              path: /
              port: 80
            initialDelaySeconds: 10
            periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: web
  namespace: ugc-marketplace
spec:
  type: ClusterIP
  ports:
    - port: 80
      targetPort: 80
  selector:
    app: web
```

### Worker Deployment

```yaml
# infrastructure/kubernetes/05-worker-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: worker
  namespace: ugc-marketplace
  labels:
    app: worker
spec:
  replicas: 2
  selector:
    matchLabels:
      app: worker
  template:
    metadata:
      labels:
        app: worker
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
      containers:
        - name: worker
          image: ugc-marketplace/worker:latest
          imagePullPolicy: Always
          envFrom:
            - configMapRef:
                name: ugc-marketplace-config
            - secretRef:
                name: ugc-marketplace-secrets
          resources:
            requests:
              cpu: 250m
              memory: 256Mi
            limits:
              cpu: "1"
              memory: 1Gi
```

### Ingress

```yaml
# infrastructure/kubernetes/06-ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ugc-marketplace-ingress
  namespace: ugc-marketplace
  annotations:
    kubernetes.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/proxy-body-size: "50m"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "300"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "300"
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/rate-limit-window: "1m"
spec:
  ingressClassName: nginx
  tls:
    - hosts:
        - api.ugc-marketplace.io
        - ugc-marketplace.io
      secretName: ugc-marketplace-tls
  rules:
    - host: api.ugc-marketplace.io
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: api
                port:
                  number: 80
    - host: ugc-marketplace.io
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: web
                port:
                  number: 80
```

### Apply All Manifests

```bash
# Apply all Kubernetes manifests
kubectl apply -f infrastructure/kubernetes/

# Or use Kustomize
kubectl apply -k infrastructure/kubernetes/overlays/production/

# Verify deployment
kubectl get pods -n ugc-marketplace
kubectl get svc -n ugc-marketplace
kubectl get ingress -n ugc-marketplace
```

### Helm Chart Deployment

```bash
# Add Helm repository
helm repo add ugc-marketplace https://charts.ugc-marketplace.io
helm repo update

# Install with custom values
helm install ugc-marketplace ugc-marketplace/ugc-marketplace \
  --namespace ugc-marketplace \
  --create-namespace \
  -f infrastructure/kubernetes/values-production.yaml

# Upgrade
helm upgrade ugc-marketplace ugc-marketplace/ugc-marketplace \
  --namespace ugc-marketplace \
  -f infrastructure/kubernetes/values-production.yaml

# Rollback
helm rollback ugc-marketplace 1 --namespace ugc-marketplace
```

---

## Terraform Infrastructure

### AWS Infrastructure

```hcl
# infrastructure/terraform/main.tf
terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "ugc-marketplace-terraform-state"
    key            = "production/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-state-lock"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "ugc-marketplace"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# Variables
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "cluster_name" {
  description = "EKS cluster name"
  type        = string
  default     = "ugc-marketplace-prod"
}

# VPC
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "${var.cluster_name}-vpc"
  cidr = "10.0.0.0/16"

  azs             = ["${var.aws_region}a", "${var.aws_region}b", "${var.aws_region}c"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]

  enable_nat_gateway     = true
  single_nat_gateway     = false
  enable_dns_hostnames   = true
  enable_dns_support     = true

  public_subnet_tags = {
    "kubernetes.io/role/elb" = "1"
  }

  private_subnet_tags = {
    "kubernetes.io/role/internal-elb" = "1"
  }
}

# EKS Cluster
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 19.0"

  cluster_name    = var.cluster_name
  cluster_version = "1.28"

  vpc_id                         = module.vpc.vpc_id
  subnet_ids                     = module.vpc.private_subnets
  control_plane_subnet_ids       = module.vpc.private_subnets

  cluster_endpoint_private_access = true
  cluster_endpoint_public_access  = true

  cluster_addons = {
    coredns = {
      most_recent = true
    }
    kube-proxy = {
      most_recent = true
    }
    vpc-cni = {
      most_recent = true
    }
    aws-ebs-csi-driver = {
      most_recent = true
    }
  }

  eks_managed_node_groups = {
    general = {
      desired_size = 3
      min_size     = 3
      max_size     = 10

      instance_types = ["m5.xlarge"]
      capacity_type  = "ON_DEMAND"

      labels = {
        workload = "general"
      }

      update_config = {
        max_unavailable_percentage = 25
      }
    }

    spot = {
      desired_size = 2
      min_size     = 0
      max_size     = 10

      instance_types = ["m5.large", "m5a.large", "m4.large"]
      capacity_type  = "SPOT"

      labels = {
        workload = "spot"
      }

      taints = [{
        key    = "spot"
        value  = "true"
        effect = "NO_SCHEDULE"
      }]
    }
  }
}

# RDS PostgreSQL
module "rds" {
  source  = "terraform-aws-modules/rds/aws"
  version = "~> 6.0"

  identifier = "${var.cluster_name}-postgres"

  engine               = "postgres"
  engine_version       = "15.4"
  family               = "postgres15"
  major_engine_version = "15"
  instance_class       = "db.r6g.xlarge"

  allocated_storage     = 100
  max_allocated_storage = 500

  db_name  = "ugc_marketplace"
  username = "ugc_admin"
  port     = 5432

  multi_az               = true
  db_subnet_group_name   = module.vpc.database_subnet_group
  vpc_security_group_ids = [aws_security_group.rds.id]

  maintenance_window      = "Mon:00:00-Mon:03:00"
  backup_window           = "03:00-06:00"
  backup_retention_period = 30

  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]
  create_cloudwatch_log_group     = true

  performance_insights_enabled    = true
  performance_insights_retention_period = 7

  deletion_protection = true
  storage_encrypted   = true
}

# ElastiCache Redis
module "elasticache" {
  source  = "terraform-aws-modules/elasticache/aws"
  version = "~> 1.0"

  cluster_id               = "${var.cluster_name}-redis"
  description              = "Redis cluster for UGC Marketplace"
  node_type                = "cache.r6g.large"
  num_cache_nodes          = 2
  engine_version           = "7.0"
  port                     = 6379
  parameter_group_name     = "default.redis7.cluster.on"
  automatic_failover_enabled = true
  multi_az_enabled         = true

  subnet_group_name        = aws_elasticache_subnet_group.redis.name
  security_group_ids       = [aws_security_group.redis.id]

  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
}

# S3 Bucket
resource "aws_s3_bucket" "assets" {
  bucket = "${var.cluster_name}-assets"
}

resource "aws_s3_bucket_versioning" "assets" {
  bucket = aws_s3_bucket.assets.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "assets" {
  bucket = aws_s3_bucket.assets.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "assets" {
  bucket = aws_s3_bucket.assets.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# CloudFront Distribution
resource "aws_cloudfront_distribution" "cdn" {
  enabled             = true
  is_ipv6_enabled     = true
  comment             = "UGC Marketplace CDN"
  default_root_object = "index.html"
  price_class         = "PriceClass_100"

  origin {
    domain_name = aws_s3_bucket.assets.bucket_regional_domain_name
    origin_id   = "S3-${aws_s3_bucket.assets.id}"

    s3_origin_config {
      origin_access_identity = aws_cloudfront_origin_access_identity.oai.cloudfront_access_identity_path
    }
  }

  origin {
    domain_name = "api.ugc-marketplace.io"
    origin_id   = "API"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  default_cache_behavior {
    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "S3-${aws_s3_bucket.assets.id}"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 86400
    max_ttl                = 31536000
    compress               = true
  }

  ordered_cache_behavior {
    path_pattern     = "/api/*"
    allowed_methods  = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "API"

    forwarded_values {
      query_string = true
      headers      = ["Authorization", "Origin"]
      cookies {
        forward = "all"
      }
    }

    viewer_protocol_policy = "https-only"
    min_ttl                = 0
    default_ttl            = 0
    max_ttl                = 0
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    acm_certificate_arn      = aws_acm_certificate.cdn.arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }
}

# Security Groups
resource "aws_security_group" "rds" {
  name_prefix = "${var.cluster_name}-rds-"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = module.vpc.private_subnets_cidr_blocks
  }
}

resource "aws_security_group" "redis" {
  name_prefix = "${var.cluster_name}-redis-"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port   = 6379
    to_port     = 6379
    protocol    = "tcp"
    cidr_blocks = module.vpc.private_subnets_cidr_blocks
  }
}

# Outputs
output "cluster_endpoint" {
  description = "EKS cluster endpoint"
  value       = module.eks.cluster_endpoint
}

output "rds_endpoint" {
  description = "RDS PostgreSQL endpoint"
  value       = module.rds.db_instance_address
  sensitive   = true
}

output "redis_endpoint" {
  description = "ElastiCache Redis endpoint"
  value       = module.elasticache.cluster_address
  sensitive   = true
}

output "s3_bucket_name" {
  description = "S3 assets bucket name"
  value       = aws_s3_bucket.assets.id
}

output "cloudfront_domain" {
  description = "CloudFront distribution domain"
  value       = aws_cloudfront_distribution.cdn.domain_name
}
```

### Terraform Commands

```bash
# Initialize Terraform
cd infrastructure/terraform/
terraform init

# Validate configuration
terraform validate

# Plan changes
terraform plan -var-file="production.tfvars" -out=tfplan

# Apply changes
terraform apply tfplan

# Destroy infrastructure (CAUTION)
terraform destroy -var-file="production.tfvars"
```

### Terraform Variables File

```hcl
# infrastructure/terraform/production.tfvars
aws_region    = "us-east-1"
environment   = "production"
cluster_name  = "ugc-marketplace-prod"
```

---

## Environment Variables

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@host:5432/db` |
| `REDIS_URL` | Redis connection string | `rediss://:pass@host:6379` |
| `ELASTICSEARCH_URL` | Elasticsearch URL | `https://host:9200` |
| `JWT_SECRET` | JWT signing secret | `<64-char-random>` |
| `S3_BUCKET` | S3 bucket for assets | `ugc-marketplace-assets-prod` |
| `S3_REGION` | S3 region | `us-east-1` |
| `S3_ACCESS_KEY` | S3 access key | `AKIA...` |
| `S3_SECRET_KEY` | S3 secret key | `...` |
| `STRIPE_SECRET_KEY` | Stripe secret key | `sk_live_...` |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook secret | `whsec_...` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PORT` | API server port | `3000` |
| `NODE_ENV` | Environment mode | `production` |
| `LOG_LEVEL` | Logging level | `info` |
| `CORS_ORIGIN` | Allowed CORS origins | `https://ugc-marketplace.io` |
| `SENDGRID_API_KEY` | SendGrid API key | — |
| `SENTRY_DSN` | Sentry DSN | — |
| `KAFKA_BROKERS` | Kafka broker list | — |
| `UPLOAD_MAX_SIZE` | Max upload size (bytes) | `52428800` |

---

## SSL/TLS Configuration

### cert-manager with Let's Encrypt

```yaml
# infrastructure/kubernetes/cert-issuer.yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@ugc-marketplace.io
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
      - http01:
          ingress:
            class: nginx
```

### AWS ACM Certificate

```bash
# Request certificate
aws acm request-certificate \
  --domain-name ugc-marketplace.io \
  --subject-alternative-names *.ugc-marketplace.io \
  --validation-method DNS \
  --region us-east-1

# Validate via Route 53 (automated with terraform-acm module)
```

---

## Monitoring & Alerting

### Prometheus Rules

```yaml
# infrastructure/kubernetes/monitoring/prometheus-rules.yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: ugc-marketplace-alerts
  namespace: ugc-marketplace
spec:
  groups:
    - name: api-alerts
      rules:
        - alert: APIHighErrorRate
          expr: |
            sum(rate(http_requests_total{status=~"5.."}[5m]))
            / sum(rate(http_requests_total[5m])) > 0.05
          for: 5m
          labels:
            severity: critical
          team: backend
          annotations:
            summary: "API error rate is above 5%"
            description: "Error rate is {{ $value | humanizePercentage }}"

        - alert: APIHighLatency
          expr: |
            histogram_quantile(0.95,
              sum(rate(http_request_duration_seconds_bucket[5m])) by (le)
            ) > 2
          for: 5m
          labels:
            severity: warning
            team: backend
          annotations:
            summary: "API P95 latency is above 2s"

        - alert: PodCrashLooping
          expr: |
            rate(kube_pod_container_status_restarts_total[15m]) > 0
          for: 5m
          labels:
            severity: critical
          annotations:
            summary: "Pod {{ $labels.pod }} is crash looping"

        - alert: HighMemoryUsage
          expr: |
            container_memory_usage_bytes{container!=""}
            / container_spec_memory_limit_bytes{container!=""} > 0.85
          for: 10m
          labels:
            severity: warning
          annotations:
            summary: "High memory usage on {{ $labels.pod }}"
```

### Grafana Dashboard

Import the provided dashboard JSON:

```bash
# Import dashboard via API
curl -X POST \
  -H "Authorization: Bearer ${GRAFANA_API_KEY}" \
  -H "Content-Type: application/json" \
  -d @infrastructure/kubernetes/monitoring/dashboard.json \
  https://grafana.ugc-marketplace.io/api/dashboards/db
```

### Key Metrics to Monitor

| Metric | Threshold | Alert |
|--------|-----------|-------|
| API Error Rate | > 5% | Critical |
| API P95 Latency | > 2s | Warning |
| API P99 Latency | > 5s | Critical |
| Pod Restart Count | > 3 in 15m | Warning |
| CPU Utilization | > 80% | Warning |
| Memory Utilization | > 85% | Warning |
| Disk Usage | > 80% | Warning |
| DB Connection Pool | > 80% | Warning |
| Queue Depth | > 1000 | Warning |

---

## Backup & Disaster Recovery

### Database Backups

```bash
# Automated RDS snapshots (configured in Terraform)
# Retention: 30 days

# Manual snapshot
aws rds create-db-snapshot \
  --db-instance-identifier ugc-marketplace-prod-postgres \
  --db-snapshot-identifier manual-$(date +%Y%m%d-%H%M%S)

# Point-in-time recovery
aws rds restore-db-instance-to-point-in-time \
  --source-db-instance-identifier ugc-marketplace-prod-postgres \
  --target-db-instance-identifier ugc-marketplace-recovery \
  --restore-time 2024-03-15T00:00:00Z
```

### S3 Backup Strategy

```bash
# Enable cross-region replication
# Primary: us-east-1
# Replica: us-west-2

# Lifecycle policy for old versions
aws s3api put-bucket-lifecycle-configuration \
  --bucket ugc-marketplace-assets-prod \
  --lifecycle-configuration file://infrastructure/terraform/s3-lifecycle.json
```

### Disaster Recovery Runbook

```mermaid
graph TD
    A[Incident Detected] --> B{Severity?}
    B -->|P1 - Critical| C[Page On-Call Engineer]
    B -->|P2 - High| D[Create Incident Channel]
    C --> E[Assess Impact]
    D --> E
    E --> F{Data Loss?}
    F -->|Yes| G[Initiate PITR Recovery]
    F -->|No| H[Failover to Standby]
    G --> I[Verify Data Integrity]
    H --> I
    I --> J[Update DNS / Route 53]
    J --> K[Verify Service Health]
    K --> L[Post-Incident Review]
```

---

## Troubleshooting

### Common Issues

#### Pod Stuck in Pending

```bash
# Check events
kubectl describe pod <pod-name> -n ugc-marketplace

# Common causes:
# - Insufficient cluster capacity
# - PVC not bound
# - Node selector/taint mismatch
# - Image pull errors
```

#### Database Connection Issues

```bash
# Test connectivity from pod
kubectl run -it --rm debug --image=postgres:15 --restart=Never -- \
  psql $DATABASE_URL -c "SELECT 1;"

# Check connection pool
kubectl exec -it deploy/api -n ugc-marketplace -- \
  curl -s http://localhost:3000/health/ready
```

#### High Memory Usage

```bash
# Check memory usage
kubectl top pod -n ugc-marketplace

# Check for memory leaks
kubectl exec -it <pod-name> -n ugc-marketplace -- \
  node --inspect -e "process.memoryUsage()"

# Restart deployment if needed
kubectl rollout restart deployment/api -n ugc-marketplace
```

#### Elasticsearch Connection Issues

```bash
# Check cluster health
curl -u $ES_USER:$ES_PASS $ELASTICSEARCH_URL/_cluster/health

# Check index settings
curl -u $ES_USER:$ES_PASS $ELASTICSEARCH_URL/_cat/indices?v

# Check shard allocation
curl -u $ES_USER:$ES_PASS $ELASTICSEARCH_URL/_cat/shards?v
```

### Debug Logging

```bash
# Enable debug logging temporarily
kubectl set env deployment/api LOG_LEVEL=debug -n ugc-marketplace

# View logs
kubectl logs -f deploy/api -n ugc-marketplace --tail=100

# Reset to info
kubectl set env deployment/api LOG_LEVEL=info -n ugc-marketplace
```

### Health Check Endpoints

| Endpoint | Description |
|----------|-------------|
| `/health/live` | Liveness probe (process running) |
| `/health/ready` | Readiness probe (dependencies OK) |
| `/health/startup` | Startup probe (initialization complete) |
| `/metrics` | Prometheus metrics |
| `/debug/pprof/` | Go pprof (if applicable) |

---

## Security Checklist

- [ ] All secrets stored in Kubernetes Secrets or AWS Secrets Manager
- [ ] Network policies restrict pod-to-pod communication
- [ ] Pod Security Standards enforced (restricted)
- [ ] Container images scanned for vulnerabilities
- [ ] RBAC configured with least privilege
- [ ] Audit logging enabled
- [ ] WAF rules configured
- [ ] DDoS protection enabled (AWS Shield)
- [ ] Encryption at rest for all data stores
- [ ] Encryption in transit (TLS 1.2+)
- [ ] Regular security patches applied
- [ ] Penetration testing completed

---

<p align="center"><a href="./README.md">← Back to README</a> | <a href="./API.md">API Reference →</a></p>
