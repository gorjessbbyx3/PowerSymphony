import { createRouter, createWebHistory } from 'vue-router'

const routes = [
    {
        path: '/',
        component: () => import('../pages/HomeView.vue')
    },
    {
        path: '/tutorial',
        component: () => import('../pages/TutorialView.vue')
    },
    {
        path: '/launch',
        component: () => import('../pages/LaunchView.vue')
    },
    {
        path: '/batch-run',
        component: () => import('../pages/BatchRunView.vue')
    },
    {
        path: '/workflows/:name?',
        component: () => import('../pages/WorkflowWorkbench.vue')
    },
    {
        path: '/system',
        component: () => import('../pages/SystemStatsView.vue')
    },
    {
        path: '/performance',
        component: () => import('../pages/AgentPerformanceView.vue')
    },
    {
        path: '/github',
        component: () => import('../pages/GitHubView.vue')
    },
    {
        path: '/diagrams',
        component: () => import('../pages/DiagramView.vue')
    },
    {
        path: '/collaboration',
        component: () => import('../pages/CollaborationView.vue')
    },
    {
        path: '/cicd',
        component: () => import('../pages/CICDView.vue')
    },
    {
        path: '/fine-tuning',
        component: () => import('../pages/FineTuningView.vue')
    },
    {
        path: '/marketplace',
        component: () => import('../pages/MarketplaceView.vue')
    }
]

const router = createRouter({
    history: createWebHistory(),
    routes,
    scrollBehavior(to, from, savedPosition) {
        if (savedPosition) {
            return savedPosition
        }
        
        if (to.hash) {
            return {
                el: to.hash,
                behavior: 'smooth',
                // Add a small delay to ensure the element exists
                top: 0
            }
        }
        
        // Otherwise scroll to top
        return { top: 0 }
    }
})

export default router