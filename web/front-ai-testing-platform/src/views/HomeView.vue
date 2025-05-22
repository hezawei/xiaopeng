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
          <button 
            class="btn btn-accent" 
            @click="startAnalysis"
            :disabled="isAnalyzing || uploadedFiles.length === 0"
          >
            开始需求分析
          </button>

          <!-- 加载动画 -->
          <div class="loading" v-if="isAnalyzing">
            <div class="loading-spinner"></div>
            <p>正在分析需求，请稍候...</p>
          </div>
        </div>

        <!-- 分析结果 -->
        <div class="section" v-if="analysisResult">
          <h2>分析结果</h2>
          <div class="analysis-result">
            <pre>{{ analysisResult }}</pre>
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
import { ref, onMounted } from 'vue';

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
const requirementDescription = ref('');
const isAnalyzing = ref(false);
const analysisResult = ref(null);
const fileInput = ref(null);

// 方法
const setActiveMenu = (menuId) => {
  activeMenu.value = menuId;
};

const triggerFileUpload = () => {
  fileInput.value.click();
};

const handleFileChange = (event) => {
  const files = event.target.files;
  if (files.length > 0) {
    for (let i = 0; i < files.length; i++) {
      uploadedFiles.value.push(files[i]);
    }
  }
};

const handleFileDrop = (event) => {
  const files = event.dataTransfer.files;
  if (files.length > 0) {
    for (let i = 0; i < files.length; i++) {
      uploadedFiles.value.push(files[i]);
    }
  }
};

const removeFile = (index) => {
  uploadedFiles.value.splice(index, 1);
};

const startAnalysis = async () => {
  isAnalyzing.value = true;
  
  // 模拟API调用
  try {
    // 这里应该是实际的API调用
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    // 模拟返回结果
    analysisResult.value = {
      summary: "需求分析完成",
      keyPoints: [
        "识别到API接口测试需求",
        "需要支持自动化测试用例生成",
        "需要支持测试报告生成"
      ],
      recommendations: [
        "建议使用RESTful API测试框架",
        "建议集成CI/CD流程"
      ]
    };
  } catch (error) {
    console.error("分析过程出错:", error);
  } finally {
    isAnalyzing.value = false;
  }
};

onMounted(() => {
  // 页面加载完成后的初始化逻辑
  console.log("页面已加载");
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
</style>

