<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { v4 as uuidv4 } from 'uuid'
import axios from 'axios'
import { useMessage, useLoadingBar, useNotification, useDialog } from 'naive-ui'
import { 
  DocumentTextOutline as DocumentIcon, 
  CodeOutline as CodeIcon, 
  AnalyticsOutline as ChartIcon, 
  DocumentAttachOutline as FileIcon,
  CopyOutline as CopyIcon,
  DownloadOutline as DownloadIcon,
  ServerOutline as ConnectionIcon,
  ArrowUpOutline,
  ArrowDownOutline,
  ChevronUpOutline,
  ChevronDownOutline,
  ReloadOutline,
  OpenOutline,
  SettingsOutline as SettingsIcon,
  SaveOutline as SaveIcon,
  ExpandOutline as ExpandIcon,
  BarChartOutline, // 或其他可能存在的图表图标
  StatsChartOutline,
  PieChartOutline,
  LinkOutline,
  AlertCircleOutline
} from '@vicons/ionicons5'
import { marked } from 'marked'
// 引入Monaco编辑器组件
// import * as monaco from 'monaco-editor'
// 使用全局monaco变量

// 初始化UI组件
const message = useMessage()
const notification = useNotification()
const dialog = useDialog()
const loadingBar = useLoadingBar()

// 应用状态管理
const state = reactive({
  apiDocsUrl: '',
  baseUrl: '',
  apiDocSupplement: '', // 接口文档补充说明
  testFocus: '', // 测试重点
  enableReview: true,
  userReview: false,
  useLocalExecutor: true,
  useStreaming: false,
  isLoading: false,
  isConnected: false,
  isAnalyzing: false,
  isGenerating: false,
  isExecuting: false,
  isReportLoading: false,      // HTML报告是否正在加载
  isAllureLoading: false,      // Allure报告是否正在加载
  allureLoadError: false,     // Allure报告加载错误状态
  htmlLoadError: false, // 新增HTML报告加载错误状态
  progress: {
    stage: 'idle',
    percentage: 0,
    message: ''
  },
  clientId: uuidv4(),
  activeTab: 'logs', // 'logs', 'results', 'code', 'analysis', 'report'
  executionStats: {
    total: 0,
    passed: 0,
    failed: 0,
    skipped: 0,
    duration: 0
  },
  configCollapsed: false  // 默认折叠配置区域，给日志更多空间
})

// 数据存储
const logMessages = ref([])
const currentStreamSources = reactive({})  // 跟踪当前正在流式输出的消息源
const testResults = ref('')
const testCode = ref('')
const editableTestCode = ref('') // 可编辑的测试代码
const analysisResult = ref('')
const testFilePath = ref('')
const reportUrl = ref('')  // 存储测试报告URL
const allureReportUrl = ref('')  // 存储Allure测试报告URL
const webSocket = ref(null)
const codeEditor = ref(null) // 代码编辑器引用
const isEditing = ref(false) // 是否处于编辑模式
const auxFiles = ref({}) // 存储辅助文件
const conftestCode = ref('') // 存储conftest.py的内容
const enhancedReportReady = ref(false)  // 标记增强报告是否已准备好

// 测试参数配置
const testParams = ref({
  timeout: 30,
  retries: 0,
  parallel: false,
  verbose: true,
  tags: '',
  customOptions: ''
})

// 在script setup部分添加状态
const testCases = ref('')
const testCaseMetadata = ref(null)

// 计算属性
const isFormValid = computed(() => {
  return state.apiDocsUrl && state.apiDocsUrl.trim() !== '' && 
         state.baseUrl && state.baseUrl.trim() !== ''
})

// 检查API URL是否有效
const isApiConfigValid = computed(() => {
  return state.apiDocsUrl && state.apiDocsUrl.trim() !== '' && 
         state.baseUrl && state.baseUrl.trim() !== '';
});

const progressPercentText = computed(() => {
  return `${state.progress.percentage}%`
})

const canRunTests = computed(() => {
  return testFilePath.value && !state.isExecuting
})

const statusColor = computed(() => {
  if (!testResults.value) return '';
  const result = typeof testResults.value === 'string' 
    ? testResults.value 
    : JSON.stringify(testResults.value);
  if (result.includes('success') || result.includes('passed')) return 'success';
  if (result.includes('failed') || result.includes('error')) return 'danger';
  return 'warning';
})

// WebSocket URL创建
const getWebSocketUrl = () => {
  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${wsProtocol}//${window.location.hostname}:9999/api/v1/agent/ws/apitest/${state.clientId}`
  console.log('创建WebSocket URL:', wsUrl)
  return wsUrl
}

// WebSocket 管理
const connectWebSocket = () => {
  if (webSocket.value && webSocket.value.readyState === WebSocket.OPEN) {
    webSocket.value.close()
  }
  
  // 添加初始日志
  addLog('system', '正在初始化WebSocket连接...', 'info')
  state.isConnected = false
  
  const wsUrl = getWebSocketUrl()
  addLog('system', `正在连接到: ${wsUrl}`, 'info')
  
  try {
    webSocket.value = new WebSocket(wsUrl)
    
    webSocket.value.onopen = () => {
      state.isConnected = true
      console.log('WebSocket连接已建立')
      addLog('system', 'WebSocket连接已建立，准备开始API测试流程...', 'info')
      
      // 发送初始配置
      sendWSMessage({
        api_docs_url: state.apiDocsUrl,
        base_url: state.baseUrl,
        enable_review: state.enableReview,
        user_review: state.userReview,
        use_local_executor: state.useLocalExecutor,
        api_doc_supplement: state.apiDocSupplement,
        test_focus: state.testFocus
      })
    }
    
    webSocket.value.onmessage = (event) => {
      console.log('收到WebSocket消息原始数据:', event.data)
      try {
        const data = JSON.parse(event.data)
        console.log('解析后的WebSocket消息:', data)
        
        // 检查data是否为有效对象
        if (!data || typeof data !== 'object') {
          console.warn('收到无效的WebSocket消息结构', data)
          addLog('system', '收到无效的WebSocket消息结构', 'warning')
          return
        }
        
        // 检查必要的属性
        if (data.type === undefined) {
          console.warn('收到无效的WebSocket消息: 缺少type属性', data)
          addLog('system', '收到无效的WebSocket消息: 缺少type属性', 'warning')
          return
        }
        
        // 特别检查content
        if (data.content !== undefined && typeof data.content === 'function') {
          console.warn('收到异常的WebSocket消息: content是函数类型', data)
          addLog('system', '收到异常的WebSocket消息格式', 'warning')
          return
        }
        
        // 打印完整的消息细节
        if (data) {
          console.log(`消息类型: ${data.type}, 来源: ${data.source}`)
          console.log('消息内容:', data.content)
        }
        
        if (data && data.content !== undefined) {
          handleWSMessage(data)
        } else {
          console.warn('收到无效的WebSocket消息', data)
        }
      } catch (e) {
        console.error('解析WebSocket消息出错:', e)
        addLog('system', `解析WebSocket消息出错: ${e.message}`, 'error')
      }
    }
    
    webSocket.value.onclose = (event) => {
      state.isConnected = false
      console.log('WebSocket连接已关闭', event)
      addLog('system', `WebSocket连接已关闭 代码: ${event.code}`, 'warning')
      state.isLoading = false
    }
    
    webSocket.value.onerror = (error) => {
      state.isConnected = false
      console.error('WebSocket错误:', error)
      addLog('system', `WebSocket连接错误`, 'error')
      state.isLoading = false
    }
  } catch (error) {
    console.error('创建WebSocket连接失败:', error)
    addLog('system', `创建WebSocket连接失败: ${error.message}`, 'error')
    state.isLoading = false
  }
}

// 发送WebSocket消息
const sendWSMessage = (data) => {
  if (webSocket.value && webSocket.value.readyState === WebSocket.OPEN) {
    const messageData = {
      ...data,
      base_url: state.baseUrl,
      use_local_executor: state.useLocalExecutor,
      api_doc_supplement: state.apiDocSupplement,
      test_focus: state.testFocus
    }
    console.log('发送WebSocket消息:', messageData)
    webSocket.value.send(JSON.stringify(messageData))
    
    // 添加系统日志表示已发送消息
    addLog('system', '已发送请求到服务器，等待响应...', 'info')
  } else {
    console.error('WebSocket连接未建立，无法发送消息')
    message.error('WebSocket连接未建立')
    addLog('system', 'WebSocket连接未建立，无法发送消息', 'error')
  }
}

