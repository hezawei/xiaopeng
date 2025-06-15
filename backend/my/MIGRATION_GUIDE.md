# 文件重命名迁移指南

## 迁移概述

本指南帮助您从旧的文件命名方案迁移到新的、更清晰的命名方案。

## 文件名变更对照表

| 旧文件名 | 新文件名 | 状态 |
|----------|----------|------|
| `document_processor_factory.py` | `document_processing_entry.py` | ✅ 已创建 |
| `document_image_processor.py` | `multimodal_document_processor.py` | ✅ 已创建 |
| `llamaindex_document_processor.py` | `text_document_processor.py` | ✅ 已创建 |

## 代码迁移步骤

### 1. 更新导入语句

#### 旧的导入方式：
```python
# 旧方式
from document_processor_factory import DocumentProcessorFactory
from document_image_processor import DocumentImageProcessor
from llamaindex_document_processor import LlamaIndexDocumentProcessor
```

#### 新的导入方式：
```python
# 新方式
from document_processing_entry import DocumentProcessingEntry
from multimodal_document_processor import MultimodalDocumentProcessor
from text_document_processor import TextDocumentProcessor
```

### 2. 更新类名和方法调用

#### 旧的调用方式：
```python
# 旧方式
processor = DocumentProcessorFactory.create_processor()
image_processor = DocumentImageProcessor()
text_processor = LlamaIndexDocumentProcessor()
```

#### 新的调用方式：
```python
# 新方式
processor = DocumentProcessingEntry.create_processor()
image_processor = MultimodalDocumentProcessor()
text_processor = TextDocumentProcessor()
```

### 3. 向后兼容性

为了确保平滑迁移，新文件中包含了向后兼容的别名：

```python
# 在 document_processing_entry.py 中
DocumentProcessorFactory = DocumentProcessingEntry
```

这意味着您可以：
1. **立即使用新文件** - 旧的调用方式仍然有效
2. **逐步迁移** - 按照自己的节奏更新代码
3. **测试验证** - 确保新旧方式都能正常工作

## 具体迁移示例

### 示例 1：基本文档处理

#### 迁移前：
```python
from document_processor_factory import DocumentProcessorFactory

# 创建处理器
processor = DocumentProcessorFactory.create_processor()

# 处理文档
result = await processor.process_document("document.docx")
```

#### 迁移后：
```python
from document_processing_entry import DocumentProcessingEntry

# 创建处理器
processor = DocumentProcessingEntry.create_processor()

# 处理文档
result = await processor.process_document("document.docx")
```

### 示例 2：多模态处理

#### 迁移前：
```python
from document_image_processor import DocumentImageProcessor

# 创建图片处理器
image_processor = DocumentImageProcessor()

# 处理包含图片的文档
text_with_descriptions = await image_processor.process_document_to_text("document.docx")
```

#### 迁移后：
```python
from multimodal_document_processor import MultimodalDocumentProcessor

# 创建多模态处理器
multimodal_processor = MultimodalDocumentProcessor()

# 处理包含图片的文档
text_with_descriptions = await multimodal_processor.process_document_to_text("document.docx")
```

### 示例 3：纯文本处理

#### 迁移前：
```python
from llamaindex_document_processor import LlamaIndexDocumentProcessor

# 创建文本处理器
text_processor = LlamaIndexDocumentProcessor()

# 处理纯文本文档
result = text_processor.process_and_query("document.txt", "查询内容")
```

#### 迁移后：
```python
from text_document_processor import TextDocumentProcessor

# 创建文本处理器
text_processor = TextDocumentProcessor()

# 处理纯文本文档
result = text_processor.process_and_query("document.txt", "查询内容")
```

## 重构后的知识库系统集成

如果您使用重构后的知识库系统，导入已经自动更新：

```python
# 重构后的系统自动使用新文件名
from knowledge_base import BusinessKnowledgeBaseManager

manager = BusinessKnowledgeBaseManager()
# 内部自动使用 DocumentProcessingEntry
```

## 迁移检查清单

### ✅ 代码迁移检查

- [ ] 更新所有 `from document_processor_factory import` 语句
- [ ] 更新所有 `from document_image_processor import` 语句  
- [ ] 更新所有 `from llamaindex_document_processor import` 语句
- [ ] 更新类名引用：`DocumentProcessorFactory` → `DocumentProcessingEntry`
- [ ] 更新类名引用：`DocumentImageProcessor` → `MultimodalDocumentProcessor`
- [ ] 更新类名引用：`LlamaIndexDocumentProcessor` → `TextDocumentProcessor`

### ✅ 测试验证检查

- [ ] 运行现有测试，确保功能正常
- [ ] 测试文档处理功能
- [ ] 测试图片处理功能
- [ ] 测试查询功能
- [ ] 验证新旧导入方式都能工作

### ✅ 文档更新检查

- [ ] 更新代码注释中的文件名引用
- [ ] 更新README文档
- [ ] 更新API文档
- [ ] 更新示例代码

## 常见问题解答

### Q1: 旧的导入语句还能用吗？
**A:** 是的，为了向后兼容，旧的导入语句仍然可以使用。但建议逐步迁移到新的命名方式。

### Q2: 需要立即更新所有代码吗？
**A:** 不需要。您可以按照自己的节奏逐步迁移。新旧方式可以并存。

### Q3: 功能有变化吗？
**A:** 没有。只是文件名和类名更改，所有功能保持完全一致。

### Q4: 如何确保迁移成功？
**A:** 运行现有的测试用例，确保所有功能正常工作。

## 迁移时间建议

### 立即可做：
- 新项目直接使用新文件名
- 更新文档和注释

### 逐步进行：
- 更新现有代码的导入语句
- 更新类名引用

### 长期目标：
- 完全迁移到新命名方案
- 移除向后兼容别名

## 获得帮助

如果在迁移过程中遇到问题：

1. **检查导入路径** - 确保新文件存在且路径正确
2. **验证功能** - 运行简单的测试确保功能正常
3. **查看示例** - 参考本指南中的示例代码
4. **逐步迁移** - 一次只更改一个文件，便于排查问题

---

**迁移指南完成** ✅

按照本指南，您可以平滑地从旧文件名迁移到新的、更清晰的命名方案！
