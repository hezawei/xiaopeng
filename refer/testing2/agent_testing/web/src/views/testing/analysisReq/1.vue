<template>
  <div class="container">
    <!-- 输入区域 -->
    <n-input
      v-model:value="demandText"
      type="textarea"
      placeholder="请输入需求..."
      :autosize="{ minRows: 3, maxRows: 10 }"
      class="input-area"
    />

    <!-- 操作按钮组 -->
    <div class="action-group">
      <n-button
        type="primary"
        class="action-btn"
        :loading="isAnalyzing"
        @click="submitDemand"
      >
        <template #icon>
          <TheIcon icon="mdi:robot" />
        </template>
        AI分析
      </n-button>

      <n-button type="primary" class="action-btn">
        <TheIcon icon="material-symbols:add" :size="18" />
        <n-upload
          :default-upload="false"
          @change="handleFileChange"
          class="upload-button"
        >
          导入需求文档
        </n-upload>
      </n-button>
    </div>

    <!-- 输出展示区 -->
    <div
      v-if="messages.length > 0"
      id="output"
      class="markdown-container"
      :class="{ 'has-content': messages.length }"
    >
      <div
        v-for="(msg, index) in messages"
        :key="index"
        class="message-item"
        :class="msg.source"
      >
        <div class="source-tag">
          <TheIcon
            :icon="msg.source === 'user' ? 'mdi:account' : 'mdi:robot'"
            :size="14"
          />
          {{ msg.source.toUpperCase() }}
        </div>
        <div class="markdown-content" v-html="msg.content"></div>
      </div>

      <!-- 加载状态 -->
      <div v-if="isAnalyzing" class="loading-indicator">
        <n-spin size="small" />
        <span>AI正在分析中...</span>
      </div>
    </div>
    <!-- 反馈区域 -->
    <transition name="slide-up">
      <div
        v-if="showFeedback"
        class="feedback-area"
      >
        <div class="feedback-header">
          <span>您的反馈将帮助我们改进</span>
          <n-button
            text
            @click="showFeedback = false"
            class="close-btn"
          >
            <TheIcon icon="mdi:close" />
          </n-button>
        </div>
        <n-input
          v-model:value="feedbackText"
          type="textarea"
          placeholder="请输入您的反馈信息..."
          :autosize="{ minRows: 2 }"
          class="feedback-input"
        />
        <n-button
          type="primary"
          class="send-btn"
          @click="submitFeedback"
        >
          提交反馈
        </n-button>
      </div>
    </transition>
  </div>
</template>
<script>
import { request } from '@/utils';
import { ref, onBeforeUnmount } from 'vue';
import { marked } from 'marked';
import DOMPurify from 'dompurify';
import hljs from 'highlight.js';
import { nextTick, watch } from 'vue';
// 配置Markdown解析器
marked.setOptions({
  highlight: (code, lang) => {
    const language = hljs.getLanguage(lang) ? lang : 'plaintext';
    return hljs.highlight(code, { language }).value;
  },
  breaks: true,
  gfm: true
});

// 创建Markdown解析函数
const parseMarkdown = (raw) => {
  return DOMPurify.sanitize(marked.parse(raw));
};