// 处理WebSocket消息
const handleWSMessage = (data) => {
  console.log('开始处理WebSocket消息:', data)
  
  // 检查data是否有效
  if (!data) {
    console.error('收到无效的WebSocket消息: data为空')
    addLog('system', '收到无效的WebSocket消息: data为空', 'error')
    return
  }
  
  // 检查必要的属性
  const { type, content, source } = data
  console.log(`处理消息 - 类型: ${type}, 来源: ${source}, 内容类型: ${typeof content}`)
  
  if (type === undefined) {
    console.error('收到无效的WebSocket消息: 缺少type属性', data)
    addLog('system', '收到无效的WebSocket消息: 缺少type属性', 'error')
    return
  }
  
  // 在任何情况下都添加一条系统日志，确保至少有一些可见的输出
  if (type !== 'log' && type !== 'progress' && type !== 'ping') {
    addLog('system', `收到${type}类型消息，来源: ${source || 'unknown'}`, 'info')
  }
  
  // 处理不同类型的消息
  switch (type) {
    case 'log':
      // 处理日志
      if (!content) {
        console.warn('收到无效的日志消息 content为空', data)
        return
      }
      
      // 根据来源标记日志
      addLog(source || 'system', content, 'info')
      break
      
    case 'complete':
      // 处理完成消息
      message.success({
        content: content || '操作已完成',
        duration: 3000
      })
      
      addLog('system', `完成: ${content || '操作已完成'}`, 'success')
      break
      
    case 'ping':
      // 仅在控制台记录ping
      console.log('收到ping', content, source)
      break
      
    case 'progress':
      // 处理进度
      if (!content || content.progress === undefined) {
        console.warn('收到无效的进度消息 content或progress为空', data)
        return
      }
      
      // 更新进度条 - 确保进度不会倒退
      if (content.progress > state.progress.percentage) {
        state.progress.percentage = content.progress
      }
      
      // 更新进度阶段，如果存在
      if (content.stage) {
        state.progress.stage = content.stage
      }
      
      // 更新状态消息
      if (content.message) {
        state.progress.message = content.message
      }
      
      // 进度完成时，显示测试结果
      if (content.progress === 100) {
        state.isExecuting = false
        state.loadingText = '完成'
        addLog('system', '自动化测试流程已完成', 'success')
        
        // 如果有报告，自动切换到报告
        if (reportUrl.value && state.activeTab === 'logs') {
          addLog('system', '发现HTML测试报告，正在切换到报告视图...', 'info')
          state.activeTab = 'report'
        } else if (allureReportUrl.value && state.activeTab === 'logs') {
          addLog('system', '发现Allure测试报告，正在切换到报告视图...', 'info')
          state.activeTab = 'allure-report'
        }
      }
      break
      
    case 'result':
      if (!content) {
        console.warn('收到无效的结果消息 content为空', data)
        addLog('system', '收到无效的结果消息', 'warning')
        return
      }

      console.log('收到测试结果消息，内容:', content)
      console.log('报告标志状态:', {
        'analysis': data.has_analysis_report,
        'html': data.has_html_report,
        'allure': data.has_allure_report
      })
      
      // 记录消息来源，用于确定显示优先级
      const resultSource = source || 'unknown';
      console.log(`结果消息来源: ${resultSource}`);
      
      // 处理报告数据
      if (content.report_data) {
        console.log('发现报告数据:', content.report_data)
        
        // 设置分析报告
        if (content.report_data.analysis) {
          analysisResult.value = content.report_data.analysis
          addLog('system', '已接收分析报告', 'info')
          
          // 来自测试结果分析器时，自动切换到分析报告标签
          if (resultSource === 'test_result_analyzer' && state.activeTab !== 'analysis') {
            state.activeTab = 'analysis'
            addLog('system', '自动切换到分析报告标签', 'info')
          }
        }
        
        // 设置HTML报告URL
        if (content.report_data.html_report) {
          reportUrl.value = content.report_data.html_report
          state.isReportLoading = true
          addLog('system', `已接收HTML报告URL: ${reportUrl.value}`, 'info')
        }
        
        // 设置Allure报告URL
        if (content.report_data.allure_report) {
          allureReportUrl.value = content.report_data.allure_report
          state.isAllureLoading = true
          addLog('system', `已接收Allure报告URL: ${allureReportUrl.value}`, 'info')
          
          // 来自测试结果分析器且有Allure报告时，自动切换到Allure报告标签
          if (resultSource === 'test_result_analyzer' && state.activeTab !== 'allure-report') {
            state.activeTab = 'allure-report'
            addLog('system', '自动切换到Allure报告标签', 'info')
          }
        }
      } else {
        console.log('消息中没有找到report_data结构')
      }
      
      // 直接从消息中提取报告URL
      if (content.report_url && !reportUrl.value) {
        reportUrl.value = content.report_url
        state.isReportLoading = true
        console.log('直接从消息中设置HTML报告URL:', reportUrl.value)
        
        // 来自测试执行器且有HTML报告时，自动切换到HTML报告标签
        if (resultSource === 'test_executor' && state.activeTab !== 'report' && !state.activeTab.startsWith('test-')) {
          state.activeTab = 'report'
          addLog('system', '自动切换到HTML报告标签', 'info')
        }
      }
      
      if (content.allure_report_url && !allureReportUrl.value) {
        allureReportUrl.value = content.allure_report_url
        state.isAllureLoading = true
        console.log('直接从消息中设置Allure报告URL:', allureReportUrl.value)
      }
      
      // 直接从消息中提取分析报告
      if (content.analysis && !analysisResult.value) {
        analysisResult.value = content.analysis
        console.log('直接从消息中设置分析报告')
      }
      
      // 检查前端渲染标志是否需要强制设置
      // 如果后端已经传递了标志，则直接使用
      if (data.has_analysis_report === undefined && analysisResult.value) {
        data.has_analysis_report = true;
        console.log('强制启用分析报告标志')
      }
      
      if (data.has_html_report === undefined && reportUrl.value) {
        data.has_html_report = true;
        console.log('强制启用HTML报告标志')
      }
      
      if (data.has_allure_report === undefined && allureReportUrl.value) {
        data.has_allure_report = true;
        console.log('强制启用Allure报告标志')
      }
      
      // 来自报告增强器的消息，自动切换到增强的HTML报告标签
      if (resultSource === 'report_enhancer' && state.activeTab !== 'report') {
        state.activeTab = 'report'
        addLog('system', '自动切换到增强的HTML报告标签', 'info')
      }
      
      handleResults(content)
      break
      
    case 'code':
      if (!content) {
        console.warn('收到无效的代码消息 content为空', data)
        addLog('system', '收到无效的代码消息', 'warning')
        return
      }
      
      // 处理测试代码
      if (content.code) {
        testCode.value = content.code || ''
        editableTestCode.value = content.code || ''
      }
      
      // 保存测试文件路径
      if (content.test_file_path) {
        testFilePath.value = content.test_file_path
      }
      
      // 保存辅助文件并合并conftest.py内容到测试代码中
      if (content.aux_files) {
        auxFiles.value = content.aux_files
        console.log('收到辅助文件:', auxFiles.value)
        
        // 如果有conftest.py，将其添加到测试代码前面
        if (content.aux_files['conftest.py']) {
          // 保存conftest.py内容（保留这个变量以便其他地方使用）
          conftestCode.value = content.aux_files['conftest.py']
          console.log('收到conftest.py，长度:', conftestCode.value.length)
          
          // 合并conftest.py内容到测试代码中
          if (testCode.value) {
            testCode.value = "# === Conftest 配置代码 ===\n" + 
                             content.aux_files['conftest.py'] + 
                             "\n\n# === 测试代码 ===\n" + 
                             testCode.value
            
            // 同步更新可编辑版本
            editableTestCode.value = testCode.value
            
            // 自动切换到code标签页显示合并后的代码
            state.activeTab = 'code'
          }
        }
      }
      break
      
    case 'analysis':
      if (!content) {
        console.warn('收到无效的分析消息 content为空', data)
        addLog('system', '收到无效的分析消息', 'warning')
        return
      }
      
      analysisResult.value = content.analysis || ''
      break
      
    case 'review':
      if (!content || !content.summary) {
        console.warn('收到无效的评审消息 content或summary为空', data)
        addLog('system', '收到无效的评审消息', 'warning')
        return
      }
      
      // 处理测试评审结果
      notification({
        title: '测试评审完成',
        message: content.summary,
        type: 'success',
        duration: 5000
      })
      break
      
    case 'enhanced_report':
      if (!content || !content.report_data || !content.report_data.html_report) {
        console.warn('收到无效的enhanced_report消息，缺少report_data或html_report', data)
        addLog('system', '收到无效的enhanced_report消息', 'warning')
        return
      }
      
      console.log('收到enhanced_report消息：', content);
      
      // 处理增强报告
      if (content.enhancement_applied) {
        message.success({
          content: '测试报告已成功增强，点击报告标签查看',
          duration: 5000
        })
        
        // 如果当前未显示报告，自动切换到报告
        if (state.activeTab !== 'report') {
          addLog('system', '报告增强完成，自动切换到报告标签', 'info')
          state.activeTab = 'report';
        }
      }
      
      // 更新报告URL
      reportUrl.value = content.report_data.html_report
      console.log('从enhanced_report消息更新HTML报告URL:', content.report_data.html_report)
      // 标记增强报告已准备好
      enhancedReportReady.value = true
      
      // 如果有Allure报告URL
      if (content.report_data.allure_report) {
        allureReportUrl.value = content.report_data.allure_report
        console.log('从enhanced_report消息更新Allure报告URL:', content.report_data.allure_report)
      }
      
      // 设置标志位表示报告可用
      data.has_html_report = true
      if (content.report_data.allure_report) {
        data.has_allure_report = true
      }
      
      // 添加日志提示报告可用
      addLog('system', `测试报告已增强完成，报告URL: ${reportUrl.value}`, 'info')
      if (content.report_data.allure_report) {
        addLog('system', 'Allure报告已准备就绪，可以在Allure报告标签中查看', 'info')
      }
      
      break
      
    case 'error':
      // 处理错误，确保content有值
      handleError(content || '未知错误', source || 'system');
      break
      
    case 'user_input_request':
      // 处理用户输入请求
      dialog.prompt(
        content || '请提供您的反馈或建议:',
        '需要您的输入',
        {
          confirmButtonText: '提交',
          cancelButtonText: '跳过',
          inputType: 'textarea',
          inputPlaceholder: '请输入您的反?..'
        }
      )
        .then(({ value }) => {
          // 发送用户输入回WebSocket
          sendWSMessage({
            response: value || '继续执行'
          })
        })
        .catch(() => {
          // 用户取消，发送默认响应
          sendWSMessage({
            response: '继续执行'
          });
        })
      break
      
    case 'test_cases':
      if (!content) {
        console.warn('收到无效的测试用例设计消息 content为空', data);
        addLog('system', '收到无效的测试用例设计消息', 'warning');
        return;
      }
      
      testCases.value = content.test_cases || ''
      testCaseMetadata.value = content.metadata || null
      break;
      
    case 'allure_report':
      if (!content) {
        console.warn('收到无效的allure_report消息 content为空', data);
        addLog('system', '收到无效的allure_report消息', 'warning');
        return;
      }

      console.log('收到allure_report消息：', content);
      
      // 从消息中提取URL
      if (content.allure_report_url) {
        allureReportUrl.value = content.allure_report_url;
        console.log('使用报告URL:', content.allure_report_url);
      } else if (content.report_data && content.report_data.allure_report) {
        allureReportUrl.value = content.report_data.allure_report;
        console.log('从report_data结构中提取报告URL:', content.report_data.allure_report);
      }
      
      // 生成处理后的URL并添加到日志中
      const processedUrl = processAllureReportUrl(allureReportUrl.value);
      state.isAllureLoading = true;
      
      // 用户通知
      message.success({
        content: 'Allure报告已生成，可在Allure报告标签查看',
        duration: 5000
      });
      
      // 自动切换到Allure报告标签，如果当前在日志标签
      if (state.activeTab === 'logs') {
        addLog('system', '检测到Allure报告已生成，自动切换到报告标签', 'info');
        state.activeTab = 'allure-report';
      }
      
      // 添加日志
      addLog('system', `Allure报告已生成: ${allureReportUrl.value}`, 'info');
      addLog('system', `直接访问链接: ${processedUrl}`, 'info');

      break;
      
    case 'test_result':
      // 处理test_result类型消息
      if (!content) {
        console.warn('收到无效的test_result消息 content为空', data)
        addLog('system', '收到无效的test_result消息', 'warning')
        return
      }

      console.log('收到test_result消息，内容:', content)
      
      // 处理测试结果
      if (content.test_result) {
        handleResults(content)
      }
      
      // 处理报告数据
      if (content.report_data) {
        console.log('从test_result消息中发现报告数据:', content.report_data)
        
        // 设置分析报告
        if (content.report_data.analysis) {
          analysisResult.value = content.report_data.analysis
          addLog('system', '已接收分析报告', 'info')
        }
        
        // 设置HTML报告URL
        if (content.report_data.html_report) {
          reportUrl.value = content.report_data.html_report
          state.isReportLoading = true
          addLog('system', `已接收HTML报告URL: ${reportUrl.value}`, 'info')
        }
        
        // 设置Allure报告URL
        if (content.report_data.allure_report) {
          allureReportUrl.value = content.report_data.allure_report
          state.isAllureLoading = true
          const processedUrl = processAllureReportUrl(content.report_data.allure_report)
          addLog('system', `已接收Allure报告URL: ${content.report_data.allure_report}`, 'info')
          addLog('system', `如果报告无法正常显示，请使用直接访问：${processedUrl}`, 'warning')
        }
      }
      break
      
    default:
      console.log('未知消息类型:', type, content)
      addLog('system', `未知消息类型: ${type}`, 'warning')
  }
}

// 滚动到底部函数
const scrollToBottom = () => {
  console.log('尝试滚动到底部')
  // 强制执行两次nextTick和setTimeout，确保DOM完全更新后再滚动
  nextTick(() => {
    nextTick(() => {
      setTimeout(() => {
        const logContainer = document.querySelector('.log-container')
        if (logContainer) {
          console.log('执行滚动，日志容器高?', logContainer.scrollHeight)
          logContainer.scrollTop = logContainer.scrollHeight
        } else {
          console.warn('未找到日志容器元素')
        }
      }, 100) // 增加延迟确保DOM完全更新
    })
  })
}

