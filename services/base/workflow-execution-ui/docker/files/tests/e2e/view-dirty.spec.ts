import { test, expect, type Page } from '@playwright/test'
import { bootView, selectDag, singleDagData } from './fixtures/mock-backend'

// The view posts kaapana:view-dirty to its parent so the shell can warn before a
// project switch reloads the iframe. Standalone (parent === window), so the
// messages land on this window — capture them via an injected listener.
async function trackDirty(page: Page) {
  await page.addInitScript(() => {
    ;(window as unknown as { __dirty: boolean[] }).__dirty = []
    window.addEventListener('message', (e: MessageEvent) => {
      if (e.data?.type === 'kaapana:view-dirty') {
        ;(window as unknown as { __dirty: boolean[] }).__dirty.push(e.data.dirty)
      }
    })
  })
}

function lastDirty(page: Page) {
  return page.evaluate(() => {
    const d = (window as unknown as { __dirty: boolean[] }).__dirty
    return d.length ? d[d.length - 1] : null
  })
}

test('selecting a dag leaves the view clean; editing a field reports dirty; Clear reports clean', async ({
  page,
}) => {
  await trackDirty(page)
  await bootView(page) // default: multiple dags -> nothing auto-selected on boot
  expect(await lastDirty(page)).toBeNull()

  // The workflow choice is not unsaved input: a reload offers it again.
  await selectDag(page, 'mock-all-fields')
  await expect(page.getByLabel('Text Field')).toHaveValue('hello')
  expect(await lastDirty(page)).toBeNull()

  await page.getByLabel('Text Field').fill('edited')
  await expect.poll(() => lastDirty(page)).toBe(true)

  await page.getByRole('button', { name: 'Clear', exact: true }).click()
  await expect.poll(() => lastDirty(page)).toBe(false)
})

test('typing a workflow name reports the view dirty', async ({ page }) => {
  await trackDirty(page)
  await bootView(page)
  await selectDag(page, 'mock-all-fields')
  await expect(page.getByLabel('Workflow name')).toHaveValue('mock-all-fields')
  expect(await lastDirty(page)).toBeNull()

  // The run name is a native field outside vjsf's formData, so it needs its
  // own place in the dirty baseline.
  await page.getByLabel('Workflow name').fill('custom-run')
  await expect.poll(() => lastDirty(page)).toBe(true)
})

// A single-dag project auto-selects its only dag on boot, so the dag choice is
// reload-idempotent and does NOT signal dirty on its own — but the user can
// still fill the form, which IS lost on reload and MUST warn.
const soloDag = () =>
  singleDagData('solo-dag', {
    workflow_form: {
      type: 'object',
      properties: {
        flag: { type: 'boolean', title: 'Solo Flag', default: false },
        note: { type: 'string', title: 'Note Field', default: 'hello' },
      },
    },
  })

test('a single-dag project auto-selecting its only dag on boot does NOT report dirty', async ({
  page,
}) => {
  await trackDirty(page)
  await bootView(page, soloDag())
  // auto-select + defaults render: all non-user transitions
  await expect(page.getByText('Solo Flag')).toBeVisible()
  await expect(page.getByLabel('Note Field')).toHaveValue('hello')
  expect(await lastDirty(page)).toBeNull()
})

test('editing a field in a single-dag project reports the view dirty', async ({ page }) => {
  await trackDirty(page)
  await bootView(page, soloDag())
  await expect(page.getByLabel('Note Field')).toHaveValue('hello')
  expect(await lastDirty(page)).toBeNull()

  // A real user edit (typing) — the dag choice never transitions here.
  await page.getByLabel('Note Field').fill('edited')
  await expect.poll(() => lastDirty(page)).toBe(true)
})
