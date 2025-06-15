# 业务知识库管理系统 - 重构版本 v2.0

## 概述

这是业务知识库管理系统的重构版本，采用模块化设计，大幅提升了代码的可读性、可维护性、可扩展性和健壮稳定性。原始的 `business_knowledge_base.py` 文件已保留作为备份。

## 重构亮点

### 🎯 核心改进

1. **模块化架构**：将原来的单一大文件拆分为9个专门的模块
2. **关注点分离**：混合搜索和关联关系构建被独立拆分
3. **依赖注入**：通过构造函数注入依赖，提高可测试性
4. **接口隔离**：每个模块提供清晰的接口定义
5. **错误处理**：增强的异常处理和日志记录

### 🔧 技术保持

- ✅ **Milvus向量数据库**：完全保留原有的Milvus集成
- ✅ **本地向量化处理**：继续使用HuggingFace嵌入模型
- ✅ **多模态处理**：保留图片处理和文档转换功能
- ✅ **所有原有功能**：无功能缺失，完全向后兼容

## 模块架构

```
knowledge_base/
├── business_knowledge_base_manager.py  # 🎯 核心管理器
├── metadata_manager.py                 # 📊 元数据管理
├── index_manager.py                    # 🔍 索引管理
├── document_processor_v2.py            # 📄 文档处理
├── relation_manager_v2.py              # 🔗 关联关系管理
├── entity_extractor.py                 # 🏷️ 实体提取
├── hybrid_search_engine.py             # 🔀 混合搜索引擎
├── query_engine.py                     # ❓ 查询引擎
├── sync_manager.py                     # 🔄 同步管理
├── utils_v2.py                         # 🛠️ 工具函数
├── example_usage.py                    # 📖 使用示例
└── README_v2.md                        # 📚 说明文档
```

## 核心模块说明

### 1. BusinessKnowledgeBaseManager
**核心管理器**，提供统一的对外接口，协调各个子模块的工作。

```python
manager = BusinessKnowledgeBaseManager(
    embedding_model_name="BAAI/bge-small-zh-v1.5",
    milvus_uri="tcp://localhost:19530"
)
```

### 2. RelationManager + EntityExtractor + HybridSearchEngine
**混合搜索核心组件**（重点拆分），负责：
- 从文档中提取实体
- 构建业务间的关联关系
- 实现跨业务的混合搜索

### 3. IndexManager
**索引管理器**，封装所有Milvus相关操作：
- 集合的创建、删除、管理
- 向量索引的构建和查询
- 索引配置的持久化

### 4. MetadataManager
**元数据管理器**，负责业务和文档信息的存储：
- 业务知识库的创建和管理
- 文档信息的存储和检索
- 数据一致性保障

### 5. DocumentProcessor
**文档处理器**，集成现有的文档处理工厂：
- 自动检测文档是否包含图片
- 智能选择处理方式（图片处理器 vs 直接处理）
- 支持PDF、DOCX、TXT等格式
- 集成多模态图片处理

## 快速开始

### 1. 基本使用

```python
import asyncio
from knowledge_base import BusinessKnowledgeBaseManager

async def main():
    # 创建管理器
    manager = BusinessKnowledgeBaseManager()
    
    # 创建业务知识库
    manager.create_business_kb("intelligent_chassis", "智能底盘")
    
    # 添加文档
    doc_ids = await manager.add_documents_to_kb(
        "intelligent_chassis", 
        ["doc1.pdf", "doc2.docx"]
    )
    
    # 查询
    result = await manager.query_business_kb(
        "intelligent_chassis", 
        "智能底盘的核心功能"
    )
    print(result["response"])

asyncio.run(main())
```

### 2. 跨业务混合搜索

```python
# 跨业务查询（重点功能）
result = await manager.query_with_cross_business(
    primary_business_id="intelligent_chassis",
    query="传感器技术应用",
    expand_to_related=True,
    max_related_businesses=2
)
```

### 3. 数据同步

```python
# 同步所有业务
sync_result = await manager.sync_all_businesses()
print(f"同步了 {sync_result['synced_businesses']} 个业务")
```

## 配置说明

### 默认配置

```python
DEFAULT_CONFIG = {
    "embedding_model_name": "BAAI/bge-small-zh-v1.5",
    "milvus_uri": "tcp://localhost:19530",
    "chunk_size": 512,
    "chunk_overlap": 50,
    "max_entities": 15,
    "similarity_top_k": 3,
    "max_related_businesses": 2
}
```

### 自定义配置

```python
manager = BusinessKnowledgeBaseManager(
    embedding_model_name="your-model-name",
    milvus_uri="your-milvus-uri",
    base_dir="/custom/path"
)
```

## 依赖要求

### 必需依赖
- `llama-index` - 文档处理和索引
- `pymilvus` - Milvus向量数据库
- `docling` - 文档转换
- `scikit-learn` - 机器学习工具
- `pathlib` - 路径处理

### 可选依赖
- `psutil` - 系统信息
- `spacy` - 自然语言处理
- `jieba` - 中文分词

## 重构对比

| 方面 | 原版本 | 重构版本 |
|------|--------|----------|
| 文件数量 | 1个大文件 | 9个专门模块 |
| 代码行数 | 1800+ 行 | 每个模块 < 300 行 |
| 可读性 | 😐 一般 | 😊 优秀 |
| 可维护性 | 😐 困难 | 😊 容易 |
| 可扩展性 | 😐 受限 | 😊 灵活 |
| 测试友好 | 😐 困难 | 😊 容易 |
| 混合搜索 | 😐 耦合 | 😊 独立 |

## 运行示例

```bash
# 运行使用示例
cd backend/my/knowledge_base
python example_usage.py
```

## 注意事项

1. **原文件保留**：`business_knowledge_base.py` 已保留作为备份
2. **功能完整**：所有原有功能都已保留，无功能缺失
3. **向后兼容**：API接口保持兼容
4. **Milvus依赖**：确保Milvus服务正常运行
5. **文档路径**：示例中的文档路径需要替换为实际路径

## 扩展指南

### 添加新的实体提取方法

```python
# 在 entity_extractor.py 中添加新方法
def _extract_by_custom_method(self, text: str, max_entities: int) -> List[str]:
    # 实现自定义实体提取逻辑
    pass
```

### 添加新的查询模式

```python
# 在 query_engine.py 中添加新的响应模式
def _build_custom_response(self, query: str, results: List[Dict]) -> Dict[str, Any]:
    # 实现自定义响应格式
    pass
```

### 集成新的向量数据库

```python
# 创建新的索引管理器
class CustomIndexManager(IndexManager):
    # 实现自定义向量数据库集成
    pass
```

## 贡献指南

1. 遵循单一职责原则
2. 保持接口简洁清晰
3. 添加充分的错误处理
4. 编写详细的文档注释
5. 提供使用示例

## 版本历史

- **v2.0.0** - 重构版本发布
  - 模块化架构设计
  - 混合搜索功能独立拆分
  - 完整保留原有功能
  - 大幅提升代码质量

---

**重构完成** ✅ 

原始功能完全保留，代码结构大幅优化，特别是混合搜索和关联关系构建部分已独立拆分，显著提升了系统的可维护性和可扩展性。
