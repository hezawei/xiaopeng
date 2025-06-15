"""
业务知识库测试脚本

本脚本演示如何使用BusinessKnowledgeBaseManager类来管理和查询业务知识库。
"""

import os
import sys
import asyncio
import argparse
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

# 在脚本开头添加这段代码以获取更详细的错误信息
import traceback

def custom_excepthook(exc_type, exc_value, exc_traceback):
    print("发生异常:")
    traceback.print_exception(exc_type, exc_value, exc_traceback)

sys.excepthook = custom_excepthook

# 导入业务知识库管理器
from business_knowledge_base import BusinessKnowledgeBaseManager

# 设置日志
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BusinessKBTester:
    """业务知识库测试工具"""
    
    def __init__(
        self,
        base_dir: str = None,
        milvus_uri: str = "http://localhost:19530",
        auto_sync: bool = True
    ):
        """
        初始化测试工具
        
        Args:
            base_dir: 知识库基础目录
            milvus_uri: Milvus服务URI
            auto_sync: 是否在初始化时自动同步数据
        """
        # 获取脚本所在目录的绝对路径
        script_dir = Path(__file__).parent.absolute()
        
        # 如果没有提供base_dir，则使用脚本目录下的test_business_kb目录
        if base_dir is None:
            self.base_dir = script_dir / "test_business_kb"
        else:
            # 如果提供的是相对路径，则相对于脚本目录
            base_path = Path(base_dir)
            if not base_path.is_absolute():
                self.base_dir = script_dir / base_path
            else:
                self.base_dir = base_path
        
        # 创建测试文档目录
        self.test_docs_dir = script_dir / "test_docs"
        self.test_docs_dir.mkdir(exist_ok=True)
        
        # 初始化知识库管理器
        print(f"正在初始化业务知识库管理器，基础目录: {self.base_dir}")
        if auto_sync:
            print("启用自动同步，正在校验知识库一致性...")
        
        # 修改这里，不传递base_dir参数
        self.kb_manager = BusinessKnowledgeBaseManager(
            milvus_uri=milvus_uri,
            auto_sync=False  # 不在初始化时自动同步
        )
        
        # 如果需要同步，手动触发同步
        if auto_sync:
            # 使用异步方法进行同步
            asyncio.create_task(self._sync_knowledge_base())
        
        print("业务知识库管理器初始化完成")

    async def _sync_knowledge_base(self):
        """同步知识库，确保索引已经建立"""
        print("正在同步知识库...")
        # 获取所有业务ID
        business_ids = list(self.kb_manager.kb_metadata["businesses"].keys())
        
        # 逐个同步业务
        success_count = 0
        for business_id in business_ids:
            try:
                # 使用公开的方法进行同步，而不是尝试调用内部方法
                # 检查业务是否存在
                if business_id in self.kb_manager.kb_metadata["businesses"]:
                    # 获取业务文档
                    documents = self.kb_manager.kb_metadata["businesses"][business_id].get("documents", {})
                    
                    # 如果有文档，尝试重新处理一个文档来触发索引更新
                    if documents:
                        # 获取第一个文档ID和路径
                        doc_id = list(documents.keys())[0]
                        doc_info = documents[doc_id]
                        file_path = doc_info.get("file_path")
                        
                        if file_path and Path(file_path).exists():
                            # 重新添加文档，这会触发索引更新
                            await self.kb_manager.add_documents_to_kb(
                                business_id=business_id,
                                file_paths=[file_path]
                            )
                            
                success_count += 1
            except Exception as e:
                print(f"同步业务 '{business_id}' 失败: {str(e)}")
        
        print(f"同步完成，结果: {success_count}/{len(business_ids)} 个业务同步成功")
        return success_count == len(business_ids)
    
    async def run_basic_test(self, business_id: str = "test_business"):
        """
        运行基本测试流程
        
        Args:
            business_id: 测试业务ID
        """
        print("\n=== 运行基本测试流程 ===")
        
        # 确保测试业务不存在
        if business_id in self.kb_manager.kb_metadata["businesses"]:
            print(f"删除已存在的测试业务 '{business_id}'")
            self.kb_manager.delete_business_kb(business_id)
        
        # 1. 创建业务知识库
        print(f"\n1. 创建业务知识库 '{business_id}'")
        success = self.kb_manager.create_business_kb(
            business_id=business_id,
            name="测试业务",
            description="这是一个测试业务知识库"
        )
        print(f"创建结果: {'成功' if success else '失败'}")
        
        # 2. 添加文档
        print("\n2. 添加文档到业务知识库")
        test_docs = self._prepare_test_documents()
        
        if test_docs:
            doc_ids = await self.kb_manager.add_documents_to_kb(
                business_id=business_id,
                file_paths=test_docs
            )
            print(f"添加了 {len(doc_ids)} 个文档，文档ID: {doc_ids}")
        else:
            print("没有可用的测试文档")
            return
        
        # 3. 查询测试
        print("\n3. 查询业务知识库")
        query = "业务知识库的主要功能是什么?"
        result = self.kb_manager.query_business_kb(
            business_id=business_id,
            query=query
        )
        
        print(f"查询: {query}")
        print(f"回答: {result['response']}")
        print("\n相关文本片段:")
        for i, node in enumerate(result["source_nodes"]):
            print(f"片段 {i+1} (相关度: {node.get('score', 0):.4f}):")
            print(f"文档: {node.get('file_name', 'unknown')}")
            print(f"内容: {node.get('text', '')[:200]}...\n")
        
        # 4. 删除文档测试
        if doc_ids:
            print("\n4. 删除文档")
            doc_id_to_delete = doc_ids[0]
            success = self.kb_manager.remove_document_from_kb(
                business_id=business_id,
                doc_id=doc_id_to_delete
            )
            print(f"删除文档 '{doc_id_to_delete}' 结果: {'成功' if success else '失败'}")
        
        # 5. 获取业务信息
        print("\n5. 获取业务信息")
        business_info = self.kb_manager.get_business_info(business_id)
        print(f"业务名称: {business_info.get('name', '')}")
        print(f"业务描述: {business_info.get('description', '')}")
        print(f"文档数量: {business_info.get('document_count', 0)}")
        print(f"文档列表:")
        for doc in business_info.get("documents", []):
            print(f"  - {doc.get('file_name', '')} (ID: {doc.get('doc_id', '')})")
        
        # 6. 删除业务知识库
        print("\n6. 删除业务知识库")
        success = self.kb_manager.delete_business_kb(business_id)
        print(f"删除业务知识库 '{business_id}' 结果: {'成功' if success else '失败'}")
    
    async def run_sync_test(self, business_id: str = "sync_test_business"):
        """
        运行同步机制测试
        
        Args:
            business_id: 测试业务ID
        """
        print("\n=== 运行同步机制测试 ===")
        
        # 1. 创建业务知识库
        print(f"\n1. 创建业务知识库 '{business_id}'")
        success = self.kb_manager.create_business_kb(
            business_id=business_id,
            name="同步测试业务",
            description="用于测试同步机制的业务知识库",
        )
        print(f"创建结果: {'成功' if success else '失败'}")
        
        # 2. 添加文档
        print("\n2. 添加文档到业务知识库")
        test_docs = self._prepare_test_documents()
        
        if not test_docs:
            print("没有可用的测试文档")
            return
        
        doc_ids = await self.kb_manager.add_documents_to_kb(
            business_id=business_id,
            file_paths=test_docs
        )
        print(f"添加了 {len(doc_ids)} 个文档，文档ID: {doc_ids}")
        
        if not doc_ids:
            print("添加文档失败，无法继续测试")
            return
        
        # 3. 测试文件缺失情况
        print("\n3. 测试文件缺失情况")
        # 获取第一个文档的路径
        business_info = self.kb_manager.get_business_info(business_id)
        doc_id = doc_ids[0]
        doc_info = None
        for doc in business_info.get("documents", []):
            if doc.get("doc_id") == doc_id:
                doc_info = doc
                break
        
        if not doc_info:
            print(f"找不到文档 '{doc_id}' 的信息，无法继续测试")
            return
        
        # 获取文档路径
        doc_path = Path(self.kb_manager.kb_metadata["businesses"][business_id]["documents"][doc_id]["kb_path"])
        print(f"文档路径: {doc_path}")
        
        # 备份文件
        backup_path = None
        if doc_path.exists():
            backup_path = self.test_docs_dir / f"backup_{doc_path.name}"
            shutil.copy2(doc_path, backup_path)
            print(f"已备份文件: {backup_path}")
            
            # 删除文件
            doc_path.unlink()
            print(f"已删除文件: {doc_path}")
        
        # 创建新的知识库管理器实例，触发自动同步
        print("\n创建新的知识库管理器实例，触发自动同步...")
        new_kb_manager = BusinessKnowledgeBaseManager(
            base_dir=self.base_dir,
            milvus_uri=self.kb_manager.milvus_uri,
            auto_sync=True
        )
        
        # 检查文档状态
        print("\n检查文档状态...")
        if business_id in new_kb_manager.kb_metadata["businesses"]:
            if doc_id in new_kb_manager.kb_metadata["businesses"][business_id]["documents"]:
                doc_status = new_kb_manager.kb_metadata["businesses"][business_id]["documents"][doc_id].get("status")
                print(f"文档 '{doc_id}' 的状态: {doc_status}")
                if doc_status == "deleted":
                    print("✓ 同步机制正确标记了缺失文件")
                else:
                    print("✗ 同步机制未正确标记缺失文件")
            else:
                print(f"✗ 文档 '{doc_id}' 已从元数据中删除")
        else:
            print(f"✗ 业务 '{business_id}' 不存在于元数据中")
        
        # 恢复文件
        if backup_path and backup_path.exists():
            shutil.copy2(backup_path, doc_path)
            print(f"\n已恢复文件: {doc_path}")
        
        # 4. 测试文件内容修改
        print("\n4. 测试文件内容修改")
        # 获取第二个文档的路径
        if len(doc_ids) > 1:
            doc_id = doc_ids[1]
            doc_path = Path(self.kb_manager.kb_metadata["businesses"][business_id]["documents"][doc_id]["kb_path"])
            
            if doc_path.exists():
                # 备份文件
                backup_path = self.test_docs_dir / f"backup_{doc_path.name}"
                shutil.copy2(doc_path, backup_path)
                print(f"已备份文件: {backup_path}")
                
                # 修改文件内容
                with open(doc_path, "a", encoding="utf-8") as f:
                    f.write("\n\n这是一段新添加的内容，用于测试文件内容修改检测。\n")
                print(f"已修改文件内容: {doc_path}")
                
                # 创建新的知识库管理器实例，触发自动同步
                print("\n创建新的知识库管理器实例，触发自动同步...")
                new_kb_manager = BusinessKnowledgeBaseManager(
                    base_dir=self.base_dir,
                    milvus_uri=self.kb_manager.milvus_uri,
                    auto_sync=True
                )
                
                # 检查文档指纹
                print("\n检查文档指纹...")
                if business_id in new_kb_manager.kb_metadata["businesses"]:
                    if doc_id in new_kb_manager.kb_metadata["businesses"][business_id]["documents"]:
                        needs_reprocessing = new_kb_manager.kb_metadata["businesses"][business_id]["documents"][doc_id].get("needs_reprocessing", False)
                        print(f"文档 '{doc_id}' 是否需要重新处理: {needs_reprocessing}")
                        if needs_reprocessing:
                            print("✓ 同步机制正确检测到文件内容变更")
                        else:
                            print("✗ 同步机制未检测到文件内容变更")
                    else:
                        print(f"✗ 文档 '{doc_id}' 不存在于元数据中")
                else:
                    print(f"✗ 业务 '{business_id}' 不存在于元数据中")
                
                # 恢复文件
                if backup_path and backup_path.exists():
                    shutil.copy2(backup_path, doc_path)
                    print(f"\n已恢复文件: {doc_path}")
        else:
            print("没有足够的文档进行测试")
        
        # 5. 删除业务知识库
        print("\n5. 删除业务知识库")
        success = self.kb_manager.delete_business_kb(business_id)
        print(f"删除业务知识库 '{business_id}' 结果: {'成功' if success else '失败'}")
    
    async def run_performance_test(self, business_id: str = "perf_test_business", doc_count: int = 10):
        """
        运行性能测试
        
        Args:
            business_id: 测试业务ID
            doc_count: 测试文档数量
        """
        print(f"\n=== 运行性能测试 (文档数量: {doc_count}) ===")
        
        # 1. 创建业务知识库
        print(f"\n1. 创建业务知识库 '{business_id}'")
        start_time = time.time()
        success = self.kb_manager.create_business_kb(
            business_id=business_id,
            name="性能测试业务",
            description="用于性能测试的业务知识库",
        )
        create_time = time.time() - start_time
        print(f"创建结果: {'成功' if success else '失败'}, 耗时: {create_time:.2f}秒")
        
        # 2. 生成测试文档
        print(f"\n2. 生成{doc_count}个测试文档")
        test_docs = []
        for i in range(doc_count):
            doc_path = self.test_docs_dir / f"perf_test_doc_{i}.txt"
            with open(doc_path, "w", encoding="utf-8") as f:
                # 生成约1KB的文本
                f.write(f"这是性能测试文档 {i}\n\n")
                for j in range(50):
                    f.write(f"这是第{j}段测试内容，用于测试业务知识库的性能。业务知识库需要能够高效处理大量文档。\n")
            test_docs.append(str(doc_path))
        
        print(f"已生成 {len(test_docs)} 个测试文档")
        
        # 3. 添加文档性能测试
        print("\n3. 添加文档性能测试")
        start_time = time.time()
        doc_ids = await self.kb_manager.add_documents_to_kb(
            business_id=business_id,
            file_paths=test_docs
        )
        add_time = time.time() - start_time
        print(f"添加了 {len(doc_ids)} 个文档，耗时: {add_time:.2f}秒，平均每个文档 {add_time/len(doc_ids):.2f}秒")
        
        # 4. 查询性能测试
        print("\n4. 查询性能测试")
        queries = [
            "业务知识库的主要功能是什么?",
            "如何高效处理大量文档?",
            "测试文档包含哪些内容?"
        ]
        
        total_query_time = 0
        for query in queries:
            start_time = time.time()
            result = self.kb_manager.query_business_kb(
                business_id=business_id,
                query=query
            )
            query_time = time.time() - start_time
            total_query_time += query_time
            print(f"查询: '{query}'，耗时: {query_time:.2f}秒")
        
        print(f"平均查询时间: {total_query_time/len(queries):.2f}秒")
        
        # 5. 同步性能测试
        print("\n5. 同步性能测试")
        start_time = time.time()
        new_kb_manager = BusinessKnowledgeBaseManager(
            base_dir=self.base_dir,
            milvus_uri=self.kb_manager.milvus_uri,
            auto_sync=True
        )
        sync_time = time.time() - start_time
        print(f"同步 {doc_count} 个文档耗时: {sync_time:.2f}秒")
        
        # 6. 删除业务知识库
        print("\n6. 删除业务知识库")
        start_time = time.time()
        success = self.kb_manager.delete_business_kb(business_id)
        delete_time = time.time() - start_time
        print(f"删除业务知识库耗时: {delete_time:.2f}秒")
        
        # 7. 清理测试文档
        print("\n7. 清理测试文档")
        for doc_path in test_docs:
            try:
                Path(doc_path).unlink()
            except Exception:
                pass
        print(f"已清理 {len(test_docs)} 个测试文档")
    
    def _prepare_test_documents(self) -> List[str]:
        """准备测试文档"""
        # 检查测试文档目录中的文档
        test_docs = []
        for ext in ['.pdf', '.docx', '.txt']:
            for doc_path in self.test_docs_dir.glob(f"*{ext}"):
                test_docs.append(str(doc_path))
        
        # 如果没有找到测试文档，创建一个简单的测试文档
        if not test_docs:
            print("未找到测试文档，创建简单的测试文档...")
            
            # 创建多个测试文档
            for i in range(3):
                test_doc = self.test_docs_dir / f"test_sample_{i}.txt"
                with open(test_doc, "w", encoding="utf-8") as f:
                    f.write(f"这是测试文档 {i}，用于测试业务知识库功能。\n")
                    f.write("业务知识库可以按业务分类管理文档，支持添加、删除和查询功能。\n")
                    f.write("每个业务知识库都是基于LlamaIndex和向量数据库实现的。\n")
                    f.write(f"这个文档包含一些特定于文档 {i} 的内容，用于区分不同文档。\n")
                
                test_docs.append(str(test_doc))
            
            print(f"已创建 {len(test_docs)} 个测试文档")
        
        return test_docs

    async def run_cross_business_test(self, base_business_id: str = "cross_test_business"):
        """
        运行跨业务查询测试 - 简化版
        
        Args:
            base_business_id: 基础业务ID前缀
        """
        print("\n=== 运行跨业务查询测试（简化版）===")
        
        # 设置更高的日志级别，减少输出
        import logging
        logging.getLogger("BusinessKB").setLevel(logging.WARNING)
        logging.getLogger("business_relation_manager").setLevel(logging.WARNING)
        
        # 初始化业务ID列表
        business_ids = []
        
        try:
            # 1. 创建测试业务
            print("\n1. 创建测试业务...")
            business_names = ["智能底盘", "自动驾驶", "车载信息娱乐"]
            
            for i, name in enumerate(business_names, 1):
                business_id = f"{base_business_id}_{i}"
                business_ids.append(business_id)
                
                # 确保测试业务不存在
                if business_id in self.kb_manager.kb_metadata["businesses"]:
                    self.kb_manager.delete_business_kb(business_id)
                
                success = self.kb_manager.create_business_kb(
                    business_id=business_id,
                    name=name,
                    description=f"测试业务: {name}"
                )
                
                if not success:
                    raise ValueError(f"创建业务 '{business_id}' 失败")
            
            print(f"✓ 创建了 {len(business_ids)} 个测试业务")
            
            # 2. 为每个业务添加测试文档
            print("\n2. 添加测试文档...")
            test_content = {
                0: [  # 业务1: 智能底盘
                    "智能底盘系统包括主动悬挂、电子稳定控制和自适应转向系统。",
                    "底盘控制单元(CCU)负责协调各个子系统的工作。"
                ],
                1: [  # 业务2: 自动驾驶
                    "自动驾驶系统依赖于多种传感器融合技术，包括摄像头、雷达和激光雷达。",
                    "感知、决策和规划是自动驾驶的三个核心模块。"
                ],
                2: [  # 业务3: 车载信息娱乐
                    "车载信息娱乐系统提供导航、多媒体和通信功能。",
                    "车载操作系统需要满足实时性、安全性和可靠性要求。"
                ]
            }
            
            for i, business_id in enumerate(business_ids):
                # 每个业务只创建一个文档
                doc_path = self.test_docs_dir / f"{business_id}_doc.txt"
                with open(doc_path, "w", encoding="utf-8") as f:
                    f.write(f"# {business_names[i]}业务测试文档\n\n")
                    f.write("所有业务都共享的智能汽车技术包括自动驾驶、车联网和电动化技术。\n\n")
                    
                    # 添加业务特定内容
                    for line in test_content[i]:
                        f.write(f"{line}\n")
            
                # 添加文档到业务
                doc_ids = await self.kb_manager.add_documents_to_kb(
                    business_id=business_id,
                    file_paths=[str(doc_path)]
                )
            
                if not doc_ids:
                    raise ValueError(f"向业务 '{business_id}' 添加文档失败")
            
            print(f"✓ 为每个业务添加了测试文档")
            
            # 3. 建立业务关联关系
            print("\n3. 建立业务关联关系...")
            
            # 确保索引已经建立完成
            print("确保索引已经建立完成...")
            await self._sync_knowledge_base()
            
            # 添加延迟，确保索引已完全建立
            print("等待索引建立完成...")
            await asyncio.sleep(10)
            
            # 建立业务1和业务2的关联
            success = self.kb_manager.relation_manager.add_relation(
                business_a=business_ids[0],
                business_b=business_ids[1],
                relation_type="related",
                weight=0.7  # 进一步降低权重值
            )
            
            if not success:
                print(f"警告: 建立业务 '{business_ids[0]}' 和 '{business_ids[1]}' 的关联失败，但继续测试")
            
            # 建立业务1和业务3的关联
            success = self.kb_manager.relation_manager.add_relation(
                business_a=business_ids[0],
                business_b=business_ids[2],
                relation_type="related",
                weight=0.7  # 进一步降低权重值
            )
            
            if not success:
                print(f"警告: 建立业务 '{business_ids[0]}' 和 '{business_ids[2]}' 的关联失败，但继续测试")
            
            # 简化关联关系输出
            for i, business_id in enumerate(business_ids):
                related = self.kb_manager.relation_manager.get_related_businesses(business_id)
                print(f"✓ {business_names[i]}业务关联: {', '.join(related) if related else '无'}")
            
            # 4. 测试跨业务查询
            print("\n4. 测试跨业务查询...")
            
            # 测试查询
            test_queries = [
                "智能底盘的主要功能是什么?",  # 业务1相关
                "自动驾驶系统如何处理传感器数据?",  # 业务2相关
                "车载信息娱乐系统有哪些功能?"  # 业务3相关
            ]
            
            # 主业务ID (业务1)
            main_business_id = business_ids[0]
            
            for i, query in enumerate(test_queries):
                print(f"\n查询 {i+1}: {query}")
                
                try:
                    # 普通查询
                    result = await self.kb_manager.query_business_kb(
                        business_id=main_business_id,
                        query=query
                    )
                    print(f"• 普通查询: {result['response'][:150]}...")
                    
                    # 跨业务查询
                    result = await self.kb_manager.query_with_cross_business(
                        business_id=main_business_id,
                        query=query,
                        expand_to_related=True,
                        max_related_businesses=2,
                        response_mode="compact"
                    )
                    print(f"• 跨业务查询: {result['response'][:150]}...")
                    
                    # 检查是否找到了额外的相关信息
                    if "related_businesses" in result and result["related_businesses"]:
                        print(f"  (找到相关业务: {', '.join(result['related_businesses'])})")
                except Exception as e:
                    print(f"查询 '{query}' 失败: {str(e)}")
        
        except Exception as e:
            print(f"测试过程中发生错误: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            # 5. 清理测试业务
            print("\n5. 清理测试业务...")
            for business_id in business_ids:
                try:
                    self.kb_manager.delete_business_kb(business_id)
                except Exception as e:
                    print(f"警告: 删除业务 '{business_id}' 失败: {str(e)}")
            
            # 恢复日志级别
            logging.getLogger("BusinessKB").setLevel(logging.INFO)
            logging.getLogger("business_relation_manager").setLevel(logging.INFO)
            
            print("\n✓ 测试完成")

async def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="业务知识库测试工具")
    parser.add_argument("--base-dir", type=str, help="知识库基础目录")
    parser.add_argument("--milvus-uri", type=str, default="http://localhost:19530", help="Milvus服务URI")
    parser.add_argument("--no-sync", action="store_true", help="禁用自动同步")
    parser.add_argument("--test", choices=["basic", "sync", "performance", "cross", "all"], default="basic", help="测试类型")
    parser.add_argument("--doc-count", type=int, default=10, help="性能测试文档数量")
    args = parser.parse_args()
    
    # 创建测试工具
    tester = BusinessKBTester(
        base_dir=args.base_dir,
        milvus_uri=args.milvus_uri,
        auto_sync=not args.no_sync
    )
    
    # 根据测试类型运行测试
    if args.test == "basic" or args.test == "all":
        await tester.run_basic_test()
    
    if args.test == "sync" or args.test == "all":
        await tester.run_sync_test()
    
    if args.test == "performance" or args.test == "all":
        await tester.run_performance_test(doc_count=args.doc_count)
    
    if args.test == "cross" or args.test == "all":
        await tester.run_cross_business_test()
    
    print("\n所有测试完成")

if __name__ == "__main__":
    # 导入可能需要的额外模块
    import shutil
    
    # 运行主函数
    asyncio.run(main())

























