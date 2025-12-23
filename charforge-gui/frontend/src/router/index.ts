import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/dashboard'
    },
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/views/auth/LoginView.vue'),
      meta: { requiresGuest: true }
    },
    {
      path: '/register',
      name: 'Register', 
      component: () => import('@/views/auth/RegisterView.vue'),
      meta: { requiresGuest: true }
    },
    {
      path: '/dashboard',
      name: 'Dashboard',
      component: () => import('@/views/DashboardView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/characters',
      name: 'Characters',
      component: () => import('@/views/CharactersView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/characters/create',
      name: 'CreateCharacter',
      component: () => import('@/views/CreateCharacterView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/characters/:id',
      name: 'CharacterDetail',
      component: () => import('@/views/CharacterDetailView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/training',
      name: 'Training',
      component: () => import('@/views/TrainingView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/inference',
      name: 'Inference',
      component: () => import('@/views/InferenceView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/gallery',
      name: 'Gallery',
      component: () => import('@/views/GalleryView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/media',
      name: 'Media',
      component: () => import('@/views/MediaView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/datasets',
      name: 'Datasets',
      component: () => import('@/views/DatasetsView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/settings',
      name: 'Settings',
      component: () => import('@/views/SettingsView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'NotFound',
      component: () => import('@/views/NotFoundView.vue')
    }
  ]
})

// Navigation guards
router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()

  // Initialize auth if not already done
  if (!authStore.user && !authStore.isLoading) {
    await authStore.initializeAuth()
  }

  // Auth is disabled by default for local power user workflow
  // Always allow access, redirect away from login/register pages
  if (!authStore.authEnabled) {
    // Ensure default user is set even if initializeAuth didn't complete
    if (!authStore.user) {
      authStore.user = {
        id: 1,
        username: 'default_user',
        email: 'default@charforge.local',
        is_active: true
      }
    }
    // Skip login/register routes when auth is disabled
    if (to.path === '/login' || to.path === '/register') {
      next('/dashboard')
      return
    }
    next()
    return
  }

  // Check if route requires authentication (when auth is enabled)
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next('/login')
  } else if (to.meta.requiresGuest && authStore.isAuthenticated) {
    next('/dashboard')
  } else {
    next()
  }
})

export default router
