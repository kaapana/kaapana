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
        name: 'extensions',
        path: '/extensions',
        component: () => import('@/views/Extensions.vue'),
        title: 'Extensions',
        permissions: {
            isPublic: false,
        },
    },
    {
        name: 'tdfadashboard',
        path: '/tdfadashboard',
        component: () => import('@/views/Dashboard.vue'),
        title: 'TFDA Dashboard',
        permissions: {
            isPublic: false,
        },
    },
    {
        name: 'status',
        path: '/status',
        component: () => import('@/views/Status.vue'),
        title: 'TFDA Status',
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
