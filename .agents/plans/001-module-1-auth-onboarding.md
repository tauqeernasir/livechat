# Implementation Plan: Module 1 - Authentication & Onboarding

This plan outlines the steps to complete Module 1 as defined in the [PRD.md](../../PRD.md), including backend schema updates, API implementation, and the frontend onboarding flow.

## Assessment
- **Complexity**: Medium
- **Execution mode**: Multiple phases (Backend → Frontend UI → Integration)
- **Sub-agent feasibility**: Yes
    - **Stream A**: Backend models and API endpoints for Organization and Workspace.
    - **Stream B**: Frontend Auth pages (Login/Register).
    - **Stream C**: Onboarding Wizard UI (Business Profile & Workspace setup).

## Clarifications Asked & Assumptions Made
1.  **Email Verification**: Assumed optional for the initial implementation but planned as an endpoint.
2.  **Logo Storage**: Assumed local filesystem storage for the MVP, with a path stored in the database.
3.  **Custom Auth**: Building custom auth using the existing FastAPI endpoints instead of third-party providers.
4.  **One User - One Org**: Assumed a 1:1 relationship for the MVP onboarding flow (one user creates one organization).

## Edge Cases and Risks
- **Duplicate Signups**: Handled by unique email constraints.
- **Incomplete Onboarding**: Users might drop off after registration but before profile setup. Need to handle "Onboarding Status".
- **File Upload Failures**: Robust error handling for logo uploads.
- **Session Expiry**: Ensuring the JWT token remains valid during the multi-step onboarding process.

## Step-by-Step Plan

### Phase 1: Backend Infrastructure
1.  **Schema Update**:
    - Create `Organization` model: `id`, `name`, `website_url`, `industry`, `logo_path`, `primary_color`.
    - Create `Workspace` model: `id`, `org_id`, `name`, `is_default`.
    - Update `User` model to link to an `Organization`.
2.  **Migrations**: Run Alembic to apply schema changes.
3.  **API Implementation**:
    - `POST /api/v1/onboarding/profile`: Create organization and link to user.
    - `POST /api/v1/onboarding/workspace`: Create the initial default workspace.
    - `GET /api/v1/users/me`: Enhanced to return onboarding status.
4.  **Logo Upload**: Add a utility for handling image uploads to S3 compatible storage. (locally we will run minIO)

### Phase 2: Frontend Auth UI
1.  **Auth State Management**: Implement a `useAuth` hook and Context to manage user tokens and state.
2.  **Login/Register Pages**: 
    - Build premium, high-aesthetic forms using Tailwind
    - Connect to existing `/register` and `/login` endpoints.
3.  **Protected Routes**: Implement a routing wrapper to redirect unauthenticated users.

### Phase 3: Onboarding Flow
1.  **Onboarding Wizard**:
    - **Step 1**: Business Profile (Name, Website, Industry).
    - **Step 2**: Brand Identity (Logo upload, Color picker).
    - **Step 3**: Workspace Name (Default to "Main Workspace").
2.  **API Integration**: Connect the wizard steps to the new onboarding endpoints.
3.  **Final Redirect**: On completion, redirect the user to the Dashboard.

## Verification Strategy
- **Backend**: 
    - Unit tests for new models.
    - Integration tests for onboarding endpoints using `TestClient`.
- **Frontend**:
    - Verify form validation for registration and profile setup.
    - Test the "Happy Path": Register → Profile Setup → Brand Setup → Dashboard.
    - Test the "Drop-off": Register → Logout → Login → Resume Onboarding.

## Dependencies and Sequencing Constraints
- Backend models must be ready before Frontend integration.
- Auth Context must be implemented before building the Onboarding Wizard.

## Definition of Done
- [ ] Users can sign up and log in.
- [ ] New users are forced to complete a multi-step onboarding flow.
- [ ] Business profile (with logo) and default workspace are saved in the database.
- [ ] User state correctly reflects "Onboarded" status.
- [ ] UI meets the "Premium" design guidelines.
