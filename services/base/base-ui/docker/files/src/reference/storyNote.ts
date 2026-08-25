import { h, type VNode } from 'vue'

// One-line framing above a reference example: what rule it shows and what to
// notice. The long-form rule stays in the design guidelines, not here.
export function note(text: string): VNode {
  return h('p', { class: 'text-body-2 text-medium-emphasis mb-4' }, text)
}
