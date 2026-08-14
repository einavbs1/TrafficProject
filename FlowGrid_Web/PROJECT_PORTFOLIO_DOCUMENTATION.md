# 2.1 User's Guide

This guide describes the standard operating procedures for **Administrators** and **Operators** using the FlowGrid web dashboard. It covers the primary workflows from sign-in through junction monitoring and user management.

---

## Overview

FlowGrid is a traffic-intelligence dashboard for monitoring AI-controlled intersections (junctions). After signing in, you select a junction to work with. The sidebar provides access to all main features. Some pages — Dashboard, Live Stream, and Device Settings — require an active junction selection before they become available.

The platform supports two roles:

| Role | Purpose |
|------|---------|
| **Administrator** | Full access to user and group management, permissions, and all operational features |
| **Operator** | Day-to-day monitoring and junction operations |

---

## 1. Signing In

1. Open the FlowGrid web application in your browser.
2. On the **Welcome back** login screen, enter your **Username** and **Password**.
3. Click **Sign in**.
4. After a brief loading state, you are redirected into the application.

**Demo accounts for evaluation:**

| Role | Username | Password |
|------|----------|----------|
| Administrator | `admin` | `admin123` |
| Operator | `operator` | `op123` |

5. If no junction is currently selected, you are directed to the **Select Junction** page before accessing the live dashboard.

You can toggle between **dark** and **light** theme at any time using the theme button in the top-right corner of the login screen (and in the sidebar after sign-in).

---

## 2. Selecting a Junction

A junction must be selected before you can view the Dashboard, Live Stream, or Device Settings. Junctions are organized in a three-level hierarchy.

### 2.1 Browse by Hierarchy

1. On the **Select Junction** page, review the list of **Districts** (e.g., Tel Aviv, Haifa, Jerusalem).
2. Click a district card to open its sub-groups.
3. Choose either a **City** (urban roads) or a **Freeway** (highway interchanges).
4. Click a **Junction card** to select it.
5. You are taken directly to the **Dashboard** for that junction.

### 2.2 Search for a Junction

1. Use the search bar at the top of the **Select Junction** page.
2. Type a junction name, city, district, freeway, or location.
3. Click the matching junction card in the results.
4. You are taken to the **Dashboard**.

### 2.3 Switch or Clear the Active Junction

Once inside the application, the sidebar shows the **Active Junction** at the top:

- Click the **switch** icon (↔) to return to **Select Junction** and choose a different junction.
- Click the **clear** icon (✕) to deselect the current junction and return to **Select Junction**.

If no junction is selected, junction-dependent menu items in the sidebar appear locked until you select one.

---

## 3. Navigating the Dashboard

The sidebar is the primary navigation control. Available pages:

| Menu Item | Description | Requires Junction |
|-----------|-------------|-----------------|
| **Dashboard** | Multi-camera live overview with traffic metrics | Yes |
| **Live Stream** | Full-screen single-camera view | Yes |
| **Device Settings** | Camera device list and configuration | Yes |
| **Manage Users** | User profiles, groups, and permissions | No |
| **Reports** | Analytics charts and incident history | No |
| **Junctions** | All junctions — view, switch, or add | No |

### 3.1 Viewing the Live Dashboard

1. Select a junction (see Section 2).
2. Click **Dashboard** in the sidebar (or arrive there automatically after selection).
3. The page header shows the junction name, camera count, and direction count.
4. Each camera appears as a **quadrant card** displaying:
   - Camera direction and name
   - Live/Offline status badge
   - Stream preview area
   - **Wait Time** (seconds)
   - **Queue** (vehicle count)
   - **Signal** state (Green, Yellow, or Red)
5. Metrics refresh automatically every five seconds.

The layout adapts to the number of cameras at the junction (2–6 cameras supported in the grid).

### 3.2 Live Stream

1. With a junction selected, click **Live Stream** in the sidebar.
2. The main panel shows the currently selected camera feed.
3. Use the **Cameras** list on the right to switch between camera angles.
4. The header displays the camera ID, direction, IP address, resolution, and camera type.

### 3.3 Device Settings

1. With a junction selected, click **Device Settings** in the sidebar.
2. Review the list of cameras assigned to the junction.
3. Click **Configure** on a device card to open the **Device Configuration** modal.
4. Review or edit device fields (name, ID, direction, IP, RTSP URL, type, firmware).
5. Click **Save Changes** to confirm, or **Cancel** to close without saving.

### 3.4 Reports

