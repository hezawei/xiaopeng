"""
业务知识库测试脚本

本脚本演示如何使用BusinessKnowledgeBaseManager类来管理和查询业务知识库。
"""

import asyncio
import os
import sys
from pathlib import Path

# 添加父目录到路径，以便导入business_knowledge_base模块
sys.path.append(str(Path(__file__).parent.parent))

from my.business_knowledge_base import BusinessKnowledgeBaseManager


async def main():
    """主函数"""
    print("=== 业务知识库测试 ===")
    
    # 获取脚本所在目录的绝对路径
    script_dir = Path(__file__).parent.absolute()
    
    # 创建知识库管理器
    kb_manager = BusinessKnowledgeBaseManager(
        base_dir=script_dir / "test_business_kb",
        milvus_uri="http://localhost:19530"  # 使用本地Docker部署的Milvus
    )
    
    # 测试创建业务知识库
    business_id = "test_business"
    print(f"\n1. 创建业务知识库 '{business_id}'")
    success = kb_manager.create_business_kb(
        business_id=business_id,
        name="测试业务",
        description="这是一个测试业务知识库",
        overwrite=True
    )
    print(f"创建结果: {'成功' if success else '失败'}")
    
    # 列出所有业务知识库
    print("\n现有业务知识库:")
    businesses = kb_manager.list_businesses()
    if businesses:
        for business in businesses:
            print(f"- {business['name']} (ID: {business['business_id']}, 文档数: {business['document_count']})")
    else:
        print("暂无业务知识库")
    
    # 创建业务知识库
    business_id = input("\n请输入要创建的业务ID (例如: intelligent_chassis): ")
    if not business_id:
        business_id = "intelligent_chassis"
        print(f"使用默认业务ID: {business_id}")
    
    business_name = input(f"请输入业务名称 (默认: {business_id}): ")
    if not business_name:
        business_name = business_id
    
    business_desc = input("请输入业务描述: ")
    
    # 检查业务是否已存在
    overwrite = False
    if business_id in [b["business_id"] for b in businesses]:
        choice = input(f"业务 '{business_id}' 已存在，是否覆盖? (y/n): ")
        overwrite = choice.lower() == 'y'
        if not overwrite:
            print("操作取消")
            return
    
    # 创建业务知识库
    success = kb_manager.create_business_kb(
        business_id=business_id,
        name=business_name,
        description=business_desc,
        overwrite=overwrite
    )
    
    if not success:
        print(f"创建业务知识库 '{business_id}' 失败")
        return
    
    print(f"业务知识库 '{business_id}' 创建成功")
    
    # 添加文档
    while True:
        print("\n=== 文档管理 ===")
        print("1. 添加文档")
        print("2. 查看文档列表")
        print("3. 删除文档")
        print("4. 查询知识库")
        print("5. 退出")
        
        choice = input("请选择操作 (1-5): ")
        
        if choice == "1":
            # 添加文档
            file_path = input("请输入文档路径 (支持PDF、DOCX、TXT等): ")
            if not file_path:
                print("文档路径不能为空")
                continue
            
            if not os.path.exists(file_path):
                print(f"文件 '{file_path}' 不存在")
                continue
            
            process_images = input("是否处理文档中的图片? (y/n, 默认: y): ").lower() != 'n'
            
            print(f"正在添加文档 '{file_path}'...")
            doc_ids = await kb_manager.add_documents_to_kb(
                business_id=business_id,
                file_paths=[file_path],
                process_images=process_images
            )
            
            if doc_ids:
                print(f"文档添加成功，文档ID: {doc_ids[0]}")
            else:
                print("文档添加失败")
        
        elif choice == "2":
            # 查看文档列表
            business_info = kb_manager.get_business_info(business_id)
            print(f"\n业务 '{business_info['name']}' 的文档列表:")
            
            if not business_info.get("documents"):
                print("暂无文档")
                continue
            
            for i, doc in enumerate(business_info["documents"]):
                print(f"{i+1}. {doc['file_name']} (ID: {doc['doc_id']})")
                print(f"   添加时间: {doc['added_at']}")
                print(f"   原始路径: {doc['original_path']}")
                print()
        
        elif choice == "3":
            # 删除文档
            business_info = kb_manager.get_business_info(business_id)
            
            if not business_info.get("documents"):
                print("暂无文档可删除")
                continue
            
            print(f"\n业务 '{business_info['name']}' 的文档列表:")
            for i, doc in enumerate(business_info["documents"]):
                print(f"{i+1}. {doc['file_name']} (ID: {doc['doc_id']})")
            
            doc_index = input("请输入要删除的文档序号 (1-N): ")
            try:
                doc_index = int(doc_index) - 1
                if doc_index < 0 or doc_index >= len(business_info["documents"]):
                    print("无效的序号")
                    continue
                
                doc_id = business_info["documents"][doc_index]["doc_id"]
                confirm = input(f"确认删除文档 '{business_info['documents'][doc_index]['file_name']}'? (y/n): ")
                
                if confirm.lower() == 'y':
                    success = kb_manager.remove_document_from_kb(business_id, doc_id)
                    if success:
                        print("文档删除成功")
                    else:
                        print("文档删除失败")
                else:
                    print("操作取消")
            
            except (ValueError, IndexError):
                print("无效的输入")
        
        elif choice == "4":
            # 查询知识库
            query = input("请输入查询内容: ")
            if not query:
                print("查询内容不能为空")
                continue
            
            top_k = input("返回的最相关结果数量 (默认: 5): ")
            try:
                top_k = int(top_k) if top_k else 5
            except ValueError:
                top_k = 5
            
            threshold = input("相似度阈值 (0-1, 默认: 0.7): ")
            try:
                threshold = float(threshold) if threshold else 0.7
                threshold = max(0, min(1, threshold))
            except ValueError:
                threshold = 0.7
            
            print(f"正在查询: {query}")
            result = kb_manager.query_business_kb(
                business_id=business_id,
                query=query,
                top_k=top_k,
                similarity_threshold=threshold
            )
            
            print(f"\n回答: {result['response']}")
            
            if result["source_nodes"]:
                print("\n相关文本片段:")
                for i, node in enumerate(result["source_nodes"]):
                    print(f"\n片段 {i+1} (相关度: {node.get('score', 0):.4f}):")
                    print(f"文档: {node.get('file_name', 'unknown')}")
                    print(f"内容: {node.get('text', '')[:200]}...")
            else:
                print("\n未找到相关文本片段")
        
        elif choice == "5":
            # 退出
            print("测试结束")
            break
        
        else:
            print("无效的选择")


if __name__ == "__main__":
    asyncio.run(main())



