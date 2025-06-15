"""
重构后业务知识库系统使用示例

本示例演示如何使用重构后的业务知识库系统，包括：
1. 创建和管理业务知识库
2. 添加和处理文档
3. 执行单业务查询
4. 执行跨业务混合搜索
5. 数据同步和维护
"""

import asyncio
import logging
from pathlib import Path

# 导入重构后的模块
from business_knowledge_base_manager import BusinessKnowledgeBaseManager

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def main():
    """
    主函数，演示系统的完整使用流程
    """
    logger.info("开始演示重构后的业务知识库系统")
    
    # 1. 创建业务知识库管理器
    logger.info("1. 创建业务知识库管理器")
    manager = BusinessKnowledgeBaseManager(
        embedding_model_name="BAAI/bge-small-zh-v1.5",
        milvus_uri="tcp://localhost:19530",
        auto_sync=False
    )
    
    # 2. 创建业务知识库
    logger.info("2. 创建业务知识库")
    
    # 创建智能底盘业务知识库
    success = manager.create_business_kb(
        business_id="intelligent_chassis",
        name="智能底盘",
        description="智能底盘相关技术文档和资料"
    )
    logger.info(f"创建智能底盘知识库: {'成功' if success else '失败'}")
    
    # 创建自动驾驶业务知识库
    success = manager.create_business_kb(
        business_id="autonomous_driving",
        name="自动驾驶",
        description="自动驾驶技术相关文档和资料"
    )
    logger.info(f"创建自动驾驶知识库: {'成功' if success else '失败'}")
    
    # 创建传感器技术业务知识库
    success = manager.create_business_kb(
        business_id="sensor_technology",
        name="传感器技术",
        description="传感器技术相关文档和资料"
    )
    logger.info(f"创建传感器技术知识库: {'成功' if success else '失败'}")
    
    # 3. 列出所有业务知识库
    logger.info("3. 列出所有业务知识库")
    businesses = manager.list_businesses()
    for business in businesses:
        logger.info(f"业务: {business['name']} (ID: {business['business_id']}) - 文档数: {business['document_count']}")
    
    # 4. 添加文档到知识库（模拟）
    logger.info("4. 添加文档到知识库")
    
    # 注意：这里使用模拟文档，实际使用时需要提供真实的文档路径
    sample_documents = create_sample_documents()
    
    # 添加文档到智能底盘知识库
    try:
        doc_ids = await manager.add_documents_to_kb(
            business_id="intelligent_chassis",
            file_paths=sample_documents["intelligent_chassis"]
        )
        logger.info(f"智能底盘知识库添加了 {len(doc_ids)} 个文档")
    except Exception as e:
        logger.error(f"添加文档到智能底盘知识库失败: {str(e)}")

    # 添加文档到自动驾驶知识库
    try:
        doc_ids = await manager.add_documents_to_kb(
            business_id="autonomous_driving",
            file_paths=sample_documents["autonomous_driving"]
        )
        logger.info(f"自动驾驶知识库添加了 {len(doc_ids)} 个文档")
    except Exception as e:
        logger.error(f"添加文档到自动驾驶知识库失败: {str(e)}")
    
    # 5. 查看业务知识库信息
    logger.info("5. 查看业务知识库信息")
    for business_id in ["intelligent_chassis", "autonomous_driving", "sensor_technology"]:
        info = manager.get_business_info(business_id)
        if "error" not in info:
            logger.info(f"{info['name']}: {info['document_count']} 个文档")
            for doc in info.get('documents', [])[:3]:  # 只显示前3个文档
                logger.info(f"  - {doc['file_name']} (实体: {len(doc.get('entities', []))} 个)")
    
    # 6. 执行单业务查询
    logger.info("6. 执行单业务查询")
    
    query = "智能底盘的核心技术"
    try:
        result = await manager.query_business_kb(
            business_id="intelligent_chassis",
            query=query,
            similarity_top_k=3,
            response_mode="compact"
        )
        logger.info(f"查询结果: {result['response'][:200]}...")
        logger.info(f"找到 {len(result['source_nodes'])} 个相关文档片段")
    except Exception as e:
        logger.error(f"单业务查询失败: {str(e)}")
    
    # 7. 执行跨业务混合搜索
    logger.info("7. 执行跨业务混合搜索")
    
    query = "传感器在智能驾驶中的应用"
    try:
        result = await manager.query_with_cross_business(
            primary_business_id="intelligent_chassis",
            query=query,
            expand_to_related=True,
            max_related_businesses=2,
            response_mode="compact"
        )
        logger.info(f"跨业务查询结果: {result['response'][:200]}...")
        logger.info(f"找到 {len(result['source_nodes'])} 个相关文档片段")
        
        # 显示相关业务信息
        if "related_businesses" in result:
            logger.info(f"涉及 {len(result['related_businesses'])} 个相关业务")
    except Exception as e:
        logger.error(f"跨业务查询失败: {str(e)}")
    
    # 8. 数据同步检查
    logger.info("8. 数据同步检查")
    
    try:
        sync_result = await manager.sync_all_businesses()
        logger.info(f"同步结果: {sync_result['synced_businesses']}/{sync_result['total_businesses']} 个业务同步成功")
        
        for business_id, result in sync_result['businesses'].items():
            logger.info(f"  {business_id}: {result['status']} - {result.get('message', '')}")
    except Exception as e:
        logger.error(f"数据同步失败: {str(e)}")
    
    # 9. 演示关联关系功能
    logger.info("9. 演示关联关系功能")
    
    try:
        # 获取智能底盘的相关业务
        related_businesses = manager.relation_manager.get_related_businesses("intelligent_chassis")
        logger.info(f"智能底盘的相关业务: {related_businesses}")
        
        # 获取业务实体
        entities = manager.relation_manager.get_business_entities("intelligent_chassis")
        logger.info(f"智能底盘的实体: {entities[:10]}...")  # 只显示前10个
        
    except Exception as e:
        logger.error(f"关联关系演示失败: {str(e)}")
    
    logger.info("演示完成")


