<script setup>
import { h, onMounted, ref, resolveDirective, withDirectives } from 'vue'
import { NButton, NForm, NFormItem, NInput, NInputNumber, NPopconfirm, NTreeSelect } from 'naive-ui'

import AgentPage from '@/components/page/AgentPage.vue'
import AgentTable from '@/components/table/AgentTable.vue'
import ReqsAnalysis from '@/components/reqs/ReqsAnalysis.vue'
import StreamOutput from '@/components/reqs/StreamOutput.vue'
import FeedbackChat from '@/components/reqs/FeedbackChat.vue'
import TheIcon from '@/components/icon/TheIcon.vue'

import { renderIcon } from '@/utils'
import { useCRUD } from '@/composables'
// import { loginTypeMap, loginTypeOptions } from '@/constant/data'
import api from '@/api'

defineOptions({ name: '需求分析' })

const $table = ref(null)
const queryItems = ref({})
const vPermission = resolveDirective('permission')


</script>

<template>
  <!-- 业务页面 -->
  <AgentPage>
    <div>
      <ReqsAnalysis />
    </div>
  </AgentPage>
</template>

<style scoped>
.chat-container {
  position: absolute; /* 固定定位 */
  bottom: 0; /* 距离底部为0 */
  left: 10px; /* 距离左侧为0 */
  width: calc(100% - 20px); /* 宽度为100%减去左右边距 */
  /* 占满父容器宽度 */
  box-sizing: border-box;
  /* 包括 padding 和 border 在内计算宽度 */
  padding: 10px;
  /* 添加内边距 */
}
</style>