1. Click **Reports** in the sidebar.
2. Use the junction filter to focus analytics on a specific intersection.
3. Review KPI cards, traffic charts, signal-phase distribution, and the incident log.

### 3.5 Junctions Overview

1. Click **Junctions** in the sidebar.
2. Browse all junctions in the system.
3. Click **Switch to this junction** on any card to make it the active junction and open the Dashboard.
4. Toggle a junction's **Active / Training** status using the power button on its card.
5. Click the **flowchart** icon to view the DQN pipeline diagram for that junction.

---

## 4. Adding a New Junction

You can add a junction from either the **Select Junction** page or the **Junctions** page.

1. Click **Add Junction** (or **Add New Junction**).
2. Complete the four-step wizard:

   **Step 1 — Location**
   - Enter the **Junction Name**.
   - Select an existing **District** or type a new district name.
   - Choose **Road Type**: **City Road** (urban) or **Freeway**.
   - For urban roads, enter the **City**. For freeways, enter the **Freeway Name**.
   - Enter **GPS / Address** coordinates or location text.
   - Click **Next**.

   **Step 2 — Directions**
   - Select one or more compass directions (e.g., North, East, South, West).
   - Each selected direction automatically provisions one camera.
   - Click **Next**.

   **Step 3 — Signals**
   - Set the number of **Traffic Signals** (recommended value shown based on direction count).
   - Click **Next**.

   **Step 4 — AI Model**
   - Select the **DQN Model Version** (Latest, Stable, or Legacy).
   - Click **Create Junction**.

3. The new junction is created with cameras auto-generated for each direction.
4. You are automatically switched to the new junction and taken to the **Dashboard**.

New junctions are created in **Training** status by default.

---

## 5. Managing Users and Groups

Navigate to **Manage Users** from the sidebar. This section is primarily used by **Administrators**, though all signed-in users can view the user list.

### 5.1 Viewing and Searching Users

1. Click **Manage Users** in the sidebar.
2. Use the **search bar** to find users by name, email, or employee ID.
3. Filter by **group** using the colored group chips (Traffic Ops, Field Technicians, Supervisors).
4. Filter by **role** using the **Administrators** or **Operators** buttons.
5. Navigate pages using the pagination controls at the bottom of the table.

### 5.2 Managing Groups (Administrator)

1. On the **Manage Users** page, locate the **Groups** row below the page title.
2. Click **New Group** to open the **Create Group** dialog.
3. Enter a group name and choose a color, then confirm creation.
4. Click a group chip to filter the user table to members of that group.
5. Click the **delete** icon on a group chip to remove the group.

### 5.3 Adding a User (Administrator)

1. Click **Add User** in the top-right corner.
2. Fill in the user profile fields: name, email, username, role, status, employee ID, and group assignments.
3. Save the new user record.

### 5.4 Editing a User Profile

1. In the user table, click the **edit** icon on a user row.
   - Administrators can edit any user.
   - Operators can edit their own profile.
2. Update the desired fields in the **Edit Profile** modal.
3. Save the changes.

### 5.5 Managing Permissions (Administrator)

1. In the user table, click the **shield** icon on a user row.
2. Review the six permission toggles:
   - View Dashboard
   - Manage Cameras
   - Edit Junctions
   - View Reports
   - Manage Users
   - System Settings
3. Enable or disable permissions as needed.
4. Click **Save Permissions**.

### 5.6 Managing Your Own Profile

1. Click your **name and avatar** at the bottom of the sidebar.
2. Update your profile details in the modal.
3. Save and close.

---

## 6. Signing Out

1. Click **Sign out** at the bottom of the sidebar.
2. You are returned to the login screen. Your active junction selection is cleared.

---

# 2.2 Maintenance Guide

This guide is intended for **developers** who will install, run, and continue building the FlowGrid web platform frontend.

---

## 1. System Overview

FlowGrid Web is a **single-page application (SPA)** built with React and bundled by Vite. It is a frontend-only project — there is no backend server, database, or API layer in this repository. All application data (junctions, users, metrics) is managed in-browser during the current prototype phase.

**Source layout:**

```
flowgrid_web/
├── index.html              # HTML entry point
├── package.json            # Dependencies and npm scripts
├── vite.config.js          # Vite + React + Tailwind configuration
├── eslint.config.js        # ESLint rules
└── src/
    ├── main.jsx            # React bootstrap
    ├── App.jsx             # Routes and context providers
    ├── AuthContext.jsx     # Authentication state
    ├── JunctionContext.jsx # Junction and camera data
    ├── ThemeContext.jsx    # Dark/light theme
    ├── index.css           # Tailwind theme and utilities
    ├── pages/              # Route-level page components
    └── components/         # Shared UI components
```

