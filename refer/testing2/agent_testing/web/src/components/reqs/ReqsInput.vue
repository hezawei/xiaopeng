<template>
  <div class="container">
    <!-- 左侧主内容区 -->
    <div class="left-panel">
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
        <!-- 文件信息展示 -->
        <div v-if="fileList.length > 0" class="file-info">
          <n-tag
            v-for="(file, index) in fileList"
            :key="file.id"
            closable
            @close="removeFile(index)"
            class="file-tag"
          >
            <TheIcon :icon="getFileIcon(file.name)" class="file-icon" />
            {{ file.name }} ({{ formatFileSize(file.size) }})
          </n-tag>
          <n-button
            v-if="fileList.length > 1"
            text
            @click="clearFiles"
            class="clear-all-btn"
          >
            清除全部
          </n-button>
        </div>
          <n-upload
            multiple
            directory-dnd
            :max="5"
            :default-upload="false"
            @change="handleFileChange"
            :file-list="fileList"
            :show-file-list="false"
            :before-upload="beforeUpload"
            class="upload-wrapper"
            ref="uploadRef"
          >
          <n-upload-dragger class="upload-dragger">
        <div class="upload-content">
          <n-button type="primary" class="upload-btn">
            <template #icon>
              <TheIcon icon="material-symbols:upload" :size="18" />
            </template>
            导入需求文档
          </n-button>
          <div class="upload-tips">支持拖拽文件或点击上传（最多5个）</div>
        </div>
      </n-upload-dragger>
        </n-upload>
      </div>

      <!-- 输出展示区 -->
      <div class="content-wrapper">
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
      </div>
      <div class="height-spacer"></div>
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

    <!-- 右侧需求列表 -->
    <div class="right-panel">
    <div class="demand-list-container">
      <h3 class="list-title">AI分析需求列表</h3>
      <n-list bordered class="demand-list">
        <!-- 列表项结构修改 -->
        <n-list-item v-for="(item, index) in demandList" :key="index">
          <n-thing>
            <template #header>
              <div class="demand-header">
                <span class="demand-name">{{ item.name }}</span>
                <n-tag :type="getTagType(item.type)" size="small" class="type-tag">
                  {{ item.type }}
                </n-tag>
              </div>
            </template>
            <template #description>
              <div class="demand-content">{{ item.content }}</div>
            </template>
          </n-thing>
        </n-list-item>
        <!-- 空状态保持 -->
      </n-list>
    </div>
    </div>

  </div>
</template>

<script>
import { request } from '@/utils';
import { ref, onBeforeUnmount, onMounted } from 'vue';
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
// 文件类型映射
const FILE_ICONS = {
  pdf: 'mdi:file-pdf',
  doc: 'mdi:file-word',
  docx: 'mdi:file-word',
  xls: 'mdi:file-excel',
  xlsx: 'mdi:file-excel',
  ppt: 'mdi:file-powerpoint',
  pptx: 'mdi:file-powerpoint',
  txt: 'mdi:file-document',
  default: 'mdi:file'
};

