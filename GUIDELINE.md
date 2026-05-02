# Project Guidelines & Best Practices

This document outlines the engineering standards and best practices for the Lagent project. Following these guidelines ensures code quality, maintainability, and scalability across our full-stack ecosystem.

---

## General Principles

- **DRY (Don't Repeat Yourself)**: Abstract common logic into reusable functions or components.
- **KISS (Keep It Simple, Stupid)**: Prioritize readability and simplicity over clever, complex solutions.
- **Security First**: Never hardcode secrets. Use environment variables. Validate all external inputs.
- **Type Safety**: Leverage TypeScript on the frontend and Python Type Hints on the backend.

---

## Backend Guidelines (FastAPI & Python)

### Best Practices
- **Service Layer Pattern**: Keep routes thin. Move business logic to `app/services/`.
- **Structured Logging**: Use `structlog` for all logs. Include context like `session_id` or `user_id`.
- **Pydantic for Everything**: Use Pydantic models for request validation, response serialization, and settings management.
- **SQLModel for DB**: Use `SQLModel` for database entities to share models between SQLAlchemy and Pydantic.
- **Migration Discipline**: Always use Alembic for database schema changes. Review auto-generated migrations before applying.
- **Docstrings**: Document all modules, classes, and public functions using Google Style docstrings.
- **Rate Limiting**: Apply `@limiter.limit` to public or expensive endpoints.
- **Dependency Injection**: Use FastAPI's `Depends` for authentication, database sessions, and other shared resources.

### Anti-Patterns to Avoid
- **Business Logic in Routes**: Don't perform complex calculations or DB queries directly in the route handler.
- **Ignoring Type Hints**: Don't use `Any` unless absolutely necessary.
- **Broad Exception Catching**: Avoid `except Exception:`. Catch specific errors and return meaningful `HTTPException` responses.
- **Synchronous Blocking**: Don't use blocking I/O (like `requests`) in `async` endpoints. Use `httpx` or other async libraries.

---

## Frontend Guidelines (React & TypeScript)

### Best Practices
- **Component Composition**: Build small, focused components. Extract logic into custom hooks.
- **Tailwind CSS**: Use Tailwind for all styling. Follow the "Premium Design" philosophy (gradients, subtle shadows, smooth transitions).
- **React Query (TanStack)**: Use `useQuery` and `useMutation` for all server-state interactions. Avoid using `useEffect` for data fetching.
- **Axios Instance**: Use the pre-configured `api` instance in `lib/api.ts` to ensure consistent base URLs and headers.
- **Strict TypeScript**: Define interfaces/types for all component props and API responses.
- **Dark Mode Support**: Always implement `dark:` variants for Tailwind classes. Ensure the UI looks premium in both modes.
- **Iconography**: Use `lucide-react` for consistent and accessible icons.

### Anti-Patterns to Avoid
- **Prop Drilling**: Avoid passing props through multiple levels. Use Context API or specialized hooks for deeply nested state.
- **Hardcoded Constants**: Don't hardcode magic numbers, strings, or URLs in components. Use a constants file or environment variables.
- **Direct DOM Manipulation**: Avoid `document.querySelector`. Use React refs or state.
- **Messy Templates**: Don't put complex logic inside the `return` JSX. Compute values beforehand.

---

## AI & Agents (LangGraph)

### Best Practices
- **State Management**: Keep the LangGraph `State` minimal and well-typed.
- **Checkpointing**: Use persistent checkpointers (Postgres) to allow session resumption.
- **Tool Definitions**: Clearly define tool schemas and docstrings so the LLM understands when and how to call them.
- **Streaming**: Always prefer streaming responses for a better user experience.
- **Tracing**: Use LangFuse for observability and debugging agent traces.

### Anti-Patterns to Avoid
- **Opaque Prompts**: Avoid giant, monolithic prompt strings. Break them into manageable templates.
- **Unbounded Loops**: Always implement a recursion limit in LangGraph to prevent infinite agent loops.
- **Hardcoding Model IDs**: Use environment variables for model names (e.g., `gpt-4o`, `claude-3-5-sonnet`) to allow easy swapping.

---

## Docker & Infrastructure

### Best Practices
- **Multi-stage Builds**: Use multi-stage Dockerfiles to keep production images small.
- **Healthchecks**: Define healthchecks in `docker-compose.yml` to ensure services are ready before dependent ones start.
- **Volume Management**: Use named volumes for persistent data (Postgres, Grafana).
- **Network Isolation**: Keep database and internal services off the public network when possible.

### Anti-Patterns to Avoid
- **Root User**: Avoid running containers as `root`.
- **Large Images**: Don't include build-time dependencies (compilers, git) in the final production image.

---

## Tooling & Workflow

### Dependency Management
- **Backend**: Use `uv` for lightning-fast dependency management. Update `pyproject.toml` and run `uv lock`.
- **Frontend**: Use `npm`. Keep `package.json` clean and group dev-dependencies correctly.

### Code Quality
- **Linting & Formatting**: 
    - Backend: `ruff`, `black`, `isort`.
    - Frontend: `eslint`, `prettier`.
- **Pre-commit Hooks**: Ensure pre-commit hooks are installed and passing before every push.

### Version Control
- **Conventional Commits**: Use clear, descriptive commit messages (e.g., `feat: add chatbot streaming`, `fix: auth token expiration`).
- **PR Reviews**: Every PR must be reviewed. Code should be tested locally before requesting a review.

---

## Design Guidelines

- **Premium Aesthetics**: Use modern typography (Inter/Outfit), generous whitespace, and subtle micro-animations.
- **Consistency**: Stick to the defined color palette (Indigo/Slate).
- **Responsive**: All features must work seamlessly on mobile and desktop.
