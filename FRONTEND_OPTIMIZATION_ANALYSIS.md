# Frontend Optimization Analysis & Plan

This document outlines the identified issues (specifically internationalization and display inconsistencies) and the plan to resolve them for a fully polished, "Grand & High-Tech" user experience.

## 1. Internationalization (i18n) Inconsistencies

The following files contain hardcoded text strings that need to be replaced with `t('...')` calls using the `useLanguage` composable. Missing keys will be added to `en.js` and `zh-CN.js`.

### `frontend/src/views/AgentChatView.vue`
*   **Hardcoded Strings:**
    *   "Preliminary Analysis Complete. Please Review."
    *   "Preliminary Investment Memo"
    *   "Company Info", "Name", "Industry", "Stage"
    *   "Team Assessment", "Team analysis completed."
    *   "Market Analysis", "Market analysis completed."
    *   "Key Due Diligence Questions"
    *   "Answer Input" placeholder: "Enter your answer or notes here..."
    *   "Analysis Completed Successfully!"
    *   "Report Saved", "Save Analysis Report"
    *   Right Sidebar: "Elapsed Time", "Est. Remaining", "Current Action", "Processing...", "Configuration", "Company", "Type", "Agents", "Active"
    *   Status Badges: "Completed", "Pending"
*   **Action:** Extract all English strings to `agentChat.hitl`, `agentChat.report`, and `agentChat.sidebar` namespaces.

### `frontend/src/components/layout/AppSidebar.vue`
*   **Hardcoded Strings:**
    *   "Megellan" (Brand name, likely fine to keep static, but subtitle might need translatability if desired)
    *   "AI INVESTMENT" (Subtitle)
*   **Action:** Add `sidebar.brandSubtitle` key.

### `frontend/src/components/analysis/ScenarioSelection.vue`
*   **Hardcoded Mock Data:**
    *   The fallback mock data has hardcoded English names/descriptions (`'Early Stage VC'`, `'Analyze pre-seed/seed...'`, etc.).
    *   **Issue:** When the backend fails or isn't running, these English strings are shown even if the user selects Chinese.
    *   **Action:** Update the mock data to use translation keys (e.g., `t('scenarios.earlyStage.name')`) or logic to switch content based on the current locale.

### `frontend/src/views/DashboardView.vue`
*   **Hardcoded Strings:**
    *   Agent Card: "ACTIVE TASKS", "IDLE" (in `AgentCard.vue` mostly, but referenced here).
    *   Charts: Tooltips and legends might need explicit translation handling if they aren't automatically updating.

## 2. Visual & Display Issues

### `frontend/src/views/AgentChatView.vue`
*   **Z-Index & Layout:**
    *   The "Back" button has `absolute top-6 left-6`. In a full-screen "Glass" layout, ensure it doesn't overlap with the sidebar or header elements on smaller screens.
*   **Contrast:**
    *   Some text colors (e.g., `text-primary/80`) on the new glass backgrounds need verification against the deep blue background to ensure readability.

### `frontend/src/components/analysis/ScenarioSelection.vue`
*   **Card Layout:**
    *   The grid uses `grid-cols-1 md:grid-cols-2 xl:grid-cols-3`. Ensure the card height is consistent if descriptions vary in length.
    *   **Fix:** Add `h-full` or `flex flex-col` to card containers to ensure equal height alignment.

## 3. Optimization Plan

### Phase 1: i18n Dictionary Update
1.  Update `frontend/src/i18n/en.js` and `frontend/src/i18n/zh-CN.js`:
    *   Add keys for `agentChat.hitl` (Human-in-the-loop) section.
    *   Add keys for `agentChat.report` (Preliminary report view).
    *   Add keys for `scenarios` (Names and descriptions for the mock data).

### Phase 2: Component Refactoring
1.  **`AgentChatView.vue`**: Replace all hardcoded strings with `t()`.
2.  **`ScenarioSelection.vue`**: Refactor the mock data generation to use `computed` properties that react to language changes, using the new `scenarios` translation keys.
3.  **`AppSidebar.vue`**: Internationalize the brand subtitle.

### Phase 3: Visual Polish
1.  **`ScenarioSelection.vue`**: Ensure scenario cards have equal heights using Flexbox/Grid alignment.
2.  **`AgentChatView.vue`**: Verify padding and z-indexes for the floating "Back" button.

---
**Next Step:** Execute Phase 1 (Dictionary Update).
