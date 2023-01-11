const routes = [
    {
        name: 'home',
        path: '/',
        component: () => import('@/views/Extensions.vue'),
        title: 'Extensions',
        permissions: {
            isPublic: false,
        },
    },
    {
        name: 'home',
        path: '/maintenance',
        component: () => import('@/views/Extensions.vue'),
        title: 'Extensions',
        permissions: {
            isPublic: false,
        },
    },
]

export default routes
