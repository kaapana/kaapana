/**
 * Typed wrappers for all KAAPANA_* env vars.
 * Centralises defaults so spec files never hardcode paths.
 */
export const WORKFLOW_UI    = process.env.KAAPANA_WORKFLOW_UI_PATH    ?? '/workflow-ui';
export const DATA_UI        = process.env.KAAPANA_DATA_UI_PATH        ?? '/data-ui/';
export const EXTENSION_MGR  = process.env.KAAPANA_EXTENSION_MGR_PATH  ?? '/extension-manager-ui';
export const PROJECTS_UI    = process.env.KAAPANA_PROJECTS_UI_PATH    ?? '/projects-ui';
export const OHIF           = process.env.KAAPANA_OHIF_PATH           ?? '/ohif/';
export const OS_DASHBOARDS  = process.env.KAAPANA_OS_DASHBOARDS_PATH  ?? '/os-dashboards/';
export const KUBE_DASHBOARD = process.env.KAAPANA_KUBE_DASHBOARD_PATH ?? '/kube-dashboard/';
