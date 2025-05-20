<template>
    <n-modal
      v-model:show="show"
      :style="{ width }"
      style="height: 600px;"
      preset="card"
      :title="title"
      size="huge"
      :bordered="false"
      :mask-closable="false"
    >
      <slot />

    </n-modal>
  </template>
  
  <script setup>
  const props = defineProps({
    width: {
      type: String,
      default: '700px',
    },
    title: {
      type: String,
      default: '',
    },
    showFooter: {
      type: Boolean,
      default: true,
    },
    visible: {
      type: Boolean,
      required: true,
    },
    loading: {
      type: Boolean,
      default: false,
    },
  })
  
  const emit = defineEmits(['update:visible', 'onSave'])
const show = computed({
  get() {
    return props.visible
  },
  set(v) {
    emit('update:visible', v)
  },
})
  </script>

  <style scoped>
  .n-modal .n-card .n-card-header {
    padding: 0 !important;
  }
  </style>
  