import type { Application, DeployedApp, ParamDecl, Person, Persona, Project } from './types'

// Seed data of the mock. Everything is invented; the names only have to make the
// stories believable.

export const MOCK_HOST = 'https://kaapana.example.org'

export const personas: Persona[] = [
  {
    id: 'anna',
    name: 'Anna Schmidt',
    admin: false,
    roles: { 'lung-ct': 'scientist', 'brain-mri': 'scientist' },
    summary: 'Scientist in Lung CT Study and Brain MRI Cohort',
  },
  {
    id: 'paul',
    name: 'Paul Weber',
    admin: false,
    roles: { 'lung-ct': 'principal-investigator', 'brain-mri': 'scientist' },
    summary: 'Principal investigator of Lung CT Study, scientist in Brain MRI Cohort',
  },
  {
    id: 'kim',
    name: 'Kim Novak',
    admin: true,
    roles: {},
    summary: 'Kaapana system admin',
  },
]

/** Further project members who appear in lists but cannot be impersonated. */
export const otherPeople: Person[] = [
  { id: 'jonas', name: 'Jonas Becker' },
  { id: 'lea', name: 'Lea Wagner' },
  { id: 'mehmet', name: 'Mehmet Yilmaz' },
  { id: 'sofia', name: 'Sofia Rossi' },
]

export const seedProjects: Project[] = [
  {
    id: 'lung-ct',
    name: 'Lung CT Study',
    bucket: 'project-lung-ct',
    folders: ['/', 'cohort-a', 'cohort-b', 'annotations', 'results'],
    members: {
      anna: 'scientist',
      paul: 'principal-investigator',
      jonas: 'scientist',
      sofia: 'scientist',
    },
  },
  {
    id: 'brain-mri',
    name: 'Brain MRI Cohort',
    bucket: 'project-brain-mri',
    folders: ['/', 't1', 'flair', 'results'],
    members: { anna: 'scientist', paul: 'scientist', lea: 'principal-investigator' },
  },
  {
    id: 'prostate-pet',
    name: 'Prostate PET Study',
    bucket: 'project-prostate-pet',
    folders: ['/', 'psma', 'results'],
    members: { lea: 'principal-investigator', mehmet: 'scientist' },
  },
]

const dataFolder = (description: string): ParamDecl => ({
  key: 'dataFolder',
  label: 'Project data folder',
  type: 'choice',
  choices: 'project-folders',
  default: '/',
  required: true,
  description,
  chartValue: 'data.projectFolder',
})

const workspace = (fallback: number): ParamDecl => ({
  key: 'workspace',
  label: 'Workspace size (GiB)',
  type: 'integer',
  default: fallback,
  min: 5,
  max: 200,
  required: true,
  description:
    'Persistent volume for your files in the application. It is kept when the application restarts or is updated.',
  chartValue: 'persistence.workspace.size',
  chartSuffix: 'Gi',
})

const gpu: ParamDecl = {
  key: 'gpu',
  label: 'Needs a GPU',
  type: 'boolean',
  default: false,
  description: 'Reserves one GPU while the application runs. GPUs are shared by all projects.',
  chartValue: 'resources.gpu.enabled',
}

const memory = (fallback: number, max: number): ParamDecl => ({
  key: 'memory',
  label: 'Memory (GiB)',
  type: 'integer',
  default: fallback,
  min: 2,
  max,
  required: true,
  description: 'Upper memory limit of the application.',
  chartValue: 'resources.limits.memory',
  chartSuffix: 'Gi',
})

const jupyterParams: ParamDecl[] = [
  dataFolder(
    'Folder of the project bucket that appears read-only as project-data/ in the notebook.',
  ),
  {
    key: 'flavour',
    label: 'Image',
    type: 'choice',
    choices: [
      { title: 'Minimal (Python 3.12)', value: 'minimal' },
      { title: 'Scientific (NumPy, SciPy, pandas)', value: 'scipy' },
      { title: 'Deep learning (PyTorch, MONAI)', value: 'pytorch' },
    ],
    default: 'scipy',
    required: true,
    description: 'Preinstalled Python packages.',
    chartValue: 'image.flavour',
  },
  gpu,
  {
    key: 'cpu',
    label: 'CPU cores',
    type: 'integer',
    default: 2,
    min: 1,
    max: 8,
    required: true,
    description: 'Number of CPU cores the notebook may use.',
    chartValue: 'resources.limits.cpu',
  },
  memory(8, 64),
  workspace(10),
  {
    key: 'gitToken',
    label: 'Git access token',
    type: 'string',
    default: '',
    secret: true,
    description:
      'Lets the notebook clone private repositories. Stored as a Kubernetes secret and never shown again.',
    chartValue: 'git.token',
  },
]

