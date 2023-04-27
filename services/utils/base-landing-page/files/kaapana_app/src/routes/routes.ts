const routes = [
    {
        name: 'home',
        path: '/',
        component: () => import('@/views/Home.vue'),
        title: 'Home',
        permissions: {
            isPublic: true,
        },
    },
    {
        name: 'pending-applications',
        path: '/pending-applications',
        component: () => import('@/views/PendingApplications.vue'),
        title: 'PendingApplications',
        permissions: {
            isPublic: false,
        },
    },
    {
        name: 'datasets',
        path: '/datasets',
        component: () => import('@/views/Datasets.vue'),
        title: 'Datasets',
        permissions: {
            isPublic: false,
        },
    },
    {
        name: 'extensions',
        path: '/extensions',
        component: () => import('@/views/Extensions.vue'),
        title: 'Extensions',
        permissions: {
            isPublic: false,
        },
    },
    {
        name: 'workflow-execution',
        path: '/workflow-execution',
        component: () => import('@/views/WorkflowExecution.vue'),
        title: 'Workflow Execution',
        permissions: {
            isPublic: false,
        },
    },
    {
        name: 'workflows',
        path: '/workflows',
        component: () => import('@/views/Workflows.vue'),
        title: 'Workflow',
        permissions: {
            isPublic: false,
        },
    },
    {
        name: 'runner-instances',
        path: '/runner-instances',
        component: () => import('@/views/RunnerInstances.vue'),
        title: 'Instance Overview',
        permissions: {
            isPublic: false,
        },
    },
    {
        name: 'results-browser',
        path: '/results-browser',
        component: () => import('@/views/ResultsBrowser.vue'),
        title: 'Results browser',
        permissions: {
            isPublic: false,
        },
    },
    {
        name: 'data-upload',
        path: '/data-upload',
        component: () => import('@/views/DataUpload.vue'),
        title: 'DataUpload',
        permissions: {
            isPublic: false,
        },
    },
    {
        name: 'iframe-view',
        path: '/web/:iFrameUrl',
        component: () => import('@/views/Iframe.vue'),
        title: 'None',
        permissions: {
            isPublic: false,
        },
    },
    {
        name: 'ew-section-view',
        path: '/web/:ewSection/:ewSubSection',
        component: () => import('@/views/Iframe.vue'),
        title: 'View',
        permissions: {
            isPublic: false,
            roles: [
                {
                    role: 'guest',
                    access: false,
                    redirect: 'home',
                },
            ],
        },
    },
]

export default routes
