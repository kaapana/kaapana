import { test, expect, type Page } from '@playwright/test'
import { defaultMockData, LAB_REPO, PUBLIC_REPO } from './fixtures/mock-backend'
import {
  API,
  card,
  cards,
  confirmAction,
  countRequests,
  dialog,
  failRoute,
  nextRequest,
  openFailureDetails,
  openView,
  pressEscapeUntil,
  recordShellMessages,
  toasts,
} from './fixtures/helpers'

function field(page: Page, label: string) {
  return dialog(page).getByRole('textbox', { name: label, exact: true })
}

async function fillNewRepository(page: Page) {
  await field(page, 'Name').fill('partner-registry')
  await field(page, 'Repository URL').fill('https://registry.partner.example.com/ai/extensions')
  await field(page, 'Description (optional)').fill('Shared with our partner site')
  await field(page, 'Username').fill('robot$reader')
  await field(page, 'Password or access token').fill('s3cret')
}

test('lists the registered repositories', async ({ page }) => {
  await openView(page, 'repositories')

  await expect(cards(page)).toHaveCount(2)
  await expect(card(page, 'kaapana-public')).toContainText(PUBLIC_REPO.repository_url)
  await expect(card(page, 'kaapana-public')).toContainText('Official Kaapana extensions')
  await expect(card(page, 'lab-internal')).toContainText('No description provided.')
})

test('adds a repository and reports it', async ({ page }) => {
  await openView(page, 'repositories')
  await page.getByTestId('new-repository').click()
  await fillNewRepository(page)

  const request = nextRequest(page, API.repositories, 'POST')
  await dialog(page).getByRole('button', { name: 'Add repository' }).click()

  expect((await request).postDataJSON()).toEqual({
    name: 'partner-registry',
    description: 'Shared with our partner site',
    repository_url: 'https://registry.partner.example.com/ai/extensions',
    username: 'robot$reader',
    password: 's3cret',
  })
  await expect(toasts(page).filter({ hasText: 'Repository added' })).toBeVisible()
  await expect(card(page, 'partner-registry')).toBeVisible()
  await expect(page.getByRole('dialog')).toHaveCount(0)
})

test('submitting an empty form explains each required field', async ({ page }) => {
  await openView(page, 'repositories')
  const creates = countRequests(page, API.repositories, 'POST')
  await page.getByTestId('new-repository').click()
  await dialog(page).getByRole('button', { name: 'Add repository' }).click()

  const form = dialog(page)
  await expect(form).toContainText('Enter a name. It identifies the repository in the catalog.')
  await expect(form).toContainText('Enter the repository URL.')
  await expect(form).not.toContainText('Use a full URL')
  await expect(form).toContainText('Enter the username or token name for the registry.')
  await expect(form).toContainText('Enter the password or access token for the registry.')
  expect(creates()).toBe(0)
})

test('a malformed URL says what a valid one looks like', async ({ page }) => {
  await openView(page, 'repositories')
  await page.getByTestId('new-repository').click()
  await field(page, 'Repository URL').fill('registry.example.com')

  await expect(dialog(page)).toContainText('Use a full URL: http(s)://<registry>/<repository>')
})

test('a rejected create stays in the form with the reason and details', async ({ page }) => {
  await openView(page, 'repositories', defaultMockData(), {
    routes: (p) =>
      failRoute(
        p,
        API.repositories,
        'A repository with the name partner-registry already exists',
        409,
        'POST',
      ),
  })
  await page.getByTestId('new-repository').click()
  await fillNewRepository(page)
  await dialog(page).getByRole('button', { name: 'Add repository' }).click()

  const failure = page.getByTestId('form-failure')
  await expect(failure).toContainText('Could not add the repository.')
  await expect(failure).toContainText('already exists')
  await failure.getByRole('button', { name: 'Details' }).click()
  await expect(page.getByRole('dialog').filter({ hasText: 'Copy details' })).toContainText('409')
})

test('editing keeps stored credentials unless both are replaced, and can clear the description', async ({
  page,
}) => {
  await openView(page, 'repositories')
  await card(page, 'kaapana-public').getByRole('button', { name: 'Edit kaapana-public' }).click()

  await expect(field(page, 'Name')).toHaveValue('kaapana-public')
  await expect(field(page, 'Username')).toHaveValue('')
  await field(page, 'Description (optional)').fill('')
  await field(page, 'Username').fill('new-robot')
  await dialog(page).getByRole('button', { name: 'Save changes' }).click()
  await expect(dialog(page)).toContainText(
    'Enter the password too, or clear the username to keep the stored credentials.',
  )

  await field(page, 'Username').fill('')
  const request = nextRequest(page, `${API.repositories}/${PUBLIC_REPO.id}`, 'PUT')
  await dialog(page).getByRole('button', { name: 'Save changes' }).click()

  expect((await request).postDataJSON()).toEqual({
    name: 'kaapana-public',
    description: '',
    repository_url: PUBLIC_REPO.repository_url,
  })
  await expect(toasts(page).filter({ hasText: 'Repository saved' })).toBeVisible()
  await expect(card(page, 'kaapana-public')).toContainText('No description provided.')
})

