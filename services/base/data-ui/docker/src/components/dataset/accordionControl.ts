import type { InjectionKey } from 'vue'

/**
 * Broadcast channel for "expand all / collapse all" across the recursive
 * dataset member accordions. EntitiesPage `provide`s a reactive instance and
 * bumps `token` whenever `command` changes so every accordion level (including
 * ones mounted later) can react.
 */
export interface AccordionControl {
  command: 'expand' | 'collapse' | 'idle'
  token: number
}

export const ACCORDION_CONTROL: InjectionKey<AccordionControl> = Symbol('accordion-control')
