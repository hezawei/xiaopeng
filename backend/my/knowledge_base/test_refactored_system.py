"""
重构后系统测试脚本

用于验证重构后的业务知识库系统是否正常工作，包括：
1. 模块导入测试
2. 基本功能测试
3. 接口兼容性测试
4. 错误处理测试
"""

import asyncio
import logging
import sys
import traceback
from pathlib import Path

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_imports():
    """
    测试模块导入
    """
    logger.info("测试模块导入...")
    
    try:
        # 测试核心模块导入
        from business_knowledge_base_manager import BusinessKnowledgeBaseManager
        from metadata_manager import MetadataManager
        from index_manager import IndexManager
        from document_processor_v2 import DocumentProcessor
        from relation_manager_v2 import RelationManager
        from entity_extractor import EntityExtractor
        from hybrid_search_engine import HybridSearchEngine
        from query_engine import QueryEngine
        from sync_manager import SyncManager
        from utils_v2 import setup_logging, load_json_file, save_json_file
        
        logger.info("✅ 所有模块导入成功")
        return True
        
    except ImportError as e:
        logger.error(f"❌ 模块导入失败: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"❌ 导入过程中出现异常: {str(e)}")
        return False


def test_basic_initialization():
    """
    测试基本初始化
    """
    logger.info("测试基本初始化...")
    
    try:
        from business_knowledge_base_manager import BusinessKnowledgeBaseManager
        
        # 创建管理器（使用测试目录）
        current_dir = Path(__file__).parent
        test_dir = current_dir / "test_knowledge_base"
        manager = BusinessKnowledgeBaseManager(
            embedding_model_name="BAAI/bge-small-zh-v1.5",
            milvus_uri="tcp://localhost:19530",
            base_dir=str(test_dir)
        )
        
        logger.info("✅ 管理器初始化成功")
        
        # 测试子模块是否正确初始化
        assert manager.metadata_manager is not None
        assert manager.index_manager is not None
        assert manager.document_processor is not None
        assert manager.relation_manager is not None
        assert manager.hybrid_search_engine is not None
        assert manager.query_engine is not None
        assert manager.sync_manager is not None
        
        logger.info("✅ 所有子模块初始化成功")
        return True, manager
        
    except Exception as e:
        logger.error(f"❌ 初始化失败: {str(e)}")
        traceback.print_exc()
        return False, None


def test_business_management(manager):
    """
    测试业务管理功能
    """
    logger.info("测试业务管理功能...")
    
    try:
        # 创建业务知识库
        success = manager.create_business_kb(
            business_id="test_business",
            name="测试业务",
            description="这是一个测试业务知识库"
        )
        
        if not success:
            logger.error("❌ 创建业务知识库失败")
            return False
        
        logger.info("✅ 业务知识库创建成功")
        
        # 列出业务
        businesses = manager.list_businesses()
        assert len(businesses) > 0
        assert any(b["business_id"] == "test_business" for b in businesses)
        
        logger.info("✅ 业务列表功能正常")
        
        # 获取业务信息
        info = manager.get_business_info("test_business")
        assert "error" not in info
        assert info["business_id"] == "test_business"
        assert info["name"] == "测试业务"
        
        logger.info("✅ 业务信息获取功能正常")
        return True
        
    except Exception as e:
        logger.error(f"❌ 业务管理测试失败: {str(e)}")
        traceback.print_exc()
        return False


def create_test_document():
    """
    创建测试文档
    """
    # 在knowledge_base目录下创建测试文档目录
    current_dir = Path(__file__).parent
    test_dir = current_dir / "test_docs"
    test_dir.mkdir(exist_ok=True)
    
    test_content = """
    测试文档内容
    
    这是一个用于测试的文档，包含以下内容：
    1. 智能底盘技术
    2. 传感器应用
    3. 自动驾驶系统
    4. 机器学习算法
    5. 数据处理方法
    
    关键技术包括：
    - 激光雷达
    - 摄像头
    - 毫米波雷达
    - 深度学习
    - 计算机视觉
    """
    
    test_file = test_dir / "test_document.txt"
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(test_content)
    
    return str(test_file)


async def test_document_processing(manager):
    """
    测试文档处理功能
    """
    logger.info("测试文档处理功能...")
    
    try:
        # 创建测试文档
        test_file = create_test_document()
        
        # 测试文档处理器
        document = await manager.document_processor.process_document(test_file)

        if document is None:
            logger.error("❌ 文档处理失败")
            return False

        assert document.text is not None
        assert len(document.text) > 0
        assert document.metadata["file_name"] == "test_document.txt"

        logger.info("✅ 文档处理功能正常")
        
        # 测试实体提取
        entities = manager.relation_manager.extract_entities_from_document(document)
        assert isinstance(entities, list)
        
        logger.info(f"✅ 实体提取功能正常，提取到 {len(entities)} 个实体")
        return True
        
    except Exception as e:
        logger.error(f"❌ 文档处理测试失败: {str(e)}")
        traceback.print_exc()
        return False


async def test_document_management(manager):
    """
    测试文档管理功能
    """
    logger.info("测试文档管理功能...")
    
    try:
        # 创建测试文档
        test_file = create_test_document()
        
        # 添加文档到知识库
        doc_ids = await manager.add_documents_to_kb(
            business_id="test_business",
            file_paths=[test_file]
        )
        
        if not doc_ids:
            logger.error("❌ 添加文档失败")
            return False
        
        logger.info(f"✅ 文档添加成功，文档ID: {doc_ids[0]}")
        
        # 检查业务信息是否更新
        info = manager.get_business_info("test_business")
        assert info["document_count"] > 0
        
        logger.info("✅ 文档管理功能正常")
        return True
        
    except Exception as e:
        logger.error(f"❌ 文档管理测试失败: {str(e)}")
        traceback.print_exc()
        return False


async def test_query_functionality(manager):
    """
    测试查询功能
    """
    logger.info("测试查询功能...")
    
    try:
        # 等待一段时间确保索引创建完成
        import time
        time.sleep(2)
        
        # 测试单业务查询
        result = await manager.query_business_kb(
            business_id="test_business",
            query="智能底盘技术",
            similarity_top_k=3
        )
        
        assert "response" in result
        assert "source_nodes" in result
        
        logger.info("✅ 单业务查询功能正常")
        
        # 测试跨业务查询
        cross_result = await manager.query_with_cross_business(
            primary_business_id="test_business",
            query="传感器技术",
            expand_to_related=True
        )
        
        assert "response" in cross_result
        assert "source_nodes" in cross_result
        
        logger.info("✅ 跨业务查询功能正常")
        return True
        
    except Exception as e:
        logger.error(f"❌ 查询功能测试失败: {str(e)}")
        traceback.print_exc()
        return False


async def test_sync_functionality(manager):
    """
    测试同步功能
    """
    logger.info("测试同步功能...")
    
    try:
        # 测试业务同步
        sync_result = await manager.sync_business_kb("test_business")
        
        assert "status" in sync_result
        
        logger.info(f"✅ 业务同步功能正常，状态: {sync_result['status']}")
        
        # 测试全量同步
        all_sync_result = await manager.sync_all_businesses()
        
        assert "total_businesses" in all_sync_result
        assert "synced_businesses" in all_sync_result
        
        logger.info("✅ 全量同步功能正常")
        return True
        
    except Exception as e:
        logger.error(f"❌ 同步功能测试失败: {str(e)}")
        traceback.print_exc()
        return False


def cleanup_test_data():
    """
    清理测试数据
    """
    logger.info("清理测试数据...")

    try:
        import shutil

        # 获取当前目录
        current_dir = Path(__file__).parent

        # 删除测试目录
        test_dirs = ["test_knowledge_base", "test_docs"]
        for test_dir_name in test_dirs:
            test_dir = current_dir / test_dir_name
            if test_dir.exists():
                shutil.rmtree(test_dir)

        logger.info("✅ 测试数据清理完成")

    except Exception as e:
        logger.error(f"❌ 清理测试数据失败: {str(e)}")


async def run_all_tests():
    """
    运行所有测试
    """
    logger.info("开始运行重构后系统测试")
    
    test_results = []
    manager = None
    
    try:
        # 1. 测试模块导入
        result = test_imports()
        test_results.append(("模块导入", result))
        
        if not result:
            logger.error("模块导入失败，停止后续测试")
            return
        
        # 2. 测试基本初始化
        result, manager = test_basic_initialization()
        test_results.append(("基本初始化", result))
        
        if not result or manager is None:
            logger.error("初始化失败，停止后续测试")
            return
        
        # 3. 测试业务管理
        result = test_business_management(manager)
        test_results.append(("业务管理", result))
        
        # 4. 测试文档处理
        result = await test_document_processing(manager)
        test_results.append(("文档处理", result))
        
        # 5. 测试文档管理
        result = await test_document_management(manager)
        test_results.append(("文档管理", result))
        
        # 6. 测试查询功能
        result = await test_query_functionality(manager)
        test_results.append(("查询功能", result))
        
        # 7. 测试同步功能
        result = await test_sync_functionality(manager)
        test_results.append(("同步功能", result))
        
    except Exception as e:
        logger.error(f"测试过程中出现异常: {str(e)}")
        traceback.print_exc()
    
    finally:
        # 清理测试数据
        cleanup_test_data()
    
    # 输出测试结果
    logger.info("\n" + "="*50)
    logger.info("测试结果汇总:")
    logger.info("="*50)
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        logger.info(f"{test_name}: {status}")
        if result:
            passed += 1
    
    logger.info("="*50)
    logger.info(f"总计: {passed}/{total} 个测试通过")
    
    if passed == total:
        logger.info("🎉 所有测试通过！重构后的系统工作正常。")
    else:
        logger.warning(f"⚠️ 有 {total - passed} 个测试失败，请检查相关功能。")


if __name__ == "__main__":
    try:
        asyncio.run(run_all_tests())
    except KeyboardInterrupt:
        logger.info("测试被用户中断")
    except Exception as e:
        logger.error(f"测试运行失败: {str(e)}")
        traceback.print_exc()
