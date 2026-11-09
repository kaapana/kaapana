export interface StoryLink {
  id: string
  title: string
  epic: string
  priority: 'MVP' | 'Release 2'
  statement: string
  where: string
  persona: 'anna' | 'paul' | 'kim'
  project?: string
  route: string
}

export const coveredStories: StoryLink[] = [
  {
    id: '1.2',
    epic: 'Registering helm-chart contents through the Extension Manager',
    title: 'Deregistering a helm-chart content when its extension is uninstalled',
    priority: 'MVP',
    statement:
      'As a kaapana-system-admin I want that the helm-chart content of an uninstalled extension can no longer be deployed.',
    where:
      'Only the marker: segmentation-review runs MITK Workbench 2024.06.1, which is no longer registered. It keeps running and can still be opened and undeployed. Uninstalling happens in the Extension Manager.',
    persona: 'paul',
    route: '/applications/segmentation-review',
  },
  {
    id: '2.1',
    epic: 'Applications with a web interface in a project',
    title: 'Deploying an application',
    priority: 'MVP',
    statement:
      'As a principal-investigator I want to deploy an application for my whole project or for one of its scientists.',
    where:
      'Application Catalog lists the applications enabled for the project with their registered versions. The deploy form preselects the newest version. Deploy runs a dry-run first; "Check configuration" runs it on its own.',
    persona: 'paul',
    route: '/catalog',
  },
  {
    id: '2.2',
    epic: 'Applications with a web interface in a project',
    title: 'Configuring an application at deploy',
    priority: 'MVP',
    statement: 'As a principal-investigator I want to set parameters when I deploy an application.',
    where:
      'The deploy form is rendered from the parameters of the chosen version; JupyterLab 4.3.0 adds one to 4.2.5. Try 40 GiB memory with a GPU to see a dry-run error, or an invalid value to see validation.',
    persona: 'paul',
    route: '/catalog/jupyterlab/deploy',
  },
  {
    id: '2.3',
    epic: 'Applications with a web interface in a project',
    title: 'Undeploying an application',
    priority: 'MVP',
    statement:
      'As a principal-investigator I want to undeploy an application that is no longer needed.',
    where:
      'Undeploy on the details page or in the row menu. The dialog warns that the workspace volume is deleted with all data on it (Q5).',
    persona: 'paul',
    route: '/applications/segmentation-review',
  },
  {
    id: '2.4',
    epic: 'Applications with a web interface in a project',
    title: 'Opening an application',
    priority: 'MVP',
    statement: 'As a scientist I want to open the web interface of a deployed application.',
    where:
      'Open is offered once the state is READY. It opens the application in a new tab, simulated here in a window.',
    persona: 'anna',
    route: '/applications',
  },
  {
    id: '2.5',
    epic: 'Applications with a web interface in a project',
    title: 'Working on existing data',
    priority: 'MVP',
    statement:
      'As a scientist I want to access and work on the data of my project from within an application.',
    where: 'Details › Data and storage shows what the application reads from the project.',
    persona: 'anna',
    route: '/applications/anna-notebook',
  },
  {
    id: '2.6',
    epic: 'Applications with a web interface in a project',
    title: 'Saving results',
    priority: 'MVP',
    statement:
      'As a scientist I want to use the results I generated in an application in a workflow of my project.',
    where: 'Details › Data and storage names the results folder and offers it as workflow input.',
    persona: 'anna',
    route: '/applications/anna-notebook',
  },
  {
    id: '2.7',
    epic: 'Applications with a web interface in a project',
    title: 'Continuing previous work',
    priority: 'MVP',
    statement:
      'As a scientist I want to continue working in my application where I left off last time.',
    where:
      'Details › Data and storage shows the persistent workspace. "For me" in the list finds your instances.',
    persona: 'anna',
    route: '/applications/anna-notebook',
  },
  {
    id: '3.1',
    epic: 'Monitoring deployed applications',
    title: 'Seeing the status of a deployed application',
    priority: 'MVP',
    statement:
      'As a scientist I want to see whether my deployed application is starting, ready or broken.',
    where: 'State column in the list; details show pods, events and the reason of a failure.',
    persona: 'anna',
    route: '/applications/nodule-labelling',
  },
  {
    id: '3.2',
    epic: 'Monitoring deployed applications',
    title: 'Seeing the configuration of a deployed application',
    priority: 'MVP',
    statement: 'As a scientist I want to see the configuration a deployed application runs with.',
    where: 'Details › Configuration lists version and parameter values; secrets are masked.',
    persona: 'anna',
    route: '/applications/anna-notebook',
  },
  {
    id: '5.1',
    epic: 'Permission and access control',
    title: 'Default permissions',
    priority: 'MVP',
    statement:
      'As a kaapana-system-admin I want a default mapping of the user groups to the actions of the Helm Chart Consumer.',
    where:
      'Switch "Viewing as" in the top bar: menu entries and actions follow the role in the selected project. Only principal investigators and admins deploy (Q2); only admins deploy platform-wide (Q11).',
    persona: 'anna',
    route: '/applications',
  },
  {
    id: '5.2',
    epic: 'Permission and access control',
    title: 'Enabling applications for a project',
    priority: 'MVP',
    statement: 'As a kaapana-system-admin I want to enable and disable applications for projects.',
    where:
      'System › Application Availability. Disabled applications disappear from the catalog of that project. New applications start disabled (Q8), and enabling covers all registered versions.',
    persona: 'kim',
    route: '/availability',
  },
  {
    id: '5.3',
    epic: 'Permission and access control',
    title: 'Restricting who can open an application',
    priority: 'MVP',
    statement:
      'As a principal-investigator I want only members of my project to open the applications deployed in it.',
    where:
      'The list only shows the current project and the platform-wide applications. Details › Access lets you try a link of another project.',
    persona: 'anna',
    route: '/applications/anna-notebook',
  },
  {
    id: '8.1',
    epic: 'Multi-deployable applications in projects',
    title: 'Deploying an application multiple times',
    priority: 'MVP',
    statement:
      'As a principal-investigator I want to deploy the same multi-deployable application several times in my project.',
    where:
      'JupyterLab can be deployed again; CVAT is already deployed and explains why it cannot be deployed twice. The limit counts all versions.',
    persona: 'paul',
    route: '/catalog',
  },
  {
    id: '8.2',
    epic: 'Multi-deployable applications in projects',
    title: 'Use case description for deployed applications',
    priority: 'MVP',
    statement:
      'As a principal-investigator I want to write a use case description when I deploy an application.',
    where: 'Description field in the deploy form; shown in the list and on the details page.',
    persona: 'paul',
    route: '/catalog/jupyterlab/deploy',
  },
  {
    id: '8.3',
    epic: 'Multi-deployable applications in projects',
    title: 'Identifying deployed applications',
    priority: 'MVP',
    statement: 'As a scientist I want to know which applications I worked with in my last session.',
    where: 'Unique names, the "For" column and the "For me" filter in the list.',
    persona: 'anna',
    route: '/applications',
  },
  {
    id: '9.1',
    epic: 'Platform-wide applications',
    title: 'Deploying an application platform-wide',
    priority: 'Release 2',
    statement: 'As a kaapana-system-admin I want to deploy an application for the whole platform.',
    where:
      'Collabora Online supports both scopes, so Kim chooses the scope in the deploy form. Paul deploys it in his project only (Q11). OHIF is already deployed platform-wide, once.',
    persona: 'kim',
    route: '/catalog/collabora/deploy',
  },
  {
    id: '9.2',
    epic: 'Platform-wide applications',
    title: 'Using a platform-wide application',
    priority: 'Release 2',
    statement: 'As a scientist I want to see and open the platform-wide applications.',
    where:
      'ohif is listed in every project, marked Platform-wide. Every user can open it; only a Kaapana system admin can undeploy it.',
    persona: 'anna',
    route: '/applications',
  },
  {
    id: '11.1',
    epic: 'Updating deployed applications',
    title: 'Browsing available versions',
    priority: 'Release 2',
    statement: 'As a user I want to see which versions of an application are available.',
    where:
      'The catalog shows the registered versions. In the list, anna-notebook is marked because a newer JupyterLab version is registered. Updating is not part of this mock.',
    persona: 'paul',
    route: '/applications',
  },
  {
    id: '12.1',
    epic: 'Operating the Helm Chart Consumer',
    title: 'Surviving restarts and platform upgrades',
    priority: 'MVP',
    statement:
      'As a platform-operator I want registered contents and deployed applications to survive a restart or an upgrade.',
    where:
      'Releases changed or removed outside Kaapana are flagged. Mock menu › Simulate platform restart reloads the list.',
    persona: 'paul',
    route: '/applications',
  },
  {
    id: '12.2',
    epic: 'Operating the Helm Chart Consumer',
    title: 'Deleting a project with deployed applications',
    priority: 'MVP',
    statement:
      'As a kaapana-system-admin I want that a project with deployed applications cannot be deleted.',
    where:
      'System › Projects › Delete. Deleting a project with deployed applications is refused, and the refusal names them (Q9). Platform-wide applications do not count.',
    persona: 'kim',
    route: '/projects',
  },
]

