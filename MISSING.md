# Open-MRE: Missing Components for Deployment

## Critical (Blocking Deployment)

- [ ] **GitHub Integration**
  - Webhook receiver endpoint for `NEW_ISSUE` events
    - Webhook signature verification
  - Issue comment posting functionality
    - GitHub API client (PyGithub or httpx)

- [ ] **Background Task Processing**
  - Async job scheduler (Celery, RQ, or similar)
  - Task queue for validation workflows
  - Job status tracking
  - Timeout and retry mechanisms

- [ ] **Data Persistence**
  - Database schema (SQLite/PostgreSQL)
  - Validation history storage
  - Issue-to-validation mapping
  - HITL approval audit trail

## High Priority

- [ ] **Deployment Configuration**
  - `Dockerfile`
  - `docker-compose.yml`
  - Production WSGI/ASGI wrapper

- [ ] **Authentication & Authorization**
  - GitHub token management
  - RBAC for comment approval workflow
  - API key rotation/management

- [ ] **Integration Tests**
  - Full E2E workflow tests
  - GitHub API integration tests
  - Daytona sandbox execution tests
  - See `tests/integration_tests/README.md` for details

## Medium Priority

- [ ] **Monitoring & Observability**
  - Structured logging (JSON format)
  - Metrics collection (Prometheus)
  - Health check endpoint (`/health`)
  - Alert thresholds

- [ ] **Error Handling & Resilience**
  - Retry logic with exponential backoff
  - Fallback mechanisms (PyPI down, Daytona down)
  - Dead letter queue for failed jobs
  - Graceful partial failure handling

- [ ] **Documentation**
  - Deployment guide
  - Architecture diagram
  - API documentation (OpenAPI/Swagger)
  - Troubleshooting runbook

## Nice to Have

- [ ] Dynamic model selection (currently hardcoded to `claude-sonnet-4-5`)
- [ ] Structured output migration (TODOs in codebase mention this)
- [ ] Local/Docker execution fallback (currently Daytona-only)