export default {
  setup() {
    // 示例数据
    const demandList = ref([
    {
      name: "用户登录功能",
      type: "功能测试",
      content: "作为一名用户，我希望通过输入邮箱和密码进行登录，这样可以访问我的个人账户。"
    },
    {
      name: "订单支付流程",
      type: "业务流程",
      content: "作为消费者，我希望在确认订单后可以选择多种支付方式（微信、支付宝、银行卡），以便完成交易。"
    },
    {
      name: "商品搜索优化",
      type: "性能优化",
      content: "作为用户，希望搜索响应时间在1秒内，并支持模糊搜索和自动补全功能。"
    },
    {
      name: "数据可视化报表",
      type: "数据分析",
      content: "作为运营人员，需要生成每日销售数据的可视化图表，支持导出PDF和Excel格式。"
    }
  ]);

    const uploadRef = ref(null);
    const demandText = ref('');
    const file = ref(null);
    const isAnalyzing = ref(false);
    const messages = ref([]);
    const socket = ref(null);

    const showFeedback = ref(false);
    const feedbackText = ref('');
    // 原有状态保持
    const fileList = ref([]);
    const uploadProgress = ref({});

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
            isAnalyzing.value = false;
          }

          // 新增需求列表处理（假设后端返回结构）
        if (data.demands) {
          demandList.value = data.demands.map(d => ({
            name: d.name,
            content: d.content
          }));
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

    // 文件处理方法
    const getFileIcon = (fileName) => {
      const extension = fileName.split('.').pop().toLowerCase();
      return FILE_ICONS[extension] || FILE_ICONS.default;
    };

    const formatFileSize = (bytes) => {
      if (bytes === 0) return '0 B';
      const k = 1024;
      const sizes = ['B', 'KB', 'MB', 'GB'];
      const i = Math.floor(Math.log(bytes) / Math.log(k));
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    };

    const beforeUpload = ({ file }) => {
      const MAX_SIZE = 10 * 1024 * 1024; // 10MB
      if (file.file.size > MAX_SIZE) {
        window.$message?.error(`${file.name} 超过大小限制（10MB）`);
        return false;
      }
      return true;
    };

    const handleFileChange = ({ fileList: files }) => {
      if (fileList.value.length >= 5) {
        window.$message?.warning('最多只能上传5个文件');
        return;
      }
      const newFiles = files.filter(f => f.status === 'pending');
      // 合并并更新文件列表
      fileList.value = [
        ...fileList.value,
        ...newFiles.map(f => ({
          id: f.id,
          name: f.name,
          size: f.file?.size || 0,
          type: f.file?.type,
          raw: f.file
        }))
      ];
      // 重置上传组件状态
      if (uploadRef.value) {
        uploadRef.value.clear();  // 清除组件内部状态
      }
    }
    const removeFile = (index) => {
      fileList.value.splice(index, 1);
    };

    const clearFiles = () => {
      fileList.value = [];
    };

    // 提交方法
    const submitDemand = async () => {
      if (!demandText.value.trim() && fileList.value.length === 0) {
        window.$message?.warning('请输入需求或上传文件');
        return;
      }

      try {
        isAnalyzing.value = true;

        if (fileList.value.length > 0) {
          const formData = new FormData();
          fileList.value.forEach((f, index) => {
          if (f.raw) {
            formData.append(`files[${index}]`, f.raw);
          }
          });

          const result = await request.post('/upload/', formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
            onUploadProgress: (progressEvent) => {
              const percent = Math.round(
                (progressEvent.loaded * 100) / progressEvent.total
              );
              uploadProgress.value[file.id] = percent;
            }
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
          file: "C:\\Users\\86134\\Desktop\\workspace\\AI\\agent_system_ui\\app\\api\\v1\\agent\\examples\\api_doc.pdf",
          user_id: 1,
          source: "user"
        }));
      } catch (error) {
        console.error('提交失败:', error);
        window.$message?.error('分析请求失败');
        isAnalyzing.value = false;
      }
    };
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
      // 添加容错处理
      try {
        outputEl.scrollTop = outputEl.scrollHeight + 100; // 额外滚动余量
        // 添加边界检测
        const isNearBottom =
          outputEl.scrollHeight - outputEl.clientHeight <=
          outputEl.scrollTop + 100;

        if (isNearBottom) {
          outputEl.scrollTo({
            top: outputEl.scrollHeight,
            behavior: 'smooth'
          });
        }
      } catch (e) {
        console.error('滚动异常:', e);
      }
    }
  });
    };
    const setupAutoScroll = () => {
    const outputEl = document.getElementById('output');
      if (outputEl) {
        // 添加手动滚动检测
        let userScrolled = false;

        outputEl.addEventListener('scroll', () => {
          const threshold = 50;
          userScrolled =
            outputEl.scrollHeight - outputEl.clientHeight >
            outputEl.scrollTop + threshold;
        });

        // 添加自动滚动恢复
        watch(() => messages.value.length, () => {
          if (!userScrolled) {
            scrollToBottom();
          }
        });
      }
    };

    // 新增标签类型映射
    const getTagType = (type) => {
      const typeMap = {
        '功能测试': 'success',
        '业务流程': 'info',
        '性能优化': 'warning',
        '数据分析': 'error'
      };
      return typeMap[type] || 'default';
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
      setupAutoScroll();
    });

    onBeforeUnmount(() => {
      resizeObserver.disconnect();
    });

    return {
      demandList,
      getTagType,
      fileList,
      uploadProgress,
      getFileIcon,
      formatFileSize,
      removeFile,
      clearFiles,
      beforeUpload,
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

/* 新增样式 */
.demand-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.demand-name {
  font-weight: 500;
  font-size: 14px;
}

.type-tag {
  height: 20px;
  line-height: 18px;
  margin-left: 8px;
}

.demand-content {
  color: #666;
  font-size: 13px;
  line-height: 1.6;
  margin-top: 6px;
  padding-left: 4px;
  white-space: pre-wrap;
}

/* 调整列表项间距 */
.n-list-item {
  padding: 12px 16px !important;
  transition: background 0.2s;
}

.n-list-item:hover {
  background: #f8f9fa;
}

/* 滚动条样式 */
.demand-list::-webkit-scrollbar {
  width: 6px;
}

.demand-list::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 4px;
}

