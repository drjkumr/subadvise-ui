# SubAdvise UI

A Vue 3 single-page web application implementing the SubAdvise design system. The application serves as an intelligent dashboard for managing recurring subscriptions, tracking five-tier expense color classifications, and interacting with the SubAdvise AI Copilot assistant.

---

## Tech Stack & Architecture

- **Framework**: Vue 3 with Composition API (`<script setup>`)
- **Build Tool**: Vite (configured for dev server on port `7073` to match backend CORS settings)
- **Routing**: `vue-router` with `/` (Subscriptions Dashboard) and `/expense-tools` (Expense Targets & Currency)
- **State Management**: Pinia (`subscriptions` store and `chat` store)
- **HTTP Client**: Centralized API client modules with timeout handling and error formatting
- **Styling**: SubAdvise Design System (`template.css` base with custom application extensions in `app.css`)
- **Persistence**: `localStorage` for chat session metadata (`subadvise.chatSessions`) and first-use notice state (`subadvise.chatIntroSeen`), plus `sessionStorage` for sidebar toggling (`subadvise.chatOpen`).

---

## Environment Configuration

Create a `.env` file in the root directory (copied from `.env.example`):

```bash
cp .env.example .env
```

### Environment Variables

| Variable | Default Value | Description |
|---|---|---|
| `VITE_SUBADVISE_API_URL` | `http://localhost:7071` | Base URL for the Spring Boot SubAdvise API |
| `VITE_SUBADVISE_AI_API_URL` | `http://localhost:7072` | Base URL for the FastAPI SubAdvise AI Assistant API |

---

## Getting Started

### Prerequisites

- Node.js (v18+ or v24+)
- npm or pnpm

### Installation

```bash
npm install
```

### Development Server

```bash
npm run dev
```

The application starts at `http://localhost:7073/`.

### Production Build

```bash
npm run build
```

The production output is generated in the `dist/` directory.

### Preview Build

```bash
npm run preview
```

---

## Features & Implementation Highlights

### 1. Subscriptions Management
- **Subscription List**: Displays recurring subscriptions with name initials, start date, renewal date, price, currency, and relative cost classification level.
- **Monthly Renewal Total**: Shows current-month renewal prices grouped by currency using `GET /api/subscriptions/monthly?year={year}&month={month}`.
- **Search by Name**: Server-side search hitting `GET /api/subscriptions/search?name={name}`, debounced by 300 ms, automatically resetting pagination to page 1.
- **Add & Edit Subscriptions**: Validates required fields client-side (`subscriptionName`, `subscriptionDate`, `renewalDate`, `subscriptionPrice`, `currency`) and surfaces server errors.
- **Delete Subscription**: Accessible confirmation dialog prior to calling `DELETE /api/subscriptions/{id}`, automatically refreshing the page if the deleted row leaves the current page empty.
- **Pagination**: Capped at 50 subscriptions per page with range display (e.g. `1–50 of 137`) and previous/next page navigation.

### 2. Five-Level Color Threshold Classification
- Configured via `GET /api/expenses/color-thresholds` and `PUT /api/expenses/color-thresholds`.
- Five descending percentage tiers:
  - **RED**: Most expensive (default: `50%`)
  - **ORANGE**: Expensive (default: `30%`)
  - **YELLOW**: Medium (default: `15%`)
  - **LIME**: Low (default: `5%`)
  - **GREEN**: Lowest cost / one of the lowest as a part of the whole (default: `0%`)
- Validates strictly descending order (`red > orange > yellow > lime > green`) and range between `0` and `100`.
- Automatically refreshes subscription rows upon saving so newly computed classifications take effect immediately.

### 3. Expense Targets & Monthly Tracking
- Creates targets with a name, amount, currency, and start/end dates using `POST /api/expenses/targets`.
- Renews a target from its progress row, carrying over its name, amount, and currency while setting the new start date to the day after the prior end date; the new end date is user-selected.
- Records actual expenses against selected targets using `POST /api/expenses`; the API enforces that target and expense currencies match.
- Shows monthly totals by currency, target progress, and expense totals using `GET /api/expenses/monthly`.
- The API does not expose a target-list endpoint, so target IDs and UI-only names are stored in browser `localStorage` under `subadvise.expenseTargets` for later expense logging.