// 添加或更新日志
const addLog = (source, content, level = 'info', shouldAppend = false) => {
  const now = new Date().toLocaleTimeString()
  console.log(`添加日志 - 来源: ${source}, 级别: ${level}, 追加: ${shouldAppend}, 内容长度: ${content?.length || 0}`)
  
  // 确保内容为字符串
  const safeContent = typeof content === 'string' 
    ? content 
    : JSON.stringify(content, null, 2)
  
  // 始终追加到同一消息
  const isStreamSource = source === 'test_executor' || source === 'api_analyzer' || 
                        source === 'test_generator' || source === 'test_result_analyzer' || 
                        source === 'result_analyzer' ||
                        source === 'report_enhancer' ||
                        source === 'test_case_designer'
  
  // 如果是流式源或明确要求追加，尝试追加到最后一条同源消息
  if ((isStreamSource || shouldAppend) && 
      currentStreamSources[source] !== undefined && 
      currentStreamSources[source] >= 0) {
    // 获取最后一条同源消息的索引
    const lastIndex = currentStreamSources[source]
    console.log(`尝试追加到索引: ${lastIndex}, 当前日志消息数量: ${logMessages.value.length}`)
    
    // 确保索引有效且消息对象存在并有content属性
    if (lastIndex >= 0 && 
        lastIndex < logMessages.value.length && 
        logMessages.value[lastIndex] && 
        logMessages.value[lastIndex].content !== undefined) {
      console.log(`追加日志到现有消息 - 索引: ${lastIndex}`)
      // 追加内容而不是创建新消息
      
      // 特殊处理：如果内容仅包含标点符号，不要添加换行
      const isPunctuation = /^[,.!?;:'")\]}]+$/.test(safeContent.trim());
      
      // 智能判断是否需要添加换行符
      const needNewline = 
        !isPunctuation && (
          (source === 'test_executor' && safeContent.trim().startsWith('===')) || // 测试分隔标记
          (safeContent.includes('\n') && safeContent.trim().length > 3) || // 内容本身包含换行且不是仅仅一个换行符
          safeContent.trim().startsWith('Step') || // 步骤信息
          /^(PASSED|FAILED|ERROR|SKIPPED)/.test(safeContent.trim()) || // 测试结果标记
          /^={3,}/.test(safeContent.trim())); // 分隔线
      
      logMessages.value[lastIndex].content += 
        (needNewline ? '\n' : '') + safeContent;
      
      // 当追加内容时也滚动到底部
      scrollToBottom();
      return;
    } else {
      console.warn(`无效的日志索引: ${lastIndex} 或消息对象不存在 创建新消息`);
    }
  }
  
  // 如果不是追加或追加失败，创建新消息
  console.log(`创建新日志消息 - 来源: ${source}`);
  const newIndex = logMessages.value.length;
  logMessages.value.push({
    time: now,
    source,
    content: safeContent,
    type: level
  });
  
  // 记录此消息源的最新索引
  currentStreamSources[source] = newIndex;
  console.log(`为来源: ${source} 设置新索引: ${newIndex}`);
  
  // 自动滚动到底部
  scrollToBottom();
  
  // 强制视图更新
  nextTick(() => {
    console.log(`日志消息添加完成, 当前总数: ${logMessages.value.length}`);
  });
}

// 更新进度
const updateProgress = (progressData) => {
  state.progress.stage = progressData.stage
  
  // 确保进度百分比不会倒退
  if (progressData.percentage > state.progress.percentage) {
    state.progress.percentage = progressData.percentage
  }
  
  state.progress.message = progressData.message
  
  // 根据阶段设置状态
  switch (progressData.stage) {
    case 'analyze':
      state.isAnalyzing = true
      break
      
    case 'design': // 新增设计阶段
      state.isAnalyzing = false
      state.isDesigning = true
      break
      
    case 'generate':
      state.isAnalyzing = false
      state.isDesigning = false
      state.isGenerating = true
      break
      
    case 'execute':
      state.isGenerating = false
      state.isExecuting = true
      break
      
    case 'complete':
      state.isAnalyzing = false
      state.isDesigning = false
      state.isGenerating = false
      state.isExecuting = false
      break
  }
}

// 处理测试结果
const handleResults = (results) => {
  console.log('处理测试结果:', results)
  
  // 保存测试结果
  testResults.value = results
  
  // 处理测试统计数据
  if (results.test_result && typeof results.test_result === 'object') {
    const stats = results.test_result.stats || {}
    const duration = results.test_result.duration || 0
    const status = results.test_result.status
    const exitCode = results.test_result.exit_code
    
    // 更新执行统计信息
    state.executionStats = {
      total: stats.total || 0,
      passed: stats.passed || 0,
      failed: stats.failed || 0,
      error: stats.error || 0,
      skipped: stats.skipped || 0,
      duration: duration
    }
    
    // 如果没有统计信息，尝试从输出解析
    if (!stats || Object.keys(stats).length === 0) {
      parseTestStats(results.test_result.output)
    }
    
    // 测试完成通知
    notification({
      title: '测试执行完成',
      message: status === 'success' ? '测试成功完成' : '测试执行失败',
      type: status === 'success' ? 'success' : 'error',
      duration: 5000
    })
  }
  
  // 设置分析结果
  if (results.analysis) {
    analysisResult.value = results.analysis
    console.log('从handleResults设置分析报告, 长度:', results.analysis.length)
  }
  
  // 处理报告数据
  if (results.report_data) {
    if (results.report_data.analysis) {
      analysisResult.value = results.report_data.analysis
      console.log('从report_data设置分析报告')
    }
    
    if (results.report_data.html_report) {
      reportUrl.value = results.report_data.html_report
      state.isReportLoading = true
      console.log('从report_data设置HTML报告URL:', reportUrl.value)
    }
    
    if (results.report_data.allure_report) {
      allureReportUrl.value = results.report_data.allure_report
      state.isAllureLoading = true
      console.log('从report_data设置Allure报告URL:', allureReportUrl.value)
    }
  }
  
  // 如果测试结果中包含测试参数，则保存
  if (results.test_params) {
    Object.assign(testParams, results.test_params)
  }
  
  // 更新报告URL (作为备选)
  if (results.report_url && !reportUrl.value) {
    reportUrl.value = results.report_url
    state.isReportLoading = true // 设置HTML报告加载中状态
    console.log('设置HTML报告URL:', reportUrl.value)
  }
  
  // 更新Allure报告URL (作为备选)
  if (results.allure_report_url && !allureReportUrl.value) {
    allureReportUrl.value = results.allure_report_url
    state.isAllureLoading = true // 设置Allure报告加载中状态
    console.log('设置Allure报告URL:', allureReportUrl.value)
  }
  
  // 自动切换到结果标签页
  state.activeTab = 'results'
  
  // 完成执行
  state.isExecuting = false
  
  // 添加完成日志
  addLog('system', '测试执行完成', 'success')
  
  // 检查并记录报告状态
  const hasAnalysisReport = !!analysisResult.value;
  const hasHtmlReport = !!reportUrl.value;
  const hasAllureReport = !!allureReportUrl.value;
  
  console.log('报告状态检查:', {
    '分析报告': hasAnalysisReport,
    'HTML报告': hasHtmlReport,
    'Allure报告': hasAllureReport
  });
  
  if (hasAnalysisReport) {
    addLog('system', '分析报告已准备就绪，可以在分析报告标签中查看', 'info');
  }
  
  if (hasHtmlReport) {
    addLog('system', 'HTML报告已准备就绪，可以在HTML报告标签中查看', 'info');
  }
  
  if (hasAllureReport) {
    addLog('system', 'Allure报告已准备就绪，可以在Allure报告标签中查看', 'info');
  }
}

// 解析测试统计信息
const parseTestStats = (output) => {
  try {
    // 使用更复杂的正则表达式匹配不同格式的pytest输出
    const fullMatch = output.match(/(\d+) passed,?\s*(\d+) failed,?\s*(\d+) error(?:ed)?,?\s*(\d+) skipped/i)
    const simpleMatch = output.match(/(\d+) passed,?\s*(\d+) failed,?\s*(\d+) skipped/i)
    const durationMatch = output.match(/in\s+([\d\.]+)s/i)
    
    if (fullMatch) {
      state.executionStats.passed = parseInt(fullMatch[1]) || 0
      state.executionStats.failed = parseInt(fullMatch[2]) || 0
      state.executionStats.error = parseInt(fullMatch[3]) || 0
      state.executionStats.skipped = parseInt(fullMatch[4]) || 0
    } else if (simpleMatch) {
      state.executionStats.passed = parseInt(simpleMatch[1]) || 0
      state.executionStats.failed = parseInt(simpleMatch[2]) || 0
      state.executionStats.skipped = parseInt(simpleMatch[3]) || 0
      state.executionStats.error = 0
    }
    
    // 计算总数
    state.executionStats.total = 
      state.executionStats.passed + 
      state.executionStats.failed + 
      state.executionStats.error + 
      state.executionStats.skipped
    
    if (durationMatch) {
      state.executionStats.duration = parseFloat(durationMatch[1])
    }
  } catch (e) {
    console.error('解析测试统计信息出错:', e)
  }
}

// 处理错误
const handleError = (content, source) => {
  addLog(source, content, 'error')
  
  message({
    message: typeof content === 'string' ? content : JSON.stringify(content),
    type: 'error',
    showClose: true,
    duration: 5000
  })
  
  // 重置状态
  state.isAnalyzing = false
  state.isGenerating = false
  state.isExecuting = false
}

// 生成测试用例
const generateTestCases = () => {
  if (!isFormValid.value) {
    message.warning('请填写API文档URL和基础URL')
    return
  }
  
  console.log('开始API测试流程', state.apiDocsUrl, state.baseUrl)
  
  // 直接开始流程，不使用对话框确认
  startApiTestProcess()
}

// 开始API测试流程
const startApiTestProcess = () => {
  state.isLoading = true
  
  // 重置状态和关闭任何现有WebSocket连接
  if (webSocket.value) {
    webSocket.value.close()
    webSocket.value = null
  }
  
  // 清空之前的数据
  logMessages.value = []
  testResults.value = ''
  testCode.value = ''
  analysisResult.value = ''
  reportUrl.value = ''
  allureReportUrl.value = ''
  enhancedReportReady.value = false  // 重置增强报告状态
  
  // 确保立即切换到日志标签页并清空日志
  state.activeTab = 'logs'
  
  // 添加初始日志
  addLog('system', '正在开始API测试...', 'info')
  
  // 确保日志可见后再连接WebSocket
  nextTick(() => {
    connectWebSocket()
  })
}

// 切换编辑模式
const toggleEditMode = () => {
  if (!isEditing.value) {
    // 进入编辑模式，初始化可编辑代码
    editableTestCode.value = testCode.value
    isEditing.value = true
    
    // 延迟初始化编辑器，确保DOM已更新
    setTimeout(() => {
      initCodeEditor()
    }, 100)
  } else {
    // 退出编辑模式，提示是否保存
    dialog.warning({
      title: '退出编辑模式',
      content: '是否保存更改？未保存的更改将丢失。',
      positiveText: '保存',
      negativeText: '不保存',
      onPositiveClick: () => {
        saveTestCode()
        isEditing.value = false
        // 销毁编辑器实例
        if (codeEditor.value) {
          codeEditor.value.dispose()
          codeEditor.value = null
        }
      },
      onNegativeClick: () => {
        // 放弃更改
        editableTestCode.value = testCode.value
        isEditing.value = false
        // 销毁编辑器实例
        if (codeEditor.value) {
          codeEditor.value.dispose()
          codeEditor.value = null
        }
      }
    })
  }
}

// 初始化代码编辑器
const initCodeEditor = () => {
  nextTick(() => {
    const editorContainer = document.getElementById('monaco-editor-container')
    if (editorContainer) {
      try {
        // 确保编辑器容器可见
        editorContainer.style.height = '65vh'
        editorContainer.style.width = '100%'
        editorContainer.style.border = '1px solid #444'
        
        // 直接使用备用文本区域，不尝试加载Monaco
        const textArea = document.createElement('textarea')
        textArea.value = editableTestCode.value || ''
        textArea.style.width = '100%'
        textArea.style.height = '65vh'
        textArea.style.fontFamily = 'monospace'
        textArea.style.fontSize = '14px'
        textArea.style.backgroundColor = '#1e1e1e'
        textArea.style.color = '#f8f8f2'
        textArea.style.padding = '10px'
        textArea.style.border = '1px solid #444'
        textArea.style.borderRadius = '4px'
        textArea.addEventListener('input', (e) => {
          editableTestCode.value = e.target.value
        })
        
        // 清空容器并添加文本区域
        editorContainer.innerHTML = ''
        editorContainer.appendChild(textArea)
        console.log('使用简单文本编辑器初始化成功')
      } catch (e) {
        console.error('编辑器初始化错误:', e)
      }
    } else {
      console.error('找不到编辑器容器元素')
    }
  })
}

// 保存测试代码
const saveTestCode = () => {
  if (!editableTestCode.value) {
    message.warning('没有可保存的测试代码')
    return
  }
  
  // 更新测试代码
  testCode.value = editableTestCode.value
  
  // 发送更新后的代码到后端
  if (webSocket.value && webSocket.value.readyState === WebSocket.OPEN) {
    sendWSMessage({
      update_test_code: true,
      test_file_path: testFilePath.value,
      code: testCode.value
    })
    
    message.success('测试代码已保存')
  } else {
    message.error('WebSocket连接未建立，无法保存')
  }
}

// 执行测试前构建参数
  const buildTestParams = () => {
  const params = {
    timeout: testParams.timeout,
    retries: testParams.retries,
    parallel: testParams.parallel,
    verbose: testParams.verbose
  }
  
  // 处理标签
  if (testParams.tags) {
    params.tags = testParams.tags.split(',').map(tag => tag.trim())
  }
  
  // 处理自定义选项
  if (testParams.customOptions) {
    params.custom_options = testParams.customOptions
  }
  
  // 添加基础URL参数
  params.base_url = state.baseUrl
  
  // 添加本地执行器设置
  params.use_local_executor = state.useLocalExecutor
  
  return params
}

// 更新执行测试方法
const runTests = () => {
  // 如果没有测试文件路径，不能执行
  if (!testFilePath.value) {
    message.error('没有可执行的测试文件')
    return
  }
  
  const testParameters = buildTestParams()
  
  // 重置增强报告状态和报告错误状态
  enhancedReportReady.value = false
  state.allureLoadError = false
  state.htmlLoadError = false
  
  // 发送WebSocket消息，包含测试参数
  sendWSMessage({ 
    run_test: true, 
    test_file_path: testFilePath.value,
    test_params: testParameters
  })
  
  // 设置执行状态和切换到日志标签
  state.isExecuting = true
  state.activeTab = 'logs'
  
  // 添加系统日志指示测试开始执行
  addLog('system', `开始执行测试: ${testFilePath.value}`, 'info')
}

// 示例URL填充
const fillExampleUrls = () => {
  state.apiDocsUrl = 'http://localhost:8001/openapi.json'
  state.baseUrl = 'http://localhost:8001'
}

// 复制测试代码
const copyTestCode = () => {
  navigator.clipboard.writeText(testCode.value)
    .then(() => {
      message.success('测试代码已复制到剪贴板')
    })
    .catch(() => {
      message.error('复制失败，请手动复制')
    })
}

// 下载测试代码
const downloadTestCode = () => {
  const blob = new Blob([testCode.value], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'test_api.py'
  document.body.appendChild(a)
  a.click()
  URL.revokeObjectURL(url)
  document.body.removeChild(a)
}

// 复制conftest.py代码到剪贴板
const copyConftestCode = () => {
  navigator.clipboard.writeText(conftestCode.value)
    .then(() => {
      message.success('conftest.py代码已复制到剪贴板')
    })
    .catch(() => {
      message.error('复制失败，请手动复制')
    })
}

// 下载conftest.py代码
const downloadConftestCode = () => {
  const blob = new Blob([conftestCode.value], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'conftest.py'
  document.body.appendChild(a)
  a.click()
  URL.revokeObjectURL(url)
  document.body.removeChild(a)
}

// 监听日志更新，强制视图更新并滚动
watch(logMessages, (newValue, oldValue) => {
  console.log(`日志消息数量变化: ${oldValue.length} -> ${newValue.length}`)
  // 触发强制重新渲染
  nextTick(() => {
    if (newValue.length > oldValue.length) {
      scrollToBottom()
    }
  })
}, { deep: true })

// 优化JSON处理，避免使用util._extend
const deepClone = (obj) => {
  try {
    return JSON.parse(JSON.stringify(obj))
  } catch (e) {
    console.error('深度克隆对象失败:', e)
    return obj
  }
}

// 组件卸载前关闭WebSocket连接
onBeforeUnmount(() => {
  if (webSocket.value) {
    webSocket.value.close()
  }
})

// 检查内容是否可能是Markdown
const isMarkdown = (content) => {
  if (!content || typeof content !== 'string') return false;
  
  // Markdown常见标记
  return content.includes('##') || 
         content.includes('```') || 
         content.includes('- ') || 
         content.includes('1. ') ||
         content.includes('> ') || // 引用块
         /\*\*.*\*\*/.test(content) || // 粗体
         /\*.*\*/.test(content) || // 斜体
         /\[.*\]\(.*\)/.test(content) || // 链接
         /^#\s+.*$/m.test(content) || // 标题
         /^---+$/m.test(content) || // 分隔线
         /^\|.*\|.*\|/m.test(content); // 表格
}
// 渲染Markdown内容
const renderMarkdown = (content) => {
  try {
    return marked(content, { breaks: true, gfm: true });
  } catch (e) {
    console.error('Markdown渲染失败:', e);
    return content;
  }
}

// 格式化日志内容，处理特殊字符和代码块
const formatLogContent = (content, source) => {
  if (!content) return ''
  
  // 确保content是字符串
  const strContent = typeof content === 'string' 
    ? content 
    : JSON.stringify(content, null, 2)
  
  try {
    // 判断源是否可能是Markdown内容的
    const markdownSources = ['api_analyzer', 'test_generator', 'test_result_analyzer', 'result_analyzer', 'report_enhancer', 'test_case_designer'];
    const isMarkdownSource = markdownSources.includes(source);

    // 尝试解析JSON并格式化 - JSON优先级最高
    if (strContent.trim().startsWith('{') || strContent.trim().startsWith('[')) {
      try {
        const jsonObj = JSON.parse(strContent)
        // 美化JSON并增加语法高亮的类名
        return `<pre class="log-json">${JSON.stringify(jsonObj, null, 2)
          .replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, 
          function (match) {
            let cls = 'json-number';
            if (/^"/.test(match)) {
              if (/:$/.test(match)) {
                cls = 'json-key';
              } else {
                cls = 'json-string';
              }
            } else if (/true|false/.test(match)) {
              cls = 'json-boolean';
            } else if (/null/.test(match)) {
              cls = 'json-null';
            }
            return '<span class="' + cls + '">' + match + '</span>';
          })}</pre>`
      } catch (e) {
        // 如果不是有效JSON，继续进行其他处理
        console.log('不是有效JSON，继续处理', e)
      }
    }

    // 检查是否Python代码块
    if (source === 'test_generator' || source === 'test_executor') {
      if (
        (strContent.includes('def ') && strContent.includes(':')) || 
        (strContent.includes('import ') && strContent.includes('from ')) ||
        /class\s+\w+\(.*\):/.test(strContent)
      ) {
        // 看起来是Python代码，进行简单的语法高亮
        const highlightedCode = strContent
          .replace(/\b(def|class|if|else|elif|for|while|try|except|finally|import|from|return|yield|as|with|in|is|not|and|or|True|False|None)\b/g, '<span class="python-keyword">$1</span>')
          .replace(/(?<![a-zA-Z0-9_])(_[a-zA-Z][a-zA-Z0-9_]*)/g, '<span class="python-private">$1</span>')
          .replace(/(["'])(?:(?=(\\?))\2.)*?\1/g, '<span class="python-string">$&</span>')
          .replace(/(?<![a-zA-Z0-9_])(\d+(?:\.\d+)?)/g, '<span class="python-number">$1</span>')
          .replace(/(#.*$)/gm, '<span class="python-comment">$1</span>')
          .replace(/\n/g, '<br/>');
        
        return `<pre class="log-python-code">${highlightedCode}</pre>`;
      }
    }

    // 检查内容是否符合Markdown格式
    if (isMarkdown(strContent)) {
      // 对于确定是Markdown内容源或者内容包含明显Markdown标记的情况
      if (isMarkdownSource || strContent.includes('##') || strContent.includes('```')) {
        const renderedMarkdown = renderMarkdown(strContent);
        return renderedMarkdown;
      }
    }

    // 如果内容包含代码块但不是完整Markdown
    if (strContent.includes('```')) {
      // 处理代码块
      const codeBlockRegex = /```(python)?\n?([\s\S]*?)```/g;
      const contentWithCodeBlocks = strContent.replace(/\n/g, '<br/>').replace(codeBlockRegex, (match, lang, code) => {
        if (lang === 'python') {
          // 对Python代码进行简单的语法高亮
          const highlightedCode = code
            .replace(/\b(def|class|if|else|elif|for|while|try|except|finally|import|from|return|yield|as|with|in|is|not|and|or|True|False|None)\b/g, '<span class="python-keyword">$1</span>')
            .replace(/(?<![a-zA-Z0-9_])(_[a-zA-Z][a-zA-Z0-9_]*)/g, '<span class="python-private">$1</span>')
            .replace(/(["'])(?:(?=(\\?))\2.)*?\1/g, '<span class="python-string">$&</span>')
            .replace(/(?<![a-zA-Z0-9_])(\d+(?:\.\d+)?)/g, '<span class="python-number">$1</span>')
            .replace(/(#.*$)/gm, '<span class="python-comment">$1</span>');
          
          return `<pre class="log-python-code">${highlightedCode}</pre>`;
        }
        return `<pre class="log-code">${code}</pre>`;
      });
      return contentWithCodeBlocks;
    }

    // 如果是普通文本，只进行换行处理
    return strContent.replace(/\n/g, '<br/>');
  } catch(e) {
    console.error('格式化日志内容出错', e);
    return strContent; // 返回原始内容
  }
}

// 切换卡片样式类名
const toggleConfigCollapse = () => {
  state.configCollapsed = !state.configCollapsed;
  
  // 添加一个微小延迟，确保DOM更新
  setTimeout(() => {
    const cardElements = document.querySelectorAll('.config-section .n-card')
    cardElements.forEach(card => {
      if (state.configCollapsed) {
        card.classList.add('n-card-collapsed')
      } else {
        card.classList.remove('n-card-collapsed')
      }
    })
  }, 0)
}

// 脚本部分添加
const renderIcon = (icon) => {
  return () => h(NIcon, null, { default: () => h(icon) })
}

// 组件挂载时初始化
onMounted(() => {
  // 在DOM更新后，确保配置区域按照初始状态折叠
  nextTick(() => {
    if (state.configCollapsed) {
      const cardElements = document.querySelectorAll('.config-section .n-card')
      cardElements.forEach(card => {
        card.classList.add('n-card-collapsed')
      })
    }
  })
})

// 刷新报告
const refreshReport = (reportType) => {
  try {
    console.log(`刷新${reportType}报告`)
    
    // 先设置加载状态
    if (reportType === 'allure') {
      if (!allureReportUrl.value) {
        message.error('没有可用的Allure报告URL')
        return
      }
      state.isAllureLoading = true
      state.allureLoadError = false // 重置错误状态
    } else {
      if (!reportUrl.value) {
        message.error('没有可用的HTML报告URL')
        return
      }
      state.isReportLoading = true
    }
    
    // 选择正确的URL
    const url = reportType === 'allure' ? allureReportUrl.value : reportUrl.value
    
    if (!url) {
      message.error(`没有可用的${reportType === 'allure' ? 'Allure' : 'HTML'}报告URL`)
      return
    }
    
    // 获取iframe引用
    const iframeRef = reportType === 'allure' ? allureIframe.value : reportIframe.value
    
    if (iframeRef) {
      // 确保URL是完整的URL
      let fullUrl = url
      
      // 使用正确的URL处理函数
      if (reportType === 'allure' && typeof processAllureReportUrl === 'function') {
        // 对于Allure报告，使用processAllureReportUrl处理
        fullUrl = processAllureReportUrl(url)
      } else if (reportType !== 'allure' && typeof getFullUrl === 'function') {
        // 对于HTML报告，使用getFullUrl处理
        fullUrl = getFullUrl(url)
      }
      
      // 添加时间戳参数，强制刷新
      const timestampedUrl = `${fullUrl}${fullUrl.includes('?') ? '&' : '?'}t=${Date.now()}`
      console.log(`设置iframe.src: ${timestampedUrl}`)
      
      // 提示正在刷新
      message.info(`正在刷新${reportType === 'allure' ? 'Allure' : 'HTML'}报告...`)
      
      // 设置iframe源
      iframeRef.src = timestampedUrl
      
      // 检查URL是否有效
      checkUrlValidity(fullUrl, (isValid) => {
        if (!isValid) {
          message.error(`报告URL不可访问: ${fullUrl}`)
          if (reportType === 'allure') {
            state.isAllureLoading = false
            state.allureLoadError = true // 设置错误状态
          } else {
            state.isReportLoading = false
          }
        }
      })
    } else {
      console.error('找不到iframe元素')
      message.error(`刷新失败: 找不到${reportType === 'allure' ? 'Allure' : 'HTML'}报告iframe`)
      
      // 重置加载状态
      if (reportType === 'allure') {
        state.isAllureLoading = false
      } else {
        state.isReportLoading = false
      }
    }
  } catch (error) {
    console.error(`刷新报告出错:`, error)
    message.error(`刷新报告出错: ${error.message}`)
    
    // 重置加载状态
    if (reportType === 'allure') {
      state.isAllureLoading = false
    } else {
      state.isReportLoading = false
    }
  }
}

// 检查URL是否有效
const checkUrlValidity = (url, callback) => {
  if (!url) {
    callback(false)
    return
  }
  
  console.log(`检查URL有效性: ${url}`)
  
  // 如果是以/static开头的URL，认为它是有效的
  if (url.startsWith('/static/')) {
    console.log(`静态资源URL，跳过有效性检查: ${url}`)
    callback(true)
    return
  }
  
  // 如果URL不是以http开头，构建完整的URL
  const fullUrl = url.startsWith('http') ? url : window.location.origin + url
  console.log(`构建完整URL进行检查: ${fullUrl}`)
  
  // 尝试发送HEAD请求检查资源是否存在
  fetch(fullUrl, { method: 'HEAD' })
    .then(response => {
      console.log(`URL检查结果: ${fullUrl}, 状态: ${response.status}`)
      callback(response.ok)
    })
    .catch(error => {
      console.error(`URL检查失败: ${fullUrl}`, error)
      
      // 对于静态资源，即使请求失败也当作成功
      if (url.startsWith('/static/')) {
        console.log('静态资源URL请求失败，但仍视为有效')
        callback(true)
      } else {
        callback(false)
      }
    })
}

// 显示警告对话框
const alert = (message) => {
  dialog.info({
    title: '调试信息',
    content: message,
    positiveText: '确定'
  })
}

// 获取进度条颜色方法
const getProgressBarColor = (passRate) => {
  if (passRate >= 0.9) return '#67c23a';  // 绿色，通过率≥90%
  if (passRate >= 0.7) return '#e6a23c';  // 橙色，通过率≥70%
  return '#f56c6c';  // 红色，通过率<70%
}

// 处理HTML报告标签页内容加载
const iframeLoaded = (reportType) => {
  console.log(`${reportType}报告加载完成`)
  if (reportType === 'html') {
    state.isReportLoading = false
    state.htmlLoadError = false // 重置HTML报告错误状态
  } else if (reportType === 'allure') {
    state.isAllureLoading = false
    state.allureLoadError = false // 重置错误状态
    
    // 检查Allure报告是否正确加载，如果iframe内容为空，可能需要额外处理
    const allureIframeEl = allureIframe.value
    if (allureIframeEl) {
      try {
        // 尝试访问iframe内容，检查是否正确加载
        const iframeDoc = allureIframeEl.contentDocument || allureIframeEl.contentWindow.document
        if (!iframeDoc || !iframeDoc.body || !iframeDoc.body.innerHTML) {
          console.warn('Allure报告iframe内容为空，可能未正确加载')
          // 尝试重新加载
          const fullUrl = processAllureReportUrl(allureReportUrl.value)
          setTimeout(() => {
            console.log('尝试重新加载Allure报告...')
            allureIframeEl.src = `${fullUrl}?t=${Date.now()}`
          }, 500)
        } else {
          console.log('Allure报告iframe成功加载内容')
        }
      } catch (e) {
        console.error('检查Allure报告iframe内容时出错:', e)
      }
    }
  }
  message.success(`${reportType === 'allure' ? 'Allure' : 'HTML'}报告加载完成`)
}

// 获取完整URL（处理静态文件路径）
const getFullUrl = (path) => {
  if (!path) return '';
  
  // 记录函数调用来源
  console.log(`getFullUrl调用: path=${path}`);
  
  // 如果是Allure报告URL(以allure_开头的静态路径)，应该使用processAllureReportUrl处理
  if (typeof path === 'string' && path.includes('/static/allure_')) {
    console.log(`检测到Allure报告URL，应该使用processAllureReportUrl处理: ${path}`);
    // 不要处理，直接返回
    return path;
  }
  
  // 如果路径以http开头，说明是完整URL，直接返回
  if (path.startsWith('http')) {
    return path;
  }
  
  // 如果是相对路径，拼接当前域名和端口
  const baseUrl = window.location.origin;
  
  // 保留查询参数，这些参数可能是必要的时间戳或其他控制参数
  // 之前删除查询参数会导致报告无法正常显示
  
  console.log(`转换路径: ${path} -> ${baseUrl}${path}`);
  return `${baseUrl}${path}`;
}

// 在iframe报告加载前添加日志
const inspectReportUrl = () => {
  // 检查当前标签页所对应的报告URL
  const currentTab = state.activeTab;
  
  if (currentTab === 'report' && reportUrl.value) {
    // 只检查HTML报告URL
    const htmlFullUrl = getFullUrl(reportUrl.value);
    
    console.log('当前HTML报告URL信息:');
    console.log(`HTML报告URL: ${reportUrl.value}`);
    console.log(`HTML报告完整URL: ${htmlFullUrl}`);
    
    // 添加系统日志
    addLog('system', `HTML报告URL信息: ${reportUrl.value}`, 'info');
    
    // 发送HEAD请求检查HTML报告URL是否可访问
    fetch(htmlFullUrl, { method: 'HEAD' })
      .then(resp => addLog('system', `HTML报告URL检查: ${resp.status} ${resp.ok ? '可访问' : '不可访问'}`, resp.ok ? 'info' : 'warning'))
      .catch(err => addLog('system', `HTML报告URL检查失败: ${err.message}`, 'error'));
  } 
  else if (currentTab === 'allure-report' && allureReportUrl.value) {
    // 只检查Allure报告URL
    const allureFullUrl = processAllureReportUrl(allureReportUrl.value);
    
    console.log('当前Allure报告URL信息:');
    console.log(`Allure报告URL: ${allureReportUrl.value}`);
    console.log(`Allure报告完整URL: ${allureFullUrl}`);
    
    // 添加系统日志
    addLog('system', `Allure报告URL信息: ${allureReportUrl.value}`, 'info');
    
    // 发送HEAD请求检查Allure报告URL是否可访问
    fetch(allureFullUrl, { method: 'HEAD' })
      .then(resp => addLog('system', `Allure报告URL检查: ${resp.status} ${resp.ok ? '可访问' : '不可访问'}`, resp.ok ? 'info' : 'warning'))
      .catch(err => addLog('system', `Allure报告URL检查失败: ${err.message}`, 'error'));
  }
  // 不要检查不相关的标签页对应的URL
}

// 监听标签页切换，初始化编辑器或报告加载状态
watch(() => state.activeTab, (newTab) => {
  if (newTab === 'code') {
    console.log('切换到代码标签页')
    // 不在此处自动初始化编辑器，而是等待用户点击编辑按钮
  } else if (newTab === 'report' && reportUrl.value) {
    console.log('切换到HTML报告标签页')
    // 如果是第一次切换到报告标签页，确保加载状态为true
    state.isReportLoading = true
    
    // 确保报告iframe显示正确的URL
    const reportIframeEl = reportIframe.value
    if (reportIframeEl) {
      const fullUrl = getFullUrl(reportUrl.value)
      console.log(`设置HTML报告iframe.src: ${fullUrl}`)
      reportIframeEl.src = fullUrl
    }
    
    // 检查报告URL状态
    inspectReportUrl()
  } else if (newTab === 'allure-report' && allureReportUrl.value) {
    console.log('切换到Allure报告标签页')
    // 如果是第一次切换到Allure报告标签页，确保加载状态为true
    state.isAllureLoading = true
    
    // 确保Allure报告iframe显示正确的URL
    const allureIframeEl = allureIframe.value
    if (allureIframeEl) {
      const fullUrl = processAllureReportUrl(allureReportUrl.value)
      console.log(`设置Allure报告iframe.src: ${fullUrl}`)
      allureIframeEl.src = fullUrl
      
      // 添加延迟检查，确保iframe正确加载
      setTimeout(() => {
        if (state.isAllureLoading) {
          // 如果5秒后仍在加载，尝试重新设置src
          console.log('Allure报告加载超时，尝试重新加载')
          allureIframeEl.src = `${fullUrl}?t=${Date.now()}`
        }
      }, 5000)
    }
    
    // 检查报告URL状态
    inspectReportUrl()
  }
})

// 检查WebSocket状态
const checkWebSocketStatus = () => {
  let status = '未知';
  let details = '';
  
  if (!webSocket.value) {
    status = '未创建';
    details = '尚未创建WebSocket连接';
  } else {
    switch (webSocket.value.readyState) {
      case WebSocket.CONNECTING:
        status = '连接中';
        details = '正在尝试连接服务器';
        break;
      case WebSocket.OPEN:
        status = '已连接';
        details = '连接已建立并可以通信';
        break;
      case WebSocket.CLOSING:
        status = '关闭中';
        details = '连接正在关闭';
        break;
      case WebSocket.CLOSED:
        status = '已关闭';
        details = '连接已关闭或无法建立';
        break;
    }
  }
  
  message.info(`WebSocket状态: ${status}\n${details}`);
  addLog('system', `WebSocket状态检查: ${status} - ${details}`, 'info');
  
  // 检查后端API可访问
  axios.get('/api/v1/agent/health')
    .then(response => {
      addLog('system', `API健康检查: ${JSON.stringify(response.data)}`, 'info');
    })
    .catch(error => {
      addLog('system', `API健康检查失败: ${error.message}`, 'error');
    });
}



// 处理测试用例展示，将分隔符转换为卡片展示
const processTestCases = (content) => {
  if (!content) return '';
  
  // 分隔符
  const separator = "===TEST_CASE_SEPARATOR===";
  
  // 如果内容中不包含分隔符，则直接返回Markdown渲染结果
  if (!content.includes(separator)) {
    return renderMarkdown(content);
  }
  
  // 按分隔符拆分内容
  const parts = content.split(separator);
  
  // 移除第一个元素（如果为空)
  if (parts[0].trim() === '') {
    parts.shift();
  }
  
  // 为每个测试用例生成HTML
  let html = `<div class="test-cases-wrapper">`;
  
  parts.forEach((part, index) => {
    if (part.trim()) {
      // 提取测试用例ID
      const idMatch = part.match(/测试用例\s*ID:\s*(TC-\d+)/i);
      const id = idMatch ? idMatch[1] : `用例${index + 1}`;
      
      // 提取测试用例类型
      const typeMatch = part.match(/\*\*类型\*\*:\s*([^\n]+)/);
      const type = typeMatch ? typeMatch[1].trim() : '';
      
      // 确定测试用例类型的标签颜色
      let tagType = 'default';
      if (type.includes('功能')) tagType = 'success';
      else if (type.includes('边界')) tagType = 'info';
      else if (type.includes('异常') || type.includes('负向')) tagType = 'warning';
      else if (type.includes('安全')) tagType = 'error';
      else if (type.includes('性能') || type.includes('并发')) tagType = 'primary';
      
      // 生成测试用例卡片
      html += `
        <div class="test-case-card">
          <div class="test-case-header">
            <span class="test-case-id">${id}</span>
            <span class="test-case-type-tag type-${tagType}">${type}</span>
          </div>
          <div class="test-case-content">
            ${renderMarkdown(part)}
          </div>
        </div>
      `;
    }
  });
  
  html += `</div>`;
  return html;
}

// 处理日志消息
const handleLog = (logSource, safeContent) => {
  console.log(`处理日志消息 - 来源: ${logSource}, 内容长度: ${safeContent?.length || 0}`)
  
  // 检查是否应该追加到现有消息
  const shouldAppend = logSource === 'api_analyzer' || 
                     logSource === 'test_generator' || 
                     logSource === 'test_executor' || 
                     logSource === 'test_result_analyzer' ||
                     logSource === 'result_analyzer' ||
                     logSource === 'report_enhancer' ||
                     logSource === 'test_case_designer'
  
  // 直接添加日志内容（不是系统消息）
  if (shouldAppend && currentStreamSources[logSource] !== undefined && 
      currentStreamSources[logSource] >= 0 && 
      currentStreamSources[logSource] < logMessages.value.length &&
      logMessages.value[currentStreamSources[logSource]] &&
      logMessages.value[currentStreamSources[logSource]].content !== undefined) {
    
    // 特殊处理：如果内容仅包含标点符号，不要添加换行
    const isPunctuation = /^[,.!?;:'")\]}]+$/.test(safeContent.trim());
    
    // 智能判断是否需要添加换行符
    const needNewline = 
      !isPunctuation && (
        (logSource === 'test_executor' && safeContent.trim().startsWith('===')) || // 测试分隔标记
        (safeContent.includes('\n') && safeContent.trim().length > 3) || // 内容本身包含换行且不是仅仅一个换行符
        safeContent.trim().startsWith('Step') || // 步骤信息
        /^(PASSED|FAILED|ERROR|SKIPPED)/.test(safeContent.trim())); // 测试结果标记
    
    logMessages.value[currentStreamSources[logSource]].content += 
      (needNewline ? '\n' : '') + safeContent;
    
    scrollToBottom();
  } else {
    console.log(`创建新消息 - 来源: ${logSource}`)
    // 重置当前源的流式状态，创建新消息
    currentStreamSources[logSource] = null
    addLog(logSource, safeContent, 'info')
  }
}

// 切换全屏
const toggleFullScreen = (iframeId) => {
  const iframe = iframeId === 'reportIframe' ? reportIframe.value : allureIframe.value
  
  if (iframe) {
    if (iframe.requestFullscreen) {
      iframe.requestFullscreen()
    } else if (iframe.mozRequestFullScreen) {
      iframe.mozRequestFullScreen()
    } else if (iframe.webkitRequestFullscreen) {
      iframe.webkitRequestFullscreen()
    } else if (iframe.msRequestFullscreen) {
      iframe.msRequestFullscreen()
    }
  } else {
    console.error(`找不到iframe元素: ${iframeId}`)
    message.error('无法进入全屏模式')
  }
}

// 加载状态
const isReportLoading = ref(true)
const isAllureLoading = ref(true)

// 报告iframe
const reportIframe = ref(null)
const allureIframe = ref(null)

// 在setup函数中添加handleResize函数定义
const handleResize = () => {
  // 调整大小逻辑
  if (chartInstance.value) {
    chartInstance.value.resize();
  }
};

// 或者修改cleanupAllResources函数，移除对handleResize的调用
const cleanupAllResources = () => {
  // 注释掉或删除对handleResize的引用
  // window.removeEventListener('resize', handleResize);
  
  // 其余清理代码保持不变
  if (socketInstance.value) {
    socketInstance.value.close();
    socketInstance.value = null;
  }
  // ...其他资源清理
};

// 路由守卫定义
window.__testGeneratorRouteGuard = (to, from, next) => {
  try {
    if (from.path.includes('/testing/api')) {
      console.log('正在清理资源...');
      cleanupAllResources();
      console.log('资源清理完成');
    }
  } catch (error) {
    console.error('资源清理错误:', error);
  } finally {
    // 确保无论如何都会调用next()
    next();
  }
};

// 报告标签和内容显示逻辑
function handleTestResult(message) {
  if (message.type === 'result') {
    // 启用报告标签
    const hasAnalysisReport = !!message.has_analysis_report;
    const hasHtmlReport = !!message.has_html_report;
    const hasAllureReport = !!message.has_allure_report;
    
    // 更新UI状态，启用相应的报告标签
    setReportTabsState({
      analysis: hasAnalysisReport,
      html: hasHtmlReport,
      allure: hasAllureReport
    });
    
    // 保存报告内容
    if (message.content && message.content.report_data) {
      const reportData = message.content.report_data;
      
      // 存储各种报告内容
      if (hasAnalysisReport) {
        setAnalysisReport(reportData.analysis);
      }
      
      if (hasHtmlReport) {
        setHtmlReport(reportData.html_report);
      }
      
      if (hasAllureReport) {
        setAllureReport(reportData.allure_report);
      }
    }
  }
}

// 特殊处理Allure报告URL
const processAllureReportUrl = (url) => {
  if (!url) return '';
  
  // 记录函数调用来源
  console.log(`processAllureReportUrl调用: url=${url}`);
  
  // 如果URL已经是完整的http路径，直接返回
  if (url.startsWith('http')) {
    console.log(`使用完整URL: ${url}`);
    return url;
  }
  
  // 处理Windows路径分隔符
  let normalizedPath = url.replace(/\\/g, '/');
  
  // 确保路径以/开头
  if (!normalizedPath.startsWith('/')) {
    normalizedPath = '/' + normalizedPath;
  }

  // 检查是否是/static/开头的路径（前端static目录下的文件）
  if (normalizedPath.startsWith('/static/')) {
    // 直接使用相对路径，加上当前origin，保留查询参数
    const baseUrl = window.location.origin;
    
    // 如果路径不以/index.html结尾，添加index.html
    if (!normalizedPath.endsWith('/index.html') && normalizedPath.includes('/allure_')) {
      normalizedPath = normalizedPath + '/index.html';
      console.log(`添加index.html: ${normalizedPath}`);
    }
    
    const fullUrl = `${baseUrl}${normalizedPath}`;
    console.log(`使用前端static文件: ${normalizedPath} -> ${fullUrl}`);
    return fullUrl;
  }
  
  // 处理其他情况 - 默认使用后端URL (9999端口)，保留查询参数
  const backendBaseUrl = 'http://localhost:9999';
  
  // 如果路径不以/index.html结尾，添加index.html
  if (!normalizedPath.endsWith('/index.html') && normalizedPath.includes('/allure_')) {
    normalizedPath = normalizedPath + '/index.html';
    console.log(`添加index.html: ${normalizedPath}`);
  }
  
  const fullUrl = `${backendBaseUrl}${normalizedPath}`;
  console.log(`使用后端API文件: ${normalizedPath} -> ${fullUrl}`);
  return fullUrl;
}

// 处理Allure报告加载错误
const handleIframeError = (reportType) => {
  console.error(`${reportType}报告加载失败`)
  
  if (reportType === 'allure') {
    state.allureLoadError = true
    
    // 获取完整URL
    const fullUrl = processAllureReportUrl(allureReportUrl.value)
    
    // 显示错误信息并提供直接链接
    message.error('Allure报告加载失败，尝试使用直接访问链接')
    message.error(`<a href="${fullUrl}" target="_blank">${fullUrl}</a>`)
    
    // 尝试自动重新加载一次
    setTimeout(() => {
      const allureIframeEl = allureIframe.value
      if (allureIframeEl) {
        console.log('尝试自动重新加载Allure报告...')
        // 添加额外参数强制刷新
        allureIframeEl.src = `${fullUrl}?forceRefresh=true&t=${Date.now()}`
      }
    }, 1000)
  } else if (reportType === 'html') {
    // 处理HTML报告加载错误
    state.htmlLoadError = true
    
    const fullUrl = getFullUrl(reportUrl.value)
    message.error('HTML报告加载失败，尝试使用直接访问链接')
    message.error(`<a href="${fullUrl}" target="_blank">${fullUrl}</a>`)
    
    // 尝试自动重新加载一次
    setTimeout(() => {
      const reportIframeEl = reportIframe.value
      if (reportIframeEl) {
        console.log('尝试自动重新加载HTML报告...')
        reportIframeEl.src = `${fullUrl}?forceRefresh=true&t=${Date.now()}`
      }
    }, 1000)
  }
}

// 显示Allure报告直接链接
const showAllureDirectLink = () => {
  dialog.info({
    title: 'Allure报告直接链接',
    content: `请使用以下链接直接访问Allure报告：<a href="${processAllureReportUrl(allureReportUrl.value)}" target="_blank">${processAllureReportUrl(allureReportUrl.value)}</a>`,
    positiveText: '确定',
    onPositiveClick: () => {
      // 用户点击确定后，可以在这里添加一些额外的操作
    }
  })
}

// 直接打开Allure报告（绕过iframe）
const openAllureReportDirectly = () => {
  const url = processAllureReportUrl(allureReportUrl.value);
  if (url) {
    console.log(`直接打开Allure报告: ${url}`);
    window.open(url, '_blank');
    message.success('已在新标签页打开Allure报告');
  } else {
    message.error('Allure报告URL不可用');
  }
}

// 直接打开HTML报告（绕过iframe）
const openHtmlReportDirectly = () => {
  const url = getFullUrl(reportUrl.value);
  if (url) {
    console.log(`直接打开HTML报告: ${url}`);
    window.open(url, '_blank');
    message.success('已在新标签页打开HTML报告');
  } else {
    message.error('HTML报告URL不可用');
  }
}

// 重置状态
const resetState = () => {
  // 重置基本配置
  state.apiDocsUrl = ''
  state.baseUrl = ''
  state.apiDocSupplement = ''
  state.testFocus = ''
  
  // 重置进度信息
  state.progress.stage = 'idle'
  state.progress.percentage = 0
  state.progress.message = ''
  
  // 重置执行状态
  state.isAnalyzing = false
  state.isDesigning = false
  state.isGenerating = false
  state.isExecuting = false
  
  // 重置报告加载状态
  state.isReportLoading = false
  state.isAllureLoading = false
  state.htmlLoadError = false
  state.allureLoadError = false
  
  // 重置执行统计
  state.executionStats = {
    total: 0,
    passed: 0,
    failed: 0,
    skipped: 0,
    duration: 0
  }
  
  // 重置测试数据
  testResults.value = ''
  testCode.value = ''
  editableTestCode.value = ''
  analysisResult.value = ''
  testFilePath.value = ''
  reportUrl.value = ''
  allureReportUrl.value = ''
  testCases.value = ''
  testCaseMetadata.value = null
  
  // 清空日志
  logMessages.value = []
  
  // 生成新的客户端ID
  state.clientId = uuidv4()
  
  // 添加初始化日志
  addLog('system', '应用状态已重置', 'info')
}
</script>

<template>
  <div class="api-test-container">
    <!-- API配置区域 - 可折?-->
    <n-card class="config-section" :class="{'collapsed': state.configCollapsed}">
      <template #header>
        <div class="config-header" @click="toggleConfigCollapse">
          <span class="config-title">API测试配置</span>
          <n-icon :size="20" class="collapse-icon">
            <chevron-up-outline v-if="!state.configCollapsed" />
            <chevron-down-outline v-else />
          </n-icon>
        </div>
      </template>
      
      <div :class="['config-content', {'collapsed': state.configCollapsed}]">
        <n-form :model="state" label-placement="left" :label-width="100" v-show="!state.configCollapsed">
          <n-grid :cols="1">
            <n-grid-item>
              <n-form-item label="API文档URL" required>
                <n-input 
                  v-model:value="state.apiDocsUrl" 
                  placeholder="输入OpenAPI格式文档URL"
                  clearable
                />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="API基础URL" required>
                <n-input 
                  v-model:value="state.baseUrl" 
                  placeholder="API服务器基础URL，如http://localhost:8001"
                  clearable
                />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="接口补充说明">
                <n-input 
                  v-model:value="state.apiDocSupplement" 
                  type="textarea"
                  placeholder="输入对API文档的补充说明，帮助更准确分析API"
                  clearable
                />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="测试重点">
                <n-input 
                  v-model:value="state.testFocus" 
                  placeholder="输入需要重点测试的功能点或接口，例如：用户注册、数据验证"
                  clearable
                />
              </n-form-item>
            </n-grid-item>
          </n-grid>
          
          <div class="action-row">
            <div class="checkbox-group">
              <n-checkbox v-model:checked="state.enableReview">启用测试用例评审</n-checkbox>
              <n-checkbox v-model:checked="state.userReview" :disabled="!state.enableReview">
                用户参与评审
              </n-checkbox>
              <n-checkbox v-model:checked="state.useLocalExecutor">使用本地执行器</n-checkbox>
            </div>
            
            <div class="button-group">
              <n-button 
                type="primary" 
                @click="generateTestCases" 
                :loading="state.isLoading"
                :disabled="!isFormValid || state.isConnected"
              >
                开始API测试
              </n-button>
              
              <n-button 
                type="success" 
                @click="runTests" 
                :disabled="!canRunTests"
              >
                执行测试
              </n-button>
              
              <n-button text @click="fillExampleUrls">
                填充示例
              </n-button>
              
              <n-tooltip trigger="hover">
                <template #trigger>
                  <n-button text @click="checkWebSocketStatus">
                    <template #icon><connection-icon /></template>
                  </n-button>
                </template>
                检查连接状?              </n-tooltip>
            </div>
          </div>
        </n-form>
      </div>
    </n-card>

    <!-- 进度?-->
    <n-card v-if="state.progress.stage !== 'idle'" class="progress-section">
      <n-grid :cols="24" :x-gap="20">
        <n-grid-item :span="18">
          <n-progress 
            :percentage="state.progress.percentage" 
            :status="statusColor"
            :indicator-placement="'inside'"
            :height="18"
            class="progress-bar"
          />
        </n-grid-item>
        <n-grid-item :span="6" class="progress-text">
          <p>{{ state.progress.message || '正在处理...' }}</p>
        </n-grid-item>
      </n-grid>
    </n-card>

    <!-- 测试结果区域 -->
    <n-card class="result-section">
      <template #header>
        <div class="card-header">
          <n-tabs v-model:value="state.activeTab">
            <n-tab-pane name="logs" tab="执行日志">
              <template #tab>
                <div class="tab-content">
                  <n-icon class="tab-icon" size="16"><document-icon /></n-icon>
                  <span>执行日志</span>
                </div>
              </template>
            </n-tab-pane>
            
            <n-tab-pane name="testcases" tab="测试用例" :disabled="!testCases">
              <template #tab>
                <div class="tab-content">
                  <n-icon class="tab-icon" size="16"><DocumentTextOutline /></n-icon>
                  <span>测试用例</span>
                </div>
              </template>
            </n-tab-pane>
            
            <n-tab-pane name="code" tab="测试代码" :disabled="!testCode">
              <template #tab>
                <div class="tab-content">
                  <n-icon class="tab-icon" size="16"><code-icon /></n-icon>
                  <span>测试代码</span>
                </div>
              </template>
            </n-tab-pane>
            
            <n-tab-pane name="params" tab="参数配置" :disabled="!testFilePath">
              <template #tab>
                <div class="tab-content">
                  <n-icon class="tab-icon" size="16"><settings-icon /></n-icon>
                  <span>参数配置</span>
                </div>
              </template>
            </n-tab-pane>
            
            <n-tab-pane name="results" tab="测试结果" :disabled="!testResults">
              <template #tab>
                <div class="tab-content">
                  <n-icon class="tab-icon" size="16"><chart-icon /></n-icon>
                  <span>测试结果</span>
                </div>
              </template>
            </n-tab-pane>
            
            <n-tab-pane name="allure-report" tab="Allure报告" :disabled="!allureReportUrl">
              <template #tab>
                <div class="tab-content">
                  <n-icon class="tab-icon" size="16"><chart-icon /></n-icon>
                  <span>Allure报告</span>
                </div>
              </template>
            </n-tab-pane>
            
            <n-tab-pane name="analysis" tab="分析报告" :disabled="!analysisResult">
              <template #tab>
                <div class="tab-content">
                  <n-icon class="tab-icon" size="16"><file-icon /></n-icon>
                  <span>分析报告</span>
                </div>
              </template>
            </n-tab-pane>
            
            <n-tab-pane name="report" tab="增强报告" :disabled="!enhancedReportReady">
              <template #tab>
                <div class="tab-content">
                  <n-icon class="tab-icon" size="16"><chart-icon /></n-icon>
                  <span>增强报告</span>
                </div>
              </template>
            </n-tab-pane>
          </n-tabs>
        </div>
      </template>
      
      <!-- 日志标签页内?-->
      <div v-if="state.activeTab === 'logs'" class="log-container">
        <div v-for="(message, index) in logMessages" :key="index" 
             :class="['log-message', `log-${message.type || 'info'}`]">
          <span class="log-time">[{{ message.time }}]</span>
          <span class="log-source">[{{ message.source }}]</span>
          <div class="log-content" v-html="formatLogContent(message.content, message.source)"></div>
        </div>
        <div v-if="logMessages.length === 0" class="empty-log">
          还没有测试日志，请先开始API测试流程。
        </div>
      </div>
      
      <!-- 添加测试用例设计内容展示区域 -->
      <div v-else-if="state.activeTab === 'testcases'" class="testcases-container">
        <div v-if="testCaseMetadata" class="test-case-metadata">
          <n-card title="测试用例概览" size="small">
            <n-grid :cols="4" :x-gap="12">
              <n-grid-item>
                <div class="metadata-item">
                  <div class="metadata-label">总用例数</div>
                  <div class="metadata-value">{{ testCaseMetadata.total_test_cases || 0 }}</div>
                </div>
              </n-grid-item>
              <n-grid-item>
                <div class="metadata-item">
                  <div class="metadata-label">覆盖率</div>
                  <div class="metadata-value">{{ testCaseMetadata.api_coverage_estimate || 'N/A' }}</div>
                </div>
              </n-grid-item>
              <n-grid-item span="2">
                <div class="metadata-item">
                  <div class="metadata-label">覆盖测试类型</div>
                  <div class="coverage-types" v-if="testCaseMetadata.coverage_types">
                    <n-tag :type="testCaseMetadata.coverage_types.functional ? 'success' : 'default'" size="small">功能测试</n-tag>
                    <n-tag :type="testCaseMetadata.coverage_types.boundary ? 'success' : 'default'" size="small">边界测试</n-tag>
                    <n-tag :type="testCaseMetadata.coverage_types.negative ? 'success' : 'default'" size="small">异常测试</n-tag>
                    <n-tag :type="testCaseMetadata.coverage_types.validation ? 'success' : 'default'" size="small">验证测试</n-tag>
                    <n-tag :type="testCaseMetadata.coverage_types.security ? 'success' : 'default'" size="small">安全测试</n-tag>
                    <n-tag :type="testCaseMetadata.coverage_types.performance ? 'success' : 'default'" size="small">性能测试</n-tag>
                  </div>
                </div>
              </n-grid-item>
            </n-grid>
          </n-card>
        </div>
        
        <div class="test-cases-content" v-html="processTestCases(testCases)"></div>
      </div>
      
      <!-- 测试代码标签页内?-->
      <div v-else-if="state.activeTab === 'code'" class="code-container">
        <div class="code-actions">
          <n-button-group v-if="!isEditing">
            <n-button size="small" type="primary" @click="toggleEditMode">
              编辑代码
            </n-button>
            <n-button size="small" @click="copyTestCode">
              <template #icon><copy-icon /></template>
              复制代码
            </n-button>
            <n-button size="small" @click="downloadTestCode">
              <template #icon><download-icon /></template>
              下载代码
            </n-button>
          </n-button-group>
          
          <n-button-group v-else>
            <n-button size="small" type="primary" @click="saveTestCode">
              <template #icon><save-icon /></template>
              保存代码
            </n-button>
            <n-button size="small" @click="toggleEditMode">
              取消编辑
            </n-button>
          </n-button-group>
        </div>
        
        <!-- 代码查看模式 -->
        <pre v-if="!isEditing" class="code-block"><code>{{ testCode }}</code></pre>
        
        <!-- 代码编辑模式 -->
        <div v-else id="monaco-editor-container" class="monaco-editor-container"></div>
      </div>
      
      <div v-else-if="state.activeTab === 'params'" class="params-container">
        <n-card title="测试执行参数" class="params-card">
          <n-form :model="testParams" label-placement="left" label-width="auto" require-mark-placement="right-hanging">
            <n-form-item label="超时时间(秒)" path="timeout">
              <n-input-number v-model:value="testParams.timeout" :min="1" :max="300" />
            </n-form-item>
            
            <n-form-item label="失败重试次数" path="retries">
              <n-input-number v-model:value="testParams.retries" :min="0" :max="5" />
            </n-form-item>
            
            <n-form-item label="并行执行" path="parallel">
              <n-switch v-model:value="testParams.parallel" />
            </n-form-item>
            
            <n-form-item label="详细日志" path="verbose">
              <n-switch v-model:value="testParams.verbose" />
            </n-form-item>
            
            <n-form-item label="测试标签" path="tags">
              <n-input v-model:value="testParams.tags" placeholder="用逗号分隔多个标签" />
            </n-form-item>
            
            <n-form-item label="自定义Pytest选项" path="customOptions">
              <n-input v-model:value="testParams.customOptions" type="textarea" placeholder="-xvs --no-header" />
            </n-form-item>
          </n-form>
          
          <div class="params-actions">
            <n-button type="primary" @click="runTests" :disabled="state.isExecuting">
              应用参数并执行测试
            </n-button>
          </div>
        </n-card>
        
        <n-card title="参数说明" class="params-help-card">
          <n-collapse>
            <n-collapse-item title="超时时间" name="timeout">
              <p>设置单个测试用例的最大执行时间（秒）。超过此时间测试将被终止并标记为失败。</p>
            </n-collapse-item>
            <n-collapse-item title="失败重试" name="retries">
              <p>测试失败后的自动重试次数。对于不稳定的API，适当设置重试可提高测试通过率。</p>
            </n-collapse-item>
            <n-collapse-item title="并行执行" name="parallel">
              <p>启用多进程并行执行测试。可显著提高执行速度，但可能导致日志混乱或资源冲突。</p>
            </n-collapse-item>
            <n-collapse-item title="测试标签" name="tags">
              <p>通过标签选择性执行测试。例如：smoke,regression 将只运行带有这些标签的测试。</p>
            </n-collapse-item>
            <n-collapse-item title="自定义选项" name="customOptions">
              <p>直接传递给pytest的命令行选项，例如：-v --no-header</p>
            </n-collapse-item>
          </n-collapse>
        </n-card>
      </div>
      
      <!-- 测试结果标签页内?-->
      <div v-else-if="state.activeTab === 'results'" class="results-container">
        <n-grid :cols="5" :x-gap="12" class="stats-row" v-if="state.executionStats.total > 0">
          <n-grid-item>
            <div class="stat-card">
              <div class="stat-value">{{ state.executionStats.total }}</div>
              <div class="stat-label">总用例数</div>
            </div>
          </n-grid-item>
          <n-grid-item>
            <div class="stat-card green">
              <div class="stat-value">{{ state.executionStats.passed }}</div>
              <div class="stat-label">通过</div>
            </div>
          </n-grid-item>
          <n-grid-item>
            <div class="stat-card red">
              <div class="stat-value">{{ state.executionStats.failed }}</div>
              <div class="stat-label">失败</div>
            </div>
          </n-grid-item>
          <n-grid-item>
            <div class="stat-card orange">
              <div class="stat-value">{{ state.executionStats.error }}</div>
              <div class="stat-label">错误</div>
            </div>
          </n-grid-item>
          <n-grid-item>
            <div class="stat-card blue">
              <div class="stat-value">{{ state.executionStats.skipped }}</div>
              <div class="stat-label">跳过</div>
            </div>
          </n-grid-item>
        </n-grid>
        
        <div class="execution-summary" v-if="state.executionStats.total > 0">
          <h3>执行摘要</h3>
          <div class="summary-details">
            <div class="summary-item">
              <span class="summary-label">通过率</span>
              <span class="summary-value">{{ ((state.executionStats.passed / state.executionStats.total) * 100).toFixed(2) }}%</span>
            </div>
            <div class="summary-item">
              <span class="summary-label">执行时间:</span>
              <span class="summary-value">{{ state.executionStats.duration.toFixed(2) }}秒</span>
            </div>
            <div class="summary-item">
              <span class="summary-label">测试文件:</span>
              <span class="summary-value file-path">{{ testFilePath }}</span>
            </div>
          </div>
          
          <n-progress
            :percentage="Math.round((state.executionStats.passed / state.executionStats.total) * 100)"
            :indicator-placement="'inside'"
            :height="20"
            :color="getProgressBarColor(state.executionStats.passed / state.executionStats.total)"
            class="pass-rate-progress"
          />
          
          <!-- 添加测试结果执行条件图示 -->
          <div v-if="testParams" class="test-execution-config">
            <h4>测试执行配置</h4>
            <n-tag v-if="testParams.timeout" type="info" round size="small">
              超时: {{ testParams.timeout }}秒            </n-tag>
            <n-tag v-if="testParams.retries" type="info" round size="small">
              重试: {{ testParams.retries }}次            </n-tag>
            <n-tag v-if="testParams.parallel" type="info" round size="small">
              并行执行
            </n-tag>
            <n-tag v-if="testParams.verbose" type="info" round size="small">
              详细日志
            </n-tag>
            <n-tag v-if="testParams.tags" type="info" round size="small">
              标签: {{ testParams.tags }}
            </n-tag>
          </div>
        </div>
        
        <div class="result-detail">
          <h3>测试输出详情</h3>
          <pre class="test-output">{{ testResults.test_result?.output }}</pre>
        </div>
        
        <div class="result-actions" v-if="reportUrl">
          <n-button type="primary" @click="state.activeTab = 'report'">
            <template #icon><chart-icon /></template>
            查看HTML报告
          </n-button>
          <n-button v-if="allureReportUrl" type="success" @click="state.activeTab = 'allure-report'">
            <template #icon><chart-icon /></template>
            查看Allure报告
          </n-button>
          <n-button v-if="analysisResult" type="info" @click="state.activeTab = 'analysis'">
            <template #icon><file-icon /></template>
            查看分析报告
          </n-button>
          <n-button @click="runTests" :disabled="state.isExecuting">
            <template #icon><ReloadOutline /></template>
            重新运行
          </n-button>
        </div>
      </div>
      
      <!-- 分析报告标签页内?-->
      <div v-else-if="state.activeTab === 'analysis'" class="analysis-container">
        <div class="markdown-content" v-html="renderMarkdown(analysisResult)"></div>
      </div>
      
      <!-- 测试图形报告标签页内?-->
      <div v-else-if="state.activeTab === 'report'" class="report-container">
        <div v-if="reportUrl" class="report-iframe-container">
          <div class="report-actions">
            <n-button size="small" type="primary" @click="refreshReport('html')">
              <template #icon><n-icon><ReloadOutline /></n-icon></template>
              刷新报告
            </n-button>
            <n-button size="small" type="info" @click="openHtmlReportDirectly()">
              <template #icon><n-icon><OpenOutline /></n-icon></template>
              在新标签页打开
            </n-button>
            <n-button size="small" type="info" @click="toggleFullScreen('reportIframe')">
              <template #icon><n-icon><ExpandIcon /></n-icon></template>
              切换全屏
            </n-button>
          </div>
          <div class="iframe-wrapper">
            <n-spin :show="state.isReportLoading" description="加载测试报告中...">
              <iframe 
                :src="getFullUrl(reportUrl)" 
                class="report-iframe" 
                frameborder="0" 
                ref="reportIframe"
                id="reportIframe"
                @load="iframeLoaded('html')"
                @error="handleIframeError('html')"
              ></iframe>
            </n-spin>
          </div>
          <div v-if="state.htmlLoadError" class="report-error-message">
            <n-alert title="加载报告失败" type="error">
              <template #icon><n-icon><AlertCircleOutline /></n-icon></template>
              <p>HTML报告加载失败，请尝试使用以下链接直接访问：</p>
              <p><a :href="getFullUrl(reportUrl)" target="_blank">{{ getFullUrl(reportUrl) }}</a></p>
            </n-alert>
          </div>
        </div>
        <div v-else class="empty-report">
          <n-empty description="没有可用的HTML测试报告，请先执行测试">
            <template #icon>
              <n-icon><DocumentTextOutline /></n-icon>
            </template>
            <template #extra>
              <n-button @click="runTests" :disabled="state.isExecuting">
                执行测试生成报告
              </n-button>
            </template>
          </n-empty>
        </div>
      </div>
      
      <!-- Allure报告标签页内容 -->
      <div v-else-if="state.activeTab === 'allure-report'" class="report-container">
        <div v-if="allureReportUrl" class="report-iframe-container">
          <div class="report-actions">
            <n-button size="small" type="primary" @click="refreshReport('allure')">
              <template #icon><n-icon><ReloadOutline /></n-icon></template>
              刷新Allure报告
            </n-button>
            <n-button size="small" type="info" @click="openAllureReportDirectly()">
              <template #icon><n-icon><OpenOutline /></n-icon></template>
              在新标签页打开
            </n-button>
            <n-button size="small" type="info" @click="toggleFullScreen('allureIframe')">
              <template #icon><n-icon><ExpandIcon /></n-icon></template>
              切换全屏
            </n-button>
          </div>
          <div class="iframe-wrapper">
            <n-spin :show="state.isAllureLoading" description="加载Allure报告中...">
              <iframe 
                :src="processAllureReportUrl(allureReportUrl)" 
                class="report-iframe" 
                frameborder="0"
                ref="allureIframe" 
                id="allureIframe"
                @load="iframeLoaded('allure')"
                @error="handleIframeError('allure')"
              ></iframe>
            </n-spin>
          </div>
          <div v-if="state.allureLoadError" class="report-error-message">
            <n-alert title="加载报告失败" type="error">
              <template #icon><n-icon><AlertCircleOutline /></n-icon></template>
              <p>Allure报告加载失败，请尝试使用以下链接直接访问：</p>
              <p><a :href="processAllureReportUrl(allureReportUrl)" target="_blank">{{ processAllureReportUrl(allureReportUrl) }}</a></p>
            </n-alert>
          </div>
        </div>
        <div v-else class="empty-report">
          <n-empty description="没有可用的Allure测试报告，请先执行测试">
            <template #icon>
              <n-icon><PieChartOutline /></n-icon>
            </template>
            <template #extra>
              <n-button @click="runTests" :disabled="state.isExecuting">
                执行测试生成报告
              </n-button>
            </template>
          </n-empty>
        </div>
      </div>
    </n-card>
  </div>
</template>

<style scoped>
.collapse-header {
  display: flex;
  align-items: center;
  gap: 10px;
}

.collapse-title {
  font-size: 16px;
  font-weight: 500;
  color: #333;
}

.api-test-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 5px 10px;
}

.page-header {
  margin-bottom: 20px;
  text-align: center;
}

.page-header h1 {
  font-size: 28px;
  color: #303133;
  margin-bottom: 8px;
}

.page-header .subtitle {
  color: #606266;
  font-size: 16px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.input-section {
  margin-bottom: 15px;
}

.progress-section {
  margin: 10px 0;
}

.progress-bar {
  margin-top: 10px;
}

.progress-text {
  text-align: center;
  font-weight: bold;
}

.button-group {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 8px;
}

.result-section {
  margin-top: 10px;
}

.log-container {
  height: 70vh; /* 使用视窗高度来确保日志区域更?*/
  overflow-y: auto;
  background-color: #1e1e1e;
  color: #f8f8f2;
  border-radius: 4px;
  padding: 12px;
  font-family: 'JetBrains Mono', monospace, 'SF Mono', Consolas;
  font-size: 13px;
  line-height: 1.2; /* 减小行高 */
  scroll-behavior: smooth;
}

.log-message {
  margin-bottom: 0px; /* 移除底部间距 */
  white-space: pre-wrap;
  word-break: break-all;
}

.log-time {
  color: #999;
  margin-right: 8px;
}

.log-source {
  color: #569cd6;
  margin-right: 8px;
  font-weight: bold;
}

.log-info {
  color: #f8f8f2;
}

.log-error {
  color: #e06c75;
}

.log-warning {
  color: #e5c07b;
}

.empty-log {
  color: #aaa;
  text-align: center;
  padding: 20px;
}

.results-container, 
.code-container, 
.analysis-container {
  min-height: 70vh; /* 保持与日志区域一?*/
  max-height: 70vh;
  overflow-y: auto;
}

.stats-row {
  margin-bottom: 20px;
}

.stat-card {
  background-color: #f5f7fa;
  border-radius: 8px;
  padding: 10px;
  text-align: center;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.stat-value {
  font-size: 24px;
  font-weight: bold;
  margin-bottom: 3px;
}

.stat-label {
  color: #606266;
}

.green {
  background-color: #f0f9eb;
  color: #67c23a;
}

.red {
  background-color: #fef0f0;
  color: #f56c6c;
}

.orange {
  background-color: #fdf6ec;
  color: #e6a23c;
}

.blue {
  background-color: #ecf5ff;
  color: #409eff;
}

.execution-summary {
  background-color: #f9f9f9;
  border-radius: 8px;
  padding: 15px;
  margin: 15px 0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.execution-summary h3 {
  margin-top: 0;
  margin-bottom: 10px;
  color: #303133;
  font-size: 16px;
}

.pass-rate-progress {
  margin-top: 10px;
}

.summary-details {
  display: flex;
  flex-wrap: wrap;
  margin-bottom: 10px;
}

.summary-item {
  flex: 1;
  min-width: 200px;
  margin-bottom: 5px;
}

.summary-label {
  font-weight: bold;
  color: #606266;
  margin-right: 5px;
}

.summary-value {
  color: #303133;
}

.summary-value.file-path {
  font-family: monospace;
  word-break: break-all;
}

.result-detail {
  margin: 20px 0;
}

.result-detail h3 {
  margin-bottom: 10px;
  font-size: 16px;
  color: #303133;
}

.test-output {
  background-color: #1e1e1e;
  color: #f8f8f2;
  padding: 12px;
  border-radius: 4px;
  font-family: 'JetBrains Mono', monospace, 'SF Mono', Consolas;
  font-size: 13px;
  line-height: 1.5;
  overflow-x: auto;
  white-space: pre-wrap;
  max-height: 500px;
  overflow-y: auto;
}

.result-actions {
  margin-top: 15px;
  display: flex;
  justify-content: center;
  gap: 10px;
}

.report-actions {
  margin-top: 10px;
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}

.code-actions {
  margin-bottom: 15px;
  display: flex;
  gap: 10px;
  justify-content: space-between;
}

.code-block {
  font-family: monospace;
  white-space: pre-wrap;
  background-color: #f5f5f5;
  border-radius: 4px;
  padding: 12px;
  overflow: auto;
}

.markdown-content {
  padding: 15px;
  overflow: auto;
  max-height: 60vh; /* 增加内容区域的高?*/
  line-height: 1.6;
}

.config-section {
  margin-bottom: 10px;
  transition: margin-bottom 0.3s, height 0.3s;
}

.config-section.collapsed {
  margin-bottom: 5px; /* 折叠时减少底部间?*/
  height: auto;
  min-height: 50px; /* 减小最小高?*/
  overflow: visible;
}

.config-content.collapsed {
  max-height: 0;
  opacity: 0;
  margin: 0;
  padding: 0;
  display: none; /* 完全隐藏内容 */
}

/* 优化表单样式，减小间?*/
:deep(.n-form) {
  row-gap: 8px;
}

:deep(.n-form-item .n-form-item-label) {
  padding: 0;
  height: 28px;
  line-height: 28px;
}

:deep(.n-form-item .n-form-item-feedback-wrapper) {
  min-height: 0;
  line-height: 1;
}

:deep(.n-input .n-input__input) {
  height: 32px;
  min-height: 32px;
}

:deep(.n-button) {
  padding: 0 12px;
  height: 32px;
}

.action-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 5px;
}

.checkbox-group {
  display: flex;
  gap: 15px;
  align-items: center;
}

.log-content {
  white-space: pre-wrap;
  word-break: break-all;
  display: inline-block;
}

/* 添加流式输出动画效果 */
@keyframes blink {
  0% { opacity: 1; }
  50% { opacity: 0.5; }
  100% { opacity: 1; }
}

.streaming .log-content::after {
  content: '■';
  display: inline-block;
  animation: blink 1s infinite;
  margin-left: 2px;
}

/* 为Markdown内容添加样式 */
.log-content :deep(h1), 
.log-content :deep(h2), 
.log-content :deep(h3), 
.log-content :deep(h4), 
.log-content :deep(h5), 
.log-content :deep(h6) {
  margin-top: 0.2em;
  margin-bottom: 0.2em;
  color: #b0c4de;
}

.log-content :deep(p) {
  margin: 0.1em 0; /* 减小段落间距 */
}

.log-content :deep(ul), 
.log-content :deep(ol) {
  padding-left: 1.2em;
  margin: 0.2em 0;
}

.log-content :deep(li) {
  margin-bottom: 0; /* 移除列表项底部间?*/
}

.log-content :deep(pre) {
  background-color: #2d2d2d;
  padding: 3px;
  border-radius: 4px;
  overflow-x: auto;
  margin: 0.2em 0;
}

.log-content :deep(code) {
  background-color: #2d2d2d;
  padding: 1px 3px;
  border-radius: 3px;
  color: #7ec699;
}

.log-content :deep(blockquote) {
  border-left: 3px solid #569cd6;
  margin: 0.2em 0;
  padding-left: 0.6em;
  color: #aaa;
}

.log-content :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 0.2em 0;
}

.log-content :deep(th), 
.log-content :deep(td) {
  border: 1px solid #444;
  padding: 2px 4px;
}

.log-content :deep(th) {
  background-color: #2d2d2d;
}

.config-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  cursor: pointer;
  user-select: none;
  border-radius: 4px;
  transition: background-color 0.2s;
  width: 100%;
  height: 100%;
}

.config-header:hover {
  background-color: rgba(0, 0, 0, 0.05);
}

.config-title {
  font-size: 16px;
  font-weight: 600;
  color: #333;
  display: flex;
  align-items: center;
}

.config-title::before {
  content: '';
  width: 4px;
  height: 18px;
  background-color: #18a058;
  margin-right: 10px;
  border-radius: 2px;
  display: inline-block;
}

.collapse-icon {
  opacity: 0.7;
  transition: all 0.3s ease;
}

.config-header:hover .collapse-icon {
  opacity: 1;
  transform: scale(1.1);
}

/* 改善Tab样式，减少不必要的间?*/
:deep(.n-tabs-tab) {
  padding: 8px 14px;
}

/* 标签页内容样?*/
.tab-content {
  display: flex;
  align-items: center;
  gap: 5px;
}

.tab-icon {
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 添加响应式样式，在不同屏幕大小下调整日志区域高度 */
@media screen and (max-height: 900px) {
  .log-container, 
  .results-container, 
  .code-container, 
  .analysis-container,
  .report-container {
    height: 65vh;
    min-height: 65vh;
    max-height: 65vh;
  }
}

@media screen and (max-height: 750px) {
  .log-container, 
  .results-container, 
  .code-container, 
  .analysis-container,
  .report-container {
    height: 60vh;
    min-height: 60vh;
    max-height: 60vh;
  }
}

:deep(.n-card-header) {
  padding: 10px 16px !important;
}

:deep(.n-tabs) {
  margin-bottom: 0;
}

:deep(.n-tabs .n-tabs-nav) {
  padding: 0 !important;
}

:deep(.n-tabs-tab-pad) {
  width: 0;
}

/* 使标签页更紧?*/
:deep(.n-tabs-pad) {
  padding: 0;
}

:deep(.n-tabs-wrapper) {
  padding: 0;
  margin: 0;
}

/* 强制设置卡片内容区域的padding */
:deep(.n-card__content) {
  padding: 12px !important;
  transition: padding 0.3s;
}

:deep(.n-card-collapsed .n-card__content) {
  padding: 0 !important;
  margin: 0 !important;
  overflow: hidden;
}

/* 调整卡片头部样式 */
:deep(.n-card__header) {
  padding: 10px 16px !important;
  min-height: 45px;
  display: block !important;
}

:deep(.n-card.n-card-collapsed .n-card__header) {
  border-bottom: none !important;
}

.report-container {
  min-height: 70vh;
  max-height: 70vh;
  width: 100%;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.report-iframe-container {
  display: flex;
  flex-direction: column;
  flex: 1;
  border-radius: 8px;
  overflow: hidden;
  background-color: #fff;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  height: 100%;
}

.report-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 10px;
  background: #f5f7fa;
  border-bottom: 1px solid #e6e6e6;
}

.report-iframe {
  width: 100%;
  height: 100%;
  border: none;
  background-color: white;
}

.empty-report {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 70vh;
  flex-direction: column;
}

.iframe-wrapper {
  position: relative;
  flex: 1;
  overflow: hidden;
  background-color: #fff;
  border-radius: 0 0 8px 8px;
}

.iframe-wrapper iframe {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  border: none;
}

.iframe-wrapper .n-spin-container {
  height: 100%;
}

.iframe-wrapper .n-spin-content {
  height: 100%;
}

/* 移除旧的不需要的样式 */
.allure-report-iframe {
  width: 100%;
  height: 100%;
  border: none;
}

.params-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 10px 0;
  height: 70vh;
  overflow-y: auto;
}

.params-card {
  background-color: #fff;
}

.params-help-card {
  background-color: #f9f9f9;
}

.params-actions {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}

.log-json {
  background-color: #1e1e1e;
  color: #9cdcfe;
  padding: 8px;
  border-radius: 4px;
  margin: 4px 0;
  overflow-x: auto;
  font-family: 'JetBrains Mono', monospace, 'SF Mono', Consolas;
  font-size: 12px;
  max-height: 300px;
  overflow-y: auto;
  line-height: 1.4;
}

.log-code, .log-python-code {
  background-color: #2d2d2d;
  color: #d4d4d4;
  padding: 8px;
  border-radius: 4px;
  margin: 4px 0;
  overflow-x: auto;
  font-family: 'JetBrains Mono', monospace, 'SF Mono', Consolas;
  font-size: 12px;
  white-space: pre;
  tab-size: 2;
  line-height: 1.4;
}

/* JSON语法高亮 */
.json-key {
  color: #9cdcfe;
}

.json-string {
  color: #ce9178;
}

.json-number {
  color: #b5cea8;
}

.json-boolean {
  color: #569cd6;
}

.json-null {
  color: #569cd6;
}

/* Python语法高亮 */
.python-keyword {
  color: #569cd6;
  font-weight: bold;
}

.python-string {
  color: #ce9178;
}

.python-number {
  color: #b5cea8;
}

.python-comment {
  color: #608b4e;
}

.python-private {
  color: #9cdcfe;
}

.log-content {
  white-space: pre-wrap;
  word-break: break-word;
}

.log-content code {
  background-color: #2d2d2d;
  padding: 2px 4px;
  border-radius: 3px;
  font-family: 'JetBrains Mono', monospace, 'SF Mono', Consolas;
}

.log-content pre {
  margin: 4px 0;
}

.log-content p {
  margin: 2px 0;
}

.log-content blockquote {
  margin: 4px 0;
  padding-left: 12px;
  border-left: 3px solid #569cd6;
  color: #aaa;
}

/* 添加测试用例页面样式 */
.testcases-container {
  min-height: 70vh;
  max-height: 70vh;
  overflow-y: auto;
  padding: 10px 0;
}

.test-case-metadata {
  margin-bottom: 20px;
}

.metadata-item {
  text-align: center;
  padding: 10px;
}

.metadata-label {
  font-size: 14px;
  color: #606266;
  margin-bottom: 5px;
}

.metadata-value {
  font-size: 24px;
  font-weight: bold;
  color: #303133;
}

.coverage-types {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  justify-content: center;
}

.test-execution-config {
  margin-top: 15px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.test-execution-config h4 {
  margin: 0;
  margin-right: 10px;
  font-size: 14px;
  color: #606266;
}

.debug-info {
  margin-top: 10px;
  font-size: 12px;
  color: #999;
}

.test-cases-wrapper {
  display: flex;
  flex-direction: column;
  gap: 20px;
  margin-top: 20px;
}

.test-case-card {
  border: 1px solid #eee;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  background-color: white;
  transition: all 0.3s ease;
}

.test-case-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

.test-case-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background-color: #f8f8f8;
  border-bottom: 1px solid #eee;
}

.test-case-id {
  font-weight: bold;
  font-size: 16px;
  color: #333;
}

.test-case-type-tag {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.type-success {
  background-color: #ebf8f2;
  color: #18a058;
}

.type-info {
  background-color: #e8f4fd;
  color: #2080f0;
}

.type-warning {
  background-color: #fff8e6;
  color: #f0a020;
}

.type-error {
  background-color: #fdece8;
  color: #d03050;
}

.type-primary {
  background-color: #e8f0fd;
  color: #335eea;
}

.type-default {
  background-color: #f5f5f5;
  color: #606060;
}

.test-case-content {
  padding: 16px;
}

.test-case-content :deep(h2) {
  margin-top: 0;
  font-size: 18px;
  color: #333;
}

.test-case-content :deep(strong) {
  color: #555;
}

.test-case-content :deep(pre) {
  background-color: #f8f8f8;
  border-radius: 4px;
  padding: 12px;
  overflow-x: auto;
}

.test-case-content :deep(code) {
  font-family: 'Courier New', Courier, monospace;
}

.test-case-content :deep(ul) {
  padding-left: 20px;
}

.test-case-content :deep(ol) {
  padding-left: 20px;
}

.iframe-wrapper {
  position: relative;
  width: 100%;
  height: 70vh;
  overflow: hidden;
}

.iframe-wrapper iframe {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  border: none;
}

.iframe-wrapper .n-spin {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
}

.iframe-wrapper .n-spin .n-spin__content {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.iframe-wrapper .n-spin .n-spin__description {
  margin-top: 10px;
  color: #606266;
}

/* 为测试代码和报告添加样式 */
.code-block {
  font-family: monospace;
  white-space: pre-wrap;
  background-color: #f5f5f5;
  border-radius: 4px;
  padding: 12px;
  overflow: auto;
}

/* 代码类型标识的样式 */
.code-prefix {
  color: #0066cc;
  font-weight: bold;
  margin-bottom: 8px;
  border-bottom: 1px solid #ddd;
  padding-bottom: 4px;
}

/* 报告标签样式 */
.report-tabs {
  display: flex;
  border-bottom: 1px solid #ddd;
}

.report-tabs .tab {
  padding: 8px 16px;
  cursor: pointer;
  border: 1px solid transparent;
}

.report-tabs .tab.active {
  border: 1px solid #ddd;
  border-bottom-color: white;
  margin-bottom: -1px;
  background-color: white;
}

.report-tabs .tab.disabled {
  color: #ccc;
  cursor: not-allowed;
}

.report-tabs .tab:not(.disabled):hover {
  background-color: #f0f0f0;
}
</style>
