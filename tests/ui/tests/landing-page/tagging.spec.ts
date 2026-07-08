import { test, expect } from '@playwright/test';
import { LandingPage } from '../helpers/LandingPage';

test('tag a series in the phantom dataset, filter/search by it, then with multiple tags at once, ending tagless', { tag: '@functional' }, async ({ page }) => {
  test.setTimeout(60_000);
  const portal = new LandingPage(page);
  await portal.goto();
  await portal.waitForLoad();

  await page.goto('/datasets');
  await portal.selectDataset('phantom');
  const firstCard = portal.seriesCards.first();
  await expect(firstCard).toBeVisible({ timeout: 20_000 });

  // Pin to this specific card by ID — filtering/searching later reorders the
  // gallery, so re-querying "first()" after that could resolve to a different card.
  const cardId = await firstCard.getAttribute('id');
  const card = portal.seriesCard(cardId!);

  const tag1 = `e2e-tag-a-${Date.now()}`;
  const tag2 = `e2e-tag-b-${Date.now()}`;

  try {
    // ── Single tag: apply, then remove by clicking the card again ───────────
    await portal.createTag(tag1);
    await expect(portal.tagBarChip(tag1)).toBeVisible({ timeout: 5_000 });

    await portal.tagBarChip(tag1).click();
    await card.click();
    await expect(portal.cardTagChips(card).filter({ hasText: tag1 })).toBeVisible({ timeout: 10_000 });

    // ── Filter and search the gallery by the tag we just applied ────────────
    // "Tags" only appears as a filterable field once at least one document
    // has it set, and OpenSearch's near-real-time refresh means it can lag
    // slightly behind the tag update — retry until the filtered card shows up.
    await expect(async () => {
      await portal.searchAddFilterButton.click();
      await portal.pickFromAutocomplete(portal.searchFilterKeySelect, 'Tags');
      await portal.pickFromAutocomplete(portal.searchFilterValueSelect, tag1);
      await portal.searchButton.click();
      await expect(card).toBeVisible({ timeout: 5_000 });
    }).toPass({ timeout: 20_000, intervals: [3_000] });
    await expect(portal.seriesCards).toHaveCount(1);

    await portal.searchFilterRow.locator('.mdi-delete').click();
    await portal.searchButton.click();
    await expect(card).toBeVisible({ timeout: 15_000 });

    await portal.searchInput.fill(tag1);
    await portal.searchButton.click();
    await expect(card).toBeVisible({ timeout: 15_000 });
    await portal.searchInput.fill('');
    await portal.searchButton.click();
    await expect(card).toBeVisible({ timeout: 15_000 });

    // tag1 is still active in the bar, so clicking the card again toggles it
    // off (removing via the chip's close icon instead races with the card's
    // own click handler, since the click can bubble up and re-trigger the
    // active-tag toggle, undoing the removal).
    await card.click();
    await expect(portal.cardTagChips(card).filter({ hasText: tag1 })).not.toBeVisible({ timeout: 10_000 });

    // ── Multiple tags: toggling "Multiple Tags" lets several chips stay
    // active at once, so a single click on the card applies (or removes)
    // all of them together instead of one at a time. ────────────────────────
    await portal.createTag(tag2);
    await expect(portal.tagBarChip(tag2)).toBeVisible({ timeout: 5_000 });

    await portal.tagBarMultipleTagsSwitch.click();
    await portal.tagBarChip(tag1).click();
    await portal.tagBarChip(tag2).click();

    await card.click();
    await expect(portal.cardTagChips(card).filter({ hasText: tag1 })).toBeVisible({ timeout: 10_000 });
    await expect(portal.cardTagChips(card).filter({ hasText: tag2 })).toBeVisible({ timeout: 10_000 });

    // Both tags are still active in the bar, so this click toggles both off
    // simultaneously, leaving the series tagless again.
    await card.click();
    await expect(portal.cardTagChips(card).filter({ hasText: tag1 })).not.toBeVisible({ timeout: 10_000 });
    await expect(portal.cardTagChips(card).filter({ hasText: tag2 })).not.toBeVisible({ timeout: 10_000 });
  } finally {
    // Best-effort: the "phantom" dataset is shared across test runs, so make
    // sure it never ends up stuck tagged if an assertion above failed partway
    // through.
    await page.goto('/datasets').catch(() => {});
    await portal.selectDataset('phantom').catch(() => {});
    for (const tag of [tag1, tag2]) {
      await portal.removeCardTag(card, tag).catch(() => {});
    }
  }
});
