import type { Meta, StoryObj } from '@storybook/vue3-vite'
import { defineComponent, h } from 'vue'
import { useProjectStore } from './project'

// Initial state only — getSelectedProject() would hit the backend and redirect.
const ProjectStoreDemo = defineComponent({
  name: 'ProjectStoreDemo',
  setup() {
    const project = useProjectStore()
    return () =>
      h('dl', [
        h('dt', 'selectedProject'),
        h('dd', h('code', JSON.stringify(project.selectedProject))),
        h('dt', 'availableProjects'),
        h('dd', h('code', JSON.stringify(project.availableProjects))),
      ])
  },
})

const meta: Meta<typeof ProjectStoreDemo> = {
  title: 'stores/project',
  component: ProjectStoreDemo,
}

export default meta
type Story = StoryObj<typeof ProjectStoreDemo>

export const Default: Story = {}
