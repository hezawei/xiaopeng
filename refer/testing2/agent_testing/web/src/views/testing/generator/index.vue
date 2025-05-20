<template>
    <div class="testcase-container flex h-full">
    <!-- 左侧需求列表区域 -->
    <div class="requirements-panel w-1/4 p-4 border-r border-[#e5e7eb]">
      <div class="search-area mb-4">
        <n-space vertical>
          <n-select
            v-model:value="searchParams.projectId"
            :options="projectList.map(p => ({ label: p.name, value: p.id }))"
            placeholder="请选择项目"
            clearable
            @update:value="handleProjectSelect"
          >
            <template #prefix>
              <n-icon><SearchOutline /></n-icon>
            </template>
          </n-select>
          <n-input
            v-model:value="searchParams.requirementName"
            placeholder="请输入需求名称"
            clearable
            @update:value="handleSearch"
          >
            <template #prefix>
              <n-icon><SearchOutline /></n-icon>
            </template>
          </n-input>
        </n-space>
      </div>

      <div class="requirements-list">
        <n-data-table
          :columns="requirementColumns"
          :data="requirementList"
          :row-key="row => row.id"
          :pagination="false"
          @update:checked-row-keys="handleRequirementSelect"
        />
      </div>
    </div>

    <!-- 右侧内容区域 -->
    <div class="content-panel flex-1 p-4">
      <!-- 上方需求详情区域 - 改为可折叠区域 -->
      <n-collapse :default-expanded-names="['requirement-details']">
        <n-collapse-item name="requirement-details" title="需求详情">
      <div class="content-wrapper pl-2">
        <n-descriptions
          :column="2"
          :vertical="false"
          bordered
          label-placement="left"
          label-align="right"
          content-style="justify-content: start"
          size="small"
        >
          <n-descriptions-item
            label="需求名称："
            :span="2"
            label-style="width: 100px; text-align: left"
          >
            <span class="font-medium">
              {{ selectedRequirement?.name || '未选择需求' }}
            </span>
                <n-tag
                  v-if="selectedRequirement?.category"
                  :bordered="false"
                  type="info"
                  size="small"
                  class="ml-2"
                >
                  {{ selectedRequirement.category }}
                </n-tag>
          </n-descriptions-item>
        </n-descriptions>

        <n-tabs class="mt-4" size="medium">
          <n-tab-pane name="description" tab="需求描述">
            <n-input
              v-model:value="selectedRequirement.description"
              type="textarea"
              :placeholder="selectedRequirement?.description ? '' : '暂无描述'"
                  :rows="2"
                  :autosize="{ minRows: 1, maxRows: 3 }"
              size="small"
                  class="description-input"
            />
          </n-tab-pane>
          <n-tab-pane name="scenario" tab="场景说明">
            <n-input
              v-model:value="scenario"
              type="textarea"
              placeholder="请输入场景说明"
                  :rows="3"
                  :autosize="{ minRows: 1, maxRows: 3 }"
              size="small"
                  class="scenario-input"
            />
          </n-tab-pane>
        </n-tabs>
      </div>
        </n-collapse-item>
      </n-collapse>

      <!-- 中间指令输入区域 -->
      <div class="command-input bg-white rounded-lg shadow-sm p-6 pl-6 mt-4">
        <div class="flex items-center gap-3">
          <n-input
            v-model:value="aiCommand"
            type="textarea"
            placeholder="请输入 AI 指令..."
            :rows="2"
            :autosize="{ minRows: 1, maxRows: 3 }"
            class="flex-1"
            size="small"
          />
          <n-button
            type="primary"
            :disabled="!selectedRequirement || isGenerating"
            :loading="isGenerating"
            @click="handleGenerateTestCase"
            class="h-[34px]"
          >
            <template #icon>
              <TheIcon icon="mdi:robot" :class="{ 'animate-spin': isGenerating }" />
            </template>
            {{ isGenerating ? '生成中...' : '生成测试用例' }}
          </n-button>
        </div>
      </div>
      <div class="output-container">
         <n-tabs v-model:value="activeTab" type="line">
          <n-tab-pane name="generation" tab="生成输出">
            <div class="output-display bg-white rounded-lg shadow-sm p-6 min-h-[400px]">
              <div
                v-if="messageBlocks.length > 0 || isGenerating"
                id="output"
                class="markdown-container"
                :class="{ 'has-content': messageBlocks.length || isGenerating }"
              >
                <div v-if="messageBlocks.length > 0">
                  <div
                    v-for="(msg, index) in messageBlocks"
                    :key="index"
                    class="message-item"
                    :class="[msg.source, {'streaming': msg.isStreaming}]"
                  >
                    <div class="source-tag">
                      <TheIcon
                        :icon="msg.source === 'user' ? 'mdi:account' : 'mdi:robot'"
                        :size="14"
                      />
                      {{ msg.source.toUpperCase() }}
              </div>
                    <div class="markdown-content" v-html="msg.content"></div>

                    <!-- 用户反馈区域 - 内嵌在消息中 -->
                    <div v-if="msg.source === 'user_proxy' && msg.showFeedback" class="feedback-container mt-4">
                      <n-input
                        v-model:value="msg.feedbackContent"
                        type="textarea"
                        placeholder="请输入您对AI助手的反馈..."
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
                <div v-if="isGenerating" class="loading-indicator">
                  <n-spin size="small" />
                  <span>AI测试用例生成中...</span>
  </div>
              </div>
            </div>
          </n-tab-pane>
        <n-tab-pane name="list" tab="用例列表">
          <div class="testcase-list bg-white rounded-lg shadow-sm p-6 min-h-[400px] flex">
            <!-- 左侧用例列表 -->
            <div class="case-list-panel flex-1 pr-4">
              <div class="case-list-wrapper overflow-y-auto">
              <n-collapse>
            <n-collapse-item
              v-for="testCase in testCaseList"
                    :key="testCase.title"
                  >
                    <template #header>
                      <div class="testcase-header">
                        <div class="testcase-title">{{ testCase.title }}</div>
                        <div class="testcase-meta">
                          <n-tag :type="getPriorityTagType(testCase.priority)" size="small">
                    {{ testCase.priority }}
                  </n-tag>
                          <n-tag :type="getStatusTagType(testCase.status)" size="small">
                    {{ testCase.status }}
                  </n-tag>
                          <span class="testcase-creator">{{ testCase.creator }}</span>
                        </div>
                      </div>
                    </template>

                    <div class="testcase-content">
                      <!-- 基本信息 -->
                      <div class="info-row">
                        <span class="info-label">用例描述：</span>
                        <span class="info-content">{{ testCase.desc }}</span>
                      </div>
                      <div class="info-row">
                        <span class="info-label">前置条件：</span>
                        <span class="info-content">{{ testCase.preconditions }}</span>
                      </div>
                      <div class="info-row">
                        <span class="info-label">后置条件：</span>
                        <span class="info-content">{{ testCase.postconditions }}</span>
                      </div>
                      <div class="info-row">
                        <span class="info-label">标签：</span>
                        <div class="tag-group">
                    <n-tag
                            v-for="tag in testCase.tags.split(',')"
                            :key="tag"
                            size="small"
                      :bordered="false"
                    >
                            {{ tag }}
                    </n-tag>
                        </div>
                      </div>

                      <!-- 测试步骤 -->
                      <div class="steps-container">
                        <div
                      v-for="(step, index) in testCase.steps"
                      :key="index"
                          class="step-item"
                    >
                          <div class="step-description">
                            <strong>步骤 {{ index + 1 }}：</strong>{{ step.description || step.step_desc }}
                        </div>
                          <div class="step-result">
                            预期结果：{{ step.expected_result }}
                          </div>
                        </div>
                      </div>
                    </div>
            </n-collapse-item>
          </n-collapse>
              </div>
            </div>

            </div>
          </n-tab-pane>
        <n-tab-pane name="mindmap" tab="思维导图">
          <div class="mindmap-container h-full" ref="mindmapRef"></div>
          </n-tab-pane>
        </n-tabs>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref, onActivated, onDeactivated, provide, inject } from 'vue'
