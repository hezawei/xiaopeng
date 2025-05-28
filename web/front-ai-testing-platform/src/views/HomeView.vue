<template>
  <div class="home-container">
    <!-- 侧边栏 -->
    <div class="sidebar">
      <h2>智能车联AI接口测试系统</h2>
      <ul>
        <li
          v-for="(item, index) in menuItems"
          :key="index"
          :class="{ active: activeMenu === item.id }"
          @click="setActiveMenu(item.id)"
        >
          {{ item.name }}
        </li>
      </ul>
    </div>

    <!-- 主内容区域 -->
    <div class="main-content">
      <!-- 需求分析页面 -->
      <div v-if="activeMenu === 'requirement-analysis'">
        <div class="header">
          <h1>需求分析</h1>
        </div>
        <div class="section">
          <h2>上传测试文档</h2>
          <div
            class="upload-area"
            @click="triggerFileUpload"
            @dragover.prevent
            @drop.prevent="handleFileDrop"
          >
            <i>↑</i>
            <p>点击或拖拽文件到此处上传</p>
            <p>支持：需求文档、接口文档、测试用例(xmind格式)、图片等</p>
            <input
              type="file"
              ref="fileInput"
              style="display: none"
              multiple
              @change="handleFileChange"
            >
          </div>
          <div class="file-list" v-if="uploadedFiles.length > 0">
            <div class="file-item" v-for="(file, index) in uploadedFiles" :key="index">
              <div class="file-name">{{ file.name }}</div>
              <button class="btn btn-danger" @click="removeFile(index)">删除</button>
            </div>
          </div>
          <div class="form-group">
            <label for="requirement-description">需求描述</label>
            <textarea
              id="requirement-description"
              class="form-control"
              placeholder="请输入需求描述或补充说明..."
              v-model="requirementDescription"
            ></textarea>
          </div>
<<<<<<< HEAD
          <button
            class="btn btn-accent"
            @click="startAnalysis"
            :disabled="isAnalyzing || uploadedFiles.length === 0"
          >
            开始需求分析
          </button>
=======
          <div class="form-group">
            <label for="analysis-query">分析问题</label>
            <input 
              type="text" 
              id="analysis-query" 
              class="form-control" 
              placeholder="请输入您想分析的问题，例如：'分析文档中的主要功能需求'"
              v-model="analysisQuery"
            >
          </div>
          <div class="button-group">
            <button 
              class="btn btn-primary" 
              @click="startAnalysisHttp"
              :disabled="isAnalyzing || uploadedFileIds.length === 0"
            >
              HTTP分析
            </button>
            <button 
              class="btn btn-accent" 
              @click="startAnalysisWebSocket"
              :disabled="isAnalyzing || uploadedFileIds.length === 0"
            >
              WebSocket实时分析
            </button>
          </div>
>>>>>>> 5ad960a4e4c6c9b78b62cb6e591e362c56328500

          <!-- 加载动画 -->
          <div class="loading" v-if="isAnalyzing">
            <div class="loading-spinner"></div>
            <p>{{ loadingMessage }}</p>
          </div>
        </div>

        <!-- 分析结果 -->
        <div class="section" v-if="analysisResult">
          <h2>分析结果</h2>
          <div class="analysis-result">
            <div v-if="analysisResult.response" class="response-container">
              <div class="response-content markdown-body" v-html="formatMarkdown(analysisResult.response)"></div>
            </div>
          </div>
        </div>

        <!-- 处理日志 -->
        <div class="section" v-if="processingLogs.length > 0">
          <h2>处理日志</h2>
          <div class="processing-logs">
            <div 
              v-for="(log, index) in processingLogs" 
              :key="index"
              :class="['log-item', `log-${log.type}`]"
            >
              {{ log.message }}
            </div>
          </div>
        </div>
      </div>

      <!-- 其他页面可以根据需要添加 -->
      <div v-else-if="activeMenu === 'test-case-generation'">
        <div class="header">
          <h1>测试用例生成</h1>
        </div>
        <div class="section">
          <h2>测试用例生成功能正在开发中...</h2>
        </div>
      </div>

      <div v-else-if="activeMenu === 'test-execution'">
        <div class="header">
          <h1>测试执行</h1>
        </div>
        <div class="section">
          <h2>测试执行功能正在开发中...</h2>
        </div>
      </div>

      <div v-else-if="activeMenu === 'test-report'">
        <div class="header">
          <h1>测试报告</h1>
        </div>
        <div class="section">
          <h2>测试报告功能正在开发中...</h2>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
