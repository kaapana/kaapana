import { describe, it, expect } from 'vitest'
import { checkAuthR, checkRoleAuthR, type PolicyData } from '@/utils/opa'

const policyData: PolicyData = {
  endpoints_per_role: {
    admin: [{ path: '.*', methods: ['GET', 'POST'] }],
    user: [
      { path: '^/data-gallery-ui/', methods: ['GET'] },
      { path: '^/landing-page/', methods: ['GET'] },
    ],
    readonly: [{ path: '^/data-gallery-ui/', methods: ['POST'] }],
  },
}

describe('checkRoleAuthR', () => {
  it('matches endpoint regex and method', () => {
    expect(checkRoleAuthR(policyData, '/data-gallery-ui/', 'user')).toBe(true)
    expect(checkRoleAuthR(policyData, '/extensions-ui/', 'user')).toBe(false)
  })

  it('rejects when method is not allowed', () => {
    // readonly only allows POST, default method is GET
    expect(checkRoleAuthR(policyData, '/data-gallery-ui/', 'readonly')).toBe(false)
    expect(checkRoleAuthR(policyData, '/data-gallery-ui/', 'readonly', 'POST')).toBe(true)
  })

  it('strips protocol and domain from absolute URLs', () => {
    expect(checkRoleAuthR(policyData, 'https://example.org/data-gallery-ui/', 'user')).toBe(true)
    expect(checkRoleAuthR(policyData, 'https://example.org/extensions-ui/', 'user')).toBe(false)
  })

  it('returns false for roles without policy entries', () => {
    expect(checkRoleAuthR(policyData, '/data-gallery-ui/', 'unknown-role')).toBe(false)
    expect(checkRoleAuthR({}, '/data-gallery-ui/', 'user')).toBe(false)
  })
})

describe('checkAuthR', () => {
  it('grants access if any user role matches', () => {
    expect(checkAuthR(policyData, '/extensions-ui/', { roles: ['user', 'admin'] })).toBe(true)
    expect(checkAuthR(policyData, '/extensions-ui/', { roles: ['user'] })).toBe(false)
  })

  it('denies users without roles', () => {
    expect(checkAuthR(policyData, '/data-gallery-ui/', { roles: [] })).toBe(false)
  })
})