import { SearchOutline } from '@vicons/ionicons5'
import api from '@/api'
import { useMessage } from 'naive-ui'
import * as echarts from 'echarts'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import hljs from 'highlight.js';
import { nextTick, watch, onBeforeUnmount, onUnmounted } from 'vue'
import TheIcon from '@/components/icon/TheIcon.vue'
import { useRoute, useRouter } from 'vue-router'

// 添加路由相关
const route = useRoute()
const router = useRouter()

// 创建一个全局标记，避免路由守卫重复处理
if (!window.__testGeneratorRouteInitialized) {
  window.__testGeneratorRouteInitialized = true
}

// 标记页面是否已挂载，用于防止重复初始化和清理
const pageIsMounted = ref(false)
// 添加一个变量跟踪是否正在导航离开页面
const isNavigatingAway = ref(false)

// 状态定义
const searchParams = reactive({
  projectId: null,
  projectName: '',
  requirementName: '',
  caseName: ''
})
const scenario = ref('')
const requirementList = ref([])
const selectedRequirement = ref({
  description: '',
  scenarioDescription: '',
  tags: []
})
const testCaseList = ref([])
const aiCommand = ref('开始生成测试用例')
const mindmapRef = ref(null)
let mindmapChart = null
const activeTab = ref('generation')

const message = useMessage()
const isGenerating = ref(false)
const messageBlocks = ref([])
let socket = null

// 添加自动滚动相关的变量
const autoScroll = ref(true)
let userScrolled = ref(false)
let scrollTimer = null

// 添加项目列表数据
const projectList = ref([])

// 需求列表列定义
const requirementColumns = [
  {
    type: 'selection'
  },
  {
    title: '需求名称',
    key: 'name',
    render: (row) => {
      return h(
        'div',
        {
          class: 'cursor-pointer hover:text-primary',
          onClick: () => handleRequirementClick(row)
        },
        row.name
      )
    }
  }
]

