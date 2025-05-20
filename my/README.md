# 需求分析系统

这是一个基于AutoGen的需求分析系统，可以分析需求文档并生成结构化的需求列表。

## 安装依赖

```bash
pip install autogen-agentchat autogen-core autogen-ext pydantic docling llama-index
```

## 使用方法

1. 将需求文档(PDF格式)放在项目根目录
2. 运行主程序:

```bash
python main.py --file your_requirement_doc.pdf
```

3. 系统会分析文档并在终端输出结构化的需求列表