.demand-list::-webkit-scrollbar-thumb {
  background: #ddd;
  border-radius: 4px;
}

.demand-list::-webkit-scrollbar-thumb:hover {
  background: #ccc;
}

/* 添加高度填充块样式 */
.height-spacer {
  height: 100px;
  flex-shrink: 0;
}
/* 新增文件相关样式 */
.file-info {
  flex-grow: 1;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-right: 12px;
}

.file-tag {
  padding: 6px 12px;
  background: #f5f5f5;
  border-radius: 6px;
  transition: all 0.2s;
}

.file-tag:hover {
  background: #eee;
}

.file-icon {
  margin-right: 6px;
  vertical-align: middle;
}

.clear-all-btn {
  color: #666;
  margin-left: 8px;
}

.upload-wrapper {
  display: inline-block;
}

.upload-dragger {
  padding: 8px 16px;
  border: 2px dashed #e0e0e0;
  border-radius: 8px;
  transition: all 0.3s;
}

.upload-dragger:hover {
  border-color: #409eff;
  background: #f5faff;
}

.upload-btn {
  padding: 8px 16px;
}

.upload-tips {
  font-size: 12px;
  color: #999;
  margin-top: 4px;
}

/* 调整操作按钮组布局 */
.action-group {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 20px;
}

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

.content-wrapper {
  flex: 1;
  position: relative;
  margin-bottom: 20px;
}
/* 调整输出容器高度 */
.markdown-container {
  height: calc(100vh - 380px); /* 动态高度计算 */
  min-height: 300px;
  overflow-y: auto;
  padding-bottom: 40px; /* 底部留白 */
}

/* 修正输出容器定位 */
.markdown-container {
  flex-grow: 1;
  position: relative; /* 修复绝对定位问题 */
  z-index: 1; /* 确保在反馈层之上 */
}

/* 修改容器布局 */
.container {
  display: flex;
  flex-direction: row;
  gap: 24px;
  min-height: 100vh;
  padding: 20px;
}
.left-panel {
  flex: 1;
  min-width: 0; /* 防止内容溢出 */
  display: flex;
  flex-direction: column;
}

.right-panel {
  width: 450px;
  min-width: 320px;
  border-left: 1px solid #eee;
  padding-left: 24px;
  height: calc(100vh - 40px);
  display: flex;
  flex-direction: column;
}

.demand-list-container {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.list-title {
  margin: 0 0 16px 0;
  color: #ffffff;
  font-size: 16px;
  font-weight: 600;
}

.demand-list {
  flex: 1;
  overflow-y: auto;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.demand-content {
  color: #666;
  font-size: 13px;
  line-height: 1.6;
  word-break: break-word;
}

.empty-tips {
  padding: 24px;
  text-align: center;
}

/* 响应式适配 */
@media (max-width: 768px) {
  .container {
    flex-direction: column;
    padding-bottom: 100px;
  }

  .right-panel {
    width: 100%;
    min-width: auto;
    border-left: 0;
    padding-left: 0;
    border-top: 1px solid #eee;
    padding-top: 24px;
    height: auto;
  }

  .demand-list {
    max-height: 400px;
  }
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
  align-items: flex-start; /* 改为顶部对齐 */
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 20px;
  position: relative; /* 为拖拽区域提供定位上下文 */
}

.upload-wrapper {
  order: 1; /* 控制上传按钮顺序 */
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
  padding: 30px;
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
  padding: 30px;
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

/* 移动端适配 */
@media (max-width: 768px) {
  .container {
    padding-bottom: 100px;
  }

  .markdown-container {
    height: calc(100vh - 320px);
    padding-bottom: 20px;
  }

  .feedback-area {
    width: calc(100% - 40px);
    right: 20px;
    left: auto;
  }
}

</style>