### 4. Currency Conversion
- Converts an arbitrary amount with `GET /api/currency/convert`, showing the conversion result, rate timestamp/provider, and required ExchangeRate-API attribution link.
- Converts and saves a subscription's price and currency with `PATCH /api/subscriptions/{id}/convert?to={currency}` from its row actions.
- Displays API errors when a rate is unavailable; exchange rates are cached by the provider and may update once per day.

### 5. AI Copilot Sidebar
- **Collapsible Drawer**: Toggled via a fixed floating button in the bottom-right corner or the navigation header, remembering state for the session.
- **First-Use Expectation Notice**: Calm, clear banner displayed once per browser (saved under `subadvise.chatIntroSeen` in `localStorage`) explaining that local AI model initialization can take time and asking users not to resend messages. Requires dismissal with a "Got it" button before chatting.
- **Session Lifecycle & History**:
  - Requires entering a session name before sending the first message.
  - Calls `POST /api/assistant/sessions` and persists `{ sessionId, name, createdAt }` in `localStorage` under `subadvise.chatSessions`.
  - Fallback to `"Untitled chat"` if a session name is missing.
  - Supports loading past sessions via `GET /api/assistant/sessions/{sessionId}`.
- **Messaging & Waiting State**:
  - Generous 120-second timeout for `POST /api/assistant/chat`.
  - Typing indicator with calm waiting reminder.
  - Preserves conversation history when errors occur.
- **Confirm and Deny Action Buttons**:
  - Automatically scans AI responses for the whole word `confirm` (case-insensitive).
  - Renders inline `Confirm` and `Deny` action buttons beneath the message.
  - Clicking `Confirm` or `Deny` sends the exact word back to the AI session.
  - Automatically dismissed once clicked or when any other message is submitted.

---

## Project Structure

```
subadvise-ui/
├── public/
│   ├── favicon.png
│   └── subadvise-logo.png
├── src/
│   ├── api/
│   │   ├── subadviseApi.js       # Central API client for Spring Boot service
│   │   └── subadviseAiApi.js     # Central API client for FastAPI AI service
│   ├── assets/
│   │   ├── app.css               # Design system extensions (modals, badges, chat)
│   │   ├── template.css          # Baseline SubAdvise Design System CSS
│   │   └── subadvise-logo.png
│   ├── components/
│   │   ├── AiChatSidebar.vue     # Collapsible AI Copilot drawer with history & notice
│   │   ├── ColorThresholdModal.vue # Five-tier threshold classification editor
│   │   ├── ConvertSubscriptionModal.vue # Convert and save a subscription currency
│   │   ├── ExpenseTargetsPanel.vue # Target budgets, actual expenses, and monthly reports
│   │   ├── CurrencyConversionPanel.vue # Ad-hoc currency conversion tool
│   │   ├── DeleteConfirmModal.vue  # Accessible confirmation modal
│   │   ├── Navbar.vue            # Brand header with logo and Copilot toggle
│   │   ├── SubscriptionModal.vue # Add/Edit subscription dialog with validation
│   │   └── SubscriptionTable.vue # Data table with search, pagination, and actions
│   ├── router/
│   │   └── index.js              # Single-route Vue router configuration
│   ├── stores/
│   │   ├── chat.js               # Pinia store for sessions, history, and AI chat
│   │   └── subscriptions.js      # Pinia store for subscriptions and thresholds
│   ├── utils/
│   │   └── currencies.js         # Supported ISO 4217 currency list from API docs
│   ├── views/
│   │   └── DashboardView.vue     # Main dashboard view matching template.html
│   ├── App.vue                   # Root Vue component
│   └── main.js                   # Application entry point
├── subadvise-template/           # Source template assets and HTML
├── resources/                    # Backend API sources and OpenAPI/Markdown docs
├── .env                          # Local environment variables
├── .env.example                  # Template environment variables
├── index.html                    # Single-page HTML shell
├── package.json
└── vite.config.js
```
