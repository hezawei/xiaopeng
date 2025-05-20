<template>
    <div class="my-card">
        <!-- 输入框 -->
        <n-input v-model:value="input" type="textarea" placeholder="请输入或导入需求..." :autosize="{ minRows: 5, maxRows: 10 }"
            style="margin-bottom: 10px;" />

        <!-- 分析按钮 -->
        <n-space justify="end" style="margin-bottom: 10px;">
            <n-button type="primary" @click="analyze">
                一键分析需求
            </n-button>
        </n-space>

        <!-- 加载状态 -->
        <div v-if="loading" class="loading">
            <n-spin />
        </div>

        <!-- 错误提示 -->
        <div v-else-if="error" class="error">
            <n-alert title="错误" type="error">
                {{ error }}
            </n-alert>
        </div>

        <!-- 输出结果 -->
        <div v-else class="output">
            <n-scrollbar style="max-height: 300px;">
                <pre>{{ output }}</pre>
            </n-scrollbar>
        </div>
    </div>
</template>

<script>
import { ref } from 'vue';
import { createAnalysisWebSocket } from '@/api/requirements';

export default {
  name: 'RequirementAnalyzer',
  setup() {
    const input = ref('');
    const output = ref('');
    const loading = ref(false);
    const error = ref(null);

    const analyze = () => {
      if (!input.value.trim()) {
        alert('请输入需求内容！');
        return;
      }

      output.value = '';
      loading.value = true;
      error.value = null;

      const ws = createAnalysisWebSocket(
        (message) => {
          output.value += message; // 实时更新输出
        },
        (err) => {
          error.value = err;
          loading.value = false;
        }
      );

      ws.send(input.value); // 发送需求到后端

      setTimeout(() => {
        ws.close(); // 关闭 WebSocket 连接
        loading.value = false;
      }, 10000); // 假设分析过程不超过 10 秒
    };

    return {
      input,
      output,
      loading,
      error,
      analyze,
    };
  },
};
</script>

<style scoped>
.loading {
    text-align: center;
}

.error {
    margin-top: 10px;
}

.output pre {
    white-space: pre-wrap;
    word-wrap: break-word;
    background-color: #181717;
    padding: 10px;
    border-radius: 4px;
}
</style>