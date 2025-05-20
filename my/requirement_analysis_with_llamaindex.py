"""
使用LlamaIndex进行需求分析示例

本脚本演示如何使用LlamaIndex处理需求文档，并使用大模型进行需求分析。
流程包括：
1. 加载需求文档
2. 文档分块处理
3. 创建向量索引
4. 提取关键需求信息
5. 使用大模型生成结构化需求列表

使用方法:
```bash
python requirement_analysis_with_llamaindex.py --file "需求文档.docx"
```
"""

import argparse
import asyncio
import json
from typing import List, Dict, Any, Optional

# 导入LlamaIndex文档处理器
from llamaindex_document_processor import LlamaIndexDocumentProcessor

# 导入需求分析相关模型
from requirement_analysis_agent import BusinessRequirement, BusinessRequirementList

# 导入大模型客户端
from llms import model_client

class RequirementAnalysisWithLlamaIndex:
    """
    使用LlamaIndex进行需求分析的类

    该类结合了LlamaIndex的文档处理能力和大模型的分析能力，
    可以从需求文档中提取关键信息，并生成结构化的需求列表。
    """

    def __init__(
        self,
        file_path: str,
        embedding_model_type: str = "huggingface",
        embedding_model_name: Optional[str] = "BAAI/bge-small-zh-v1.5",
        openai_api_key: Optional[str] = None
    ):
        """
        初始化需求分析器

        Args:
            file_path: 需求文档路径
            embedding_model_type: 嵌入模型类型，可选值：
                - "huggingface": 使用HuggingFace嵌入模型
                - "openai": 使用OpenAI嵌入模型
            embedding_model_name: 嵌入模型名称
            openai_api_key: OpenAI API密钥（仅当embedding_model_type为"openai"时需要）
        """
        self.file_path = file_path
        self.document_processor = LlamaIndexDocumentProcessor(
            persist_dir="./requirement_index",
            embedding_model_type=embedding_model_type,
            embedding_model_name=embedding_model_name,
            openai_api_key=openai_api_key
        )

    async def extract_requirements(self) -> Dict[str, Any]:
        """
        从需求文档中提取关键需求信息

        Returns:
            包含关键需求信息的字典
        """
        # 定义需求相关的查询列表
        requirement_queries = [
            "文档中描述了哪些功能需求?",
            "文档中描述了哪些性能需求?",
            "文档中描述了哪些安全需求?",
            "文档中描述了哪些业务模块?",
            "文档中描述了哪些验收标准?"
        ]

        # 处理文档并执行查询
        results = {}
        for query in requirement_queries:
            print(f"\n执行查询: {query}")
            result = self.document_processor.process_and_query(
                file_path=self.file_path,
                query=query,
                chunk_method="sentence",
                use_existing_index=True,
                top_k=3
            )
            results[query] = result["response"]

        return results

    async def generate_structured_requirements(self, extracted_info: Dict[str, Any]) -> BusinessRequirementList:
        """
        使用大模型生成结构化需求列表

        Args:
            extracted_info: 从文档中提取的需求信息

        Returns:
            结构化的需求列表
        """
        # 构建提示词
        prompt = """
        请根据以下从需求文档中提取的信息，生成结构化的需求列表。
        每个需求项应包含以下字段：
        - requirement_id: 需求编号(业务缩写+需求类型+随机3位数字)
        - requirement_name: 需求名称
        - requirement_type: 功能需求/性能需求/安全需求/其它需求
        - parent_requirement: 该需求的上级需求(如果有)
        - module: 所属的业务模块
        - requirement_level: 需求层级[BR]
        - reviewer: 审核人
        - estimated_hours: 预计完成工时(整数类型)
        - description: 需求描述
        - acceptance_criteria: 验收标准

        提取的信息如下：
        """

        # 添加提取的信息
        for query, response in extracted_info.items():
            prompt += f"\n## {query}\n{response}\n"

        # 添加输出格式说明
        prompt += """
        请以JSON格式输出，格式如下：
        {
          "requirements": [
            {
              "requirement_id": "...",
              "requirement_name": "...",
              "requirement_type": "...",
              "parent_requirement": "...",
              "module": "...",
              "requirement_level": "BR",
              "reviewer": "审核人",
              "estimated_hours": 8,
              "description": "...",
              "acceptance_criteria": "..."
            },
            ...
          ]
        }
        """

        # 调用大模型生成结构化需求
        print("\n正在使用大模型生成结构化需求列表...")
        response = await model_client.create(
            messages=[{"role": "user", "content": prompt}]
        )

        # 解析响应
        content = response.choices[0].message.content

        # 尝试从响应中提取JSON
        try:
            # 查找JSON开始和结束的位置
            json_start = content.find("{")
            json_end = content.rfind("}") + 1

            if json_start >= 0 and json_end > json_start:
                json_str = content[json_start:json_end]
                data = json.loads(json_str)

                # 转换为BusinessRequirementList对象
                requirements = []
                for req_data in data.get("requirements", []):
                    requirement = BusinessRequirement(
                        requirement_id=req_data.get("requirement_id", ""),
                        requirement_name=req_data.get("requirement_name", ""),
                        requirement_type=req_data.get("requirement_type", ""),
                        parent_requirement=req_data.get("parent_requirement"),
                        module=req_data.get("module", ""),
                        requirement_level=req_data.get("requirement_level", "BR"),
                        reviewer=req_data.get("reviewer", "审核人"),
                        estimated_hours=req_data.get("estimated_hours", 8),
                        description=req_data.get("description", ""),
                        acceptance_criteria=req_data.get("acceptance_criteria", "")
                    )
                    requirements.append(requirement)

                return BusinessRequirementList(requirements=requirements)
            else:
                print("无法从响应中提取JSON")
                return BusinessRequirementList(requirements=[])
        except Exception as e:
            print(f"解析响应失败: {str(e)}")
            print(f"原始响应: {content}")
            return BusinessRequirementList(requirements=[])

    async def analyze(self) -> BusinessRequirementList:
        """
        执行完整的需求分析流程

        Returns:
            结构化的需求列表
        """
        # 提取需求信息
        extracted_info = await self.extract_requirements()

        # 生成结构化需求
        requirements = await self.generate_structured_requirements(extracted_info)

        return requirements


