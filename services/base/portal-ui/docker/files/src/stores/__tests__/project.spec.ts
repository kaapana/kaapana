import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('@/api/projects', () => ({
  fetchCurrentAiiUser: vi.fn(),
  fetchProjects: vi.fn(),
  clearLegacyProjectCookie: vi.fn(),
}))

import { useProjectStore, withProjectSlug } from '@/stores/project'
import { useMenuStore } from '@/stores/menu'
import { fetchCurrentAiiUser, fetchProjects, type Project } from '@/api/projects'

const P = (id: number, name: string): Project => ({ id, name, short_id: name })

describe('project store refreshProjects', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.mocked(fetchCurrentAiiUser).mockResolvedValue({ id: 'u1', realm_roles: ['admin'] })
  })

  it('grows the list when a project appears, without disturbing the selection', async () => {
    const store = useProjectStore()
    store.availableProjects = [P(1, 'a')]
    store.selectedProject = P(1, 'a')
    vi.mocked(fetchProjects).mockResolvedValue([P(1, 'a'), P(2, 'b')])

    await store.refreshProjects()

    expect(store.availableProjects.map((p) => p.id)).toEqual([1, 2])
    expect(store.selectedProject?.id).toBe(1)
  })

  it('keeps the last list when the fetch fails', async () => {
    const store = useProjectStore()
    store.availableProjects = [P(1, 'a')]
    vi.mocked(fetchProjects).mockRejectedValue(new Error('boom'))

    await store.refreshProjects()

    expect(store.availableProjects.map((p) => p.id)).toEqual([1])
  })

  it('does not replace the list reference when the payload is unchanged', async () => {
    const store = useProjectStore()
    store.availableProjects = [P(1, 'a')]
    const before = store.availableProjects
    vi.mocked(fetchProjects).mockResolvedValue([P(1, 'a')])

    await store.refreshProjects()

    expect(store.availableProjects).toBe(before)
  })
})

describe('menu store polling piggybacks the project refresh', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('refreshes the project list on the menu-poll cadence', () => {
    vi.useFakeTimers()
    const menu = useMenuStore()
    const project = useProjectStore()
    const refreshProjects = vi.spyOn(project, 'refreshProjects').mockResolvedValue()
    vi.spyOn(menu, 'refresh').mockResolvedValue()

    menu.startPolling()
    expect(refreshProjects).not.toHaveBeenCalled()

    vi.advanceTimersByTime(15_000)
    expect(refreshProjects).toHaveBeenCalledTimes(1)

    vi.advanceTimersByTime(15_000)
    expect(refreshProjects).toHaveBeenCalledTimes(2)

    vi.useRealTimers()
  })
})

describe('withProjectSlug', () => {
  it('swaps an existing prefix', () => {
    expect(withProjectSlug('/project/old/data/gallery', 'new')).toBe('/project/new/data/gallery')
  })

  it('swaps a bare prefix', () => {
    expect(withProjectSlug('/project/old', 'new')).toBe('/project/new')
  })

  it('prepends to an unprefixed path', () => {
    expect(withProjectSlug('/data/gallery', 'new')).toBe('/project/new/data/gallery')
  })

  it('maps "/" to the bare prefix', () => {
    expect(withProjectSlug('/', 'new')).toBe('/project/new')
  })
})
