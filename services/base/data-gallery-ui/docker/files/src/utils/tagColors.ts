import { contrastingColor } from '@kaapana/base-ui'

// Hues every 15° at one saturation and lightness (55 %, 45 %): no tag is
// near-white or near-black, so each stands apart from both themes' backgrounds.
const TAG_BACKGROUNDS = [
  '#B23434', '#B25334', '#B27334', '#B29234', '#B2B234', '#92B234',
  '#73B234', '#53B234', '#34B234', '#34B253', '#34B273', '#34B292',
  '#34B2B2', '#3492B2', '#3473B2', '#3453B2', '#3434B2', '#5334B2',
  '#7334B2', '#9234B2', '#B234B2', '#B23492', '#B23473', '#B23453',
]

function hashString(str: string): number {
  let hash = 0
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash)
    hash |= 0
  }
  return Math.abs(hash)
}

export interface TagColor {
  background: string
  text: string
}

export function tagColor(tag: string): TagColor {
  if (!tag) return { background: 'transparent', text: 'inherit' }
  const background = TAG_BACKGROUNDS[hashString(tag) % TAG_BACKGROUNDS.length]
  const text = contrastingColor(background)
  return { background, text }
}
