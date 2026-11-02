# TabBoard API — Backend

**The backend services powering TabBoard's personalized productivity workspace.**

TabBoard API is a Django-based REST backend responsible for authentication, user management, onboarding, task scheduling, goal management, and application data.

It provides the foundation for TabBoard's Chrome extension, exposing authenticated APIs and structured user data to support personalized productivity workflows.

## Architecture Overview

The backend is maintained as a separate application, decoupling business logic and data management from the Chrome extension frontend.

Its primary responsibilities include:

- User authentication and identity management.
- Profile creation and management.
- Multi-step onboarding and personalization.
- Task creation, scheduling, and progress tracking.
- Goal management and categorization.
- Providing structured user context for future AI-powered functionality.

## Core Modules

### Authentication & User Management
- Google OAuth-based authentication.
- JWT-based API authentication.
- User identity and account management.
- Authenticated access to user-specific resources.

### Onboarding & Personalization
- Multi-step onboarding workflow.
- Basic profile information.
- Structured personalization questions and responses.
- Interest and personality preference management.
- Onboarding completion tracking.

The onboarding API exposes structured profile and preference data to the frontend, allowing the application to maintain a consistent user context.

### Task Management
- Create, retrieve, update, and delete tasks.
- Scheduled start and end times.
- Task status and priority management.
- Optional association between tasks and goals.
- Date-based task retrieval for daily and weekly planning.

Tasks are designed around scheduled execution rather than an unrestricted unscheduled backlog.

### Goal Management
- Goal creation and lifecycle management.
- Goal categories across different areas of life.
- Due dates and progress tracking.
- Association between goals and scheduled tasks.
- Active and completed goal states.

### AI-Ready User Context

TabBoard's backend establishes a structured foundation for future AI-powered planning.

Profile information, onboarding responses, interests, and personality preferences can provide contextual inputs for personalized recommendations and daily planning.

Gemini integration is planned as a subsequent development phase.

## Technology Stack

| Category | Technologies |
|---|---|
| Language | Python |
| Framework | Django |
| API | Django REST Framework |
| Database | PostgreSQL |
| Authentication | JWT / Google OAuth |
| Database Hosting | Supabase |
| API Architecture | REST |
| Development | Python Virtual Environment |

## Engineering & Design Considerations

### API-First Architecture

The backend exposes REST endpoints consumed by the Chrome extension, keeping business logic and data persistence independent of frontend implementation.

### User-Scoped Data Access

Authenticated endpoints enforce user-specific data access, ensuring that tasks, goals, and profile information are associated with the appropriate account.

### Date-Based Task Retrieval

Task retrieval is designed around date-based queries, supporting daily and weekly planning without requiring the frontend to download and filter an unrestricted task history.

### Structured Domain Modelling

Separate domain models represent users, onboarding information, tasks, goals, and goal categories, supporting clearer business logic and maintainability.

### Extensible Personalization

Onboarding responses and profile preferences are stored as structured data, establishing a foundation for future AI-assisted recommendations.

## API Overview

The API is versioned under `/api/v1/`.

| Module | Endpoint | Purpose |
|---|---|---|
| Authentication | `/api/v1/auth/` | Authentication and account access |
| Onboarding | `/api/v1/onboarding/` | Profile setup and personalization |
| Tasks | `/api/v1/tasks/` | Task management and scheduling |
| Goals | `/api/v1/goals/` | Goal management |
| Goal Categories | `/api/v1/goals/categories/` | Available goal categories |

*Endpoint paths are provided at the module level. Consult the implementation for individual HTTP methods and request/response contracts.*

## Getting Started

### Prerequisites
- Python
- PostgreSQL
- Git
- Python virtual environment support

### Installation

```bash
git clone <BACKEND_REPOSITORY_URL>
cd tabboard_api

python -m venv venv
source venv/bin/activate

pip install -r requirements.txt
```

### Environment Configuration

Configure the required environment variables for:

- Django secret key.
- Database connection.
- Google OAuth credentials.
- Authentication configuration.
- Allowed hosts and CORS settings.

Do not commit secrets or production credentials to the repository.

### Database Setup

```bash
python manage.py migrate
```

### Run Development Server

```bash
python manage.py runserver
```

The development API will be available at:

`http://127.0.0.1:8000/`

## Related Repository

- **Frontend:** [TabBoard Chrome Extension] https://github.com/RishabBaisakh/tabboard.git

## Development Status

**In Development**

The backend provides the foundation for TabBoard's authentication, onboarding, and core productivity workflows.

Further development focuses on expanding application capabilities, refining API contracts, and introducing AI-powered personalization.