def create_sample_documents():
    """
    创建示例文档（模拟）

    Returns:
        示例文档路径字典
    """
    # 获取knowledge_base目录下的sample_docs路径
    current_dir = Path(__file__).parent
    sample_docs_dir = current_dir / "sample_docs"

    # 注意：这些是模拟的文档路径，实际使用时需要提供真实的文档
    return {
        "intelligent_chassis": [
            str(sample_docs_dir / "intelligent_chassis_overview.pdf"),
            str(sample_docs_dir / "chassis_control_system.docx"),
            str(sample_docs_dir / "suspension_technology.txt")
        ],
        "autonomous_driving": [
            str(sample_docs_dir / "autonomous_driving_basics.pdf"),
            str(sample_docs_dir / "perception_algorithms.docx"),
            str(sample_docs_dir / "path_planning.txt")
        ],
        "sensor_technology": [
            str(sample_docs_dir / "lidar_technology.pdf"),
            str(sample_docs_dir / "camera_sensors.docx"),
            str(sample_docs_dir / "radar_systems.txt")
        ]
    }


def create_sample_text_documents():
    """
    创建示例文本文档用于测试
    """
    # 创建示例文档目录在knowledge_base目录下
    current_dir = Path(__file__).parent
    sample_dir = current_dir / "sample_docs"
    sample_dir.mkdir(exist_ok=True)
    
    # 智能底盘相关文档
    chassis_content = """
    智能底盘技术概述
    
    智能底盘是现代汽车的重要组成部分，集成了多种先进技术：
    1. 主动悬挂系统 - 提供更好的乘坐舒适性和操控性
    2. 电子稳定控制系统 - 确保车辆在各种路况下的稳定性
    3. 自适应阻尼控制 - 根据路况自动调节悬挂阻尼
    4. 线控转向系统 - 提供精确的转向控制
    5. 制动能量回收系统 - 提高能源利用效率
    
    关键技术包括传感器融合、实时控制算法、机械电子一体化设计等。
    """
    
    # 自动驾驶相关文档
    autonomous_content = """
    自动驾驶技术基础
    
    自动驾驶技术是未来交通的发展方向，主要包括：
    1. 环境感知 - 使用激光雷达、摄像头、毫米波雷达等传感器
    2. 决策规划 - 基于感知信息进行路径规划和行为决策
    3. 控制执行 - 将决策转化为具体的车辆控制指令
    4. 高精度地图 - 提供厘米级的道路信息
    5. 车联网通信 - 实现车与车、车与基础设施的通信
    
    技术挑战包括复杂场景理解、安全性保障、法规标准等。
    """
    
    # 传感器技术相关文档
    sensor_content = """
    传感器技术在智能驾驶中的应用
    
    传感器是智能驾驶系统的眼睛和耳朵：
    1. 激光雷达 - 提供高精度的3D环境信息
    2. 摄像头 - 识别交通标志、车道线、行人等
    3. 毫米波雷达 - 在恶劣天气下仍能正常工作
    4. 超声波传感器 - 用于近距离障碍物检测
    5. IMU惯性测量单元 - 提供车辆运动状态信息
    
    传感器融合技术将多种传感器数据结合，提高感知的准确性和可靠性。
    """
    
    # 写入文件
    documents = {
        "intelligent_chassis_overview.txt": chassis_content,
        "autonomous_driving_basics.txt": autonomous_content,
        "sensor_technology.txt": sensor_content
    }
    
    for filename, content in documents.items():
        file_path = sample_dir / filename
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    logger.info(f"创建了 {len(documents)} 个示例文档")
    
    return {
        "intelligent_chassis": [str(sample_dir / "intelligent_chassis_overview.txt")],
        "autonomous_driving": [str(sample_dir / "autonomous_driving_basics.txt")],
        "sensor_technology": [str(sample_dir / "sensor_technology.txt")]
    }


async def demo_with_real_documents():
    """
    使用真实文档的演示（需要先创建示例文档）
    """
    logger.info("创建示例文档并演示系统功能")
    
    # 创建示例文档
    sample_docs = create_sample_text_documents()
    
    # 创建管理器
    manager = BusinessKnowledgeBaseManager()
    
    # 创建业务知识库
    for business_id, name in [
        ("intelligent_chassis", "智能底盘"),
        ("autonomous_driving", "自动驾驶"),
        ("sensor_technology", "传感器技术")
    ]:
        manager.create_business_kb(business_id, name)
    
    # 添加文档
    for business_id, file_paths in sample_docs.items():
        try:
            doc_ids = await manager.add_documents_to_kb(business_id, file_paths)
            logger.info(f"{business_id}: 添加了 {len(doc_ids)} 个文档")
        except Exception as e:
            logger.error(f"添加文档失败: {str(e)}")
    
    # 执行查询
    query = "传感器技术"
    try:
        result = await manager.query_with_cross_business(
            "sensor_technology", query, expand_to_related=True
        )
        logger.info(f"查询结果: {result['response'][:300]}...")
    except Exception as e:
        logger.error(f"查询失败: {str(e)}")


if __name__ == "__main__":
    # 运行演示
    try:
        # 运行带真实文档的演示
        asyncio.run(demo_with_real_documents())
    except KeyboardInterrupt:
        logger.info("演示被用户中断")
    except Exception as e:
        logger.error(f"演示过程中出错: {str(e)}")
        import traceback
        traceback.print_exc()
