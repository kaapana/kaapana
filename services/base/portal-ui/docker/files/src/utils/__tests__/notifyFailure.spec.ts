import { describe, it, expect, vi } from 'vitest'

vi.mock('@kyvg/vue3-notification', () => ({ notify: vi.fn() }))

import { notify } from '@kyvg/vue3-notification'
import { notifyFailure } from '@/utils/notifyFailure'

describe('notifyFailure', () => {
  it('toasts the sentence and carries the request detail for the details dialog', () => {
    const err = {
      message: 'Request failed with status code 500',
      config: { method: 'put', url: '/kaapana-backend/settings' },
      response: {
        status: 500,
        statusText: 'Internal Server Error',
        data: { detail: 'no write access' },
        headers: {},
      },
    }
    notifyFailure('Could not save settings', 'Your changes were not stored.', err)
    expect(notify).toHaveBeenCalledWith(
      expect.objectContaining({
        type: 'error',
        title: 'Could not save settings',
        text: 'Your changes were not stored. Select this message for details.',
        data: {
          failure: expect.objectContaining({
            error: expect.objectContaining({
              status: 500,
              method: 'PUT',
              url: '/kaapana-backend/settings',
              detail: 'no write access',
            }),
          }),
        },
      }),
    )
  })
})
