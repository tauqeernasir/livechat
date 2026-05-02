# Product Requirement Document: AI-Support SaaS MVP

## 1. Executive Summary
A B2B SaaS platform allowing business owners to deploy AI-powered customer support agents. The system leverages RAG (Retrieval-Augmented Generation) to provide accurate, business-specific responses, capture leads, and reduce support overhead.

---

## 2. Module 1: Authentication & Onboarding
**Goal:** Minimize friction while securing business data.

* **1.1 User Auth:** * Sign-up/Login via Email/Password.
    * Password reset flow.
    * Email verification (OTP or Link).
* **1.2 Business Profile:**
    * Basic metadata: Business name, website URL, industry.
    * Brand Identity: Upload logo, primary brand color (used for the widget).
* **1.3 Workspace:** * Each user gets one default "Project" or "Chatbot" workspace.

---

## 3. Module 2: Knowledge Base & Training
**Goal:** Provide the "brain" for the AI with high accuracy and control.

* **2.1 Data Ingestion:**
    * **File Upload:** PDF, Docx, TXT (Max 10MB per file).
    * **Text Editor:** Rich text area for manual entry of policies or FAQ.
    * **Website Scraper:** Enter a URL to crawl and extract text content.
* **2.2 Data Processing:**
    * Automatic chunking and embedding generation (using any embedding model).
    * Vector Store storage (Postgresql + pgvector).
* **2.3 Training Guardrails (Rules):**
    * System Prompt Editor: Define the AI's "Persona" (e.g., "You are a helpful assistant for [Business Name]").
    * "Fallback" Rule: Instructions for what to do when an answer isn't found (e.g., "Collect email and say a human will respond").

---

## 4. Module 3: Internal Testing Interface
**Goal:** Allow owners to verify the AI's knowledge before going live.

* **3.1 Playground:** * A full-page chat interface that mimics the widget.
    * **Source Citations:** Display which document/link the AI used to generate the answer (transparency for the owner).
* **3.2 Knowledge Selection:** * Toggle specific documents "On" or "Off" to see how it affects response accuracy.
* **3.3 Reset Session:** Clear chat history to test different user journeys.

---

## 5. Module 4: The Chat Widget
**Goal:** A lightweight, performant, and customizable UI for the end-user.

* **4.1 Customization:**
    * Visual: Color, position (bottom-right/left), custom icon.
    * Content: Custom welcome message, placeholder text.
* **4.2 Technical Delivery:**
    * **Script Tag:** A single line of `<script>` for businesses to copy-paste.
    * **Iframe vs. Shadow DOM:** Use a Shadow DOM approach to prevent CSS leakage from the parent site.
* **4.3 Lead Generation:** * Inline form: "Please provide your email to start the chat" (Optional toggle).

---

## 6. Module 5: Business Dashboard & Analytics
**Goal:** Centralized hub for management and performance review.

* **5.1 Chat Logs:**
    * Full history of every conversation between AI and customers.
    * Ability to export logs as CSV.
* **5.2 Performance Metrics:**
    * Total Conversations.
    * Leads Captured.
    * Response Accuracy Rating (User Thumbs Up/Down on the widget).
* **5.3 Subscription Management:**
    * Plan details (Free vs. Pro).
    * Usage tracking (e.g., "50 of 100 messages used").
    * Integration with Stripe Billing.

---

## 7. Technical Requirements (MVP)
* **Frontend:** React + Vite, Tailwind, tanstack query (Dashboard)
* **Backend:** Python (FastAPI), Langgraph, Langchain.
* **Database:** PostgreSQL + pgvector.
* **LLM:** Any Commericial but cost-effective LLM.

---

## 8. Success Metrics
* **Time to Deploy:** A user should be able to go from sign-up to live widget in < 5 minutes.
* **Accuracy:** > 80% customer satisfaction on AI responses during the first month.