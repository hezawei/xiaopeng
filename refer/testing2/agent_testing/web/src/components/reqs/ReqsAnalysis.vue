<template>
  <div class="container">
    <!-- 左侧主内容区 -->
    <div class="left-panel">
      <!-- 输入区域 -->
      <n-input
        v-model:value="demandText"
        type="textarea"
        placeholder="请输入需求分析描述..."
        :autosize="{ minRows: 2, maxRows: 10 }"
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
            :type="file.status === 'success' ? 'success' : 'warning'"
            @close="removeFile(index)"
            class="file-tag"
            :disabled="isAnalyzing"
          >
            <TheIcon :icon="getFileIcon(file.name)" class="file-icon" />
            {{ file.name }}
            <template #icon v-if="file.status !== 'success'">
              <n-spin size="small" />
            </template>

            <n-progress
              v-if="file.status === 'uploading'"
              type="line"
              :percentage="file.progress"
              :show-indicator="false"
              height="2px"
              class="upload-progress"
            />
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
            :disabled="isAnalyzing"
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
          v-if="messages.length > 0 || isAnalyzing"
          id="output"
          class="markdown-container"
          :class="{ 'has-content': messages.length || isAnalyzing }"
        >
          <div v-if="messages.length > 0">
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
              
              <!-- 内联反馈区域 -->
              <div v-if="msg.showFeedback" class="inline-feedback">
                <n-input
                  v-model:value="msg.feedbackContent"
                  type="textarea"
                  placeholder="请输入您的反馈..."
                  :rows="2"
                  class="feedback-input"
                />
                <div class="feedback-actions mt-2">
                  <n-button size="small" type="primary" @click="sendFeedback(index)">发送</n-button>
                  <n-button size="small" type="success" @click="approveResponse(index)" class="ml-2">同意</n-button>
                  <n-button size="small" @click="closeFeedback(index)" class="ml-2">取消</n-button>
                </div>
              </div>
            </div>
          </div>
          <!-- 加载状态 -->
          <div v-if="isAnalyzing" class="loading-indicator">
            <n-spin size="small" />
            <span>AI需求分析进行中...</span>
          </div>
        </div>
      </div>

      <div class="height-spacer"></div>
    </div>

    <!-- 右侧需求列表 -->
    <div class="right-panel">
      <div class="demand-list-container">
        <h3 class="list-title">AI分析需求列表</h3>
        <div class="demand-list-wrapper">
          <n-list bordered class="demand-list">
            <n-list-item v-for="(item, index) in requirementsList" :key="index">
              <n-thing>
                <template #header>
                  <div class="demand-header">
                    <span class="demand-name">{{ item.name }}</span>
                    <n-tag :type="getTagType(item.category)" size="small" class="type-tag">
                      {{ item.category }}
                    </n-tag>
                  </div>
                </template>
                <template #description>
                  <div class="demand-content">{{ item.description }}</div>
                  <div class="created-time" v-if="item.created_at">
                    {{ formatDate(item.created_at) }}
                  </div>
                </template>
              </n-thing>
            </n-list-item>
            <n-list-item v-if="requirementsList.length === 0">
              <n-empty description="暂无分析结果" class="empty-tips"></n-empty>
            </n-list-item>
          </n-list>
        </div>
        <!-- 分页控件 -->
        <div v-if="totalPages > 1" class="pagination-controls">
          <n-button
            size="small"
            @click="handlePageChange(currentPage - 1)"
            :disabled="currentPage === 1"
            class="page-btn"
          >
            上一页
          </n-button>
          <span class="page-indicator">第 {{ currentPage }} 页 / 共 {{ totalPages }} 页</span>
          <n-button
            size="small"
            @click="handlePageChange(currentPage + 1)"
            :disabled="currentPage >= totalPages"
            class="page-btn"
          >
            下一页
          </n-button>
        </div>
      </div>
    </div>

  </div>
</template>

<script>
import { request } from '@/utils';
import { ref, onBeforeUnmount, onMounted, computed } from 'vue';
import { marked } from 'marked';
import DOMPurify from 'dompurify';
import hljs from 'highlight.js';
import { nextTick, watch } from 'vue';
import api from '@/api'
import TheIcon from '@/components/icon/TheIcon.vue'
import { useRoute, useRouter } from 'vue-router'

