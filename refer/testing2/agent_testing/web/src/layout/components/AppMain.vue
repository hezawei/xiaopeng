<template>
  <router-view v-slot="{ Component, route }">
    <KeepAlive :include="keepAliveRouteNames">
      <component
        :is="Component"
        v-if="appStore.reloadFlag"
        :key="appStore.aliveKeys[route.name] || route.fullPath"
      />
    </KeepAlive>
  </router-view>
</template>

<script setup>
import { useAppStore } from '@/store'
import { useRouter } from 'vue-router'
const appStore = useAppStore()
const router = useRouter()

const allRoutes = router.getRoutes()
const keepAliveRouteNames = computed(() => {
  return allRoutes.filter((route) => route.meta?.keepAlive).map((route) => route.name)
})
</script>

<style lang="scss">
.n-card {
  box-shadow: 0 4px 20px rgba(148, 163, 184, 0.1);
  transition: all 0.3s ease;
  background: #FFFFFF !important;
  border: 1px solid rgba(109, 40, 217, 0.08);
  border-radius: 12px;

  &:hover {
    box-shadow: 0 8px 30px rgba(148, 163, 184, 0.15);
    border-color: rgba(109, 40, 217, 0.2);
  }
}

.n-card > .n-card__content {
  background: #F8FAFC !important;
  border-radius: 0 0 12px 12px;
  padding: 20px !important;
}

.n-card-header {
  background: #FFFFFF !important;
  border-bottom: 1px solid rgba(109, 40, 217, 0.08);
  color: #1E293B !important;
  font-weight: 600;
  border-radius: 12px 12px 0 0;
  padding: 20px !important;
}

.n-card__footer {
  background: #F8FAFC !important;
  border-top: 1px solid rgba(109, 40, 217, 0.08);
  padding: 16px 20px !important;
}

.dark .dark\:bg-black, .dark [dark\:bg-black=""] {
  background-color: #F8FAFC;
}
</style>