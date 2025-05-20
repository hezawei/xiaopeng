<template>
  <div>
    <n-input type="textarea" :autosize="{ minRows: 3, maxRows: 10 }" v-model:value="chatInput" placeholder="输入您的反馈信息..."
      @keypress.enter="sendFeedback" style="margin-bottom: 10px" />
    <div>
      <n-button type="primary" class="float-right mr-15" @click="sendFeedback">
        发送
      </n-button>
    </div>
  </div>
</template>

<script>
import { request } from '@/utils';
import { ref } from 'vue';

export default {
  setup() {
    const chatInput = ref('');

    const sendFeedback = async () => {
      // 模拟发送反馈到后端
      console.log('Feedback sent:', chatInput.value);
      chatInput.value = '';
    };

    return { chatInput, sendFeedback };
  },
};
</script>