// 配置Markdown解析器
marked.setOptions({
  highlight: (code, lang) => {
    const language = hljs.getLanguage(lang) ? lang : 'plaintext';
    try {
      return hljs.highlight(code, { language }).value;
    } catch (e) {
      return hljs.highlightAuto(code).value;
    }
  },
  breaks: true,
  gfm: true,
  pedantic: false,
  smartLists: true,
  smartypants: true
});

// 创建Markdown解析函数
const cachedMarkdown = new Map();

const parseMarkdown = (raw) => {
  if (cachedMarkdown.has(raw)) {
    return cachedMarkdown.get(raw);
  }

  const clean = DOMPurify.sanitize(marked.parse(raw), {
    ADD_TAGS: ['iframe'],
    ADD_ATTR: ['allow', 'allowfullscreen', 'frameborder', 'scrolling']
  });

  cachedMarkdown.set(raw, clean);
  return clean;
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
const FILE_FIELD_MAP = {
  path: ['path', 'filePath', 'uri', 'location'],
  id: ['serverId', 'fileId', 'id', 'docId']
};
export default {
  components: { TheIcon },
  setup() {
    // 添加路由相关
    const route = useRoute()
    const router = useRouter()
    
    // 添加导航状态标记
    const isNavigatingAway = ref(false)
    
    // 示例数据，category："功能", "性能", "安全", "接口", "体验", "改进", "其它"
    const requirementsList = ref([
    {
      name: "用户登录功能",
      category: "功能",
      description: "作为一名用户，我希望通过输入邮箱和密码进行登录，这样可以访问我的个人账户。"
    },
    {
      name: "订单支付流程",
      category: "接口",
      description: "作为消费者，我希望在确认订单后可以选择多种支付方式（微信、支付宝、银行卡），以便完成交易。"
    },
    {
      name: "商品搜索优化",
      category: "性能",
      description: "作为用户，希望搜索响应时间在1秒内，并支持模糊搜索和自动补全功能。"
    },
    {
      name: "数据可视化报表",
      category: "改进",
      description: "作为运营人员，需要生成每日销售数据的可视化图表，支持导出PDF和Excel格式。"
    }
  ]);
    const currentPage = ref(1);
    const pageSize = ref(10);
    const totalDemands = ref(0);
    const totalPages = computed(() => Math.ceil(totalDemands.value / pageSize.value));

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
    const limit = ref(100);
    const formatDate = (timestamp) => {
      if (!timestamp) return '';
      const date = new Date(timestamp);
      return date.toLocaleDateString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      });
    };

    // 添加获取需求列表方法
    const fetchRequirementsList = async (page = 1) => {
      try {
        const response = await api.getRequirementsList({
          params: {
            page: page,
            page_size: pageSize.value,
            limit: limit.value,
            project_id: 2
          }
        });

        // 确保响应数据的正确处理
        if (response && response.data) {
          requirementsList.value = Array.isArray(response.data) ? response.data : [];
          totalDemands.value = response.total || requirementsList.value.length;
          currentPage.value = page;
        }

        console.log('分页信息:', {
          currentPage: currentPage.value,
          totalPages: totalPages.value,
          totalDemands: totalDemands.value
        });

      } catch (error) {
        console.error('获取需求列表失败:', error);
        window.$message?.error('获取需求列表失败');
        requirementsList.value = [];
        totalDemands.value = 0;
      }
    };
    // 修改分页处理方法
    const handlePageChange = (newPage) => {
      if (newPage < 1 || newPage > totalPages.value) return;
      currentPage.value = newPage;
      fetchRequirementsList(newPage);
    };
    // 添加监听器，确保数据变化时更新分页
    watch([requirementsList], () => {
      if (requirementsList.value.length > 0 && totalDemands.value === 0) {
        totalDemands.value = requirementsList.value.length;
      }
    });
        // WebSocket生命周期管理
    const initWebSocket = () => {
      // 确保在创建新连接前关闭旧连接
      closeWebSocket()

      try {
        console.log('初始化WebSocket连接...')
        socket.value = new WebSocket(import.meta.env.VITE_WS_BASE_API + `/api/v1/agent/ws/analyze`)
        
        // 设置连接超时
        const connectionTimeout = setTimeout(() => {
          if (socket.value && socket.value.readyState !== WebSocket.OPEN) {
            console.error('WebSocket连接超时')
            window.$message?.error('连接超时，请重试')
            isAnalyzing.value = false
          }
        }, 5000)
        
        // 连接打开时
        socket.value.onopen = () => {
          clearTimeout(connectionTimeout)
          console.log('WebSocket连接已建立')
        }

        socket.value.onmessage = (event) => {
          // 如果正在导航离开，不处理新消息
          if (isNavigatingAway.value) {
            console.log('正在导航离开，忽略新消息')
            return
          }
          
          try {
            const data = JSON.parse(event.data);
            
            // 检查是否是用户反馈请求
            if (data.source === 'user_proxy') {
              messages.value.push({
                source: data.source,
                content: parseMarkdown(data.content || '需要您的反馈'),
                rawContent: data.content || '需要您的反馈',
                timestamp: new Date().toISOString(),
                showFeedback: true,
                feedbackContent: ''
              });
              
              // 滚动到底部显示反馈区域
              nextTick(() => {
                scrollToBottom(true);
                highlightCodeBlocks();
              });
            } else if (data.source === 'database' && !data.is_final) {
              // 直接从database消息中获取需求列表，类似测试用例页面的处理方式
              try {
                const requirementsData = JSON.parse(data.content);
                if (requirementsData && requirementsData.requirements) {
                  // 更新需求列表
                  requirementsList.value = requirementsData.requirements;
                  totalDemands.value = requirementsData.requirements.length;
                  currentPage.value = 1;
                  console.log('从WebSocket更新需求列表', requirementsList.value);
                }
              } catch (parseError) {
                console.error('解析需求列表数据失败:', parseError);
              }
            } else {
              // 实现流式效果处理逻辑
              const lastMessage = messages.value.length > 0 ? messages.value[messages.value.length - 1] : null;
              
              // 如果存在最后一条消息且来源相同且不是最终消息，则更新该消息内容
              if (lastMessage && lastMessage.source === data.source && !data.is_final && !lastMessage.showFeedback) {
                // 更新现有消息的内容而不是添加新消息
                lastMessage.rawContent += data.content;
                // 重新解析完整的Markdown内容，保证表格、列表等复杂元素正确渲染
                lastMessage.content = parseMarkdown(lastMessage.rawContent);
                
                // 添加一个微小延迟以确保DOM更新后再应用高亮
                setTimeout(() => {
                  highlightCodeBlocks();
                }, 50);
              } else {
                // 否则添加新消息
                messages.value.push({
                  source: data.source,
                  content: parseMarkdown(data.content),
                  rawContent: data.content,
                  timestamp: new Date().toISOString()
                });
                
                // 为新消息应用代码高亮
                nextTick(() => {
                  highlightCodeBlocks();
                });
              }
            }
            
            // 检测分析结束标记
            if (data.is_final) {
              isAnalyzing.value = false;
              
              // 不再需要调用fetchRequirementsList，因为我们直接使用了WebSocket返回的需求列表
              // 只需处理状态变更
              console.log('需求分析完成');
            }

          } catch (error) {
            console.error('消息解析失败:', error);
            if (!isNavigatingAway.value) {
              window.$message?.error('消息解析失败');
            }
          }
          
          // 自动滚动到底部
          nextTick(() => {
            scrollToBottom();
          });
        };

        // 发生错误时
        socket.value.onerror = (error) => {
          clearTimeout(connectionTimeout)
          console.error('WebSocket错误:', error);
          if (!isNavigatingAway.value) {
            window.$message?.error('连接失败，请重试');
          }
          isAnalyzing.value = false;
        };

        // 连接关闭时
        socket.value.onclose = (event) => {
          clearTimeout(connectionTimeout)
          console.log('WebSocket连接已关闭', event);
          
          // 只有在非导航离开且非正常关闭时才显示错误
          if (!isNavigatingAway.value && !event.wasClean) {
            window.$message?.error('连接已断开，请重试');
          }
          isAnalyzing.value = false;
        };
      } catch (error) {
        console.error('WebSocket初始化失败:', error);
        if (!isNavigatingAway.value) {
          window.$message?.error('连接初始化失败，请重试');
        }
        isAnalyzing.value = false;
      }
    };

    // 增加WebSocket关闭函数
    const closeWebSocket = () => {
      if (!socket.value) return;
      
      console.log('正在关闭WebSocket连接...', socket.value?.readyState);
      try {
        // 先解除所有事件监听器，防止错误事件触发
        if (socket.value) {
          socket.value.onopen = null;
          socket.value.onmessage = null;
          socket.value.onerror = null;
          socket.value.onclose = null;
          
          // 如果连接仍处于打开状态，先发送关闭信号
          if (socket.value.readyState === WebSocket.OPEN) {
            try {
              socket.value.send(JSON.stringify({
                source: 'client',
                content: 'CLIENT_DISCONNECTING'
              }));
            } catch (e) {
              console.warn('发送关闭信号失败:', e);
            }
            
            // 设置关闭超时，避免无限等待
            const closeTimeout = setTimeout(() => {
              console.warn('WebSocket关闭超时，强制清理');
              socket.value = null;
            }, 1000);
            
            // 正常关闭连接
            socket.value.close(1000, '用户离开页面');
            
            // 关闭成功后清除超时
            socket.value.onclose = () => {
              clearTimeout(closeTimeout);
              console.log('WebSocket连接已正常关闭');
              socket.value = null;
            };
          } else if (socket.value.readyState === WebSocket.CONNECTING) {
            // 如果还在连接中，直接关闭
            socket.value.close(1000, '连接被中止');
            socket.value = null;
          } else {
            // 其他状态直接置空
            socket.value = null;
          }
        }
      } catch (e) {
        console.error('关闭WebSocket出错:', e);
        socket.value = null; // 确保无论如何都重置socket引用
      }
    };

    // 添加资源清理函数
    const cleanupResources = () => {
      console.log('执行资源清理');
      
      // 关闭WebSocket连接
      closeWebSocket();
      
      // 移除全局事件监听器
      window.removeEventListener('resize', handleWindowResize);
      window.removeEventListener('beforeunload', handlePageUnload);
      
      // 移除ResizeObserver
      if (resizeObserver) {
        resizeObserver.disconnect();
      }
    };
    
    // 窗口大小变化处理函数
    const handleWindowResize = () => {
      if (!isNavigatingAway.value) {
        scrollToBottom();
      }
    };
    
    // 页面卸载处理函数
    const handlePageUnload = (event) => {
      console.log('页面即将卸载');
      isNavigatingAway.value = true;
      closeWebSocket();
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

    // 优化后的beforeUpload验证
    const beforeUpload = ({ file }) => {
      const MAX_SIZE = 10 * 1024 * 1024
      const ALLOWED_TYPES = [
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'text/plain'
      ]

      if (file.file.size > MAX_SIZE) {
        window.$message?.error(`${file.name} 超过大小限制（10MB）`)
        return false
      }

      if (!ALLOWED_TYPES.includes(file.file.type)) {
        window.$message?.error(`${file.name} 不支持的文件类型`)
        return false
      }

      return true
    }

    const handleFileChange = async ({ fileList: newFileList }) => {
  try {
    const updatedList = [...newFileList].slice(0, 5)
    fileList.value = updatedList

    const pendingFiles = updatedList.filter(f =>
      f.status === 'pending' ||
      (f.status === 'success' && !f.path)
    )

    // 使用Promise.allSettled处理所有上传
    const results = await Promise.allSettled(
      pendingFiles.map(fileInfo => uploadSingleFile(fileInfo))
    )

    // 处理上传结果
    results.forEach((result, index) => {
      if (result.status === 'rejected') {
        const fileName = pendingFiles[index].name
        window.$message?.error(`文件 ${fileName} 上传失败: ${result.reason.message}`)
        removeFailedFile(pendingFiles[index].id)
      }
    })

  } catch (error) {
    console.error('上传处理异常:', error)
  }
}

    // 单个文件上传逻辑
    const uploadSingleFile = async (fileInfo) => {
      try {
        const targetIndex = fileList.value.findIndex(f => f.id === fileInfo.id)
        if (targetIndex === -1) return

        // 更新为上传中状态
        fileList.value.splice(targetIndex, 1, {
          ...fileInfo,
          status: 'uploading',
          progress: 0
        })

        // 带进度回调的上传
        const res = await api.uploadFile(1, fileInfo.file, (progressEvent) => {
          const progress = Math.round(
            (progressEvent.loaded / progressEvent.total) * 100
          )
          const currentIndex = fileList.value.findIndex(f => f.id === fileInfo.id)
          if (currentIndex !== -1) {
            fileList.value.splice(currentIndex, 1, {
              ...fileList.value[currentIndex],
              progress
            })
          }
        })
        // 更新成功状态
        const successIndex = fileList.value.findIndex(f => f.id === fileInfo.id)
        if (successIndex === -1) return

        fileList.value.splice(successIndex, 1, {
          ...fileInfo,
          status: 'success',
          path: res.data.filePath,       // 文件存储路径
          serverId: res.data.fileId,     // 服务端返回的文件ID
          size: fileInfo.file.size,      // 文件大小
          mimeType: fileInfo.file.type,  // 文件类型
          uploadedAt: new Date().toISOString(),
          progress: 100,
          _rawResponse: res.data
        })

      } catch (error) {
        console.error('上传失败:', fileInfo.name, error)
        throw error
      }
    }

    // 移除失败文件
    const removeFailedFile = (fileId) => {
      const index = fileList.value.findIndex(f => f.id === fileId)
      if (index !== -1) {
        fileList.value.splice(index, 1)
      }
    }


    const removeFile = (index) => {
      fileList.value.splice(index, 1);
    };

    const clearFiles = () => {
      fileList.value = [];
    };

    // 添加文件验证函数
    const validateFiles = () => {
      // 检查是否存在未完成文件
      const pendingFiles = fileList.value.filter(
        f => ['uploading', 'pending'].includes(f.status)
      );
      if (pendingFiles.length > 0) {
        window.$message?.warning(`${pendingFiles.length}个文件仍在上传中`);
        return false;
      }

      // 验证成功文件完整性
      const validFiles = fileList.value.filter(f =>
        f.status === 'success' &&
        FILE_FIELD_MAP.id.some(k => f[k]) &&
        FILE_FIELD_MAP.path.some(k => f[k])
      );

      if (fileList.value.length > 0 && validFiles.length === 0) {
        window.$message?.error('所有文件上传无效');
        return false;
      }
      return true;
    };

    const submitDemand = async () => {
      try {
        // 防止重复提交
        if (isAnalyzing.value) return;
        
        // 1. 空输入检查
        if (!demandText.value.trim()) {
          window.$message?.warning('请输入需求分析描述', {
            duration: 3000
          });
          return;
        }
        if (fileList.value.length === 0) {
          window.$message?.warning('请上传需求文档', {
            duration: 3000
          });
          return;
        }

        isAnalyzing.value = true;
        messages.value = [];
        showFeedback.value = false;

        // 2. 文件状态验证
        if (!validateFiles()) {
          isAnalyzing.value = false;
          return;
        }

        // 准备请求数据
        const buildFilePayload = (file) => {
          const findField = (fields) => fields.reduce((acc, cur) => acc || file[cur], null);

          return {
            id: findField(FILE_FIELD_MAP.id),
            path: findField(FILE_FIELD_MAP.path),
            name: file.name,
            size: file.size,
            type: file.mimeType,
            uploaded_at: file.uploadedAt
          };
        };

        const requestData = {
          content: demandText.value.trim(),
          source: 'user',
          files: fileList.value.filter(f => f.status === 'success').map(buildFilePayload),
          userId: 1,
          timestamp: Date.now()
        };

        console.debug('[请求数据]', JSON.parse(JSON.stringify(requestData)));

        // WebSocket连接管理 - 更可靠的连接方法
        try {
          // 初始化WebSocket
          initWebSocket();
          
          // 等待连接建立，使用更可靠的方法
          let connectionEstablished = false;
          
          // 尝试多次建立连接
          for (let attempt = 0; attempt < 3; attempt++) {
            if (isNavigatingAway.value) break; // 如果正在离开页面，中止连接
            
            // 检查连接状态
            if (socket.value?.readyState === WebSocket.OPEN) {
              connectionEstablished = true;
              break;
            } else if (!socket.value || socket.value.readyState === WebSocket.CLOSED || socket.value.readyState === WebSocket.CLOSING) {
              // 如果连接已关闭或正在关闭，重新初始化
              console.log(`连接尝试 ${attempt + 1}: 重新初始化WebSocket`);
              initWebSocket();
            }
            
            // 等待连接建立
            await new Promise(resolve => setTimeout(resolve, 1000));
          }
          
          // 如果无法建立连接，抛出错误
          if (!connectionEstablished) {
            throw new Error('无法建立WebSocket连接');
          }
          
          // 发送数据
          socket.value.send(JSON.stringify(requestData));
          console.log('已发送需求分析请求');
          
        } catch (error) {
          console.error('[WS连接失败]-', error);
          window.$message?.error(`连接失败: ${error.message}`);
          isAnalyzing.value = false;
        }

      } catch (error) {
        console.error('[提交异常]', error);
        window.$message?.error(`处理失败: ${error.message}`);
        isAnalyzing.value = false;
      }
    };
    
    // 添加发送反馈方法
    const sendFeedback = (index) => {
      const feedbackContent = messages.value[index].feedbackContent?.trim();
      if (socket.value && socket.value.readyState === WebSocket.OPEN) {
        socket.value.send(JSON.stringify({
          source: 'feedback',
          content: feedbackContent || 'APPROVE'
        }));
      }
      
      // 隐藏反馈输入框
      messages.value[index].showFeedback = false;
    };
    
    // 添加同意方法
    const approveResponse = (index) => {
      if (socket.value && socket.value.readyState === WebSocket.OPEN) {
        socket.value.send(JSON.stringify({
          source: 'feedback',
          content: 'APPROVE'
        }));
      }
      
      // 隐藏反馈输入框
      messages.value[index].showFeedback = false;
    };
    
    // 添加取消反馈方法 
    const closeFeedback = (index) => {
      // 发送默认反馈
      if (socket.value && socket.value.readyState === WebSocket.OPEN) {
        socket.value.send(JSON.stringify({
          source: 'feedback',
          content: 'APPROVE'
        }));
      }
      
      // 隐藏反馈输入框
      messages.value[index].showFeedback = false;
    };
    
    // 添加路由守卫
    onMounted(() => {
      // 设置窗口事件监听
      window.addEventListener('resize', handleWindowResize);
      window.addEventListener('beforeunload', handlePageUnload);
      
      // 设置ResizeObserver
      const outputEl = document.getElementById('output');
      if (outputEl) {
        resizeObserver = new ResizeObserver(scrollToBottom);
        resizeObserver.observe(outputEl);
      }
      
      // 设置自动滚动
      setupAutoScroll();
      
      // 添加路由守卫
      router.beforeEach((to, from, next) => {
        // 如果要离开当前页面
        if (from.path.includes('/reqs') && !to.path.includes('/reqs')) {
          console.log('离开需求分析页面，关闭资源');
          isNavigatingAway.value = true;
          closeWebSocket();
          cleanupResources();
        }
        next();
      });
    });

    // 修改卸载钩子
    onBeforeUnmount(() => {
      console.log('组件即将卸载');
      isNavigatingAway.value = true;
      cleanupResources();
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

    // 更新标签类型映射
    const getTagType = (type) => {
      const typeMap = {
        '功能': 'success',
        '接口': 'info',
        '性能': 'warning',
        '安全': 'error',
        '体验': 'default',
        '改进': 'success',
        '其它': 'default'
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
    let resizeObserver = new ResizeObserver(scrollToBottom);
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

    // 添加一个新的函数来处理代码高亮
    const highlightCodeBlocks = () => {
      nextTick(() => {
        // 高亮代码块
        document.querySelectorAll('.markdown-content pre code').forEach(block => {
          if (!block.classList.contains('hljs')) {
            hljs.highlightElement(block);
          }
        });
        
        // 确保表格正确显示
        document.querySelectorAll('.markdown-content table').forEach(table => {
          if (!table.classList.contains('markdown-table')) {
            table.classList.add('markdown-table');
          }
        });
      });
    };

    // 修改现有的代码高亮watch
    watch(() => messages.value, () => {
      highlightCodeBlocks();
    }, { deep: true });

    return {
      requirementsList,
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
      submitFeedback,
      handlePageChange,
      currentPage,
      totalPages,
      formatDate,
      // 添加新方法到返回值
      sendFeedback,
      approveResponse,
      closeFeedback
    };
  }
};
</script>

<style scoped>
/* 添加创建时间样式 */
.created-time {
  font-size: 12px;
  color: #999;
  margin-top: 8px;
}
/* 新增分页按钮样式 */
.pagination-controls {
  position: sticky;  /* 改为sticky定位 */
  bottom: 0;
  left: 0;
  right: 0;
  background: #fff;
  padding: 12px 16px;
  border-top: 1px solid #f0f0f0;
  box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.05);
  z-index: 10;
  display: flex;
  justify-content: center;
  gap: 16px;
}

.page-btn {
  min-width: 80px;
  padding: 4px 12px;
  background: #f4f4f4;
  border: 1px solid #ddd;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.page-btn:hover {
  background: #e8e8e8;
}

.page-btn:disabled {
  background: #f9f9f9;
  color: #ccc;
  cursor: not-allowed;
}

.page-indicator {
  font-size: 13px;
  color: #666;
  line-height: 32px;
}

/* 调整列表容器高度 */
.demand-list-container {
  height: calc(100vh - 100px);
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
}

.demand-list-wrapper {
  flex: 1;
  overflow-y: auto;
  padding-bottom: 60px; /* 为分页控件留出空间 */
}

/* 调整需求列表样式 */
.demand-list {
  height: 100%;
  overflow-y: auto;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  margin-bottom: 0;
}

/* 优化空状态显示 */
.empty-tips {
  padding: 40px 0;
}
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
  padding: 5px;
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
  color: #333333;
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

  .demand-list-container {
    height: auto;
    min-height: 500px;
  }
  
  .pagination-controls {
    position: sticky;
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
  overflow-wrap: break-word;
}


.markdown-content h1,
.markdown-content h2,
.markdown-content h3 {
  margin: 1.5em 0 1em;
  font-weight: 600;
  border-bottom: 1px solid #eee;
  padding-bottom: 0.3em;
}

.markdown-content pre {
  background: #f6f8fa;
  border-radius: 8px;
  padding: 1em;
  margin: 1.2em 0;
  overflow-x: auto;
}

.markdown-content code {
  font-family: 'Fira Code', monospace;
  font-size: 0.9em;
  background: rgba(175, 184, 193, 0.2);
  padding: 0.2em 0.4em;
  border-radius: 4px;
}

.markdown-content blockquote {
  color: #6a737d;
  border-left: 4px solid #dfe2e5;
  margin: 1em 0;
  padding: 0 1em;
  background: #f8f9fa;
}

.markdown-content table {
  border-collapse: collapse;
  margin: 1.5em 0;
  width: 100%;
  max-width: 100%;
  overflow-x: auto;
  display: block;
}

.markdown-content table.markdown-table {
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  border-radius: 6px;
  border: 1px solid #eaeaea;
}

.markdown-content thead {
  background-color: #f6f8fa;
}

.markdown-content th {
  background-color: #f6f8fa;
  border-bottom: 2px solid #ddd;
  font-weight: 600;
}

.markdown-content td,
.markdown-content th {
  border: 1px solid #dfe2e5;
  padding: 0.6em 1em;
  text-align: left;
}

.markdown-content tr:nth-child(even) {
  background: #f8f8f8;
}

.markdown-content tr:hover {
  background-color: #f1f1f1;
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

/* 添加内联反馈样式 */
.inline-feedback {
  margin-top: 12px;
  padding: 12px;
  background: #f8f9fa;
  border-radius: 8px;
  border-left: 3px solid #2185d0;
}

.feedback-input {
  margin-bottom: 8px;
}

.feedback-actions {
  display: flex;
  gap: 8px;
}

.mt-2 {
  margin-top: 8px;
}

.ml-2 {
  margin-left: 8px;
}

</style>