// Markdown解析配置 - 修改这里以优化JSON显示
marked.setOptions({
  highlight: (code, lang) => {
    // 处理JSON格式
    if (lang === 'json') {
      try {
        // 尝试格式化JSON
        const formattedJson = JSON.stringify(JSON.parse(code), null, 2);
        return hljs.highlight(formattedJson, { language: 'json' }).value;
      } catch (e) {
        // 如果解析失败，作为普通代码处理
        return hljs.highlight(code, { language: 'json' }).value;
      }
    }

    // 处理其他语言
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

// JSON格式化函数 - 添加新函数
const formatJsonString = (jsonString) => {
  try {
    const parsed = JSON.parse(jsonString);
    return JSON.stringify(parsed, null, 2);
    } catch (e) {
    return jsonString; // 如果不是有效的JSON，返回原始字符串
    }
};

// 解析Markdown - 修改以更好地处理JSON
const parseMarkdown = (raw) => {
  if (!raw) return '';

  // 检测是否包含JSON内容
  const hasJsonBlock = raw.includes('```json');
  let processedContent = raw;

  // 替换JSON代码块，添加特殊标记
  if (hasJsonBlock) {
    processedContent = raw.replace(/```json\s*([\s\S]*?)```/g, (match, jsonContent) => {
      try {
        const formattedJson = formatJsonString(jsonContent.trim());
        // 使用具有唯一ID的wrapper，避免选择器问题
        const wrapperID = `json-wrapper-${Date.now()}-${Math.floor(Math.random() * 10000)}`;
        return `<div class="json-wrapper" id="${wrapperID}">
          <div class="json-header">
            <span class="json-title">JSON</span>
            <button class="json-toggle" data-wrapper="${wrapperID}" title="展开/折叠">
              <span class="toggle-icon">▼</span>
            </button>
          </div>
          <pre class="language-json"><code>${formattedJson}</code></pre>
        </div>`;
      } catch (e) {
        return match; // 保持原样
      }
    });
  }

  const result = DOMPurify.sanitize(marked.parse(processedContent));

  // 如果包含JSON代码块，下一个tick时设置交互
  if (hasJsonBlock) {
    nextTick(() => {
      setupJsonInteractions();
    });
  }

  return result;
};

// 添加JSON代码块交互处理
const setupJsonInteractions = () => {
    nextTick(() => {
    // 使用document.body查询，确保可以找到元素，即使在scoped CSS中
    document.querySelectorAll('.json-toggle').forEach(button => {
      if (!button.hasJsonListener) {
        button.hasJsonListener = true;
        button.addEventListener('click', function() {
          // 使用data属性查找对应的wrapper
          const wrapperId = this.getAttribute('data-wrapper');
          const wrapper = document.getElementById(wrapperId);
          if (!wrapper) return;

          const codeBlock = wrapper.querySelector('pre');
          const icon = this.querySelector('.toggle-icon');

          if (codeBlock.classList.contains('collapsed')) {
            codeBlock.classList.remove('collapsed');
            icon.textContent = '▼';
          } else {
            codeBlock.classList.add('collapsed');
            icon.textContent = '▶';
          }
        });
      }
    });
  });
};

  const highlightCodeBlocks = () => {
  nextTick(() => {
  document.querySelectorAll('.markdown-content pre code').forEach(block => {
    if (!block.classList.contains('hljs')) {
      hljs.highlightElement(block);
    }
  });

    // 设置JSON交互功能
    setupJsonInteractions();
  });
};

// 方法定义
const handleSearch = async () => {
  try {
    const params = {
      project_id: searchParams.projectId,
      requirement_name: searchParams.requirementName
    }
    const { data } = await api.getRequirementsList(params)
    requirementList.value = data
  } catch (error) {
    message.error('获取需求列表失败')
  }
}

const handleRequirementSelect = (keys, rows) => {
  if (rows.length > 0) {
    selectedRequirement.value = {
      ...rows[rows.length - 1],
      scenarioDescription: rows[rows.length - 1].scenarioDescription || '' // 确保字段存在
    }
    // loadTestCases()
  } else {
    selectedRequirement.value = null
    testCaseList.value = []
  }
}

const handleRequirementClick = (row) => {
  selectedRequirement.value = row
  // loadTestCases()
}
const loadTestCases = async () => {
  if (!selectedRequirement.value) return

  try {
    const params = {
      requirement_id: selectedRequirement.value.id,
      project_id: 2
    }
    const { data } = await api.getTestCases(params)
    testCaseList.value = data
    renderMindmap()
  } catch (error) {
    message.error('获取测试用例失败')
  }
}

const handleGenerateTestCase = async () => {
  // 检查是否选择了需求
  if (!selectedRequirement.value || !selectedRequirement.value.id) {
    message.warning('请先在左侧选择一条需求')
    return
  }

  // 检查AI指令是否为空
  if (!aiCommand.value || aiCommand.value.trim() === '') {
    message.warning('请输入 AI 指令')
    return
  }

  // 检查是否正在生成中
  if (isGenerating.value) {
    return
  }

  try {
    // 设置生成中状态
    isGenerating.value = true
    messageBlocks.value = []

    // 初始化WebSocket连接
    initWebSocket()

    // 准备请求数据
    const requestData = {
      ...selectedRequirement.value,
      scenario: scenario.value,
      task: aiCommand.value,
    }

    // 等待连接建立，使用更可靠的方法
    let connectionEstablished = false

    // 尝试多次建立连接
    for (let attempt = 0; attempt < 3; attempt++) {
      if (isNavigatingAway.value) break // 如果正在离开页面，中止连接

      // 检查连接状态
      if (socket?.readyState === WebSocket.OPEN) {
        connectionEstablished = true
        break
      } else if (!socket || socket.readyState === WebSocket.CLOSED || socket.readyState === WebSocket.CLOSING) {
        // 如果连接已关闭或正在关闭，重新初始化
        console.log(`连接尝试 ${attempt + 1}: 重新初始化WebSocket`)
        initWebSocket()
    }

    // 等待连接建立
      await new Promise(resolve => setTimeout(resolve, 1000))
    }

    // 如果无法建立连接，抛出错误
    if (!connectionEstablished) {
      throw new Error('无法建立WebSocket连接')
    }

    // 发送数据
    socket.send(JSON.stringify(requestData))
    console.log('已发送测试用例生成请求')

  } catch (error) {
    console.error('生成失败:', error)
    message.error('生成失败: ' + error.message)
    handleGenerationError()
  }
}

// 工具方法
const getPriorityTagType = (priority) => {
  const types = {
    '高': 'error',
    '中': 'warning',
    '低': 'info'
  }
  return types[priority] || 'default'
}

const getStatusTagType = (status) => {
  const types = {
    '未开始': 'default',
    '进行中': 'info',
    '已完成': 'success',
    '已废弃': 'error'
  }
  return types[status] || 'default'
}

// 思维导图渲染
const renderMindmap = () => {
  if (!mindmapRef.value) return

  // 确保有测试用例数据
  if (!testCaseList.value || testCaseList.value.length === 0) {
    if (mindmapChart) {
      mindmapChart.dispose()
      mindmapChart = null
    }
    return
  }

  // 等待DOM更新完成
  nextTick(() => {
    // 如果不在思维导图标签页，先切换到思维导图标签
    if (activeTab.value !== 'mindmap') {
      // 先不切换，只在用户手动切换时渲染
      // 这里可以设置一个标记，表示数据已准备好
      return;
    }

    // 检查容器是否可见
    if (mindmapRef.value.offsetParent === null) return

    // 如果图表已存在，先销毁
    if (mindmapChart) {
      mindmapChart.dispose()
      mindmapChart = null
    }

    // 短暂延迟确保DOM已完全更新
    setTimeout(() => {
      // 初始化图表
      try {
        mindmapChart = echarts.init(mindmapRef.value)

        const data = {
          name: selectedRequirement.value?.name || '需求',
          children: testCaseList.value.map(testCase => ({
            name: testCase.title,
            children: (testCase.steps || []).map(step => ({
              name: step.description || step.step_desc
            }))
          }))
        }

        const option = {
          series: [
            {
              type: 'tree',
              data: [data],
              top: '5%',
              left: '5%',
              bottom: '5%',
              right: '15%',
              symbolSize: 7,
              initialTreeDepth: -1,
              layout: 'force',
              orient: 'LR',
              label: {
                position: 'left',
                verticalAlign: 'middle',
                align: 'right',
                fontSize: 12,
                distance: 8
              },
              leaves: {
                label: {
                  position: 'right',
                  verticalAlign: 'middle',
                  align: 'left'
                }
              },
              emphasis: {
                focus: 'descendant'
              },
              expandAndCollapse: true,
              animationDuration: 550,
              animationDurationUpdate: 750,
              roam: true,
              draggable: true,
              nodeDraggable: true,
              edgeDraggable: true,
              force: {
                layoutAnimation: true,
                repulsion: 1000,
                gravity: 0.1,
                edgeLength: 100,
                friction: 0.6
              },
              lineStyle: {
                width: 2,
                curveness: 0.3
              },
              itemStyle: {
                borderWidth: 2,
                borderColor: '#fff',
                shadowColor: 'rgba(0, 0, 0, 0.1)',
                shadowBlur: 10
              }
            }
          ],
          tooltip: {
            trigger: 'item',
            triggerOn: 'mousemove'
          }
        }

        mindmapChart.setOption(option)

        // 添加拖拽事件监听
        mindmapChart.on('mousedown', function(params) {
          if (params.dataType === 'node') {
            mindmapChart.setOption({
              series: [{
                data: [data],
                draggable: true,
                nodeDraggable: true,
                force: {
                  layoutAnimation: true,
                  friction: 0.1
                }
              }]
            })
          }
        })

        mindmapChart.on('mouseup', function() {
          mindmapChart.setOption({
            series: [{
              data: [data],
              force: {
                layoutAnimation: false,
                friction: 0.6
              }
            }]
          })
        })

        // 添加resize监听
        const resizeObserver = new ResizeObserver(() => {
          if (mindmapChart && mindmapRef.value.offsetParent !== null) {
            mindmapChart.resize()
          }
        })
        resizeObserver.observe(mindmapRef.value)
      } catch (error) {
        console.error('渲染思维导图失败:', error)
      }
    }, 300)
  })
}

// 添加标签页切换监听
watch(() => activeTab.value, (newValue) => {
  if (newValue === 'mindmap' && testCaseList.value && testCaseList.value.length > 0) {
    // 切换到思维导图标签页时重新渲染
    nextTick(() => {
      renderMindmap();
    });
  }
});

// WebSocket初始化方法 - 完全重构
const initWebSocket = () => {
  // 确保在创建新连接前关闭现有连接
  closeWebSocket()

  try {
    console.log('初始化WebSocket连接...')
    // 创建新的WebSocket连接
    socket = new WebSocket(import.meta.env.VITE_WS_BASE_API + '/api/v1/agent/ws/generate')
    console.log('创建WebSocket URL:', import.meta.env.VITE_WS_BASE_API + '/api/v1/agent/ws/generate')
    // 设置连接超时
    const connectionTimeout = setTimeout(() => {
      if (socket && socket.readyState !== WebSocket.OPEN) {
        console.error('WebSocket连接超时')
        message.error('连接超时，请重试')
        handleGenerationError()
      }
    }, 5000)

    // 连接打开时
    socket.onopen = () => {
      clearTimeout(connectionTimeout)
      console.log('WebSocket连接已建立')
    }

    // 接收消息时
    socket.onmessage = (event) => {
      // 如果正在导航离开，不处理新消息
      if (isNavigatingAway.value) {
        console.log('正在导航离开，忽略新消息')
        return
      }

      try {
        const data = JSON.parse(event.data);

        // 处理数据库返回的测试用例数据
        if (data.source === 'database') {
          try {
            console.log('数据库返回的测试用例数据:', data.content)
            const parsedContent = JSON.parse(data.content);
            console.log('解析后的测试用例数据:', parsedContent.testcases);
            testCaseList.value = Array.isArray(parsedContent.testcases) ? parsedContent.testcases : [];
            // 自动切换到用例列表标签页
            activeTab.value = 'list';
            // 渲染思维导图
            nextTick(() => {
              renderMindmap();
            });
          } catch (error) {
            console.error('测试用例数据解析失败:', error);
          }
        }
        // 处理用户反馈请求
        else if (data.source === 'user_proxy') {
          // 先隐藏所有已有的反馈区域，避免出现多个反馈框
          if (messageBlocks.value.length > 0) {
            const updatedMessages = [...messageBlocks.value];
            for (let i = 0; i < updatedMessages.length; i++) {
              if (updatedMessages[i].showFeedback) {
                updatedMessages[i] = {
                  ...updatedMessages[i],
                  showFeedback: false
                };
              }
            }
            messageBlocks.value = updatedMessages;
          }

          // 添加消息到消息列表，并设置显示反馈属性
          messageBlocks.value.push({
            source: data.source,
            content: parseMarkdown(data.content || '需要您的反馈'),
            rawContent: data.content || '需要您的反馈',
            timestamp: new Date().toISOString(),
            showFeedback: true,
            feedbackContent: '',
            isStreaming: false
          });

          // 滚动到底部显示反馈区域
          nextTick(() => {
            scrollToBottom(true);
          });
        }
        else {
          // 处理普通消息 - 修改这里实现连续相同source的消息合并
          const lastMessage = messageBlocks.value.length > 0 ? messageBlocks.value[messageBlocks.value.length - 1] : null;

          // 如果存在上一条消息，且source相同，且不是反馈消息，则合并内容
          if (lastMessage &&
              lastMessage.source === data.source &&
              !lastMessage.showFeedback &&
              !data.is_final) { // 非最终消息才合并

            // 更新现有消息的内容
            const updatedMessages = [...messageBlocks.value];
            const currentIndex = updatedMessages.length - 1;

            // 如果是第一次追加内容，保存原始markdown
            if (!lastMessage.isStreaming) {
              updatedMessages[currentIndex] = {
                ...updatedMessages[currentIndex],
                originalContent: updatedMessages[currentIndex].content,
                isStreaming: true
              };
            }

            // 合并原始内容
            const combinedRawContent = (lastMessage.rawContent || '') + (data.content || '');

            // 更新消息内容
            updatedMessages[currentIndex] = {
              ...updatedMessages[currentIndex],
              content: parseMarkdown(combinedRawContent),
              rawContent: combinedRawContent,
              timestamp: new Date().toISOString(),
              isStreaming: true
            };

            messageBlocks.value = updatedMessages;
          } else {
            // 创建新的消息块
            messageBlocks.value.push({
              source: data.source || 'ai',
              content: parseMarkdown(data.content),
              rawContent: data.content,
              timestamp: new Date().toISOString(),
              showFeedback: false,
              isStreaming: false
            });
          }
        }

        // 检查是否为最终消息
        if (data.is_final) {
          // 如果是最终消息，将当前消息标记为非流式
          if (messageBlocks.value.length > 0) {
            const updatedMessages = [...messageBlocks.value];
            const currentIndex = updatedMessages.length - 1;

            updatedMessages[currentIndex] = {
              ...updatedMessages[currentIndex],
              isStreaming: false
            };

            messageBlocks.value = updatedMessages;
          }

          nextTick(() => {
            scrollToBottom(true); // 强制滚动到底部
            isGenerating.value = false; // 最后才更新状态
            // 检查是否有测试用例数据，如果有则渲染思维导图
            if (testCaseList.value.length > 0) {
              renderMindmap();
            }
          });
        } else {
          nextTick(() => {
            scrollToBottom();
          });
        }

        nextTick(() => {
          highlightCodeBlocks();
          setupJsonInteractions(); // 额外调用一次确保JSON交互被设置
        });
      } catch (error) {
        console.error('消息解析失败:', error);
        if (!isNavigatingAway.value) {
          message.error('消息解析失败');
        }
        handleGenerationError();
      }
    };

    // 发生错误时
    socket.onerror = (error) => {
      clearTimeout(connectionTimeout)
      console.error('WebSocket错误:', error)
      if (!isNavigatingAway.value) {
        message.error('连接失败，请重试')
      }
      handleGenerationError();
    }

    // 连接关闭时
    socket.onclose = (event) => {
      clearTimeout(connectionTimeout)
      console.log('WebSocket连接已关闭', event)
      // 只有在非导航离开且非正常关闭时才显示错误
      if (!isNavigatingAway.value && !event.wasClean) {
        message.error('连接已断开，请重试')
        handleGenerationError();
      }
    }
  } catch (error) {
    console.error('WebSocket初始化失败:', error)
    if (!isNavigatingAway.value) {
      message.error('连接初始化失败，请重试')
    }
    handleGenerationError();
  }
}

// 强化关闭WebSocket连接的方法
const closeWebSocket = () => {
  if (!socket) return;

  console.log('正在关闭WebSocket连接...', socket.readyState)
  try {
    // 先解除所有事件监听器，防止错误事件触发
    socket.onopen = null
    socket.onmessage = null
    socket.onerror = null
    socket.onclose = null

    // 如果连接仍处于打开状态，先发送关闭信号
    if (socket.readyState === WebSocket.OPEN) {
      try {
        socket.send(JSON.stringify({
          source: 'client',
          content: 'CLIENT_DISCONNECTING'
        }))
      } catch (e) {
        console.warn('发送关闭信号失败:', e)
      }

      // 设置关闭超时，避免无限等待
      const closeTimeout = setTimeout(() => {
        console.warn('WebSocket关闭超时，强制清理')
        socket = null
      }, 1000)

      // 正常关闭连接
      socket.close(1000, '用户离开页面')

      // 关闭成功后清除超时
      socket.onclose = () => {
        clearTimeout(closeTimeout)
        console.log('WebSocket连接已正常关闭')
        socket = null
      }
    } else if (socket.readyState === WebSocket.CONNECTING) {
      // 如果还在连接中，直接关闭
      socket.close(1000, '连接被中止')
      socket = null
    } else {
      // 其他状态直接置空
      socket = null
    }
  } catch (e) {
    console.error('关闭WebSocket出错:', e)
    socket = null // 确保无论如何都重置socket引用
  }
}

// 完全重写错误处理方法
const handleGenerationError = () => {
  isGenerating.value = false
  closeWebSocket()

  // 重置UI状态
  try {
    messageBlocks.value = messageBlocks.value.map(msg => {
      if (msg.isStreaming) {
        return {
          ...msg,
          isStreaming: false
        }
      }
      return msg
    })
  } catch (e) {
    console.error('重置消息状态失败:', e)
  }
}

// 重写所有生命周期钩子和事件处理
onMounted(async () => {
  console.log('页面挂载')
  // 标记页面已挂载
  pageIsMounted.value = true
  isNavigatingAway.value = false

  // 延迟初始化资源，避免导航冲突
  await nextTick()

  // 初始化项目和需求列表
  try {
    await getProjectList()
  await handleSearch()
  } catch (e) {
    console.error('初始化数据失败:', e)
  }

  // 使用模块级变量存储引用，以便可以在任何地方删除
  window.__testGeneratorResizeHandler = handleWindowResize
  window.__testGeneratorUnloadHandler = handlePageUnload

  // 添加事件监听器
  window.addEventListener('resize', window.__testGeneratorResizeHandler)
  window.addEventListener('beforeunload', window.__testGeneratorUnloadHandler)

  // 设置滚动行为
  setupAutoScroll()

  // 观察输出容器变化
  const outputEl = document.querySelector('.markdown-container')
  if (outputEl) {
    window.__testGeneratorResizeObserver = new ResizeObserver(scrollToBottom)
    window.__testGeneratorResizeObserver.observe(outputEl)
  }

  // 添加路由守卫，但确保全局只添加一次
  if (!window.__testGeneratorRouteGuard) {
    window.__testGeneratorRouteGuard = (to, from, next) => {
      // 如果要离开当前页面
      if (from.path.includes('/testing/generator') && !to.path.includes('/testing/generator')) {
        console.log('检测到路由离开测试用例生成页面', from.path, '到', to.path)

        // 标记正在离开
        isNavigatingAway.value = true

        // 停止所有正在进行的操作
        isGenerating.value = false

        // 关闭WebSocket连接
        closeWebSocket()

        // 清理所有资源
        cleanupAllResources()
      }
      // 始终允许导航
      next()
    }

    // 添加到路由
    router.beforeEach(window.__testGeneratorRouteGuard)
  }

  // 添加激进的解决方案: 拦截所有导航链接点击
  setTimeout(() => {
    interceptNavigationLinks()
  }, 500)
})

// 新增: 拦截导航链接的点击事件
const interceptNavigationLinks = () => {
  // 找到所有导航链接
  const navLinks = document.querySelectorAll('.n-menu-item-content, .n-menu-item-content a')

  console.log('找到导航链接数量:', navLinks.length)

  // 添加点击事件拦截
  navLinks.forEach(link => {
    // 跳过已经处理过的链接
    if (link.__intercepted) return

    // 标记此链接已被处理
    link.__intercepted = true

    // 添加数据属性以标识原始URL
    const originalHref = link.getAttribute('href')
    if (originalHref) {
      link.setAttribute('data-original-href', originalHref)
    }

    // 获取菜单项的路由信息
    const routeInfo = link.getAttribute('data-route-info') || link.parentElement?.getAttribute('data-route-info')
    if (routeInfo) {
      link.setAttribute('data-route-info', routeInfo)
    }

    // 添加点击事件处理
    link.addEventListener('click', async (event) => {
      // 如果当前不在测试生成页面，使用正常导航
      if (!window.location.href.includes('/testing/generator')) {
        return
      }

      // 阻止默认导航
      event.preventDefault()
      event.stopPropagation()

      // 获取目标URL
      let targetPath = link.getAttribute('data-original-href') || link.getAttribute('href')

      // 如果没有找到URL但有路由信息，尝试构建URL
      if (!targetPath && routeInfo) {
        try {
          const routeData = JSON.parse(routeInfo)
          targetPath = routeData.path
        } catch (e) {
          console.error('解析路由数据失败:', e)
        }
      }

      if (!targetPath) {
        console.error('无法确定导航目标')
        return
      }

      console.log('拦截到导航请求，目标:', targetPath)

      // 执行清理
      isNavigatingAway.value = true
      isGenerating.value = false
      closeWebSocket()
      await cleanupAllResources()

      // 延迟一下以确保清理完成
      setTimeout(() => {
        // 使用更直接的导航方法
        safeNavigate(targetPath)
      }, 100)
    })
  })
}

// 新增: 安全导航方法
const safeNavigate = (path) => {
  console.log('执行安全导航到:', path)

  try {
    // 尝试使用Vue Router导航
    router.push(path).catch(error => {
      console.error('Vue Router导航失败:', error)

      // 如果Vue Router导航失败，使用window.location
      if (path.startsWith('/')) {
        // 相对路径
        window.location.href = path
      } else {
        // 绝对路径
        window.location.href = path
      }
    })
  } catch (e) {
    console.error('导航过程中发生错误:', e)

    // 最后的手段：硬重定向
    window.location.href = path
  }
}

// 修改现有的清理函数为async
const cleanupAllResources = async () => {
  console.log('执行全面资源清理')

  // 确保WebSocket连接已关闭
  closeWebSocket()

  // 移除DOM事件监听器
  document.removeEventListener('mousemove', handleResize)
  document.removeEventListener('mouseup', stopResize)

  // 处理JSON交互的事件监听器
  try {
    document.querySelectorAll('.json-toggle').forEach(button => {
      button.removeEventListener('click', null)
      button.hasJsonListener = false
    })
  } catch (e) {
    console.error('清理JSON交互监听器失败:', e)
  }

  // 销毁图表
  if (mindmapChart) {
    try {
      mindmapChart.dispose()
    } catch (e) {
      console.error('销毁图表失败:', e)
    } finally {
      mindmapChart = null
    }
  }

  // 重置状态
  isGenerating.value = false

  // 清除所有可能存在的定时器
  if (scrollTimer) {
    clearTimeout(scrollTimer)
    scrollTimer = null
  }

  // 等待一小段时间确保资源释放
  return new Promise(resolve => setTimeout(resolve, 50))
}

// 修改专门的预清理函数为async
const cleanupBeforeLeaving = async () => {
  console.log('执行预清理操作')

  // 关闭WebSocket
  closeWebSocket()

  // 移除全局事件监听器
  if (window.__testGeneratorResizeHandler) {
    window.removeEventListener('resize', window.__testGeneratorResizeHandler)
  }

  if (window.__testGeneratorUnloadHandler) {
    window.removeEventListener('beforeunload', window.__testGeneratorUnloadHandler)
  }

  // 移除ResizeObserver
  if (window.__testGeneratorResizeObserver) {
    window.__testGeneratorResizeObserver.disconnect()
    window.__testGeneratorResizeObserver = null
  }

  // 清理所有资源
  await cleanupAllResources()
}

// 修改卸载钩子
onBeforeUnmount(async () => {
  console.log('组件即将卸载 (Before)')
  // 立即标记离开状态，防止新事件处理
  isNavigatingAway.value = true

  // 清理资源
  await cleanupBeforeLeaving()
})

// 修改额外的卸载钩子
onUnmounted(async () => {
  console.log('组件已卸载 (After)')
  // 确保已标记离开状态
  isNavigatingAway.value = true

  // 再次清理所有资源，防止遗漏
  await cleanupBeforeLeaving()
})

// 修改为使用函数表达式定义事件处理器，以便可以精确移除
const handleWindowResize = () => {
  if (mindmapChart && !isNavigatingAway.value) {
    mindmapChart.resize()
  }
}

const handlePageUnload = (event) => {
  console.log('页面即将卸载')
  isNavigatingAway.value = true
  closeWebSocket()
  cleanupAllResources()
}

// 添加项目选择处理方法
const handleProjectSelect = (value) => {
  const selectedProject = projectList.value.find(p => p.id === value)
  if (selectedProject) {
    searchParams.projectName = selectedProject.name
    searchParams.projectId = selectedProject.id
    // 清空需求选择
    selectedRequirement.value = null
    testCaseList.value = []
    // 重新获取需求列表
    handleSearch()
  }
}

// 获取项目列表
const getProjectList = async () => {
  try {
    const { data } = await api.getProjts()
    projectList.value = data
  } catch (error) {
    message.error('获取项目列表失败')
  }
}

// 发送用户反馈 - 修改为接收消息索引
const sendFeedback = (index) => {
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({
      source: 'feedback',
      content: messageBlocks.value[index].feedbackContent || 'APPROVE'
    }));
  }

  // 创建消息副本并更新showFeedback属性，确保Vue检测到更改
  const updatedMessages = [...messageBlocks.value];
  updatedMessages[index] = {
    ...updatedMessages[index],
    showFeedback: false
  };
  messageBlocks.value = updatedMessages;
}

// 关闭反馈窗口并发送默认回复 - 修改为接收消息索引
const closeFeedback = (index) => {
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({
      source: 'feedback',
      content: 'APPROVE'
    }));
  }

  // 创建消息副本并更新showFeedback属性，确保Vue检测到更改
  const updatedMessages = [...messageBlocks.value];
  updatedMessages[index] = {
    ...updatedMessages[index],
    showFeedback: false
  };
  messageBlocks.value = updatedMessages;
}

