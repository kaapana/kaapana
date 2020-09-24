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
        name: 'application-links',
        path: '/application-links',
        component: () => import('@/views/ApplicationLinks.vue'),
        title: 'ApplicationLinks',
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
        component: () => import('@/views/IframeView.vue'),
        title: 'None',
        permissions: {
            isPublic: false,
        },
    },
    {
        name: 'ew-section-view',
        path: '/web/:ewSection/:ewSubSection',
        component: () => import('@/views/IframeView.vue'),
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