test('replacing both credentials sends them', async ({ page }) => {
  await openView(page, 'repositories')
  await card(page, 'lab-internal').getByRole('button', { name: 'Edit lab-internal' }).click()
  await field(page, 'Username').fill('robot')
  await field(page, 'Password or access token').fill('rotated')

  const request = nextRequest(page, `${API.repositories}/${LAB_REPO.id}`, 'PUT')
  await dialog(page).getByRole('button', { name: 'Save changes' }).click()
  expect((await request).postDataJSON()).toMatchObject({ username: 'robot', password: 'rotated' })
})

test.describe('unsaved changes', () => {
  test('closing an untouched form needs no confirmation', async ({ page }) => {
    await openView(page, 'repositories')
    await page.getByTestId('new-repository').click()
    await pressEscapeUntil(page, async () => (await page.getByRole('dialog').count()) === 0)
  })

  for (const how of ['Cancel', 'Escape', 'Close'] as const) {
    test(`${how} on an edited form asks before discarding`, async ({ page }) => {
      await openView(page, 'repositories')
      await page.getByTestId('new-repository').click()
      await field(page, 'Name').fill('half-typed')

      if (how === 'Escape') {
        await pressEscapeUntil(page, () =>
          page.getByText('Discard the new repository?').isVisible(),
        )
      } else {
        await dialog(page).getByRole('button', { name: how, exact: true }).click()
      }

      const confirm = dialog(page)
      await expect(confirm).toContainText('Discard the new repository?')
      await expect(confirm.getByRole('button', { name: 'Keep editing' })).toBeFocused()
      await confirm.getByRole('button', { name: 'Keep editing' }).click()
      await expect(field(page, 'Name')).toHaveValue('half-typed')

      await dialog(page).getByRole('button', { name: 'Cancel', exact: true }).click()
      await confirmAction(page, 'Discard changes')
      await expect(page.getByRole('dialog')).toHaveCount(0)
    })
  }

  test('an edited form reports the view as dirty to the shell, and clean once closed', async ({
    page,
  }) => {
    const messages = await recordShellMessages(page)
    await openView(page, 'repositories')
    await card(page, 'kaapana-public').getByRole('button', { name: 'Edit kaapana-public' }).click()
    await field(page, 'Name').fill('renamed')

    await expect
      .poll(
        async () => (await messages()).filter((m) => m.type === 'kaapana:view-dirty').at(-1)?.dirty,
      )
      .toBe(true)

    await field(page, 'Name').fill('kaapana-public')
    await expect
      .poll(
        async () => (await messages()).filter((m) => m.type === 'kaapana:view-dirty').at(-1)?.dirty,
      )
      .toBe(false)
  })
})

test.describe('removal', () => {
  test('states that installed extensions stop being tracked, then removes', async ({ page }) => {
    await openView(page, 'repositories')
    await card(page, 'kaapana-public')
      .getByRole('button', { name: 'Remove kaapana-public' })
      .click()

    const confirm = dialog(page)
    await expect(confirm).toContainText('Remove repository "kaapana-public"?')
    await expect(confirm).toContainText('no longer appear in the catalog')
    await expect(confirm).toContainText('stops tracking the 1 extension installed from it')

    const request = nextRequest(page, `${API.repositories}/${PUBLIC_REPO.id}`, 'DELETE')
    await confirmAction(page, 'Remove repository')
    await request
    await expect(toasts(page).filter({ hasText: 'Repository removed' })).toBeVisible()
    await expect(cards(page)).toHaveCount(1)
  })

  test('a repository without installations does not mention tracking', async ({ page }) => {
    await openView(page, 'repositories', { ...defaultMockData(), extensions: [] })
    await card(page, 'lab-internal').getByRole('button', { name: 'Remove lab-internal' }).click()

    await expect(dialog(page)).not.toContainText('stops tracking')
  })

  test('a failed removal keeps the repository and is reported', async ({ page }) => {
    await openView(page, 'repositories', defaultMockData(), {
      routes: (p) =>
        failRoute(p, `${API.repositories}/${LAB_REPO.id}`, 'database locked', 500, 'DELETE'),
    })
    await card(page, 'lab-internal').getByRole('button', { name: 'Remove lab-internal' }).click()
    await confirmAction(page, 'Remove repository')

    const details = await openFailureDetails(page, 'Removing the repository failed')
    await expect(details).toContainText('database locked')
    await expect(cards(page)).toHaveCount(2)
  })
})

test('no repositories yet offers to add one', async ({ page }) => {
  await openView(
    page,
    'repositories',
    { repositories: [], manifests: {}, extensions: [] },
    { waitFor: 'empty' },
  )

  const empty = page.getByTestId('empty-state')
  await expect(empty).toContainText('No repositories registered yet')
  await empty.getByRole('button', { name: 'New repository' }).click()
  await expect(dialog(page)).toContainText('Register an OCI repository')
})
