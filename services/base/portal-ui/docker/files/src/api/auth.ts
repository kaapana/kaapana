import http from '@/api/http'
import type { PolicyData } from '@/utils/opa'

export interface UserinfoJwt {
  preferredUsername: string
  groups: string[]
  user: string
}

export async function fetchUserinfo(): Promise<UserinfoJwt> {
  // In dev mode the auth proxy is absent; a static token file stands in.
  const oauthUrl = import.meta.env.PROD ? '/oauth2/userinfo' : '/jsons/testingAuthenticationToken.json'
  const res = await http.get<UserinfoJwt>(oauthUrl)
  return res.data
}

export async function fetchPolicyData(): Promise<PolicyData> {
  const res = await http.get<PolicyData>('/kaapana-backend/open-policy-data')
  return res.data
}

export function logout(): void {
  location.href = '/kaapana-backend/oidc-logout'
}
