import { createRouter, createWebHistory } from 'vue-router'
import { authState } from '../utils/auth'

const routes = [
    {
        path: '/login',
        component: () => import('../pages/LoginView.vue'),
        meta: { public: true }
    },
    {
        path: '/signup',
        component: () => import('../pages/SignupView.vue'),
        meta: { public: true }
    },
    {
        path: '/',
        component: () => import('../pages/HomeView.vue')
    },

    // --- Primary navigation ---
    {
        path: '/missions',
        component: () => import('../pages/MissionsView.vue')
    },
    {
        path: '/missions/:id',
        component: () => import('../pages/MissionChatView.vue')
    },
    {
        path: '/missions/:id/office',
        component: () => import('../pages/MissionOfficeView.vue')
    },
    {
        path: '/missions/:id/office3d',
        component: () => import('../pages/MissionOffice3DView.vue')
    },
    {
        path: '/activity',
        component: () => import('../pages/ActivityFeedView.vue')
    },
    {
        path: '/team',
        component: () => import('../pages/TeamView.vue')
    },

    // --- Secondary / internal pages (accessible but not in main nav) ---
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
    },
    {
        path: '/orchestration',
        component: () => import('../pages/OrchestrationView.vue')
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
                top: 0
            }
        }
        
        return { top: 0 }
    }
})

router.beforeEach((to, from, next) => {
    if (to.meta.public) {
        if (authState.isAuthenticated && (to.path === '/login' || to.path === '/signup')) {
            return next('/')
        }
        return next()
    }
    if (!authState.isAuthenticated) {
        return next('/login')
    }
    next()
})

export default router
