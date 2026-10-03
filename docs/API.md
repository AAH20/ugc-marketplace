# UGC Marketplace API Reference

> Complete REST API reference for the UGC Marketplace platform.

**Base URL**: `https://api.ugc-marketplace.io/api/v1`

**Version**: 1.0.0

---

## Table of Contents

- [Authentication](#authentication)
- [Rate Limiting](#rate-limiting)
- [Error Handling](#error-handling)
- [Pagination](#pagination)
- [Users](#users)
- [Content](#content)
- [Search](#search)
- [Orders](#orders)
- [Payments](#payments)
- [Collections](#collections)
- [Notifications](#notifications)
- [Analytics](#analytics)
- [Webhooks](#webhooks)

---

## Authentication

The API uses **Bearer Token** authentication via JWT.

### Obtaining a Token

```bash
POST /api/v1/auth/login
```

**Request:**

```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

**Response:**

```json
{
  "success": true,
  "data": {
    "accessToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refreshToken": "dGhpcyBpcyBhIHJlZnJlc2ggdG9rZW4...",
    "expiresIn": 604800,
    "user": {
      "id": "usr_abc123",
      "email": "user@example.com",
      "name": "Jane Doe",
      "role": "creator"
    }
  }
}
```

### Using the Token

Include the token in the `Authorization` header:

```bash
curl -H "Authorization: Bearer <access_token>" \
     -H "Content-Type: application/json" \
     https://api.ugc-marketplace.io/api/v1/users/me
```

### Token Refresh

```bash
POST /api/v1/auth/refresh
```

**Request:**

```json
{
  "refreshToken": "dGhpcyBpcyBhIHJlZnJlc2ggdG9rZW4..."
}
```

### OAuth2 Providers

| Provider | Endpoint |
|----------|----------|
| Google | `GET /api/v1/auth/google` |
| GitHub | `GET /api/v1/auth/github` |
| Apple | `GET /api/v1/auth/apple` |

---

## Rate Limiting

All API endpoints are rate-limited. Rate limit headers are included in every response:

| Header | Description |
|--------|-------------|
| `X-RateLimit-Limit` | Maximum requests allowed in the window |
| `X-RateLimit-Remaining` | Remaining requests in the current window |
| `X-RateLimit-Reset` | Unix timestamp when the window resets |

**Default Limits:**

| Tier | Requests | Window |
|------|----------|--------|
| Anonymous | 30 | 1 minute |
| Authenticated | 120 | 1 minute |
| Creator | 300 | 1 minute |
| Enterprise | 1000 | 1 minute |

**429 Response:**

```json
{
  "success": false,
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests. Please try again later.",
    "retryAfter": 45
  }
}
```

---

## Error Handling

All errors follow a consistent format:

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": [
      {
        "field": "email",
        "message": "Must be a valid email address"
      }
    ]
  }
}
```

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 204 | No Content |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 409 | Conflict |
| 422 | Unprocessable Entity |
| 429 | Too Many Requests |
| 500 | Internal Server Error |
| 503 | Service Unavailable |

### Error Codes

| Code | HTTP | Description |
|------|------|-------------|
| `VALIDATION_ERROR` | 400 | Request validation failed |
| `UNAUTHORIZED` | 401 | Missing or invalid authentication |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `CONFLICT` | 409 | Resource already exists |
| `RATE_LIMIT_EXCEEDED` | 429 | Rate limit exceeded |
| `INTERNAL_ERROR` | 500 | Internal server error |
| `SERVICE_UNAVAILABLE` | 503 | Service temporarily unavailable |

---

## Pagination

List endpoints support cursor-based pagination:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | integer | 20 | Items per page (max 100) |
| `cursor` | string | — | Opaque cursor for next page |
| `sort` | string | `created_at:desc` | Sort field and direction |

**Response:**

```json
{
  "success": true,
  "data": [...],
  "pagination": {
    "total": 1543,
    "limit": 20,
    "hasMore": true,
    "nextCursor": "eyJpZCI6MTIzNDV9"
  }
}
```

---

## Users

### Get Current User

```bash
GET /api/v1/users/me
```

**Response:**

```json
{
  "success": true,
  "data": {
    "id": "usr_abc123",
    "email": "user@example.com",
    "name": "Jane Doe",
    "username": "janedoe",
    "avatar": "https://cdn.ugc-marketplace.io/avatars/usr_abc123.jpg",
    "bio": "Digital artist and content creator",
    "role": "creator",
    "verified": true,
    "stats": {
      "totalSales": 342,
      "totalEarnings": 12450.00,
      "rating": 4.8,
      "reviewCount": 156
    },
    "createdAt": "2024-01-15T10:30:00Z"
  }
}
```

### Update Current User

```bash
PATCH /api/v1/users/me
```

**Request:**

```json
{
  "name": "Jane Doe Updated",
  "bio": "Updated bio text",
  "avatar": "https://example.com/new-avatar.jpg"
}
```

### Get User by ID

```bash
GET /api/v1/users/:id
```

### Get User Public Profile

```bash
GET /api/v1/users/:username
```

### List Users

```bash
GET /api/v1/users?role=creator&verified=true&sort=rating:desc
```

### Delete User

```bash
DELETE /api/v1/users/me
```

---

## Content

### List Content Items

```bash
GET /api/v1/content?type=image&category=illustration&price_min=5&price_max=50
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `type` | string | `image`, `video`, `audio`, `3d`, `document` |
| `category` | string | Content category slug |
| `tags` | string[] | Filter by tags |
| `price_min` | number | Minimum price |
| `price_max` | number | Maximum price |
| `license` | string | `personal`, `commercial`, `extended` |
| `creator` | string | Creator user ID |
| `sort` | string | `relevance`, `newest`, `popular`, `price_asc`, `price_desc` |

**Response:**

```json
{
  "success": true,
  "data": [
    {
      "id": "cnt_xyz789",
      "title": "Abstract Digital Artwork",
      "description": "A vibrant abstract composition...",
      "type": "image",
      "category": "illustration",
      "tags": ["abstract", "digital", "colorful"],
      "thumbnail": "https://cdn.ugc-marketplace.io/thumbs/cnt_xyz789.jpg",
      "preview": "https://cdn.ugc-marketplace.io/previews/cnt_xyz789.jpg",
      "price": 29.99,
      "currency": "USD",
      "licenses": {
        "personal": { "price": 29.99, "usage": "Personal use only" },
        "commercial": { "price": 99.99, "usage": "Commercial use, up to 500k impressions" },
        "extended": { "price": 299.99, "usage": "Unlimited commercial use" }
      },
      "creator": {
        "id": "usr_abc123",
        "name": "Jane Doe",
        "username": "janedoe",
        "avatar": "https://cdn.ugc-marketplace.io/avatars/usr_abc123.jpg"
      },
      "stats": {
        "views": 12453,
        "downloads": 342,
        "likes": 892,
        "rating": 4.8
      },
      "createdAt": "2024-03-10T14:22:00Z"
    }
  ],
  "pagination": {
    "total": 1543,
    "limit": 20,
    "hasMore": true,
    "nextCursor": "eyJpZCI6MTIzNDV9"
  }
}
```

### Get Content Item

```bash
GET /api/v1/content/:id
```

### Create Content Item

```bash
POST /api/v1/content
Content-Type: multipart/form-data
```

**Request:**

```json
{
  "title": "My New Artwork",
  "description": "A beautiful digital illustration",
  "type": "image",
  "category": "illustration",
  "tags": ["digital", "art", "colorful"],
  "price": 29.99,
  "currency": "USD",
  "licenses": {
    "personal": { "price": 29.99, "usage": "Personal use only" },
    "commercial": { "price": 99.99, "usage": "Commercial use" }
  },
  "file": "<binary_file>"
}
```

### Update Content Item

```bash
PATCH /api/v1/content/:id
```

### Delete Content Item

```bash
DELETE /api/v1/content/:id
```

### Upload Content File

```bash
POST /api/v1/content/:id/files
Content-Type: multipart/form-data
```

### Get Content Download URL

```bash
POST /api/v1/content/:id/download
```

**Request:**

```json
{
  "license": "commercial",
  "orderId": "ord_def456"
}
```

**Response:**

```json
{
  "success": true,
  "data": {
    "downloadUrl": "https://downloads.ugc-marketplace.io/...",
    "expiresAt": "2024-04-10T14:22:00Z",
    "licenseCertificate": "https://downloads.ugc-marketplace.io/cert/..."
  }
}
```

### Like Content

```bash
POST /api/v1/content/:id/like
```

### Unlike Content

```bash
DELETE /api/v1/content/:id/like
```

### Report Content

```bash
POST /api/v1/content/:id/report
```

**Request:**

```json
{
  "reason": "copyright_infringement",
  "description": "This content infringes on my copyright",
  "evidence": "https://example.com/original-work"
}
```

---

## Search

### Full-Text Search

```bash
GET /api/v1/search?q=abstract+digital+art&type=image&category=illustration
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `q` | string | Search query string |
| `type` | string | Content type filter |
| `category` | string | Category filter |
| `tags` | string[] | Tag filters |
| `price_min` | number | Minimum price |
| `price_max` | number | Maximum price |
| `rating_min` | number | Minimum rating |
| `date_from` | date | Upload date start |
| `date_to` | date | Upload date end |
| `sort` | string | `relevance`, `newest`, `popular`, `price_asc`, `price_desc` |

### Autocomplete

```bash
GET /api/v1/search/autocomplete?q=abs&limit=10
```

**Response:**

```json
{
  "success": true,
  "data": {
    "suggestions": [
      { "text": "abstract art", "type": "query", "count": 1234 },
      { "text": "abstract background", "type": "query", "count": 856 },
      { "text": "abstract", "type": "tag", "count": 3421 }
    ]
  }
}
```

### Faceted Search

```bash
GET /api/v1/search/facets?q=abstract
```

**Response:**

```json
{
  "success": true,
  "data": {
    "categories": [
      { "slug": "illustration", "count": 456 },
      { "slug": "photography", "count": 234 }
    ],
    "types": [
      { "value": "image", "count": 567 },
      { "value": "video", "count": 123 }
    ],
    "priceRanges": [
      { "min": 0, "max": 10, "count": 234 },
      { "min": 10, "max": 50, "count": 456 }
    ],
    "tags": [
      { "name": "abstract", "count": 3421 },
      { "name": "digital", "count": 2100 }
    ]
  }
}
```

---

## Orders

### Create Order

```bash
POST /api/v1/orders
```

**Request:**

```json
{
  "items": [
    {
      "contentId": "cnt_xyz789",
      "license": "commercial",
      "quantity": 1
    }
  ],
  "paymentMethod": "stripe",
  "paymentToken": "tok_visa",
  "couponCode": "WELCOME10"
}
```

**Response:**

```json
{
  "success": true,
  "data": {
    "id": "ord_def456",
    "status": "pending",
    "items": [
      {
        "contentId": "cnt_xyz789",
        "title": "Abstract Digital Artwork",
        "license": "commercial",
        "price": 99.99,
        "quantity": 1
      }
    ],
    "subtotal": 99.99,
    "discount": 10.00,
    "tax": 7.20,
    "total": 97.19,
    "currency": "USD",
    "createdAt": "2024-03-15T10:30:00Z"
  }
}
```

### Get Order

```bash
GET /api/v1/orders/:id
```

### List Orders

```bash
GET /api/v1/orders?status=completed&sort=created_at:desc
```

### Cancel Order

```bash
POST /api/v1/orders/:id/cancel
```

### Get Order Invoice

```bash
GET /api/v1/orders/:id/invoice
```

**Response:** PDF file download

---

## Payments

### Get Payment Methods

```bash
GET /api/v1/payments/methods
```

### Add Payment Method

```bash
POST /api/v1/payments/methods
```

**Request:**

```json
{
  "type": "card",
  "token": "tok_visa",
  "isDefault": true
}
```

### Remove Payment Method

```bash
DELETE /api/v1/payments/methods/:id
```

### Get Payout Balance

```bash
GET /api/v1/payments/balance
```

**Response:**

```json
{
  "success": true,
  "data": {
    "available": 12450.00,
    "pending": 2340.00,
    "currency": "USD",
    "nextPayoutDate": "2024-04-01"
  }
}
```

### Request Payout

```bash
POST /api/v1/payments/payouts
```

**Request:**

```json
{
  "amount": 5000.00,
  "method": "bank_transfer",
  "destination": "ba_1234567890"
}
```

### List Payouts

```bash
GET /api/v1/payments/payouts
```

### Get Transaction History

```bash
GET /api/v1/payments/transactions?type=sale&date_from=2024-01-01
```

---

## Collections

### List Collections

```bash
GET /api/v1/collections?creator=usr_abc123
```

### Get Collection

```bash
GET /api/v1/collections/:id
```

### Create Collection

```bash
POST /api/v1/collections
```

**Request:**

```json
{
  "name": "My Favorites",
  "description": "A collection of my favorite artworks",
  "isPublic": true,
  "contentIds": ["cnt_xyz789", "cnt_abc123"]
}
```

### Update Collection

```bash
PATCH /api/v1/collections/:id
```

### Delete Collection

```bash
DELETE /api/v1/collections/:id
```

### Add to Collection

```bash
POST /api/v1/collections/:id/items
```

**Request:**

```json
{
  "contentId": "cnt_xyz789"
}
```

### Remove from Collection

```bash
DELETE /api/v1/collections/:id/items/:contentId
```

---

## Notifications

### List Notifications

```bash
GET /api/v1/notifications?unread=true
```

### Mark as Read

```bash
PATCH /api/v1/notifications/:id/read
```

### Mark All as Read

```bash
POST /api/v1/notifications/read-all
```

### Delete Notification

```bash
DELETE /api/v1/notifications/:id
```

### Get Notification Preferences

```bash
GET /api/v1/notifications/preferences
```

### Update Notification Preferences

```bash
PUT /api/v1/notifications/preferences
```

**Request:**

```json
{
  "email": {
    "orderUpdates": true,
    "newFollowers": true,
    "promotions": false,
    "newsletter": true
  },
  "push": {
    "orderUpdates": true,
    "newFollowers": false,
    "promotions": false
  }
}
```

---

## Analytics

### Creator Dashboard

```bash
GET /api/v1/analytics/dashboard?period=30d
```

**Response:**

```json
{
  "success": true,
  "data": {
    "period": "30d",
    "overview": {
      "totalRevenue": 12450.00,
      "totalSales": 342,
      "totalViews": 45678,
      "conversionRate": 0.75,
      "averageOrderValue": 36.40
    },
    "revenue": {
      "daily": [
        { "date": "2024-03-01", "revenue": 450.00, "sales": 15 }
      ],
      "byContent": [
        { "contentId": "cnt_xyz789", "title": "Abstract Art", "revenue": 3450.00 }
      ]
    },
    "topContent": [
      {
        "contentId": "cnt_xyz789",
        "title": "Abstract Digital Artwork",
        "sales": 156,
        "revenue": 4680.00,
        "views": 12453
      }
    ],
    "topBuyers": [
      {
        "userId": "usr_buyer1",
        "name": "John Smith",
        "totalSpent": 1250.00,
        "orders": 12
      }
    ]
  }
}
```

### Content Analytics

```bash
GET /api/v1/analytics/content/:id?period=30d
```

### Platform Analytics (Admin)

```bash
GET /api/v1/analytics/platform?period=30d
```

---

## Webhooks

### Register Webhook

```bash
POST /api/v1/webhooks
```

**Request:**

```json
{
  "url": "https://your-app.com/webhooks/ugc-marketplace",
  "events": ["order.created", "order.completed", "content.published"],
  "secret": "your-webhook-secret"
}
```

### List Webhooks

```bash
GET /api/v1/webhooks
```

### Get Webhook

```bash
GET /api/v1/webhooks/:id
```

### Update Webhook

```bash
PATCH /api/v1/webhooks/:id
```

### Delete Webhook

```bash
DELETE /api/v1/webhooks/:id
```

### Webhook Events

| Event | Description |
|-------|-------------|
| `order.created` | New order placed |
| `order.completed` | Order payment completed |
| `order.cancelled` | Order cancelled |
| `order.refunded` | Order refunded |
| `content.published` | New content published |
| `content.updated` | Content updated |
| `content.deleted` | Content deleted |
| `content.approved` | Content approved by moderation |
| `content.rejected` | Content rejected by moderation |
| `user.registered` | New user registered |
| `payout.completed` | Payout processed |
| `review.created` | New review submitted |

### Webhook Payload Example

```json
{
  "id": "evt_abc123",
  "type": "order.completed",
  "createdAt": "2024-03-15T10:30:00Z",
  "data": {
    "orderId": "ord_def456",
    "userId": "usr_buyer1",
    "total": 97.19,
    "currency": "USD",
    "items": [
      {
        "contentId": "cnt_xyz789",
        "title": "Abstract Digital Artwork",
        "license": "commercial",
        "price": 99.99
      }
    ]
  }
}
```

### Webhook Signature Verification

```javascript
const crypto = require('crypto');

function verifyWebhookSignature(payload, signature, secret) {
  const expected = crypto
    .createHmac('sha256', secret)
    .update(payload)
    .digest('hex');
  return crypto.timingSafeEqual(
    Buffer.from(signature),
    Buffer.from(expected)
  );
}
```

---

## SDKs & Libraries

Official SDKs are available for:

| Language | Package | Installation |
|----------|---------|-------------|
| JavaScript | `@ugc-marketplace/sdk` | `npm install @ugc-marketplace/sdk` |
| Python | `ugc-marketplace` | `pip install ugc-marketplace` |
| Ruby | `ugc_marketplace` | `gem install ugc_marketplace` |
| Go | `github.com/ugc-marketplace/go-sdk` | `go get github.com/ugc-marketplace/go-sdk` |

### JavaScript SDK Example

```javascript
import { UGCClient } from '@ugc-marketplace/sdk';

const client = new UGCClient({
  apiKey: 'your-api-key',
  baseURL: 'https://api.ugc-marketplace.io/api/v1'
});

// Search content
const results = await client.search({
  q: 'abstract art',
  type: 'image',
  limit: 10
});

// Create an order
const order = await client.orders.create({
  items: [{ contentId: 'cnt_xyz789', license: 'commercial' }],
  paymentMethod: 'stripe',
  paymentToken: 'tok_visa'
});
```

---

## Changelog

See the [Changelog](./CHANGELOG.md) for API version history and breaking changes.

---

<p align="center"><a href="./README.md">← Back to README</a></p>
