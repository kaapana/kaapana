export { postViewDirty } from './utils/viewDirty'
export { getProjectBase, getProjectSlug, switchProject } from './utils/selectedProject'
export { navigateShell } from './utils/shellNavigation'
export { httpClient, httpClientWithoutTimeout } from './utils/httpClient'
export { default as AuthService, type UserinfoJwt } from './utils/authService'
export { default as kaapanaApiService } from './utils/kaapanaApiService'
export { useAuthStore, type User } from './stores/auth'
export { useProjectStore, type Project } from './stores/project'
export {
  kaapanaThemeLight,
  kaapanaThemeDark,
  KAAPANA_THEME_LIGHT,
  KAAPANA_THEME_DARK,
} from './utils/vuetifyTheme'
export { createKaapanaVuetify, type KaapanaVuetifyOptions } from './utils/createKaapanaVuetify'
export { kaapanaIcons, type KaapanaIconName } from './utils/icons'
export { useShellSettings } from './composables/useShellSettings'