const idleShutdown: ParamDecl = {
  key: 'idleHours',
  label: 'Stop idle kernels after (hours)',
  type: 'integer',
  default: 12,
  min: 1,
  max: 72,
  required: true,
  description: 'Frees memory and a reserved GPU when nobody has used a kernel for this long.',
  chartValue: 'jupyter.culling.idleHours',
}

const mitkParams: ParamDecl[] = [
  dataFolder('Folder of the project bucket that MITK opens images and segmentations from.'),
  {
    key: 'resolution',
    label: 'Screen resolution',
    type: 'choice',
    choices: [
      { title: '1280 × 800', value: '1280x800' },
      { title: '1920 × 1080', value: '1920x1080' },
      { title: '2560 × 1440', value: '2560x1440' },
    ],
    default: '1920x1080',
    required: true,
    description: 'Size of the remote desktop.',
    chartValue: 'display.resolution',
  },
  gpu,
  workspace(5),
]

const cvatParams: ParamDecl[] = [
  dataFolder('Folder of the project bucket that CVAT imports tasks from.'),
  {
    key: 'storage',
    label: 'Annotation storage (GiB)',
    type: 'integer',
    default: 20,
    min: 5,
    max: 500,
    required: true,
    description: 'Persistent volume for annotations and the CVAT database.',
    chartValue: 'persistence.data.size',
    chartSuffix: 'Gi',
  },
  {
    key: 'modelAssist',
    label: 'Model-assisted labelling',
    type: 'boolean',
    default: false,
    description: 'Suggests annotations with a pretrained model. Needs a GPU.',
    chartValue: 'nuclio.enabled',
  },
  {
    key: 'adminPassword',
    label: 'CVAT admin password',
    type: 'string',
    default: '',
    required: true,
    minLength: 12,
    secret: true,
    description:
      'Password of the CVAT superuser. Stored as a Kubernetes secret and never shown again.',
    chartValue: 'cvat.superuser.password',
  },
]

