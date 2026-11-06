// The MVP user stories of concept.md and where the mock shows them. "Show me"
// in the story panel switches to the persona, opens the route and highlights the
// elements tagged with <StoryRef> for the story.

export interface StoryLink {
  id: string
  title: string
  epic: string
  statement: string
  where: string
  persona: 'anna' | 'paul' | 'kim'
  project?: string
  route: string
}

export const coveredStories: StoryLink[] = [
  {
    id: '2.1',
    epic: 'Applications with a web interface in a project',
    title: 'Deploying an application',
    statement: 'As a principal-investigator I want to deploy an application for one of the scientists in my project.',
    where: 'Application Catalog lists the applications enabled for the project. Deploy runs a dry-run first; "Check configuration" runs it on its own.',
    persona: 'paul',
    route: '/catalog',
  },
  {
    id: '2.2',
    epic: 'Applications with a web interface in a project',
    title: 'Configuring an application at deploy',
    statement: 'As a principal-investigator I want to set parameters when I deploy an application.',
    where: 'The deploy form is rendered from the declared parameters. Try 40 GiB memory with a GPU to see a dry-run error, or an invalid value to see validation.',
    persona: 'paul',
    route: '/catalog/jupyterlab/deploy',
  },
  {
    id: '2.3',
    epic: 'Applications with a web interface in a project',
    title: 'Undeploying an application',
    statement: 'As a principal-investigator I want to undeploy an application that is no longer needed.',
    where: 'Undeploy on the details page or in the row menu. The dialog warns about unsaved data and the workspace volume (Q5).',
    persona: 'paul',
    route: '/applications/segmentation-review',
  },
  {
    id: '2.4',
    epic: 'Applications with a web interface in a project',
    title: 'Opening an application',
    statement: 'As a scientist I want to open the web interface of a deployed application.',
    where: 'Open is offered once the state is READY. It opens the application in a new tab, simulated here in a window.',
    persona: 'anna',
    route: '/applications',
  },
  {
    id: '2.5',
    epic: 'Applications with a web interface in a project',
    title: 'Working on existing data',
    statement: 'As a scientist I want to access and work on the data of my project from within an application.',
    where: 'Details › Data and storage shows what the application reads from the project.',
    persona: 'anna',
    route: '/applications/anna-notebook',
  },
  {
    id: '2.6',
    epic: 'Applications with a web interface in a project',
    title: 'Saving results',
    statement: 'As a scientist I want to use the results I generated in an application in a workflow of my project.',
    where: 'Details › Data and storage names the results folder and offers it as workflow input.',
    persona: 'anna',
    route: '/applications/anna-notebook',
  },
  {
    id: '2.7',
    epic: 'Applications with a web interface in a project',
    title: 'Continuing previous work',
    statement: 'As a scientist I want to continue working in my application where I left off last time.',
    where: 'Details › Data and storage shows the persistent workspace. "For me" in the list finds your instances.',
    persona: 'anna',
    route: '/applications/anna-notebook',
  },
  {
    id: '3.1',
    epic: 'Monitoring deployed applications',
    title: 'Seeing the status of a deployed application',
    statement: 'As a scientist I want to see whether my deployed application is starting, ready or broken.',
    where: 'State column in the list; details show pods, events and the reason of a failure.',
    persona: 'anna',
    route: '/applications/nodule-labelling',
  },
  {
    id: '3.2',
    epic: 'Monitoring deployed applications',
    title: 'Seeing the configuration of a deployed application',
    statement: 'As a scientist I want to see the configuration a deployed application runs with.',
    where: 'Details › Configuration lists version and parameter values; secrets are masked.',
    persona: 'anna',
    route: '/applications/anna-notebook',
  },
  {
    id: '5.1',
    epic: 'Permission and access control',
    title: 'Default permissions',
    statement: 'As a kaapana-system-admin I want a default mapping of the user groups to the actions of the Helm Chart Consumer.',
    where: 'Switch "Viewing as" in the top bar: menu entries and actions follow the role in the selected project.',
    persona: 'anna',
    route: '/applications',
  },
  {
    id: '5.2',
    epic: 'Permission and access control',
    title: 'Enabling applications for a project',
    statement: 'As a kaapana-system-admin I want to enable and disable applications for projects.',
    where: 'System › Application Availability. Disabled applications disappear from the catalog of that project.',
    persona: 'kim',
    route: '/availability',
  },
  {
    id: '5.3',
    epic: 'Permission and access control',
    title: 'Restricting who can open an application',
    statement: 'As a principal-investigator I want only members of my project to open the applications deployed in it.',
    where: 'The list only shows the current project. Details › Access lets you try a link of another project.',
    persona: 'anna',
    route: '/applications/anna-notebook',
  },
  {
    id: '8.1',
    epic: 'Multi-deployable applications in projects',
    title: 'Deploying an application multiple times',
    statement: 'As a principal-investigator I want to deploy the same multi-deployable application several times in my project.',
    where: 'JupyterLab can be deployed again; CVAT is already deployed and explains why it cannot be deployed twice.',
    persona: 'paul',
    route: '/catalog',
  },
  {
    id: '8.2',
    epic: 'Multi-deployable applications in projects',
    title: 'Use case description for deployed applications',
    statement: 'As a principal-investigator I want to write a use case description when I deploy an application.',
    where: 'Description field in the deploy form; shown in the list and on the details page.',
    persona: 'paul',
    route: '/catalog/jupyterlab/deploy',
  },
  {
    id: '8.3',
    epic: 'Multi-deployable applications in projects',
    title: 'Identifying deployed applications',
    statement: 'As a scientist I want to know which applications I worked with in my last session.',
    where: 'Unique names, the "For" column and the "For me" filter in the list.',
    persona: 'anna',
    route: '/applications',
  },
  {
    id: '12.1',
    epic: 'Operating the Helm Chart Consumer',
    title: 'Surviving restarts and platform upgrades',
    statement: 'As a platform-operator I want registered contents and deployed applications to survive a restart or an upgrade.',
    where: 'Releases changed or removed outside Kaapana are flagged. Mock menu › Simulate platform restart reloads the list.',
    persona: 'paul',
    route: '/applications',
  },
  {
    id: '12.2',
    epic: 'Operating the Helm Chart Consumer',
    title: 'Deleting a project with deployed applications',
    statement: 'As a kaapana-system-admin I want that deleting a project does not leave its deployed applications behind.',
    where: 'System › Projects › Delete. The behaviour follows Q9 in Mock menu › Concept options.',
    persona: 'kim',
    route: '/projects',
  },
]

/** MVP stories the request left out of the mock, with the reason. */
export const excludedStories = [
  { id: '1.1', title: 'Registering a helm-chart content when its extension is installed', reason: 'Extension Manager' },
  { id: '1.2', title: 'Deregistering a helm-chart content when its extension is uninstalled', reason: 'Extension Manager' },
  { id: '4.1', title: 'Packaging a helm chart as an extension', reason: 'Extension development' },
  { id: '4.2', title: 'Declaring how Kaapana presents and deploys an application', reason: 'Extension development' },
  { id: '4.3', title: 'Avoiding conflicts with existing Kubernetes resources', reason: 'Extension development' },
  { id: '4.4', title: 'Exposing the web interface of an application', reason: 'Extension development' },
  { id: '4.5', title: 'Authenticated access to Kaapana APIs', reason: 'Extension development' },
]

export const storyTitles: Record<string, string> = Object.fromEntries([
  ...coveredStories.map((s) => [s.id, s.title]),
  ['Q1', 'Open question: ownership of a deployed application'],
  ['Q5', 'Open question: persistent volumes on undeploy'],
  ['Q8', 'Open question: default enablement of new applications'],
  ['Q9', 'Open question: deleting a project with deployed applications'],
])