<<<<<<< HEAD
import { ref, onMounted } from 'vue';
import axios from 'axios'
=======
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue';
import { v4 as uuidv4 } from 'uuid';
// 导入marked和DOMPurify库用于Markdown渲染和安全处理
import { marked } from 'marked';
import DOMPurify from 'dompurify';
import hljs from 'highlight.js';

// API配置
const API_BASE_URL = 'http://localhost:8000';
const WS_BASE_URL = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.hostname}:8000`;
console.log(WS_BASE_URL)
// 客户端ID
const clientId = ref(uuidv4());

// WebSocket连接
let wsConnection = null;
let messageTimeoutId = null;
let hasRequestBeenSent = false; // 添加标志，防止重复发送请求
>>>>>>> 5ad960a4e4c6c9b78b62cb6e591e362c56328500

// 菜单项
const menuItems = [
  { id: 'requirement-analysis', name: '需求分析' },
  { id: 'test-case-generation', name: '测试用例生成' },
  { id: 'test-execution', name: '测试执行' },
  { id: 'test-report', name: '测试报告' }
];

// 状态管理
const activeMenu = ref('requirement-analysis');
const uploadedFiles = ref([]);
const uploadedFileIds = ref([]);
const requirementDescription = ref('');
const analysisQuery = ref('分析这个文档的主要需求和功能点');
const isAnalyzing = ref(false);
const loadingMessage = ref('正在分析需求，请稍候...');
const analysisResult = ref(null);
<<<<<<< HEAD
const analysisError = ref(null);
=======
const processingLogs = ref([]);
>>>>>>> 5ad960a4e4c6c9b78b62cb6e591e362c56328500
const fileInput = ref(null);

// 添加服务器状态检测
const serverStatus = ref('checking');

// 方法
const setActiveMenu = (menuId) => {
  activeMenu.value = menuId;
};

const triggerFileUpload = () => {
  fileInput.value.click();
};

const handleFileChange = async (event) => {
  const files = event.target.files;
  if (files.length > 0) {
    await uploadFiles(files);
    // 重置文件输入框，允许重新选择相同文件
    resetFileUpload();
  }
};

const handleFileDrop = async (event) => {
  const files = event.dataTransfer.files;
  if (files.length > 0) {
    await uploadFiles(files);
    // 重置文件输入框
    resetFileUpload();
  }
};

const uploadFiles = async (files) => {
  // 先检查服务器状态
  if (serverStatus.value !== 'online') {
    await checkServerStatus();
    if (serverStatus.value !== 'online') {
      addLog('error', '后端服务器未连接，无法上传文件');
      return;
    }
  }
  
  // 临时存储新添加的文件索引，用于在上传失败时移除
  const newFileIndices = [];
  const startIndex = uploadedFiles.value.length;
  
  try {
    const formData = new FormData();
    
    // 先添加到本地显示列表
    for (let i = 0; i < files.length; i++) {
      formData.append('files', files[i]);
      uploadedFiles.value.push(files[i]);
      newFileIndices.push(startIndex + i);
    }
    
    // 发送到服务器
    const response = await fetch(`${API_BASE_URL}/api/upload`, {
      method: 'POST',
      body: formData
    });
    
    const result = await response.json();
    console.log('上传响应:', result);
    
    if (result.status === 'success' && result.files && result.files.length > 0) {
      // 保存上传的文件ID
      result.files.forEach(file => {
        uploadedFileIds.value.push(file.id);
      });
      
      addLog('success', `成功上传 ${result.files.length} 个文件`);
    } else {
      // 上传失败，从显示列表中移除这些文件
      // 注意：需要从后往前移除，以保持索引有效
      for (let i = newFileIndices.length - 1; i >= 0; i--) {
        uploadedFiles.value.splice(newFileIndices[i], 1);
      }
      
      addLog('error', `文件上传失败: ${result.message || '未知错误'}`);
    }
  } catch (error) {
    console.error('上传文件出错:', error);
    
    // 上传出错，从显示列表中移除这些文件
    for (let i = newFileIndices.length - 1; i >= 0; i--) {
      uploadedFiles.value.splice(newFileIndices[i], 1);
    }
    
    addLog('error', `上传文件出错: ${error.message}`);
  }
};

<<<<<<< HEAD
const startAnalysis = async () => {
  isAnalyzing.value = true;
  analysisError.value = null;

  try {
    const formData = new FormData();

    // 添加文件到 FormData
    uploadedFiles.value.forEach(file => {
      formData.append('file', file);
    });

    // 添加描述和分块方法参数
    formData.append('description', requirementDescription.value || '进行需求分析');
    formData.append('chunk_method', 'sentence');

    // 发送请求到后端
    const response = await axios.post('/api/analyze', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });

    // 处理响应数据
    if (response.data.code === 200) {
      analysisResult.value = {
        summary: response.data.data.summary,
        keyPoints: extractKeyPoints(response.data.data.response),
        recommendations: extractRecommendations(response.data.data.response)
      };
    } else {
      throw new Error('API 返回异常');
    }

  } catch (error) {
    analysisError.value = error.response?.data?.message || '分析失败';
    console.error("分析错误:", error);
=======
const removeFile = async (index) => {
  try {
    const fileId = uploadedFileIds.value[index];
    
    // 从前端列表中移除
    const removedFile = uploadedFiles.value.splice(index, 1)[0];
    uploadedFileIds.value.splice(index, 1);
    
    // 通知后端删除文件（如果有fileId）
    if (fileId) {
      try {
        const response = await fetch(`${API_BASE_URL}/api/delete-file`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ file_id: fileId })
        });
        
        const result = await response.json();
        if (result.status === 'success') {
          addLog('success', `文件 ${removedFile.name || '未知文件'} 已删除`);
        } else {
          addLog('warning', `文件删除请求失败，但UI已更新: ${result.message || '未知错误'}`);
        }
      } catch (error) {
        console.error('删除文件请求出错:', error);
        addLog('warning', `删除文件请求出错，但UI已更新`);
      }
    }
  } catch (error) {
    console.error('删除文件出错:', error);
    addLog('error', `删除文件出错: ${error.message}`);
  }
};

// 添加清除所有文件的方法
const clearAllFiles = async () => {
  try {
    // 如果有文件ID，通知后端删除
    if (uploadedFileIds.value.length > 0) {
      try {
        const response = await fetch(`${API_BASE_URL}/api/delete-files`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ file_ids: uploadedFileIds.value })
        });
        
        const result = await response.json();
        if (result.status === 'success') {
          addLog('success', '所有文件已删除');
        } else {
          addLog('warning', '批量删除文件请求失败，但UI已更新');
        }
      } catch (error) {
        console.error('批量删除文件请求出错:', error);
        addLog('warning', '批量删除文件请求出错，但UI已更新');
      }
    }
    
    // 清空前端列表
    uploadedFiles.value = [];
    uploadedFileIds.value = [];
  } catch (error) {
    console.error('清除所有文件出错:', error);
    addLog('error', `清除所有文件出错: ${error.message}`);
  }
};

// 添加文件上传状态重置方法
const resetFileUpload = () => {
  // 重置文件输入框
  if (fileInput.value) {
    fileInput.value.value = '';
  }
};

const startAnalysisHttp = async () => {
  if (uploadedFileIds.value.length === 0) {
    addLog('error', '请先上传文件');
    return;
  }
  
  isAnalyzing.value = true;
  loadingMessage.value = '正在通过HTTP分析需求，请稍候...';
  processingLogs.value = [];
  analysisResult.value = null;
  
  try {
    addLog('info', '开始HTTP分析请求');
    
    const response = await fetch(`${API_BASE_URL}/api/analyze`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        file_ids: uploadedFileIds.value,
        description: requirementDescription.value,
        query: analysisQuery.value
      })
    });
    
    const result = await response.json();
    
    if (result.status === 'success') {
      addLog('success', '分析完成');
      analysisResult.value = result.result;
    } else {
      addLog('error', `分析失败: ${result.message}`);
    }
  } catch (error) {
    console.error('分析过程出错:', error);
    addLog('error', `分析过程出错: ${error.message}`);
>>>>>>> 5ad960a4e4c6c9b78b62cb6e591e362c56328500
  } finally {
    isAnalyzing.value = false;
  }
};

<<<<<<< HEAD
// 提取关键点的辅助函数
function extractKeyPoints(text) {
  const points = [];
  const pointRegex = /识别到(.*?)\./g;
  let match;

  while ((match = pointRegex.exec(text)) !== null) {
    points.push(match[0]);
  }

  return points.length ? points : ['未识别到关键点'];
}

// 提取建议的辅助函数
function extractRecommendations(text) {
  const recommendations = [];
  const recRegex = /建议(.*?)\./g;
  let match;

  while ((match = recRegex.exec(text)) !== null) {
    recommendations.push(match[0]);
  }

  return recommendations.length ? recommendations : ['无建议'];
=======

const startAnalysisWebSocket = () => {
  if (uploadedFileIds.value.length === 0) {
    addLog('error', '请先上传文件');
    return;
  }
  
  isAnalyzing.value = true;
  loadingMessage.value = '正在通过WebSocket实时分析需求...';
  processingLogs.value = [];
  analysisResult.value = null;
  
  // 创建WebSocket连接
  connectWebSocket();
  
  // 不再使用setTimeout发送请求，而是在onopen事件中发送
};

const connectWebSocket = () => {
  // 如果已有连接，先关闭
  if (wsConnection) {
    console.log('关闭现有WebSocket连接');
    try {
      wsConnection.onopen = null;
      wsConnection.onmessage = null;
      wsConnection.onerror = null;
      wsConnection.onclose = null;
      if (wsConnection.readyState === WebSocket.OPEN || 
          wsConnection.readyState === WebSocket.CONNECTING) {
        wsConnection.close();
      }
    } catch (e) {
      console.error('关闭WebSocket连接出错:', e);
    }
    wsConnection = null;
  }
  
  // 重置发送标志
  hasRequestBeenSent = false;
  
  // 构建WebSocket URL
  const wsUrl = `${WS_BASE_URL}/ws/analyze/${Date.now()}`;
  addLog('info', `正在连接WebSocket: ${wsUrl}`);
  
  try {
    wsConnection = new WebSocket(wsUrl);
    console.log('WebSocket 对象已创建:', wsConnection);
    
    // 连接打开事件
    wsConnection.onopen = () => {
      addLog('info', 'WebSocket连接已建立');
      console.log('WebSocket连接已建立');
      
      // 只有在尚未发送请求时才发送
      if (!hasRequestBeenSent) {
        sendAnalysisRequest();
      }
    };
    
    // 接收消息事件
    wsConnection.onmessage = (event) => {
      // 收到消息，清除超时
      if (messageTimeoutId) {
        clearTimeout(messageTimeoutId);
        messageTimeoutId = null;
      }
      
      console.log('收到WebSocket消息:', event.data);
      
      try {
        const message = JSON.parse(event.data);
        console.log('解析后的消息:', message);
        
        // 根据消息类型处理
        if (message.status === 'success') {
          addLog('success', '分析完成');
          analysisResult.value = message.result;
          isAnalyzing.value = false;
          // 分析完成后关闭WebSocket连接
          closeWebSocketConnection();
        } else if (message.type === 'result' && message.data) {
          addLog('success', '分析完成');
          analysisResult.value = message.data;
          isAnalyzing.value = false;
          // 分析完成后关闭WebSocket连接
          closeWebSocketConnection();
        } else if (message.status === 'processing' || message.type === 'status') {
          // 处理状态消息
          addLog('info', message.message || '处理中...');
        } else if (message.status === 'error' || message.type === 'error') {
          addLog('error', message.message || '发生错误');
          isAnalyzing.value = false;
          // 错误时关闭WebSocket连接
          closeWebSocketConnection();
        } else {
          // 处理其他类型的消息
          console.log('未知消息类型:', message);
          addLog('info', `收到消息: ${JSON.stringify(message)}`);
        }
      } catch (error) {
        console.error('解析WebSocket消息出错:', error);
        addLog('error', `解析WebSocket消息出错: ${error.message}`);
      }
    };
    
    // 错误处理
    wsConnection.onerror = (error) => {
      console.error('WebSocket错误:', error);
      addLog('error', 'WebSocket连接错误');
      isAnalyzing.value = false;
    };
    
    // 连接关闭
    wsConnection.onclose = () => {
      console.log('WebSocket连接已关闭');
      if (isAnalyzing.value) {
        addLog('warning', 'WebSocket连接已关闭，但分析可能尚未完成');
        isAnalyzing.value = false;
      }
    };
    
  } catch (error) {
    console.error('创建WebSocket连接出错:', error);
    addLog('error', `创建WebSocket连接出错: ${error.message}`);
    isAnalyzing.value = false;
  }
};

// 发送分析请求
const sendAnalysisRequest = () => {
  if (!wsConnection || wsConnection.readyState !== WebSocket.OPEN) {
    console.error('WebSocket未连接，无法发送请求');
    addLog('error', 'WebSocket未连接，无法发送请求');
    isAnalyzing.value = false;
    return;
  }
  
  // 标记请求已发送
  hasRequestBeenSent = true;
  
  const requestData = {
    file_ids: uploadedFileIds.value,
    description: requirementDescription.value,
    query: analysisQuery.value
  };
  
  console.log('发送WebSocket分析请求:', requestData);
  wsConnection.send(JSON.stringify(requestData));
  addLog('info', '已发送WebSocket分析请求');
  
  // 设置超时
  messageTimeoutId = setTimeout(() => {
    addLog('error', '分析请求超时，未收到响应');
    isAnalyzing.value = false;
    closeWebSocketConnection();
  }, 60000); // 60秒超时
};

// 关闭WebSocket连接
const closeWebSocketConnection = () => {
  if (wsConnection) {
    console.log('主动关闭WebSocket连接');
    try {
      wsConnection.onopen = null;
      wsConnection.onmessage = null;
      wsConnection.onerror = null;
      wsConnection.onclose = null;
      if (wsConnection.readyState === WebSocket.OPEN || 
          wsConnection.readyState === WebSocket.CONNECTING) {
        wsConnection.close();
      }
    } catch (e) {
      console.error('关闭WebSocket连接出错:', e);
    }
    wsConnection = null;
  }
};

const addLog = (type, message) => {
  processingLogs.value.push({ type, message });
};

const formatScore = (score) => {
  return (score * 100).toFixed(2) + '%';
};

// 检查服务器连接状态
const checkServerStatus = async () => {
  try {
    serverStatus.value = 'checking';
    // 尝试连接后端健康检查接口
    const response = await fetch(`${API_BASE_URL}/api/health`, { 
      method: 'GET',
      // 设置较短的超时时间
      signal: AbortSignal.timeout(3000)
    });
    
    if (response.ok) {
      serverStatus.value = 'online';
      addLog('success', '后端服务器连接正常');
    } else {
      serverStatus.value = 'error';
      addLog('error', `后端服务器返回错误: ${response.status}`);
    }
  } catch (error) {
    console.error('服务器连接检查失败:', error);
    serverStatus.value = 'offline';
    addLog('error', `无法连接到后端服务器: ${error.message}`);
  }
};

// 添加窗口大小变化监听，以便在调整窗口大小时重新处理表格
let resizeTimeout;
const handleResize = () => {
  clearTimeout(resizeTimeout);
  resizeTimeout = setTimeout(() => {
    if (analysisResult.value) {
      processTablesAfterRender();
    }
  }, 200);
>>>>>>> 5ad960a4e4c6c9b78b62cb6e591e362c56328500
};

onMounted(() => {
  console.log("页面已加载");
  checkServerStatus();
  
  // 添加窗口大小变化监听
  window.addEventListener('resize', handleResize);
  
  // 初始处理表格
  if (analysisResult.value) {
    processTablesAfterRender();
  }
});

onBeforeUnmount(() => {
  // 清除超时
  if (messageTimeoutId) {
    clearTimeout(messageTimeoutId);
  }
  
  // 关闭WebSocket连接
  if (wsConnection) {
    wsConnection.close();
  }
  
  // 移除窗口大小变化监听
  window.removeEventListener('resize', handleResize);
  
  // 清除表格相关的超时
  clearTimeout(resizeTimeout);
});

// 在setup函数中添加formatMarkdown方法
const formatMarkdown = (text) => {
  if (!text) return '';
  
  // 配置marked选项
  marked.setOptions({
    breaks: true,        // 将换行符转换为<br>
    gfm: true,           // 使用GitHub风格的Markdown
    headerIds: true,     // 为标题添加ID
    mangle: false,       // 不转义标题中的HTML
    smartLists: true,    // 使用更智能的列表行为
    smartypants: true,   // 使用更智能的标点符号
    xhtml: false,        // 不使用自闭合标签
    highlight: function(code, lang) {
      try {
        if (lang && hljs.getLanguage(lang)) {
          return hljs.highlight(code, { language: lang }).value;
        } else {
          return hljs.highlightAuto(code).value;
        }
      } catch (e) {
        console.error('代码高亮出错:', e);
        return code;
      }
    }
  });
  
  // 将Markdown转换为HTML并进行安全处理
  const rawHtml = marked.parse(text);
  const cleanHtml = DOMPurify.sanitize(rawHtml);
  
  return cleanHtml;
};

const processTablesAfterRender = () => {
  // 使用nextTick确保DOM已更新
  nextTick(() => {
    // 查找所有表格
    const tables = document.querySelectorAll('.markdown-body table');
    
    tables.forEach(table => {
      // 检查表格是否需要处理长内容
      const cells = table.querySelectorAll('td');
      cells.forEach(cell => {
        // 如果单元格内容超过一定长度，添加特殊类
        if (cell.textContent && cell.textContent.length > 100) {
          cell.classList.add('long-content');
          
          // 添加鼠标悬停时显示完整内容的提示
          cell.setAttribute('title', cell.textContent);
        }
      });
      
      // 检查表格是否需要水平滚动
      // 如果表格宽度超过容器，添加指示器
      if (table.scrollWidth > table.clientWidth) {
        const container = table.parentElement;
        if (!container.querySelector('.table-scroll-indicator')) {
          const indicator = document.createElement('div');
          indicator.className = 'table-scroll-indicator';
          indicator.innerHTML = '← 滑动查看更多 →';
          container.insertBefore(indicator, table);
          
          // 滚动时隐藏指示器
          table.addEventListener('scroll', () => {
            indicator.style.opacity = '0';
            // 滚动停止一段时间后，如果表格未完全滚动到末尾，则重新显示指示器
            clearTimeout(table.scrollTimeout);
            table.scrollTimeout = setTimeout(() => {
              if (table.scrollLeft < table.scrollWidth - table.clientWidth - 10) {
                indicator.style.opacity = '0.7';
              }
            }, 1000);
          });
        }
      }
    });
  });
};

// 修改watch以在分析结果更新时处理表格
watch(() => analysisResult.value, (newVal) => {
  if (newVal) {
    processTablesAfterRender();
  }
});

// 在onMounted中也添加处理
onMounted(() => {
  console.log("页面已加载");
  checkServerStatus();
  
  // 初始处理表格
  if (analysisResult.value) {
    processTablesAfterRender();
  }
});


</script>

<style scoped>
/* 基础样式 */
.home-container {
  display: flex;
  min-height: 100vh;
  background-color: var(--light-bg);
}

/* 侧边栏样式 */
.sidebar {
  width: 220px;
  background-color: var(--primary-color);
  color: white;
  padding: 0;
}

.sidebar h2 {
  text-align: center;
  margin: 0;
  padding: 25px 15px;
  font-size: 1.3rem;
  line-height: 1.4;
  background-color: var(--primary-dark);
  letter-spacing: 0.5px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.sidebar ul {
  list-style: none;
  margin-top: 20px;
  padding: 0;
}

.sidebar li {
  padding: 14px 25px;
  cursor: pointer;
  transition: all 0.2s;
  position: relative;
  font-weight: 500;
}

.sidebar li:hover {
  background-color: var(--primary-light);
}

.sidebar li.active {
  background-color: var(--primary-light);
}

.sidebar li.active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  height: 100%;
  width: 4px;
  background-color: var(--accent-color);
}

/* 主内容区域样式 */
.main-content {
  flex: 1;
  padding: 25px;
  overflow-y: auto;
  background-color: var(--light-bg);
}

.header {
  margin-bottom: 25px;
  position: relative;
}

.header h1 {
  font-size: 1.5rem;
  color: var(--primary-color);
  margin-bottom: 0;
  font-weight: 700;
  letter-spacing: 0.5px;
  text-transform: uppercase;
  display: inline-block;
}

.header h1::after {
  content: '';
  position: absolute;
  bottom: -8px;
  left: 0;
  width: 35px;
  height: 3px;
  background-color: var(--accent-color);
}

.section {
  background-color: var(--white);
  padding: 20px;
  border-radius: 4px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
  margin-bottom: 25px;
}

.section h2 {
  margin-bottom: 20px;
  color: var(--primary-color);
  font-weight: 600;
  font-size: 1.2rem;
  position: relative;
  padding-bottom: 8px;
  border-bottom: 1px solid #eee;
}

.upload-area {
  border: 2px dashed #ccc;
  padding: 40px;
  text-align: center;
  border-radius: 4px;
  margin-bottom: 25px;
  cursor: pointer;
  transition: all 0.2s;
  background-color: var(--secondary-color);
}

.upload-area:hover {
  border-color: var(--accent-color);
}

.upload-area p {
  color: var(--text-light);
  margin-bottom: 10px;
}

.upload-area i {
  font-size: 2.5rem;
  color: var(--text-light);
  margin-bottom: 15px;
  display: block;
}

.file-list {
  margin-top: 25px;
}

.file-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 15px;
  background-color: var(--secondary-color);
  border-radius: 4px;
  margin-bottom: 10px;
}

.file-name {
  font-size: 0.95rem;
  color: var(--text-color);
  font-weight: 500;
}

.btn {
  padding: 8px 16px;
  background-color: var(--primary-color);
  color: white;
  border: none;
  border-radius: 3px;
  cursor: pointer;
  transition: all 0.2s;
  margin-right: 6px;
  font-weight: 500;
  text-transform: uppercase;
  font-size: 0.75rem;
  letter-spacing: 0.5px;
}

.btn:hover {
  background-color: var(--primary-light);
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-danger {
  background-color: var(--danger-color);
}

.btn-danger:hover {
  background-color: #d62836;
}

.btn-accent {
  background-color: var(--accent-color);
}

.btn-accent:hover {
  background-color: #d62836;
}

.form-group {
  margin-bottom: 15px;
}

.form-group label {
  display: block;
  margin-bottom: 6px;
  color: var(--primary-color);
  font-weight: 600;
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.form-control {
  width: 100%;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 0.9rem;
  transition: border-color 0.2s;
}

textarea.form-control {
  min-height: 100px;
  resize: vertical;
}

.form-control:focus {
  border-color: var(--accent-color);
  outline: none;
}

.loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-top: 20px;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(0, 0, 0, 0.1);
  border-radius: 50%;
  border-top-color: var(--accent-color);
  animation: spin 1s ease-in-out infinite;
  margin-bottom: 10px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.analysis-result {
  background-color: var(--secondary-color);
  padding: 15px;
  border-radius: 4px;
  margin-top: 15px;
}

.analysis-result pre {
  white-space: pre-wrap;
  font-family: monospace;
  margin: 0;
}

.processing-logs {
  background-color: var(--secondary-color);
  padding: 15px;
  border-radius: 4px;
  margin-top: 15px;
}

.log-item {
  margin-bottom: 10px;
  padding: 8px 12px;
  border-radius: 4px;
  font-size: 0.9rem;
}

.log-info {
  background-color: var(--primary-light);
}

.log-success {
  background-color: var(--success-color);
}

.log-error {
  background-color: var(--danger-color);
}

/* 添加Markdown样式 */
.response-container {
  background-color: #f9f9f9;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.response-content {
  padding: 20px;
  line-height: 1.6;
  font-size: 16px;
  color: #333;
  overflow-wrap: break-word;
}

/* Markdown样式 */
.markdown-body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
}

.markdown-body h1, 
.markdown-body h2, 
.markdown-body h3, 
.markdown-body h4, 
.markdown-body h5, 
.markdown-body h6 {
  margin-top: 24px;
  margin-bottom: 16px;
  font-weight: 600;
  line-height: 1.25;
  color: #24292e;
}

.markdown-body h1 { font-size: 2em; border-bottom: 1px solid #eaecef; padding-bottom: 0.3em; }
.markdown-body h2 { font-size: 1.5em; border-bottom: 1px solid #eaecef; padding-bottom: 0.3em; }
.markdown-body h3 { font-size: 1.25em; }
.markdown-body h4 { font-size: 1em; }

.markdown-body p {
  margin-top: 0;
  margin-bottom: 16px;
}

.markdown-body ul, 
.markdown-body ol {
  padding-left: 2em;
  margin-top: 0;
  margin-bottom: 16px;
}

.markdown-body li {
  margin-bottom: 0.25em;
}

.markdown-body code {
  padding: 0.2em 0.4em;
  margin: 0;
  font-size: 85%;
  background-color: rgba(27, 31, 35, 0.05);
  border-radius: 3px;
  font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
}

.markdown-body pre {
  padding: 16px;
  overflow: auto;
  font-size: 85%;
  line-height: 1.45;
  background-color: #f6f8fa;
  border-radius: 3px;
  margin-bottom: 16px;
}

.markdown-body pre code {
  padding: 0;
  margin: 0;
  background-color: transparent;
  border: 0;
  word-break: normal;
  white-space: pre;
}

.markdown-body blockquote {
  padding: 0 1em;
  color: #6a737d;
  border-left: 0.25em solid #dfe2e5;
  margin: 0 0 16px 0;
}

/* 表格容器样式 - 添加横向滚动 */
.markdown-body table {
  display: block;
  width: 100%;
  overflow-x: auto;  /* 添加横向滚动 */
  -webkit-overflow-scrolling: touch; /* 提升移动设备上的滚动体验 */
  border-spacing: 0;
  border-collapse: collapse;
  margin-bottom: 16px;
}

/* 美化滚动条样式 */
.markdown-body table::-webkit-scrollbar {
  height: 8px;  /* 滚动条高度 */
}

.markdown-body table::-webkit-scrollbar-track {
  background: #f1f1f1;  /* 滚动条轨道颜色 */
  border-radius: 4px;
}

.markdown-body table::-webkit-scrollbar-thumb {
  background: #c1c1c1;  /* 滚动条颜色 */
  border-radius: 4px;
}

.markdown-body table::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;  /* 鼠标悬停时的滚动条颜色 */
}

/* 确保表格内容不会被压缩 */
.markdown-body table th,
.markdown-body table td {
  padding: 6px 13px;
  border: 1px solid #dfe2e5;
  white-space: nowrap;  /* 防止内容换行 */
  min-width: 80px;      /* 设置最小宽度 */
}

/* 对于特别长的单元格内容，可以设置最大宽度并使用省略号 */
.markdown-body table td.long-content {
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.markdown-body table tr {
  background-color: #fff;
  border-top: 1px solid #c6cbd1;
}

.markdown-body table tr:nth-child(2n) {
  background-color: #f6f8fa;
}

/* 表格标题样式 */
.markdown-body table th {
  font-weight: 600;
  background-color: #f0f0f0;
  position: sticky;
  top: 0;  /* 如果表格很长，表头会固定 */
  z-index: 1;
}

/* 添加表格滚动指示器样式 */
.table-scroll-indicator {
  text-align: center;
  color: #666;
  font-size: 0.8rem;
  padding: 4px 0;
  background-color: #f8f8f8;
  border-radius: 4px;
  margin-bottom: 5px;
  opacity: 0.7;
  transition: opacity 0.3s ease;
}

/* 为超宽表格添加特殊样式 */
.markdown-body table.wide-table {
  position: relative;
  border: 1px solid #e1e4e8;
  box-shadow: 0 1px 2px rgba(0,0,0,0.05);
}

/* 添加表格内容过长时的渐变效果 */
.markdown-body table::after {
  content: '';
  position: absolute;
  top: 0;
  right: 0;
  height: 100%;
  width: 30px;
  background: linear-gradient(to right, rgba(255,255,255,0), rgba(249,249,249,0.7));
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.3s ease;
}

.markdown-body table.has-overflow::after {
  opacity: 1;
}

/* 移动设备上的表格优化 */
@media (max-width: 768px) {
  .markdown-body table {
    font-size: 14px;
  }
  
  .markdown-body table th,
  .markdown-body table td {
    padding: 4px 8px;
  }
  
  .table-scroll-indicator {
    font-size: 0.7rem;
    padding: 3px 0;
  }
  
  /* 在小屏幕上使表格更紧凑 */
  .markdown-body table td.long-content {
    max-width: 200px;
  }
}
</style>

























