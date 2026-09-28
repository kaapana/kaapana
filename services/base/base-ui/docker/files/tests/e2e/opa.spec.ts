import { expect, test } from '@playwright/test'
import { checkAuthR, checkRoleAuthR, type PolicyData } from '../../src/utils/opa'

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

test.describe('checkRoleAuthR', () => {
  test('matches endpoint regex and method', () => {
    expect(checkRoleAuthR(policyData, '/data-gallery-ui/', 'user')).toBe(true)
    expect(checkRoleAuthR(policyData, '/extensions-ui/', 'user')).toBe(false)
  })

  test('rejects when method is not allowed', () => {
    // readonly only allows POST, default method is GET
    expect(checkRoleAuthR(policyData, '/data-gallery-ui/', 'readonly')).toBe(false)
    expect(checkRoleAuthR(policyData, '/data-gallery-ui/', 'readonly', 'POST')).toBe(true)
  })

  test('strips protocol and domain from absolute URLs', () => {
    expect(checkRoleAuthR(policyData, 'https://example.org/data-gallery-ui/', 'user')).toBe(true)
    expect(checkRoleAuthR(policyData, 'https://example.org/extensions-ui/', 'user')).toBe(false)
  })

  test('returns false for roles without policy entries', () => {
    expect(checkRoleAuthR(policyData, '/data-gallery-ui/', 'unknown-role')).toBe(false)
    expect(checkRoleAuthR({}, '/data-gallery-ui/', 'user')).toBe(false)
  })

  // extensions-ui grants its kube-helm endpoints with end-anchored paths.
  test('an end-anchored grant does not match a longer endpoint', () => {
    const anchored: PolicyData = {
      endpoints_per_role: { user: [{ path: '^/kube-helm-api/extensions$', methods: ['GET'] }] },
    }
    expect(checkRoleAuthR(anchored, '/kube-helm-api/extensions', 'user')).toBe(true)
    expect(checkRoleAuthR(anchored, '/kube-helm-api/extensions-foo', 'user')).toBe(false)
  })
})

test.describe('checkAuthR', () => {
  test('grants access if any user role matches', () => {
    expect(checkAuthR(policyData, '/extensions-ui/', { roles: ['user', 'admin'] })).toBe(true)
    expect(checkAuthR(policyData, '/extensions-ui/', { roles: ['user'] })).toBe(false)
  })

  test('denies users without roles', () => {
    expect(checkAuthR(policyData, '/data-gallery-ui/', { roles: [] })).toBe(false)
  })

  // home-ui's "no authorization" state: the role exists but grants nothing.
  test('denies a role whose grant list is empty', () => {
    expect(checkAuthR({ endpoints_per_role: { user: [] } }, '/data-gallery-ui/', { roles: ['user'] })).toBe(
      false,
    )
  })
})
