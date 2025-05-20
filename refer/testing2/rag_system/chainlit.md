# 欢迎使用但问智库平台 🚀🤖
## 平台使用说明
### 1、大模型对话
- **输入您的问题，直接与超强大语言模型对话**
- **上传多格式文件，与您的文档直接精准对话**
### 2、Excel&CSV对话
- **上传Excel、CSV文件，进行精准高效的数据分析与统计**
- **支持输出多种类型图表数据**
### 3、数据库对话
- **生成SQL语句、执行SQL语句、输出各种图表数据**
- **支持MySQL、PostgreSQL、SQLite、Oracle、DuckDB、Hive、Snowflake等多种数据库**
- **默认测试数据：[Chinook](https://github.com/lerocha/chinook-database/)**
- **[Chinook](https://github.com/lerocha/chinook-database/)样本数据库包含11张表：**
  * 员工表（employees table）存储员工数据，如ID、姓氏、名字等。它还有一个名为ReportsTo的字段，用于指定谁向谁汇报。
  * 客户表（customers table）存储客户数据。
  * 发票和发票项表（invoices & invoice_items tables）：这两张表存储发票数据。发票表存储发票头数据，而发票项表存储发票行项数据。
  * 艺术家表（artists table）存储艺术家数据。这是一个简单的表格，包含ID和名字。
  * 专辑表（albums table）存储关于一系列曲目的数据。每个专辑属于一个艺术家，但一个艺术家可能有多个专辑。
  * 媒体类型表（media_types table）存储媒体类型，如MPEG音频和AAC音频文件。
  * 类型表（genres table）存储音乐类型，如摇滚、爵士、金属等。
  * 曲目表（tracks table）存储歌曲数据。每首曲目属于一个专辑。
  * 播放列表和播放列表曲目表（playlists & playlist_track tables）：播放列表表存储关于播放列表的数据。每个播放列表包含一系列曲目。每首曲目可能属于多个播放列表。播放列表和曲目表之间的关系是多对多的。播放列表曲目表用于反映这种关系。
  * ![](/public/chinook-schema.png)
  
- **数据库对话常见问题**
  [数据库对话常见问题及答案参考（支持中文提问）](https://m-soro.github.io/Business-Analytics/SQL-for-Data-Analysis/L4-Project-Query-Music-Store/)
  
### 4、多模态高性能Agent+RAG系统

- **文档多模态对话:** 精确解读文档中的图表并展示
- **主流大语言模型:** 自由切换国内外开源及闭源大语言模型
- **知识库高效准确:** 基于VLLM+LLMs+RAG+Agent等组合技术，精确获取答案
- **多格式文件对话:** 图片、图表、PDF、PPT、DOC、Excel、Markdown、数据库等
- **多场景知识获取:** 自主识别大模型对话、联网搜索、数据库、知识库对话
- **显示引用来源:** 可以查看引用的知识库数据来源，让答案更具说服力
- **持续更新中:** ......

在这里，您可以自由的与您的私有数据库、知识库及文件对话，并支持聊天数据永久存储在本地服务器。