// 添加同意响应的方法
const approveResponse = (index) => {
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({
      source: 'feedback',
      content: 'APPROVE'
    }));
  }

  // 创建消息副本并更新showFeedback属性，确保Vue检测到更改
  const updatedMessages = [...messageBlocks.value];
  updatedMessages[index] = {
    ...updatedMessages[index],
    showFeedback: false
  };
  messageBlocks.value = updatedMessages;
}

// 添加自动滚动到底部的函数
const scrollToBottom = (force = false) => {
  if (!autoScroll.value && !force) return;
  
  const outputContainer = document.querySelector('.markdown-container');
  if (outputContainer) {
    // 使用requestAnimationFrame确保在DOM更新后滚动
    requestAnimationFrame(() => {
      outputContainer.scrollTop = outputContainer.scrollHeight;
    });
  }
}

// 设置自动滚动功能
const setupAutoScroll = () => {
  const outputContainer = document.querySelector('.markdown-container');
  if (!outputContainer) return;
  
  // 监听滚动事件
  outputContainer.addEventListener('scroll', () => {
    // 如果用户手动向上滚动，则暂停自动滚动
    if (outputContainer.scrollHeight - outputContainer.scrollTop - outputContainer.clientHeight > 100) {
      autoScroll.value = false;
      userScrolled.value = true;
    } else {
      // 如果滚动到接近底部，恢复自动滚动
      autoScroll.value = true;
      userScrolled.value = false;
    }
  });
}
</script>

