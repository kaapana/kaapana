import { defineComponent, h } from 'vue'
import { VBtn, VTooltip } from 'vuetify/components'

// A keyboard-focusable (i) button that reveals a field's help in a tooltip on
// hover and focus. type="button" keeps it from submitting a surrounding v-form.
export const HelpIcon = defineComponent({
  name: 'HelpIcon',
  props: { text: { type: String, required: true } },
  setup(props) {
    return () =>
      h(VTooltip, { location: 'top', text: props.text }, {
        activator: ({ props: activator }: any) =>
          h(VBtn, {
            ...activator,
            icon: 'mdi-information-outline',
            type: 'button',
            variant: 'text',
            density: 'compact',
            size: 'small',
            class: 'wfe-help-icon',
            'aria-label': 'Field help',
          }),
      })
  },
})