export default {
  setup() {
    const demandText = ref('');
    const file = ref(null);
    const isAnalyzing = ref(false);
    const messages = ref([]);
    const socket = ref(null);

    const showFeedback = ref(false);
    const feedbackText = ref('');

    // WebSocket生命周期管理
    const initWebSocket = () => {
      if (socket.value) {
        socket.value.close();
      }

      socket.value = new WebSocket(`ws://localhost:9999/api/v1/agent/ws/analyze`);

      socket.value.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          messages.value.push({
            source: data.source,
            content: parseMarkdown(data.content),
            timestamp: new Date().toISOString()
          });
          // 检测分析结束标记（根据后端返回的数据判断）
          if (data.is_final) {
            showFeedback.value = true;
          }
        } catch (error) {
          console.error('消息解析失败:', error);
        }
      };

      socket.value.onerror = (error) => {
        console.error('WebSocket错误:', error);
        isAnalyzing.value = false;
      };

      socket.value.onclose = () => {
        // 确保在连接关闭时显示反馈
        showFeedback.value = true;
        isAnalyzing.value = false;
      };
    };

    const handleFileChange = ({ file: uploadedFile }) => {
      file.value = uploadedFile.file;
    };

    const submitDemand = async () => {
      if (!demandText.value.trim() && !file.value) {
        window.$message?.warning('请输入需求或上传文件');
        return;
      }

      try {
        isAnalyzing.value = true;

        if (file.value) {
          const formData = new FormData();
          formData.append('file', file.value);
          const result = await request.post('/upload/', formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
          });
          demandText.value = result.text;
        }

        initWebSocket();

        // 等待连接建立
        await new Promise((resolve) => {
          if (socket.value.readyState === WebSocket.OPEN) {
            resolve();
          } else {
            socket.value.onopen = resolve;
          }
        });

        socket.value.send(JSON.stringify({
          content: demandText.value,
          file: "C:\\Users\\86134\\Desktop\\workspace\\AI\\agent_system_ui\\app\\api\\v1\\agent\\api_doc.pdf",
          user_id: 1,
          source: "user"
        }));
      } catch (error) {
        console.error('提交失败:', error);
        window.$message?.error('分析请求失败');
        isAnalyzing.value = false;
      }
    };

    // 组件卸载时关闭连接
    onBeforeUnmount(() => {
      if (socket.value) {
        socket.value.close();
      }
    });
    // 新增反馈提交方法
    const submitFeedback = async () => {
      if (feedbackText.value.trim()) {
        await request.post('/feedback', {
          content: feedbackText.value,
          session_id: sessionId.value
        });
        feedbackText.value = '';
        showFeedback.value = false;
        window.$message?.success('反馈提交成功');
      }
    };
        // 添加滚动控制逻辑
    const scrollToBottom = () => {
      nextTick(() => {
        const outputEl = document.getElementById('output');
        if (outputEl) {
          outputEl.scrollTop = outputEl.scrollHeight;
        }
      });
    };

    // 监听消息变化自动滚动
    watch(
      () => messages.value.length,
      () => scrollToBottom(),
      { immediate: true }
    );

    // 当容器尺寸变化时也触发滚动
    const resizeObserver = new ResizeObserver(scrollToBottom);
    onMounted(() => {
      const outputEl = document.getElementById('output');
      if (outputEl) {
        resizeObserver.observe(outputEl);
      }
    });

    onBeforeUnmount(() => {
      resizeObserver.disconnect();
    });
    return {
      demandText,
      file,
      isAnalyzing,
      messages,
      submitDemand,
      handleFileChange,
      showFeedback,
      feedbackText,
      submitFeedback
    };
  }
};
</script>
<style scoped>
/* 新增反馈区域样式 */
.feedback-area {
  position: fixed;
  bottom: 20px;
  right: 20px;
  width: 350px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  padding: 16px;
  z-index: 1000;
}

.feedback-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.close-btn {
  color: #999;
  transition: color 0.2s;

  &:hover {
    color: #666;
  }
}

.feedback-input {
  margin-bottom: 12px;
}

.send-btn {
  width: 100%;
}

/* 进场动画 */
.slide-up-enter-active,
.slide-up-leave-active {
  transition: all 0.3s ease;
}

.slide-up-enter-from,
.slide-up-leave-to {
  opacity: 0;
  transform: translateY(100%);
}

/* 调整输出容器高度 */
.markdown-container {
  max-height: calc(70vh - 120px); /* 为反馈区留出空间 */
  margin-bottom: 20px;
}

@media (max-width: 768px) {
  .feedback-area {
    width: calc(100% - 40px);
    bottom: 10px;
    right: 10px;
    left: 10px;
  }

  .markdown-container {
    max-height: calc(60vh - 100px);
  }
}

.container {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}

.input-area {
  margin: 15px 0;
  border-radius: 8px;
  transition: box-shadow 0.3s ease;
}

.input-area:focus {
  box-shadow: 0 0 0 2px rgba(24, 160, 88, 0.2);
}

.action-group {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  margin-bottom: 20px;
}

.action-btn {
  padding: 8px 16px;
  border-radius: 6px;
  transition: transform 0.2s ease;
}

.action-btn:hover {
  transform: translateY(-1px);
}

.markdown-container {
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
  min-height: 300px;
  max-height: 70vh;
  padding: 20px;
  overflow-y: auto;
  position: relative;
}

.markdown-container.has-content {
  border: 1px solid #e0e0e0;
}

.message-item {
  margin-bottom: 20px;
  padding: 16px;
  background: #fafafa;
  border-radius: 8px;
  animation: fadeIn 0.3s ease;
}

.message-item.ai {
  background: #f8ffff;
  border-left: 3px solid #2185d0;
}

.message-item.user {
  background: #fff8f6;
  border-left: 3px solid #db2828;
}

.source-tag {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #666;
  font-size: 0.85em;
  margin-bottom: 8px;
  font-weight: 500;
}

.markdown-content {
  font-family: 'Inter', system-ui, sans-serif;
  color: #333;
  line-height: 1.7;
}

.markdown-content h1 {
  font-size: 1.8em;
  margin: 1.2em 0 0.8em;
  border-bottom: 2px solid #eee;
}

.markdown-content pre {
  position: relative;
  margin: 1em 0;
  border-radius: 8px;
}

.markdown-content pre code {
  display: block;
  padding: 1.2em;
  font-size: 0.9em;
}

.markdown-content blockquote {
  color: #666;
  border-left: 4px solid #ddd;
  margin: 1em 0;
  padding: 0.5em 1em;
  background: #f9f9f9;
}

.loading-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  color: #666;
  font-size: 0.9em;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 768px) {
  .container {
    padding: 15px;
  }

  .markdown-container {
    max-height: 60vh;
    padding: 15px;
  }
}
</style>