<style>
/* 将JSON样式放在非scoped区域，确保可以应用到动态生成的内容 */
.json-wrapper {
  position: relative;
  margin: 1.2em 0;
  border-radius: 8px;
  overflow: hidden;
  background: #f8f8f8;
}

.json-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #2c3e50;
  color: white;
  padding: 8px 12px;
  font-family: monospace;
  font-size: 0.9em;
}

.json-title {
  font-weight: 600;
}

.json-toggle {
  background: none;
  border: none;
  color: white;
  cursor: pointer;
  font-size: 0.8em;
  padding: 2px 6px;
  border-radius: 4px;
  transition: background-color 0.2s;
}

.json-toggle:hover {
  background-color: rgba(255, 255, 255, 0.2);
}

.json-wrapper pre {
  margin: 0;
  max-height: 400px;
  overflow: auto;
  transition: max-height 0.3s ease;
  padding: 12px;
  background: #f8f8f8;
}

.json-wrapper pre.collapsed {
  max-height: 60px;
  overflow: hidden;
}

/* JSON语法高亮自定义样式 */
.json-wrapper .hljs-string {
  color: #42b983;
}

.json-wrapper .hljs-number {
  color: #ae81ff;
}

.json-wrapper .hljs-literal {
  color: #fd971f;
}