async def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='使用LlamaIndex进行需求分析')
    parser.add_argument('--file', type=str, required=True, help='需求文档路径')
    parser.add_argument('--embedding-model', type=str, default="huggingface",
                        choices=["huggingface", "openai"], help='嵌入模型类型')
    parser.add_argument('--model-name', type=str,
                        help='嵌入模型名称，默认为huggingface使用BAAI/bge-small-zh-v1.5，openai使用text-embedding-3-small')
    parser.add_argument('--openai-api-key', type=str, help='OpenAI API密钥（仅当使用OpenAI嵌入模型时需要）')
    args = parser.parse_args()

    # 设置模型名称
    model_name = args.model_name
    if model_name is None:
        if args.embedding_model == "huggingface":
            model_name = "BAAI/bge-small-zh-v1.5"
        else:
            model_name = "text-embedding-3-small"

    # 创建需求分析器
    analyzer = RequirementAnalysisWithLlamaIndex(
        file_path=args.file,
        embedding_model_type=args.embedding_model,
        embedding_model_name=model_name,
        openai_api_key=args.openai_api_key
    )

    # 执行需求分析
    print(f"开始分析需求文档: {args.file}")
    print(f"使用嵌入模型类型: {args.embedding_model}")
    print(f"使用嵌入模型名称: {model_name}")
    requirements = await analyzer.analyze()

    # 打印结构化需求
    print("\n分析结果:")
    for i, req in enumerate(requirements.requirements):
        print(f"\n--- 需求 {i+1} ---")
        print(f"需求ID: {req.requirement_id}")
        print(f"需求名称: {req.requirement_name}")
        print(f"需求类型: {req.requirement_type}")
        print(f"所属模块: {req.module}")
        print(f"需求层级: {req.requirement_level}")
        print(f"审核人: {req.reviewer}")
        print(f"预计工时: {req.estimated_hours}小时")
        print(f"需求描述: {req.description}")
        print(f"验收标准: {req.acceptance_criteria}")

    print("\n需求分析完成")


if __name__ == "__main__":
    asyncio.run(main())
