# 🌌 Calendly ↔ Zoho CRM: Master Orchestration Hub

A high-fidelity, enterprise-grade synchronization engine designed to bridge the gap between **Calendly's dynamic booking ecosystem** and **Zoho CRM's relational intelligence**. This application serves as a centralized "Central Command" for managing real-time data flow, automated field provisioning, and personalized outreach.

---

## 🚀 The Core Vision

The mission of this extension is to transform scheduling from a manual task into a **data-driven orchestration**. By treating Calendly accounts as "Synchronization Nodes," the application ensures that every booking, cancellation, and no-show is immediately reflected in Zoho CRM, while allowing CRM data to "flow back" into Calendly via intelligent pre-fill matrices.

---

## 🛠️ System Architecture & Flow

### 1. Node Authentication (The Entry Point)
Users connect multiple Calendly accounts via OAuth 2.0. Each account is treated as a distinct **Synchronization Node**, allowing a single Zoho organization to manage bookings across multiple departments or team members.

### 2. Global Sync Directives
The **Master Orchestration Hub** provides two modes of operation:
*   **Standardized Orchestration (Default)**: A "one-click" high-performance mapping protocol for standard fields (URI, Status, Answers).
*   **Manual Tactical Mapping**: Granular control over which Calendly data point lands in which Zoho field, including **Auto-Creation** functionality that provision new fields in Zoho CRM directly from the extension UI.

### 3. Real-Time Data Streaming (Webhook Hub)
The engine utilizes a **Payload Strategy Node** to manage webhook subscriptions.
*   **Auto-Sync Hub**: With one click, the system negotiates with Calendly to set up public-facing webhooks (via secure tunnels) tracking `invitee.created`, `canceled`, and `rescheduled` events.
*   **Administrative Oversight**: Monitor the status, scope, and target URLs of all active streams in a real-time dashboard.

### 4. Pre-fill Orchestration Matrix
This is the "Intelligence Layer" where users map Zoho Lead/Contact fields to Calendly URL aliases (e.g., `a1`, `a2`, `a3`).
*   **Dynamic Link Synthesis**: When a Zoho record is accessed, the system generates a personalized booking URL where the user's details are already filled in.
*   **Vector Management**: Add and rearrange field vectors to match complex custom questions in your Calendly event types.

### 5. Outreach & Deployment
*   **Mailing Intelligence**: Integrated SMTP configuration allows users to send these synthesized booking links directly to Leads or Contacts from their own authorized mail nodes.
*   **System Simulator**: A built-in testing environment to validate URL generation and mapping logic before going live.

---

## 🧬 Technical Stack

*   **Logic Engine**: Django 4.1 (Python 3.14 compatible)
*   **Intelligence Layer**: MongoDB (Djongo) for flexible JSON field mapping and credential storage.
*   **Visual Interface**: Vanilla CSS & Tailwind CSS with a "High-Depth Glassmorphism" aesthetic.
*   **Integrations**: 
    - **Calendly API v2**: OAuth, Webhooks, Resource retrieval.
    - **Zoho CRM API**: Module management, Custom Field provisioning, Search & Update.
*   **Connectivity**: Designed for **ngrok/Public Tunnel** compatibility for seamless local-to-cloud development.

---

## 🌓 High-Fidelity Dashboard

The UI is built with a **Premium Multi-Pillar** design:
1.  **Left Column**: Master Sync Directives & Manual Field Overrides.
2.  **Right Column**: Deployment Control, SMTP Mailing Suite, and Architectural Support.
3.  **Real-Time Status Banners**: Instant feedback on Node health and Stream activity.

---

## 🚦 Getting Started

1.  **Authorize**: Connect your Zoho CRM account and at least one Calendly Node.
2.  **Directive Setup**: Choose "Standardized Orchestration" for instant setup or use "Manual Mapping" to create custom Zoho fields.
3.  **Tunnel Deployment**: Enter your public tunnel URL (ngrok) in the "Finalize Strategy" card.
4.  **Stream Sync**: Hit **"Sync Streams"** to authorize Calendly webhooks.
5.  **Matrices**: Configure your **Pre-fill Vectors** in the Credentials section to begin generating personalized booking flows.

---

> [!IMPORTANT]
> **Enterprise Reliability**: Always ensure your **Public Tunnel URL** is active when testing real-time webhooks locally. Calendly will reject private IP addresses (127.0.0.1).