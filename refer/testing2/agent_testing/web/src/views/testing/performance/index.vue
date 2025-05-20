<script setup>
import { ref, onMounted, h } from 'vue';
import { Button, Card, Upload, Spin, Table, Progress, Tabs, Empty, Divider, Alert, Tag, message } from 'ant-design-vue';
import { UploadOutlined, FileTextOutlined, ThunderboltOutlined, DashboardOutlined, BulbOutlined } from '@ant-design/icons-vue';
import axios from 'axios';

// 上传文件相关状态
const fileList = ref([]);
const uploading = ref(false);
const showResult = ref(false);

// 分析结果相关状态
const isAnalyzing = ref(false);
const analysisResult = ref({
  summary: {},
  bottlenecks: [],
  recommendations: [],
  metrics: {},
  charts: []
});

// 消息处理函数 - 接收流式响应
let messageHandler = null;
const messages = ref([]);
const analysisFinished = ref(false);

// 处理上传前的验证
const beforeUpload = (file) => {
  const isPerfJson = file.type === 'application/json' || file.name.endsWith('.json');
  const isPerfHtml = file.type === 'text/html' || file.name.endsWith('.html');
  const isPerfValidFormat = isPerfJson || isPerfHtml || file.name.endsWith('.har');
  
  if (!isPerfValidFormat) {
    message.error('请上传性能报告文件（支持 JSON/HTML/HAR 格式）');
  }
  
  return isPerfValidFormat || Upload.LIST_IGNORE;
};

// 自定义上传
const customRequest = async ({ file, onSuccess, onError }) => {
  const formData = new FormData();
  formData.append('file', file);
  
  try {
    uploading.value = true;
    const response = await axios.post('/api/v1/agent/performance/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    
    if (response.data.success) {
      onSuccess(response, file);
      fileList.value = [{ uid: '1', name: file.name, status: 'done', url: response.data.fileUrl }];
      message.success('文件上传成功');
    } else {
      onError(response);
      message.error('文件上传失败');
    }
  } catch (error) {
    onError(error);
    message.error('文件上传失败');
  } finally {
    uploading.value = false;
  }
};

// 分析性能报告
const analyzePerformance = async () => {
  if (fileList.value.length === 0) {
    message.warning('请先上传性能报告文件');
    return;
  }
  
  isAnalyzing.value = true;
  analysisFinished.value = false;
  messages.value = [];
  showResult.value = true;
  
  try {
    // 使用EventSource获取流式响应
    const eventSource = new EventSource(`/api/v1/agent/performance/analyze?file_id=${fileList.value[0].uid}`);
    
    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      messages.value.push(data);
      
      // 如果是最终结果，更新分析结果
      if (data.is_final) {
        analysisFinished.value = true;
        analysisResult.value = data.result || analysisResult.value;
        eventSource.close();
      }
    };
    
    eventSource.onerror = (error) => {
      message.error('分析过程中出现错误');
      eventSource.close();
      isAnalyzing.value = false;
    };
    
    messageHandler = eventSource;
  } catch (error) {
    message.error('启动分析失败');
    isAnalyzing.value = false;
  }
};

// 在组件卸载时关闭连接
onMounted(() => {
  return () => {
    if (messageHandler) {
      messageHandler.close();
    }
  };
});

// 定义表格列
const bottleneckColumns = [
  {
    title: '问题类型',
    dataIndex: 'type',
    key: 'type',
    width: '15%',
    customRender: ({ text }) => {
      const colorMap = {
        '严重': 'red',
        '中等': 'orange',
        '轻微': 'blue'
      };
      return h(Tag, { color: colorMap[text] || 'blue' }, () => text);
    }
  },
  {
    title: '问题描述',
    dataIndex: 'description',
    key: 'description',
    width: '40%'
  },
  {
    title: '影响',
    dataIndex: 'impact',
    key: 'impact',
    width: '15%'
  },
  {
    title: '位置',
    dataIndex: 'location',
    key: 'location',
    width: '15%'
  },
  {
    title: '严重程度',
    dataIndex: 'severity',
    key: 'severity',
    width: '15%',
    customRender: ({ text }) => {
      const percent = text === '严重' ? 90 : text === '中等' ? 60 : 30;
      const color = text === '严重' ? 'red' : text === '中等' ? 'orange' : 'green';
      return h(Progress, { percent: percent, size: 'small', strokeColor: color });
    }
  }
];

// 性能指标列
const metricsColumns = [
  {
    title: '指标名称',
    dataIndex: 'name',
    key: 'name',
    width: '30%'
  },
  {
    title: '当前值',
    dataIndex: 'value',
    key: 'value',
    width: '20%'
  },
  {
    title: '基准值',
    dataIndex: 'benchmark',
    key: 'benchmark',
    width: '20%'
  },
  {
    title: '状态',
    dataIndex: 'status',
    key: 'status',
    width: '30%',
    customRender: ({ text, record }) => {
      const color = text === '良好' ? 'green' : text === '一般' ? 'orange' : 'red';
      const percent = record.percentOfBenchmark || 0;
      return h('div', [
        h(Tag, { color: color }, () => text),
        h(Progress, { percent: percent, size: 'small', strokeColor: color })
      ]);
    }
  }
];
</script>