export const applications: Application[] = [
  {
    id: 'jupyterlab',
    name: 'JupyterLab',
    description: 'Notebooks and a terminal for analysing the data of your project in Python.',
    icon: 'mdi-notebook-outline',
    multiDeployable: true,
    scopes: ['project'],
    versions: [
      {
        version: '4.3.0',
        registered: true,
        entryPath: 'lab',
        workspaceParam: 'workspace',
        dataFolderParam: 'dataFolder',
        params: [...jupyterParams, idleShutdown],
      },
      {
        version: '4.2.5',
        registered: true,
        entryPath: 'lab',
        workspaceParam: 'workspace',
        dataFolderParam: 'dataFolder',
        params: jupyterParams,
      },
    ],
  },
  {
    id: 'mitk',
    name: 'MITK Workbench',
    description: 'MITK Workbench in the browser for viewing images and correcting segmentations.',
    icon: 'mdi-brain',
    multiDeployable: true,
    scopes: ['project'],
    versions: [
      {
        version: '2024.12.0',
        registered: true,
        entryPath: 'vnc.html',
        workspaceParam: 'workspace',
        dataFolderParam: 'dataFolder',
        params: mitkParams,
      },
      {
        version: '2024.06.1',
        registered: false,
        entryPath: 'vnc.html',
        workspaceParam: 'workspace',
        dataFolderParam: 'dataFolder',
        params: mitkParams,
      },
    ],
  },
  {
    id: 'cvat',
    name: 'CVAT',
    description: 'Annotation tool for labelling images as a team. One shared instance per project.',
    icon: 'mdi-vector-square-edit',
    multiDeployable: false,
    scopes: ['project'],
    versions: [
      {
        version: '2.11.0',
        registered: true,
        entryPath: '',
        workspaceParam: 'storage',
        dataFolderParam: 'dataFolder',
        params: cvatParams,
      },
      {
        version: '2.10.3',
        registered: true,
        entryPath: '',
        workspaceParam: 'storage',
        dataFolderParam: 'dataFolder',
        params: cvatParams,
      },
    ],
  },
  {
    id: 'slicer',
    name: '3D Slicer',
    description: '3D Slicer in the browser for segmentation and 3D visualisation.',
    icon: 'mdi-cube-scan',
    multiDeployable: true,
    scopes: ['project'],
    versions: [
      {
        version: '5.6.2',
        registered: true,
        entryPath: 'vnc.html',
        workspaceParam: 'workspace',
        dataFolderParam: 'dataFolder',
        params: [
          dataFolder('Folder of the project bucket that Slicer opens data from.'),
          memory(8, 32),
          workspace(10),
        ],
      },
    ],
  },
  {
    id: 'code-server',
    name: 'VS Code',
    description:
      'VS Code (code-server) in the browser for writing and testing code on project data.',
    icon: 'mdi-microsoft-visual-studio-code',
    multiDeployable: true,
    scopes: ['project'],
    versions: [
      {
        version: '4.89.1',
        registered: true,
        entryPath: '',
        workspaceParam: 'workspace',
        dataFolderParam: 'dataFolder',
        params: [
          dataFolder('Folder of the project bucket that appears read-only in the workspace.'),
          memory(4, 32),
          workspace(10),
        ],
      },
    ],
  },
  {
    id: 'tensorboard',
    name: 'TensorBoard',
    description: 'Training curves of the models trained in this project.',
    icon: 'mdi-chart-line',
    multiDeployable: false,
    scopes: ['project'],
    versions: [
      {
        version: '2.17.0',
        registered: true,
        entryPath: '',
        dataFolderParam: 'dataFolder',
        params: [dataFolder('Folder of the project bucket that holds the training logs.')],
      },
    ],
  },
  {
    id: 'collabora',
    name: 'Collabora Online',
    description: 'Edit documents and spreadsheets together in the browser.',
    icon: 'mdi-file-document-edit-outline',
    multiDeployable: false,
    scopes: ['project', 'platform'],
    versions: [
      {
        version: '24.04.6',
        registered: true,
        entryPath: '',
        params: [
          {
            key: 'language',
            label: 'Default language',
            type: 'choice',
            choices: [
              { title: 'English', value: 'en' },
              { title: 'German', value: 'de' },
            ],
            default: 'en',
            required: true,
            description: 'Language of menus and spell checking.',
            chartValue: 'collabora.language',
          },
          memory(4, 16),
        ],
      },
    ],
  },
  {
    id: 'ohif',
    name: 'OHIF Viewer',
    description: 'Zero-footprint DICOM viewer for the images of the project you work in.',
    icon: 'mdi-image-filter-center-focus-weak',
    multiDeployable: false,
    scopes: ['platform'],
    versions: [
      {
        version: '3.8.2',
        registered: true,
        entryPath: 'viewer',
        params: [
          {
            key: 'layout',
            label: 'Default layout',
            type: 'choice',
            choices: [
              { title: 'One viewport', value: '1x1' },
              { title: 'Two viewports side by side', value: '1x2' },
            ],
            default: '1x1',
            required: true,
            description: 'Viewport layout a study opens with.',
            chartValue: 'ohif.defaultLayout',
          },
        ],
      },
    ],
  },
]

/** Applications enabled per project (Story 5.2). */
export const seedAvailability: Record<string, string[]> = {
  'lung-ct': ['jupyterlab', 'mitk', 'cvat', 'slicer', 'collabora'],
  'brain-mri': ['jupyterlab', 'slicer', 'code-server', 'tensorboard', 'collabora'],
  'prostate-pet': ['jupyterlab', 'mitk'],
}

const MIN = 60_000
const HOUR = 60 * MIN
const DAY = 24 * HOUR

function running(name: string, startedAt: number, restarts = 0) {
  return { name, status: 'Running', ready: '1/1', restarts, startedAt }
}