.json-wrapper .hljs-punctuation {
  color: #89bdff;
}

.json-wrapper .hljs-property {
  color: #66d9ef;
}
</style>

<style scoped>
/* 添加打字机动画 */
@keyframes typing {
  from { width: 0 }
  to { width: 100% }
}

.streaming-text {
  display: inline-block;
  white-space: pre-wrap;
  word-break: break-word;
  animation: fadeIn 0.2s ease-out;
}

/* 流式块样式 */
.streaming-block {
  position: relative;
  min-height: 1.2em;
  line-height: 1.6;
  padding: 4px 0;
}

.streaming-block::after {
  content: "▋";
  display: inline-block;
  vertical-align: middle;
  animation: blink 0.8s infinite;
  color: rgba(14, 165, 233, 0.6);
  margin-left: 2px;
}

/* 最终块样式 */
.final-block .streaming-text {
  animation: none;
}

.final-block::after {
  display: none;
}
.streaming-content {
  padding: 12px 16px;
  white-space: pre-wrap;
}

.testcase-container {
  height: 100vh;
  display: flex;
  overflow: hidden;
}

.requirements-panel {
  height: 100%;
  overflow-y: auto;
  border-right: 1px solid #e5e7eb;
  padding: 16px;
}

.content-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 16px;
}

