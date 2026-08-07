import http from '@/api/http'

export interface AiiUser {
  id: string
  realm_roles: string[]
}

export interface Project {
  id: string | number
  name: string
  short_id?: string
  is_archived?: boolean
  /** The caller's role in this project (see fetchProjects for the source). */
  role_name?: string
}

export async function fetchCurrentAiiUser(): Promise<AiiUser> {
  const res = await http.get<AiiUser>('/aii/users/current')
  return res.data
}

export async function fetchProjects(user: AiiUser): Promise<Project[]> {
  const isAdmin = user.realm_roles.includes('admin')
  const url = isAdmin ? '/aii/projects' : `/aii/users/${user.id}/projects`
  const res = await http.get<Project[]>(url)
  // The per-user listing carries role_name; the admin listing has none, but the
  // gateway grants realm admins admin scope in every project regardless of
  // membership, so their global role is the accurate per-project answer.
  return isAdmin ? res.data.map((p) => ({ ...p, role_name: 'admin' })) : res.data
}

// Drop the legacy Project cookie a pre-URL-scoping session may have left
// behind: nothing reads it anymore, and auth-backend no longer falls back to
// it. Removable once no deployment upgrades from cookie-based versions.
export function clearLegacyProjectCookie(): void {
  document.cookie = 'Project=; path=/; max-age=0'
}
