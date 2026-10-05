# UGC Marketplace

> A production-grade marketplace platform for buying, selling, and managing user-generated content (UGC) — digital assets, media, templates, and creative works.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![CI](https://img.shields.io/badge/CI-passing-brightgreen.svg)](https://github.com/ugc-marketplace/ugc-marketplace/actions)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://hub.docker.com/r/ugc-marketplace/api)

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Quick Start](#quick-start)
- [Development](#development)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

UGC Marketplace is a full-stack platform that enables creators to monetize their digital content and consumers to discover, license, and download high-quality user-generated assets. The platform supports multiple content types including images, videos, audio, 3D models, templates, and written content.

### Key Capabilities

- **Multi-format content support** — images, video, audio, 3D, documents
- **Creator monetization** — flexible pricing, licensing tiers, revenue sharing
- **Advanced discovery** — faceted search, recommendations, collections
- **Secure transactions** — escrow, payouts, fraud detection
- **Rights management** — license enforcement, watermarking, DMCA compliance
- **Analytics** — creator dashboards, sales reports, trend analysis

---

## Architecture

```mermaid
graph TB
    subgraph "Client Layer"
        WEB[Web App<br/>React + TypeScript]
        MOB[Mobile App<br/>React Native]
        API_CLIENT[API Clients<br/>REST / GraphQL]
    end

    subgraph "Edge Layer"
        CDN[CDN<br/>CloudFront / Cloudflare]
        WAF[WAF<br/>AWS WAF]
        LB[Load Balancer<br/>ALB / Nginx]
    end

    subgraph "API Gateway"
        GW[API Gateway<br/>Kong / AWS API Gateway]
        AUTH[Auth Service<br/>OAuth2 + JWT]
        RATE[Rate Limiter<br/>Redis-backed]
    end

    subgraph "Service Layer"
        USER_SVC[User Service<br/>Node.js]
        CONTENT_SVC[Content Service<br/>Node.js]
        SEARCH_SVC[Search Service<br/>Go]
        ORDER_SVC[Order Service<br/>Node.js]
        PAYMENT_SVC[Payment Service<br/>Node.js]
        NOTIF_SVC[Notification Service<br/>Node.js]
        ANALYTICS_SVC[Analytics Service<br/>Python]
    end

    subgraph "Data Layer"
        PG[(PostgreSQL<br/>Primary DB)]
        MONGO[(MongoDB<br/>Content Metadata)]
        REDIS[(Redis<br/>Cache + Sessions)]
        ES[(Elasticsearch<br/>Search Index)]
        S3[(Object Storage<br/>S3 / MinIO)]
        KAFKA[(Kafka<br/>Event Bus)]
    end

    subgraph "Worker Layer"
        IMG_WORKER[Image Processor<br/>Sharp / FFmpeg]
        VID_WORKER[Video Transcoder<br/>FFmpeg]
        EMAIL_WORKER[Email Worker]
        PAYOUT_WORKER[Payout Worker]
    end

    WEB --> CDN
    MOB --> CDN
    API_CLIENT --> GW
    CDN --> WAF --> LB --> GW
    GW --> AUTH
    GW --> RATE
    GW --> USER_SVC
    GW --> CONTENT_SVC
    GW --> SEARCH_SVC
    GW --> ORDER_SVC
    GW --> PAYMENT_SVC
    GW --> NOTIF_SVC

    USER_SVC --> PG
    CONTENT_SVC --> MONGO
    CONTENT_SVC --> S3
    SEARCH_SVC --> ES
    ORDER_SVC --> PG
    PAYMENT_SVC --> PG
    NOTIF_SVC --> REDIS
    ANALYTICS_SVC --> PG

    CONTENT_SVC --> KAFKA
    ORDER_SVC --> KAFKA
    KAFKA --> IMG_WORKER
    KAFKA --> VID_WORKER
    KAFKA --> EMAIL_WORKER
    KAFKA --> PAYOUT_WORKER
    IMG_WORKER --> S3
    VID_WORKER --> S3
```

### Technology Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, TypeScript, Tailwind CSS, Vite |
| Mobile | React Native, Expo |
| API | Node.js, Express, GraphQL (Apollo) |
| Search | Go, Elasticsearch |
| Analytics | Python, FastAPI, Pandas |
| Databases | PostgreSQL 15, MongoDB 6, Redis 7 |
| Message Queue | Apache Kafka |
| Object Storage | AWS S3 / MinIO |
| Infrastructure | Docker, Kubernetes, Terraform |
| CI/CD | GitHub Actions |
| Monitoring | Prometheus, Grafana, Sentry |

---

## Features

### For Creators

- [x] **Storefront Builder** — Customizable creator storefronts with themes and branding
- [x] **Flexible Pricing** — Fixed price, pay-what-you-want, subscription, and auction models
- [x] **License Management** — Multiple license tiers (personal, extended, commercial)
- [x] **Bulk Upload** — Drag-and-drop bulk upload with metadata extraction
- [x] **Analytics Dashboard** — Real-time sales, views, conversion funnels
- [x] **Payout System** — Automated payouts via Stripe Connect, PayPal, or bank transfer
- [x] **Version Control** — Content versioning with update notifications for buyers

### For Buyers

- [x] **Advanced Search** — Full-text search with filters (format, price, license, rating)
- [x] **Preview System** — Watermarked previews, video/audio streaming previews
- [x] **Collections** — Curated collections and personalized recommendations
- [x] **Secure Download** — Time-limited download links with license certificates
- [x] **Order History** — Complete purchase history with re-download capability
- [x] **Favorites** — Save and organize favorite items

### Platform

- [x] **Content Moderation** — AI-powered + human review pipeline
- [x] **Rights Protection** — Automated DMCA takedown, fingerprinting
- [x] **Fraud Detection** — ML-based fraud scoring on transactions
- [x] **Multi-language** — i18n support for 12 languages
- [x] **Accessibility** — WCAG 2.1 AA compliant
- [x] **API & Webhooks** — RESTful API with webhook integrations

---

## Quick Start

### Prerequisites

- [Node.js](https://nodejs.org/) >= 18.0
- [Docker](https://www.docker.com/) >= 24.0
- [Docker Compose](https://docs.docker.com/compose/) >= 2.20
- [PostgreSQL](https://www.postgresql.org/) >= 15 (or use Docker)
- [Redis](https://redis.io/) >= 7 (or use Docker)

### 1. Clone the Repository

```bash
git clone https://github.com/ugc-marketplace/ugc-marketplace.git
cd ugc-marketplace
```

### 2. Environment Configuration

```bash
cp .env.example .env
# Edit .env with your configuration
```

Key environment variables:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/ugc_marketplace
REDIS_URL=redis://localhost:6379

# JWT
JWT_SECRET=your-super-secret-key
JWT_EXPIRES_IN=7d

# Storage
S3_BUCKET=ugc-marketplace-assets
S3_REGION=us-east-1
S3_ACCESS_KEY=your-access-key
S3_SECRET_KEY=your-secret-key

# Payment
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Search
ELASTICSEARCH_URL=http://localhost:9200

# App
PORT=3000
NODE_ENV=development
CORS_ORIGIN=http://localhost:5173
```

### 3. Start with Docker Compose

```bash
docker-compose up -d
```

This starts:
- API server on `http://localhost:3000`
- Web frontend on `http://localhost:5173`
- PostgreSQL on `localhost:5432`
- Redis on `localhost:6379`
- Elasticsearch on `localhost:9200`
- MinIO (S3-compatible) on `http://localhost:9000`

### 4. Run Database Migrations

```bash
npm run migrate
npm run seed
```

### 5. Access the Application

| Service | URL | Credentials |
|---------|-----|-------------|
| Web App | http://localhost:5173 | — |
| API | http://localhost:3000/api/v1 | — |
| API Docs | http://localhost:3000/api-docs | — |
| MinIO Console | http://localhost:9000 | minioadmin / minioadmin |
| Kibana | http://localhost:5601 | — |

### 6. Create an Admin User

```bash
npm run create:admin -- --email admin@example.com --password SecurePass123!
```

---

## Development

### Project Structure

```
ugc-marketplace/
├── apps/
│   ├── api/                 # Backend API (Node.js + Express)
│   │   ├── src/
│   │   │   ├── modules/     # Feature modules
│   │   │   ├── shared/      # Shared utilities
│   │   │   ├── config/      # Configuration
│   │   │   └── main.ts      # Entry point
│   │   ├── tests/
│   │   ├── Dockerfile
│   │   └── package.json
│   ├── web/                 # Frontend (React + Vite)
│   │   ├── src/
│   │   │   ├── components/
│   │   │   ├── pages/
│   │   │   ├── hooks/
│   │   │   ├── stores/
│   │   │   └── App.tsx
│   │   ├── Dockerfile
│   │   └── package.json
│   └── worker/              # Background workers
│       ├── src/
│       ├── Dockerfile
│       └── package.json
├── packages/
│   ├── shared/              # Shared types and utilities
│   ├── ui/                  # Shared UI component library
│   └── config/              # Shared configuration
├── infrastructure/
│   ├── terraform/           # IaC for AWS/GCP
│   ├── kubernetes/          # K8s manifests
│   └── docker/              # Docker compose files
├── docs/                    # Documentation
├── scripts/                 # Build and utility scripts
├── .github/                 # GitHub Actions workflows
├── docker-compose.yml
├── docker-compose.prod.yml
└── turbo.json
```

### Common Commands

```bash
# Install dependencies
npm install

# Run all services in development
npm run dev

# Run tests
npm test                    # All tests
npm run test:unit          # Unit tests only
npm run test:integration   # Integration tests only
npm run test:e2e           # End-to-end tests

# Lint and format
npm run lint
npm run lint:fix
npm run format

# Build
npm run build              # Build all packages
npm run build:api          # Build API only
npm run build:web          # Build web only

# Database
npm run migrate            # Run migrations
npm run migrate:rollback   # Rollback last migration
npm run seed               # Seed database
npm run db:reset           # Reset and reseed
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [API Reference](./API.md) | Complete REST API endpoint reference |
| [Deployment Guide](./DEPLOYMENT.md) | Docker, Kubernetes, and Terraform deployment |
| [Contributing Guide](./CONTRIBUTING.md) | How to contribute to the project |
| [Changelog](./CHANGELOG.md) | Version history and release notes |

---

## Contributing

We welcome contributions! Please see our [Contributing Guide](./CONTRIBUTING.md) for details on:

- Code of Conduct
- Development workflow
- Pull request process
- Commit message conventions

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

## Support

- **Documentation**: [https://docs.ugc-marketplace.io](https://docs.ugc-marketplace.io)
- **Issues**: [GitHub Issues](https://github.com/ugc-marketplace/ugc-marketplace/issues)
- **Discussions**: [GitHub Discussions](https://github.com/ugc-marketplace/ugc-marketplace/discussions)
- **Email**: support@ugc-marketplace.io

---

<p align="center">Built with ❤️ by the UGC Marketplace team</p>