/** MVP stories the request left out of the mock, with the reason. */
export const excludedStories = [
  {
    id: '1.1',
    title: 'Registering a helm-chart content when its extension is installed',
    reason: 'Extension Manager',
  },
  { id: '4.1', title: 'Packaging a helm chart as an extension', reason: 'Extension development' },
  {
    id: '4.2',
    title: 'Declaring how Kaapana presents and deploys an application',
    reason: 'Extension development',
  },
  {
    id: '4.3',
    title: 'Avoiding conflicts with existing Kubernetes resources',
    reason: 'Extension development',
  },
  {
    id: '4.4',
    title: 'Exposing the web interface of an application',
    reason: 'Extension development',
  },
  { id: '4.5', title: 'Authenticated access to Kaapana APIs', reason: 'Extension development' },
]

const questionTitles: Record<string, string> = {
  Q1: 'Answered: every member can open every application of the project; "For" does not restrict access',
  Q3: 'Answered: several versions of an application can be registered at the same time',
  Q5: 'Answered: undeploying deletes the persistent volumes and their data',
  Q7: 'Answered: an application acts on behalf of its project, with the permissions of a scientist',
  Q8: 'Answered: new applications start disabled in all projects',
  Q9: 'Answered: deleting a project with deployed applications is refused',
  Q11: 'Answered: only a kaapana-system-admin chooses the scope; a PI cannot deploy platform-wide',
  Q12: 'Not decided yet: whether a newly registered version starts disabled',
  Q13: 'Not decided yet: on whose behalf a platform-wide application acts',
}

export const storyTitles: Record<string, string> = {
  ...Object.fromEntries([...coveredStories, ...excludedStories].map((s) => [s.id, s.title])),
  ...questionTitles,
}
