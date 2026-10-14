import { test, expect, type Page } from '@playwright/test'
import { installMockBackend } from './fixtures/mock-backend'

// A walkthrough reported no selection highlight after a theme switch; it was
// not reproduced. This test switches the theme in a view that follows the
// shell's theme and checks that text stays selectable. The highlight itself is
// checked by eye: a --headed run saves a screenshot of each selection.

const VIEW = `<!doctype html><html><head><style>
  html { color-scheme: dark; background: #121212; color: #fff; font-family: sans-serif }
  pre { background: #1e1e1e; padding: 12px }
</style></head><body style="padding:40px">
<p id="para">Selectable text inside the view</p>
<pre id="code">dcmsend -v host 11112 --scan-directories</pre>
<script>
  addEventListener('storage', (e) => {
    if (e.key !== 'settings') return
    const dark = JSON.parse(e.newValue || '{}').darkMode
    document.documentElement.style.colorScheme = dark ? 'dark' : 'light'
    document.documentElement.style.background = dark ? '#121212' : '#eeeeee'
    document.documentElement.style.color = dark ? '#fff' : '#000'
  })
</script></body></html>`

async function dragSelectInView(page: Page, id: string): Promise<string> {
  const frame = page.frameLocator('iframe.kaapana-iframe')
  const box = (await frame.locator('#' + id).boundingBox())!
  await page.mouse.move(box.x + 2, box.y + box.height / 2)
  await page.mouse.down()
  await page.mouse.move(box.x + box.width - 4, box.y + box.height / 2, { steps: 6 })
  await page.mouse.up()
  return frame.locator('body').evaluate(() => window.getSelection()?.toString() ?? '')
}

async function chooseTheme(page: Page, theme: 'System' | 'Light' | 'Dark') {
  await page.getByRole('button', { name: 'Settings' }).click()
  await page.locator('.theme-select .v-field__input').click()
  await page.getByRole('option', { name: theme }).click()
  await page.keyboard.press('Escape')
  await expect(page.getByRole('button', { name: 'Save', exact: true })).toBeHidden()
}

test('text in the view stays selectable across theme switches', async ({
  page,
  headless,
}, testInfo) => {
  const screenshot = async (name: string) => {
    if (!headless) await page.screenshot({ path: testInfo.outputPath(name) })
  }
  await page.emulateMedia({ colorScheme: 'dark' })
  await installMockBackend(page)
  await page.route('**/data-gallery-ui**', (r) =>
    r.fulfill({ status: 200, contentType: 'text/html', body: VIEW }),
  )
  await page.goto('/')
  await page.frameLocator('iframe.kaapana-iframe').locator('#para').waitFor()

  expect(await dragSelectInView(page, 'code')).toBe('dcmsend -v host 11112 --scan-directories')
  await screenshot('1-before.png')

  await chooseTheme(page, 'Light')
  await expect(page.locator('.v-application')).toHaveClass(/v-theme--kaapanaThemeLight/)
  expect(await dragSelectInView(page, 'code')).toBe('dcmsend -v host 11112 --scan-directories')
  await screenshot('2-after-light.png')

  await chooseTheme(page, 'Dark')
  await expect(page.locator('.v-application')).toHaveClass(/v-theme--kaapanaThemeDark/)
  expect(await dragSelectInView(page, 'para')).toBe('Selectable text inside the view')
  await screenshot('3-after-dark.png')
})
