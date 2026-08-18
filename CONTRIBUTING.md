# Contributing to TrafficSMS

First and foremost, thank you for your interest in contributing to **TrafficSMS**.

TrafficSMS is being engineered as a production-grade SaaS platform that delivers AI-powered, real-time traffic intelligence through SMS, mobile web, and future native mobile applications. Our goal is to build software that is reliable, secure, scalable, and maintainable.

Whether you're fixing a bug, improving documentation, enhancing the user experience, or implementing a new feature, your contributions are appreciated.

---

# Table of Contents

- Code of Conduct
- Project Vision
- Development Philosophy
- Repository Structure
- Development Environment
- Getting Started
- Branching Strategy
- Coding Standards
- Pull Request Process
- Commit Message Guidelines
- Testing Requirements
- Database Migrations
- Documentation Requirements
- Security Guidelines
- Reporting Bugs
- Requesting Features
- Release Process
- License

---

# Code of Conduct

Please be respectful, professional, and constructive.

We expect contributors to:

- Treat everyone with respect.
- Provide constructive feedback.
- Welcome new contributors.
- Keep discussions professional.
- Focus on improving the project.

Harassment, discrimination, or abusive behavior will not be tolerated.

---

# Project Vision

TrafficSMS is designed to become the fastest and most convenient way for drivers to receive accurate traffic information.

Long-term goals include:

- Nationwide traffic coverage
- AI-powered traffic summaries
- Community traffic reporting
- Police activity awareness
- Speed camera awareness
- DUI checkpoint notifications
- Saved locations
- Personalized alerts
- Mobile applications
- Enterprise fleet support

Every contribution should move the project toward these goals.

---

# Development Philosophy

TrafficSMS follows several core principles.

## Production First

Every feature should be written as if it will be deployed to production.

Avoid:

- Placeholder code
- Demo implementations
- Hardcoded secrets
- Temporary hacks

---

## Security First

Assume all public endpoints are exposed to malicious traffic.

Every feature should consider:

- Authentication
- Authorization
- Validation
- Input sanitization
- Rate limiting
- Logging
- Error handling

---

## Maintainability

Favor readable, maintainable code over clever code.

Future developers should understand your implementation without extensive explanation.

---

## Scalability

Design features that can support:

- Thousands of users
- Millions of requests
- Horizontal scaling
- Cloud deployment

---

# Repository Structure

```
TrafficSMS/

backend/
frontend/
docker-compose.yml
docker-compose.dev.yml
docker-compose.prod.yml

README.md
CHANGELOG.md
PRODUCTION_ROADMAP.md
CONTRIBUTING.md
SECURITY.md
```

Please maintain this organization.

---

# Development Environment

Required software:

- Python 3.12+
- Node.js 22+
- Docker Desktop
- Docker Compose
- PostgreSQL 17
- Redis
- Git

Recommended IDE:

Visual Studio Code

---

# Getting Started

Clone the repository:

```bash
git clone git@github.com:JasonAlanJames/TrafficSMS.git

cd TrafficSMS
```

Copy environment files.

Backend:

```bash
cp backend/.env.example backend/.env
```

Frontend:

```bash
cp frontend/.env.local.example frontend/.env.local
```

Start the development environment:

```bash
docker compose -f docker-compose.dev.yml up --build
```

Verify:

Frontend:

```
http://localhost:3000
```

Backend:

```
http://localhost:8000
```

API Docs:

```
http://localhost:8000/docs
```

---

# Branching Strategy

Never commit unfinished work directly to `main`.

Recommended workflow:

```
main

↓

feature/authentication

↓

feature/stripe

↓

feature/twilio

↓

feature/mobile-app
```

Keep pull requests focused on a single feature or bug fix.

---

# Commit Message Guidelines

Use descriptive commit messages.

Examples:

```
Add JWT authentication service

Implement password reset endpoint

Fix Stripe webhook verification

Improve SMS parser

Add Redis caching

Update Docker Compose

Repair Alembic migration
```

Avoid messages such as:

```
Update

Changes

Fix

Misc

Testing
```

---

# Coding Standards

## Python

Follow:

