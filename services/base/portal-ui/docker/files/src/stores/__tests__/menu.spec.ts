import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useMenuStore, NO_SECTION } from '@/stores/menu'
import { useAuthStore } from '@/stores/auth'
import { fetchMenu } from '@/api/menu'
import { fetchPolicyData } from '@/api/auth'
import type { MenuEntry, MenuSection } from '@/types/menu'

vi.mock('@/api/menu', () => ({ fetchMenu: vi.fn() }))
vi.mock('@/api/auth', () => ({ fetchPolicyData: vi.fn() }))

function entry(id: string, path: string, isDefault = false): MenuEntry {
  return {
    type: 'entry',
    id,
    label: id,
    icon: 'mdi-test',
    path,
    target: 'iframe',
    project: 'path',
    default: isDefault,
    order: 0,
  }
}

const section: MenuSection = {
  type: 'section',
  id: 'workflows',
  label: 'Workflows',
  icon: 'mdi-gamepad-variant',
  order: 0,
  entries: [entry('datasets', '/data-gallery-ui/'), entry('workflows', '/workflow-list-ui/')],
}

function setupStores(userRoles: string[]) {
  setActivePinia(createPinia())
  const auth = useAuthStore()
  auth.user = { username: 'test', roles: userRoles, groups: [], id: '1' }
  auth.isAuthenticated = true

  const menu = useMenuStore()
  menu.items = [entry('landing', '/landing-page/', true), section, entry('extensions', '/extensions-ui/')]
  menu.policyData = {
    endpoints_per_role: {
      admin: [{ path: '.*', methods: ['GET'] }],
      user: [{ path: '^/data-gallery-ui/', methods: ['GET'] }],
    },
  }
  menu.loaded = true
  return menu
}

describe('menu store OPA filtering', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('shows everything to a role matching all paths', () => {
    const menu = setupStores(['admin'])
    expect(menu.visibleItems).toHaveLength(3)
  })

  it('hides unauthorized entries and empty sections', () => {
    const menu = setupStores(['user'])
    expect(menu.visibleItems).toHaveLength(1)
    const visibleSection = menu.visibleItems[0] as MenuSection
    expect(visibleSection.type).toBe('section')
    expect(visibleSection.entries.map((e) => e.id)).toEqual(['datasets'])
  })

  it('hides all entries when no policy data is loaded', () => {
    const menu = setupStores(['admin'])
    menu.policyData = null
    expect(menu.visibleItems).toHaveLength(0)
  })
})

describe('menu store dev links', () => {
  const devLinks = [
    { label: 'Kaapana Backend', path: '/kaapana-backend/docs' },
    { label: 'AII', path: '/aii/docs' },
  ]

  it('offers every link a matching role can reach', () => {
    const menu = setupStores(['admin'])
    expect(menu.visibleDevLinks({ ...entry('a', '/a'), devLinks })).toHaveLength(2)
  })

  it('drops links outside the roles, even on a visible entry', () => {
    const menu = setupStores(['user'])
    menu.policyData = {
      endpoints_per_role: {
        user: [{ path: '^/data-gallery-ui/', methods: ['GET'] }],
      },
    }
    expect(menu.visibleDevLinks({ ...entry('datasets', '/data-gallery-ui/'), devLinks })).toEqual([])
  })

  it('offers nothing for an entry declaring no links', () => {
    const menu = setupStores(['admin'])
    expect(menu.visibleDevLinks(entry('a', '/a'))).toEqual([])
  })
})

describe('menu store entry resolution', () => {
  it('finds the default entry', () => {
    const menu = setupStores(['admin'])
    expect(menu.defaultEntry?.id).toBe('landing')
  })

  it('resolves path segments to section and top-level entries', () => {
    const menu = setupStores(['admin'])
    expect(menu.resolvePath(['workflows', 'datasets'])?.entry.path).toBe('/data-gallery-ui/')
    expect(menu.resolvePath(['extensions'])?.entry.path).toBe('/extensions-ui/')
    expect(menu.resolvePath(['workflows', 'datasets', 'a', 'b'])?.rest).toEqual(['a', 'b'])
    expect(menu.resolvePath(['extensions', 'deep'])?.rest).toEqual(['deep'])
    expect(menu.resolvePath(['datasets'])).toBeNull()
    expect(menu.resolvePath(['workflows'])).toBeNull()
    expect(menu.resolvePath(['workflows', 'nope'])).toBeNull()
    expect(menu.resolvePath([])).toBeNull()
  })

  it('maps entries back to their section slug', () => {
    const menu = setupStores(['admin'])
    expect(menu.sectionOf(section.entries[0]!)).toBe('workflows')
    expect(menu.sectionOf(menu.defaultEntry!)).toBe(NO_SECTION)
  })
})

describe('menu store refresh', () => {
  it('picks up installed and dropped entries, keeps identity when unchanged', async () => {
    const menu = setupStores(['admin'])
    vi.mocked(fetchPolicyData).mockResolvedValue(menu.policyData!)

    // extension installed: new entry appears
    const withExtension = [...menu.items, entry('mitk-flow', '/mitk-flow/')]
    vi.mocked(fetchMenu).mockResolvedValue({ items: withExtension })
    await menu.refresh()
    expect(menu.items.map((i) => i.id)).toContain('mitk-flow')

    // nothing changed: same payload must not replace state (no drawer churn)
    const before = menu.items
    await menu.refresh()
    expect(menu.items).toBe(before)

    // extension uninstalled: entry disappears
    vi.mocked(fetchMenu).mockResolvedValue({ items: before.filter((i) => i.id !== 'mitk-flow') })
    await menu.refresh()
    expect(menu.items.map((i) => i.id)).not.toContain('mitk-flow')
  })

  it('records a failed refresh, keeps the last known menu, clears on recovery', async () => {
    const menu = setupStores(['admin'])
    vi.mocked(fetchPolicyData).mockResolvedValue(menu.policyData!)
    vi.mocked(fetchMenu).mockRejectedValue(new Error('boom'))

    await expect(menu.refresh()).rejects.toThrow('boom')
    expect(menu.error).toBe(true)
    expect(menu.items).toHaveLength(3)

    vi.mocked(fetchMenu).mockResolvedValue({ items: menu.items })
    await menu.refresh()
    expect(menu.error).toBe(false)
  })
})
