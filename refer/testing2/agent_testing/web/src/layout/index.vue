<template>
  <n-layout has-sider wh-full>
    <n-layout-sider
      bordered
      collapse-mode="width"
      :collapsed-width="64"
      :width="220"
      :native-scrollbar="false"
      :collapsed="appStore.collapsed"
      class="layout-sider"
    >
      <SideBar />
    </n-layout-sider>

    <article flex-col flex-1 overflow-hidden>
      <header
        class="flex items-center px-15 layout-header"
        :style="`height: ${header.height}px`"
      >
        <AppHeader />
      </header>
      <section v-if="tags.visible" class="layout-tags">
        <AppTags :style="{ height: `${tags.height}px` }" />
      </section>
      <section class="appSection layout-main" flex-1 overflow-hidden>
        <AppMain />
      </section>
    </article>
  </n-layout>
</template>

<script setup>
import AppHeader from './components/header/index.vue'
import SideBar from './components/sidebar/index.vue'
import AppMain from './components/AppMain.vue'
import AppTags from './components/tags/index.vue'
import { useAppStore } from '@/store'
import { header, tags } from '~/settings'

// 移动端适配
import { useBreakpoints } from '@vueuse/core'

const appStore = useAppStore()
const breakpointsEnum = {
  xl: 1600,
  lg: 1199,
  md: 991,
  sm: 666,
  xs: 575,
}
const breakpoints = reactive(useBreakpoints(breakpointsEnum))
const isMobile = breakpoints.smaller('sm')
const isPad = breakpoints.between('sm', 'md')
const isPC = breakpoints.greater('md')
watchEffect(() => {
  if (isMobile.value) {
    // Mobile
    appStore.setCollapsed(true)
    appStore.setFullScreen(false)
  }

  if (isPad.value) {
    // IPad
    appStore.setCollapsed(true)
    appStore.setFullScreen(false)
  }

  if (isPC.value) {
    // PC
    appStore.setCollapsed(false)
    appStore.setFullScreen(true)
  }
})
</script>

<style lang="scss">
.layout-sider {
  background: rgba(255, 255, 255, 0.9) !important;
  backdrop-filter: blur(12px);
  border-right: 1px solid rgba(109, 40, 217, 0.1);
}

.layout-header {
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(109, 40, 217, 0.1);
}

.layout-tags {
  background: rgba(255, 255, 255, 0.8);
  border-bottom: 1px solid rgba(109, 40, 217, 0.1);
}

.layout-main {
  background: rgba(248, 250, 252, 0.6);
}

.n-card {
  border-radius: 12px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.9) !important;
  backdrop-filter: blur(12px);
  border: 1px solid rgba(109, 40, 217, 0.1);
  transition: all 0.3s ease;

  &:hover {
    border-color: rgba(109, 40, 217, 0.2);
    box-shadow: 0 8px 30px rgba(148, 163, 184, 0.15);
  }
}

.dark .dark\:bg-hex-121212 {
  background-color: rgba(255, 255, 255, 0.9);
}

.bg-\[\#f5f6fb\], [bg-hex-f5f6fb=""] {
  background: linear-gradient(135deg, #F8FAFC 0%, #F1F5F9 100%);
}
</style>