PEP 8

Use:

- Type hints
- Docstrings
- Dependency injection
- SQLAlchemy ORM
- Alembic migrations

Avoid:

- Global variables
- Raw SQL unless necessary
- Duplicate logic

---

## TypeScript

Use:

- Strong typing
- Functional React components
- Server Components where appropriate
- CSS Modules

Avoid:

- any
- Inline styles
- Large monolithic components

---

## API Design

Use RESTful conventions.

Example:

```
POST /auth/register

POST /auth/login

POST /auth/logout

GET /users/me

PUT /users/me
```

Return consistent JSON responses.

---

# Database Migrations

Never modify production tables manually.

Always create Alembic migrations.

Example:

```bash
alembic revision --autogenerate -m "add user preferences"
```

Then:

```bash
alembic upgrade head
```

Every migration should be:

- Reversible
- Tested
- Production safe

---

# Authentication

TrafficSMS uses:

- JWT
- Refresh Tokens
- Password Hashing
- Email Verification

Never:

- Store plaintext passwords
- Log passwords
- Return sensitive information

---

# Stripe

When working with billing:

Never trust the frontend.

Always validate:

- Webhook signatures
- Subscription status
- Customer ownership

Billing logic belongs in the backend.

---

# Twilio

When working with SMS:

Always:

- Validate webhook signatures
- Respect STOP
- Respect HELP
- Respect START

Never send unsolicited messages.

---

# Environment Variables

Never commit:

```
.env

.env.local

Secrets

API Keys

Private Keys

Passwords
```

Use:

```
.env.example
```

instead.

---

# Testing Requirements

Every feature should include testing where practical.

Recommended testing:

- Unit tests
- Integration tests
- API tests
- Migration tests

Before submitting:

```
Frontend builds successfully

Docker starts

Database migrations succeed

API endpoints function
```

---

# Documentation

Update documentation whenever functionality changes.

This includes:

README.md

CHANGELOG.md

PRODUCTION_ROADMAP.md

API documentation

Environment examples

---

# Pull Requests

Each Pull Request should include:

## Summary

Describe:

- What changed
- Why it changed

---

## Testing

Explain how the feature was tested.

---

## Screenshots

Include screenshots for UI changes.

---

## Migration Notes

If database changes exist, explain them.

---

## Breaking Changes

Clearly document breaking changes.

---

# Reporting Bugs

Please include:

Operating System

Browser

Docker version

Steps to reproduce

Expected behavior

Actual behavior

Logs

Screenshots if applicable

---

# Feature Requests

Describe:

Current limitation

Proposed solution

Benefits

Potential drawbacks

Alternative approaches

---

# Security

Do not create GitHub Issues for security vulnerabilities.

Instead:

See:

```
SECURITY.md
```

for responsible disclosure procedures.

---

# Project Documentation

Please review:

README.md

CHANGELOG.md

PRODUCTION_ROADMAP.md

SECURITY.md

before contributing.

---

# Release Process

Development generally follows this sequence:

```
Feature Branch

↓

Testing

↓

Code Review

↓

Merge to Main

↓

Git Tag

↓

GitHub Release

↓

Production Deployment
```

---

# Versioning

TrafficSMS follows Semantic Versioning.

```
Major.Minor.Patch
```

Examples:

```
1.0.0

1.1.0

1.1.1
```

Alpha and beta releases are identified with suffixes.

Examples:

```
v0.5.0-alpha

v0.9.0-beta

v1.0.0
```

---

# Current Development Focus

Current milestone:

**Complete Authentication System**

Next priorities:

- Registration
- Login
- JWT
- Refresh Tokens
- Password Reset
- Email Verification
- Stripe Integration
- Production Deployment
- Twilio Toll-Free Verification

---

# Questions

For questions regarding development, architecture, or project direction, please open a GitHub Discussion or Issue (for non-security matters).

---

# License

By contributing to TrafficSMS, you agree that your contributions will be licensed under the same license as the project.

Please review the LICENSE file for additional information.

---

Thank you for contributing to TrafficSMS and helping build a secure, scalable, AI-powered traffic intelligence platform.