.requirement-detail {
  flex-shrink: 0;
  margin-bottom: 16px;
}

.content-wrapper {
  flex-shrink: 0;
  margin-bottom: 16px;
}

.command-input {
  flex-shrink: 0;
  margin-bottom: 16px;
}

.output-container {
  flex: 1;
  min-height: 0; /* 关键：允许容器缩小 */
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.n-tabs {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.n-tabs :deep(.n-tabs-nav) {
  flex-shrink: 0;
  margin-bottom: 16px;
}

.n-tabs :deep(.n-tabs-pane-wrapper) {
  flex: 1;
  overflow: hidden;
  height: 100%;
}

.n-tab-pane {
  height: 100%;
}

.output-display {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
  padding: 0; /* 移除所有内边距 */
}

.markdown-container {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  padding-bottom: 80px; /* 增加更多底部空间 */
  margin-bottom: 40px; /* 添加底部边距 */
  background: #ffffff;
  border-radius: 12px;
  position: relative;
  scroll-behavior: smooth; /* 添加平滑滚动 */

  /* 自定义滚动条样式 */

  &::-webkit-scrollbar {
    width: 8px;
    height: 8px;
  }

  &::-webkit-scrollbar-track {
    background: #f1f1f1;
    border-radius: 4px;
  }

  &::-webkit-scrollbar-thumb {
    background: rgba(14, 165, 233, 0.3);
    border-radius: 4px;
    transition: all 0.3s ease;

    &:hover {
      background: rgba(14, 165, 233, 0.5);
    }
  }
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
  transition: all 0.3s ease;

  &:last-child {
    margin-bottom: 20px; /* 为最后一个消息添加底部边距 */
  }

  &.new-message {
    animation: slideInUp 0.3s ease;
  }
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
}

.markdown-content td,
.markdown-content th {
  border: 1px solid #dfe2e5;
  padding: 0.6em 1em;
}

.markdown-content tr:nth-child(even) {
  background: #f6f8fa;
}

.loading-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 16px 24px;
  margin: 16px 0;
  color: #666;
  font-size: 0.9em;
  background: rgba(255, 255, 255, 0.9);
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  min-height: 60px;
  width: 100%;
  position: sticky;
  bottom: 0;
  z-index: 10;
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

.output-container {
  position: relative;
  flex: 1;
}

/* 测试用例列表样式 */
.testcase-list {
  height: 100%;
  display: flex;
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
  padding: 24px;
  gap: 24px;
  overflow: hidden; /* 添加overflow: hidden */
}

.case-list-panel {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  height: 100%; /* 确保面板占满高度 */
  overflow: hidden; /* 添加overflow: hidden */
}

.case-list-wrapper {
  flex: 1; /* 改为flex: 1 */
  overflow-y: auto;
  padding-right: 8px;
  height: 100%; /* 确保wrapper占满高度 */
  min-height: 0; /* 添加min-height: 0 */

  /* 自定义滚动条样式 */

  &::-webkit-scrollbar {
    width: 8px;
    height: 8px;
  }

  &::-webkit-scrollbar-track {
    background: #f1f1f1;
    border-radius: 4px;
  }

  &::-webkit-scrollbar-thumb {
    background: rgba(14, 165, 233, 0.3);
    border-radius: 4px;
    transition: all 0.3s ease;

    &:hover {
      background: rgba(14, 165, 233, 0.5);
    }
  }
}

.mindmap-panel {
  display: flex;
  flex-direction: column;
  min-width: 500px;
  border-left: 1px solid #e5e7eb;
  padding-left: 24px;
}

.mindmap-container {
  height: 100%;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  overflow: auto;
  position: relative;
  background: #ffffff;
  padding: 16px;

  /* 自定义滚动条样式 */

  &::-webkit-scrollbar {
    width: 8px;
    height: 8px;
  }

  &::-webkit-scrollbar-track {
    background: #f1f1f1;
    border-radius: 4px;
  }

  &::-webkit-scrollbar-thumb {
    background: rgba(14, 165, 233, 0.3);
    border-radius: 4px;
    transition: all 0.3s ease;

    &:hover {
      background: rgba(14, 165, 233, 0.5);
    }
  }
}

.mindmap-container :deep(.echarts) {
  min-height: 100%;
  min-width: 100%;
  width: 100% !important;
  height: 100% !important;
}

/* 添加测试用例卡片样式 */
.testcase-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.testcase-title {
  font-weight: 500;
  font-size: 14px;
  color: #333;
  flex: 1;
}

.testcase-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.testcase-creator {
  font-size: 12px;
  color: #666;
}

.step-description {
  margin-bottom: 8px;
}

.step-result {
  color: #666;
  font-size: 13px;
  padding-left: 24px;
  margin-bottom: 16px;
}

.tag-group {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 8px;
}

.info-row {
  display: flex;
  gap: 16px;
  margin-bottom: 12px;
}

.info-label {
  color: #666;
  min-width: 80px;
}

.info-content {
  color: #333;
  flex: 1;
}

.steps-container {
  margin-top: 16px;
  border-top: 1px solid #f0f0f0;
  padding-top: 16px;
}

.step-item {
  margin-bottom: 16px;
  padding-left: 16px;
  border-left: 2px solid #e8e8e8;
}

.step-item:last-child {
  margin-bottom: 0;
}

/* 需求列表样式 */
.requirements-list {
  height: calc(100% - 80px);
  overflow-y: auto;

  /* 自定义滚动条样式 */

  &::-webkit-scrollbar {
    width: 8px;
    height: 8px;
  }

  &::-webkit-scrollbar-track {
    background: #f1f1f1;
    border-radius: 4px;
  }

  &::-webkit-scrollbar-thumb {
    background: rgba(14, 165, 233, 0.3);
    border-radius: 4px;
    transition: all 0.3s ease;

    &:hover {
      background: rgba(14, 165, 233, 0.5);
    }
  }
}

.n-input :deep(.n-input__border) {
  border-radius: 6px;
}

/* 调整输入框对齐 */
.command-input .n-input {
  margin-left: -4px; /* 补偿按钮间距 */
}

/* 统一内容区域内边距 */
.content-wrapper,
.n-tabs,
.n-collapse {
  padding-left: 8px;
}

@keyframes slideInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.scenario-input {
  height: 150px;
  overflow-y: auto;

  :deep(.n-input__textarea-el) {
    height: 100% !important;
    resize: none;
  }

  /* 自定义滚动条样式 */

  :deep(.n-input__textarea-el::-webkit-scrollbar) {
    width: 6px;
    height: 6px;
  }

  :deep(.n-input__textarea-el::-webkit-scrollbar-track) {
    background: #f1f1f1;
    border-radius: 3px;
  }

  :deep(.n-input__textarea-el::-webkit-scrollbar-thumb) {
    background: rgba(14, 165, 233, 0.3);
    border-radius: 3px;
    transition: all 0.3s ease;

    &:hover {
      background: rgba(14, 165, 233, 0.5);
    }
  }
}

.description-input {
  height: 50px;
  overflow-y: auto;

  :deep(.n-input__textarea-el) {
    height: 100% !important;
    resize: none;
  }

  /* 自定义滚动条样式 */

  :deep(.n-input__textarea-el::-webkit-scrollbar) {
    width: 6px;
    height: 6px;
  }

  :deep(.n-input__textarea-el::-webkit-scrollbar-track) {
    background: #f1f1f1;
    border-radius: 3px;
  }

  :deep(.n-input__textarea-el::-webkit-scrollbar-thumb) {
    background: rgba(14, 165, 233, 0.3);
    border-radius: 3px;
    transition: all 0.3s ease;

    &:hover {
      background: rgba(14, 165, 233, 0.5);
    }
  }
}

/* 添加反馈相关样式 */
.feedback-container {
  background-color: #f9f9f9;
  border-radius: 8px;
  padding: 12px;
  border: 1px dashed #d9d9d9;
}

.feedback-input {
  width: 100%;
}

.feedback-actions {
  display: flex;
  justify-content: flex-end;
}

/* 调整user_proxy消息的样式 */
.message-item.user_proxy {
  background: #fff8dc;
  border-left: 3px solid #ff9800;
}

/* 添加流式输出相关的样式 */
.message-item.streaming {
  position: relative;
}

.message-item.streaming::after {
  content: "▋";
  display: inline-block;
  vertical-align: middle;
  animation: blink 0.8s infinite;
  color: rgba(14, 165, 233, 0.6);
  font-size: 1.2em;
  position: absolute;
  bottom: 16px;
  right: 16px;
}

@keyframes blink {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0;
  }
}
</style>