---

## 2. Required Software Environment

The following tools must be available on the development machine before working with this project.

| Tool | Requirement |
|------|-------------|
| **Node.js** | Version **20.x** or **22.x** (LTS recommended). Required by Vite 8. |
| **npm** | Version **10.x** or later (bundled with Node.js). Used for dependency management and scripts. |
| **Git** | Any recent version. Required to clone the repository. |

**Core framework versions** (from `package.json`):

| Package | Version |
|---------|---------|
| React | ^19.2.6 |
| React DOM | ^19.2.6 |
| React Router DOM | ^7.15.1 |
| Vite | ^8.0.12 |
| Tailwind CSS | ^4.3.0 |
| Recharts | ^3.8.1 |
| Lucide React | ^1.16.0 |

**npm scripts available:**

| Script | Command | Purpose |
|--------|---------|---------|
| Development server | `npm run dev` | Start Vite dev server with hot module replacement |
| Production build | `npm run build` | Compile optimized static assets to `dist/` |
| Preview build | `npm run preview` | Serve the production build locally for testing |
| Lint | `npm run lint` | Run ESLint across the project |

---

## 3. Installation Instructions

Follow these steps to set up the FlowGrid frontend for local development.

### Step 1 — Clone the Repository

```bash
git clone <repository-url>
cd flowgrid_web
```

Replace `<repository-url>` with the actual Git remote URL for the FlowGrid web project.

### Step 2 — Install Dependencies

From the project root directory, install all npm packages:

```bash
npm install
```

This reads `package.json` and `package-lock.json` and installs React, Vite, Tailwind CSS, and all other dependencies into `node_modules/`.

### Step 3 — Start the Development Server

```bash
npm run dev
```

Vite starts a local development server. By default, the application is available at:

```
http://localhost:5173
```

Open this URL in a browser. The dev server supports **hot module replacement (HMR)** — code changes in `src/` are reflected in the browser without a full page reload.

### Step 4 — Verify the Application

1. Navigate to `http://localhost:5173`.
2. Sign in with the demo Administrator account (`admin` / `admin123`).
3. Select a junction and confirm the Dashboard loads with camera quadrant cards.

---

## 4. Additional Development Commands

### Production Build

To compile the application for deployment:

```bash
npm run build
```

Output is written to the `dist/` directory as static HTML, CSS, and JavaScript files suitable for hosting on any static file server or CDN.

### Preview Production Build

To test the production build locally before deployment:

```bash
npm run preview
```

### Linting

To check code quality with ESLint:

```bash
npm run lint
```

---

## 5. Configuration Files

| File | Purpose |
|------|---------|
| `vite.config.js` | Registers the React and Tailwind CSS Vite plugins |
| `eslint.config.js` | ESLint flat config with React Hooks and React Refresh rules |
| `src/index.css` | Tailwind v4 `@theme` tokens, glassmorphism utilities, dark/light theme variables |
| `index.html` | SPA shell; page title set to "FlowGrid — Traffic Intelligence" |

No environment variables (`.env`) are required for the current prototype. When a backend API is integrated in the future, Vite environment variables should be prefixed with `VITE_` (e.g., `VITE_API_URL`).

---

## 6. Architecture Notes for Future Development

These points are relevant when extending the codebase:

- **State management:** Application state uses React Context (`AuthContext`, `JunctionContext`, `ThemeContext`). No global store library is present.
- **Routing:** React Router v7 with two guards — `ProtectedRoute` (authentication) and `RequiresJunction` (junction selection).
- **Data layer:** Junction and user data are currently in-memory mock data. Replacing Context providers with API calls (e.g., via TanStack Query) is the expected next step.
- **Authentication:** Demo credentials in `AuthContext.jsx`; session stored in `sessionStorage` under key `fg_user`.
- **Styling:** Tailwind CSS v4 with custom design tokens. Theme switching via `data-theme` attribute on `<html>`.
- **No TypeScript:** The project uses plain JSX. Migration to TypeScript is recommended for production hardening.
- **No test suite:** No test runner is configured in `package.json`.

For a full technical audit of the current implementation, refer to `DEVELOPMENT_STATUS_AND_ARCHITECTURE_REPORT.md` in the repository root.