/** Fresh copies of the deployed applications, relative to `now`. */
export function seedDeployed(now: number): DeployedApp[] {
  const ago = (ms: number) => now - ms
  const seed: DeployedApp[] = [
    {
      id: 'd1',
      name: 'anna-notebook',
      appId: 'jupyterlab',
      version: '4.2.5',
      scope: { kind: 'project', projectId: 'lung-ct', forPerson: 'anna' },
      description: 'Radiomics feature exploration on cohort A',
      deployedBy: 'paul',
      deployedAt: ago(3 * DAY + 2 * HOUR),
      values: {
        dataFolder: 'cohort-a',
        flavour: 'scipy',
        gpu: false,
        cpu: 2,
        memory: 8,
        workspace: 10,
        gitToken: 'ghp_mock-token',
      },
      state: 'READY',
      pods: [running('anna-notebook-jupyterlab-6c9f7d8b5-x2k4q', ago(3 * DAY + 2 * HOUR))],
      events: [],
    },
    {
      id: 'd2',
      name: 'jonas-notebook',
      appId: 'jupyterlab',
      version: '4.3.0',
      scope: { kind: 'project', projectId: 'lung-ct', forPerson: 'jonas' },
      description: 'Training data preparation for nodule detection',
      deployedBy: 'paul',
      deployedAt: ago(12 * DAY),
      values: {
        dataFolder: 'cohort-b',
        flavour: 'pytorch',
        gpu: true,
        cpu: 4,
        memory: 32,
        workspace: 50,
        gitToken: '',
        idleHours: 24,
      },
      state: 'READY',
      pods: [running('jonas-notebook-jupyterlab-84d6b9c7f-mm2tw', ago(2 * DAY), 2)],
      events: [],
    },
    {
      id: 'd3',
      name: 'segmentation-review',
      appId: 'mitk',
      version: '2024.06.1',
      scope: { kind: 'project', projectId: 'lung-ct', forPerson: null },
      description: 'Review and correct lung lobe segmentations before training',
      deployedBy: 'paul',
      deployedAt: ago(26 * HOUR),
      values: { dataFolder: 'annotations', resolution: '1920x1080', gpu: false, workspace: 5 },
      state: 'READY',
      pods: [running('segmentation-review-mitk-5f7b9c6d4-q8rnz', ago(26 * HOUR))],
      events: [],
    },
    {
      id: 'd4',
      name: 'nodule-labelling',
      appId: 'cvat',
      version: '2.11.0',
      scope: { kind: 'project', projectId: 'lung-ct', forPerson: null },
      description: 'Label nodules in cohort B with the clinical team',
      deployedBy: 'paul',
      deployedAt: ago(42 * MIN),
      values: {
        dataFolder: 'cohort-b',
        storage: 20,
        modelAssist: false,
        adminPassword: 'mock-password-123',
      },
      state: 'FAILED',
      pods: [
        {
          name: 'nodule-labelling-cvat-server-7d9f8c6b5-h4kz2',
          status: 'ImagePullBackOff',
          ready: '0/1',
          restarts: 0,
          startedAt: ago(42 * MIN),
        },
        running('nodule-labelling-cvat-db-0', ago(42 * MIN)),
      ],
      events: [
        {
          type: 'Normal',
          reason: 'Scheduled',
          object: 'pod/nodule-labelling-cvat-server-7d9f8c6b5-h4kz2',
          message:
            'Successfully assigned nodule-labelling-cvat-server-7d9f8c6b5-h4kz2 to node gpu-worker-2',
          at: ago(42 * MIN),
        },
        {
          type: 'Normal',
          reason: 'Pulling',
          object: 'pod/nodule-labelling-cvat-server-7d9f8c6b5-h4kz2',
          message: 'Pulling image "registry.kaapana.example.org/cvat/server:2.11.0"',
          at: ago(41 * MIN),
        },
        {
          type: 'Warning',
          reason: 'Failed',
          object: 'pod/nodule-labelling-cvat-server-7d9f8c6b5-h4kz2',
          message:
            'Failed to pull image "registry.kaapana.example.org/cvat/server:2.11.0": manifest unknown',
          at: ago(41 * MIN),
        },
        {
          type: 'Warning',
          reason: 'BackOff',
          object: 'pod/nodule-labelling-cvat-server-7d9f8c6b5-h4kz2',
          message: 'Back-off pulling image "registry.kaapana.example.org/cvat/server:2.11.0"',
          at: ago(3 * MIN),
        },
      ],
      failure: {
        reason:
          'The container image cvat/server:2.11.0 could not be downloaded: the registry has no such image. Ask your administrator to check the CVAT extension.',
        helm: 'Release "nodule-labelling" deployed, but deployment/nodule-labelling-cvat-server is not ready: 0/1 pods available (ImagePullBackOff).',
      },
    },
    {
      id: 'd5',
      name: 'airway-segmentation',
      appId: 'slicer',
      version: '5.6.2',
      scope: { kind: 'project', projectId: 'lung-ct', forPerson: 'paul' },
      description: 'Airway segmentation experiments',
      deployedBy: 'paul',
      deployedAt: ago(6 * DAY),
      values: { dataFolder: 'cohort-a', memory: 16, workspace: 10 },
      state: 'READY',
      pods: [running('airway-segmentation-slicer-6b8d7f5c9-2rj7v', ago(19 * HOUR))],
      events: [],
      drift: { kind: 'changed', detectedAt: ago(19 * HOUR), revision: 5, recordedRevision: 3 },
    },
    {
      id: 'd6',
      name: 'pilot-notebook',
      appId: 'jupyterlab',
      version: '4.2.5',
      scope: { kind: 'project', projectId: 'lung-ct', forPerson: 'sofia' },
      description: 'Pilot analysis from the project kick-off',
      deployedBy: 'paul',
      deployedAt: ago(40 * DAY),
      values: {
        dataFolder: '/',
        flavour: 'minimal',
        gpu: false,
        cpu: 1,
        memory: 4,
        workspace: 5,
        gitToken: '',
      },
      state: 'FAILED',
      pods: [],
      events: [],
      failure: {
        reason:
          'The helm release pilot-notebook no longer exists in the cluster. It was removed outside Kaapana.',
        helm: 'Error: release: not found',
      },
      drift: { kind: 'removed', detectedAt: ago(5 * HOUR) },
    },
    {
      id: 'd7',
      name: 'flair-notebook',
      appId: 'jupyterlab',
      version: '4.3.0',
      scope: { kind: 'project', projectId: 'brain-mri', forPerson: 'anna' },
      description: 'FLAIR lesion statistics',
      deployedBy: 'lea',
      deployedAt: ago(8 * DAY),
      values: {
        dataFolder: 'flair',
        flavour: 'scipy',
        gpu: false,
        cpu: 2,
        memory: 8,
        workspace: 20,
        gitToken: '',
        idleHours: 12,
      },
      state: 'READY',
      pods: [running('flair-notebook-jupyterlab-7c5d8f9b6-t6wq1', ago(8 * DAY))],
      events: [],
    },
    {
      id: 'd8',
      name: 'training-curves',
      appId: 'tensorboard',
      version: '2.17.0',
      scope: { kind: 'project', projectId: 'brain-mri', forPerson: null },
      description: 'Monitor the nnU-Net training runs',
      deployedBy: 'lea',
      deployedAt: ago(2 * DAY),
      values: { dataFolder: 'results' },
      state: 'READY',
      pods: [running('training-curves-tensorboard-5d9c7b8f6-zz8kp', ago(2 * DAY))],
      events: [],
    },
    {
      id: 'd9',
      name: 'psma-review',
      appId: 'mitk',
      version: '2024.12.0',
      scope: { kind: 'project', projectId: 'prostate-pet', forPerson: 'mehmet' },
      description: 'PSMA PET lesion review',
      deployedBy: 'lea',
      deployedAt: ago(4 * DAY),
      values: { dataFolder: 'psma', resolution: '1920x1080', gpu: false, workspace: 5 },
      state: 'READY',
      pods: [running('psma-review-mitk-6d8b7c5f4-k9p3s', ago(4 * DAY))],
      events: [],
    },
    {
      id: 'd10',
      name: 'ohif',
      appId: 'ohif',
      version: '3.8.2',
      scope: { kind: 'platform' },
      description: 'DICOM viewer for all projects',
      deployedBy: 'kim',
      deployedAt: ago(21 * DAY),
      values: { layout: '1x1' },
      state: 'READY',
      pods: [running('ohif-7f6c9d8b4-w2n5h', ago(9 * DAY))],
      events: [],
    },
  ]
  for (const d of seed) {
    const known = applications
      .find((a) => a.id === d.appId)
      ?.versions.some((v) => v.version === d.version)
    if (!known)
      throw new Error(
        `Seed instance ${d.name} runs ${d.appId} ${d.version}, which no application declares.`,
      )
  }
  return seed
}
