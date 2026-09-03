// Tag chips are coloured by name so the same tag looks the same everywhere.
// That is identity, not meaning — the chip always carries its label too, so no
// information depends on colour perception (design guidelines, "Color").
//
// The previous hash folded straight into RGB, which produced anything from
// near-black to near-white behind text that kept the surrounding foreground
// colour: unreadable on a fair share of tags, in both themes. Hashing into a
// hue at a fixed saturation and lightness keeps every chip inside one readable
// band, and the foreground is then chosen by luminance the same way the shared
// theme picks its `on-*` colours.

const CHIP_SATURATION = 0.55
const CHIP_LIGHTNESS = 0.45

function hashString(str: string): number {
  let hash = 0
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash)
    hash |= 0
  }
  return Math.abs(hash)
}

function toHex(value: number): string {
  return Math.round(value * 255)
    .toString(16)
    .padStart(2, '0')
}

function hslToHex(h: number, s: number, l: number): string {
  const chroma = (1 - Math.abs(2 * l - 1)) * s
  const secondary = chroma * (1 - Math.abs(((h / 60) % 2) - 1))
  const match = l - chroma / 2
  const [r, g, b] = (
    h < 60
      ? [chroma, secondary, 0]
      : h < 120
        ? [secondary, chroma, 0]
        : h < 180
          ? [0, chroma, secondary]
          : h < 240
            ? [0, secondary, chroma]
            : h < 300
              ? [secondary, 0, chroma]
              : [chroma, 0, secondary]
  ).map((channel) => channel + match)
  return `#${toHex(r)}${toHex(g)}${toHex(b)}`
}

/** WCAG relative luminance of an `#rrggbb` colour. */
function relativeLuminance(hex: string): number {
  const channels = [1, 3, 5].map((offset) => {
    const value = parseInt(hex.slice(offset, offset + 2), 16) / 255
    return value <= 0.03928 ? value / 12.92 : Math.pow((value + 0.055) / 1.055, 2.4)
  })
  return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]
}

export interface TagColor {
  background: string
  text: string
}

/** Deterministic chip colours for a tag, with a foreground picked for contrast. */
export function tagColor(tag: string): TagColor {
  if (!tag) return { background: 'transparent', text: 'inherit' }
  const background = hslToHex(hashString(tag) % 360, CHIP_SATURATION, CHIP_LIGHTNESS)
  // Same rule as the shared theme's `on-*` colours: whichever of black or white
  // contrasts more with the background.
  const text = relativeLuminance(background) > 0.179 ? '#000000' : '#FFFFFF'
  return { background, text }
}