<template>
  <div class="performance-analysis-container">
    <Card title="性能分析智能体" class="performance-card">
      <div class="upload-section">
        <div v-if="!showResult" class="upload-container">
          <Upload
            v-model:fileList="fileList"
            :beforeUpload="beforeUpload"
            :customRequest="customRequest"
            :maxCount="1"
            class="upload-area"
          >
            <Button :disabled="uploading" :loading="uploading" type="primary">
              <UploadOutlined />
              上传性能报告
            </Button>
            <div class="upload-hint">支持 JSON/HTML/HAR 格式的性能报告文件</div>
          </Upload>
          
          <div class="analysis-actions">
            <Button 
              type="primary" 
              :disabled="fileList.length === 0 || uploading" 
              :loading="isAnalyzing"
              @click="analyzePerformance"
            >
              <ThunderboltOutlined />
              开始分析
            </Button>
          </div>
        </div>
        
        <div v-if="showResult" class="result-container">
          <Tabs>
            <Tabs.TabPane key="analysis" tab="分析过程">
              <div class="message-container">
                <Spin v-if="isAnalyzing && !analysisFinished" tip="正在分析中..." class="analysis-loading" />
                
                <div v-for="(msg, index) in messages" :key="index" class="message">
                  <Alert 
                    :message="msg.source" 
                    :description="msg.content" 
                    :type="msg.source.includes('瓶颈') ? 'warning' : 'info'" 
                    showIcon
                  />
                </div>
                
                <div v-if="messages.length === 0 && isAnalyzing" class="empty-message">
                  <Empty description="等待分析结果..." />
                </div>
              </div>
            </Tabs.TabPane>
            
            <Tabs.TabPane key="summary" tab="性能概览" disabled="!analysisFinished">
              <div v-if="analysisFinished" class="summary-container">
                <Card title="性能总结" class="summary-card">
                  <div v-if="analysisResult.summary">{{ analysisResult.summary.content }}</div>
                  <Empty v-else description="暂无总结数据" />
                </Card>
                
                <Divider />
                
                <Card title="关键性能指标" class="metrics-card">
                  <Table 
                    :dataSource="analysisResult.metrics.data || []"
                    :columns="metricsColumns"
                    :pagination="false" 
                    rowKey="name"
                  />
                </Card>
              </div>
              <Empty v-else description="请先完成性能分析" />
            </Tabs.TabPane>
            
            <Tabs.TabPane key="bottlenecks" tab="瓶颈分析" disabled="!analysisFinished">
              <div v-if="analysisFinished && analysisResult.bottlenecks && analysisResult.bottlenecks.length > 0">
                <Table 
                  :dataSource="analysisResult.bottlenecks" 
                  :columns="bottleneckColumns" 
                  rowKey="id"
                />
              </div>
              <Empty v-else description="暂无瓶颈数据" />
            </Tabs.TabPane>
            
            <Tabs.TabPane key="recommendations" tab="优化建议" disabled="!analysisFinished">
              <div v-if="analysisFinished && analysisResult.recommendations && analysisResult.recommendations.length > 0">
                <Card v-for="(rec, index) in analysisResult.recommendations" 
                      :key="index"
                      :title="rec.title"
                      class="recommendation-card"
                >
                  <div class="recommendation-content">
                    <BulbOutlined class="recommendation-icon" />
                    <div class="recommendation-body">
                      <div class="recommendation-desc">{{ rec.description }}</div>
                      <div class="recommendation-impl">
                        <strong>实施方法：</strong> {{ rec.implementation }}
                      </div>
                      <div class="recommendation-impact">
                        <strong>预期影响：</strong>
                        <Tag :color="rec.impact_level === '高' ? 'red' : rec.impact_level === '中' ? 'orange' : 'green'">
                          {{ rec.impact_level }}
                        </Tag>
                        {{ rec.impact }}
                      </div>
                    </div>
                  </div>
                </Card>
              </div>
              <Empty v-else description="暂无优化建议" />
            </Tabs.TabPane>
          </Tabs>
          
          <div class="result-actions">
            <Button type="primary" @click="showResult = false; isAnalyzing = false;">
              返回上传
            </Button>
          </div>
        </div>
      </div>
    </Card>
  </div>
</template>

<style scoped>
.performance-analysis-container {
  padding: 20px;
  background-color: #f5f5f5;
  min-height: 100vh;
}

.performance-card {
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.upload-section {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.upload-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40px 0;
  width: 100%;
}

.upload-area {
  margin-bottom: 20px;
  text-align: center;
}

.upload-hint {
  margin-top: 8px;
  color: #888;
  font-size: 13px;
}

.analysis-actions {
  margin-top: 30px;
}

.result-container {
  width: 100%;
  padding: 20px 0;
}

.result-actions {
  margin-top: 20px;
  text-align: center;
}

.message-container {
  margin: 20px 0;
  max-height: 500px;
  overflow-y: auto;
  padding: 10px;
  border: 1px solid #f0f0f0;
  border-radius: 4px;
}

.message {
  margin-bottom: 10px;
}

.analysis-loading {
  display: flex;
  justify-content: center;
  margin: 40px 0;
}

.summary-container {
  margin: 20px 0;
}

.metrics-card,
.summary-card {
  margin-bottom: 20px;
}

.recommendation-card {
  margin-bottom: 16px;
}

.recommendation-content {
  display: flex;
  align-items: flex-start;
}

.recommendation-icon {
  font-size: 24px;
  color: #1890ff;
  margin-right: 16px;
  margin-top: 4px;
}

.recommendation-body {
  flex: 1;
}

.recommendation-desc {
  margin-bottom: 12px;
}

.recommendation-impl {
  margin-bottom: 8px;
  color: #555;
}

.recommendation-impact {
  color: #555;
}

.empty-message {
  padding: 40px 0;
  text-align: center;
}
</style>