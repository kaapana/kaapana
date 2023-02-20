const routes = [
    {
        name: 'Platforms',
        path: '/platforms',
        component: () => import('@/views/Platforms.vue'),
        title: 'Platforms',
        permissions: {
            isPublic: false,
        },
    },
    {
        name: 'Extensions',
        path: '/extensions',
        component: () => import('@/views/Extensions.vue'),
        title: 'Extensions',
        permissions: {
            isPublic: false,
        },
    },
]

export default routes
