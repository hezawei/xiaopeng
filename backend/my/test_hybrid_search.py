from pymilvus import MilvusClient
import numpy as np
import time

# 连接到Milvus服务
client = MilvusClient(uri="http://localhost:19530")
print(f"已连接到Milvus服务: http://localhost:19530")

# 创建测试集合
collection_name = f"hybrid_test_{int(time.time())}"
print(f"创建测试集合: {collection_name}")

# 创建集合
client.create_collection(
    collection_name=collection_name,
    dimension=128,
    metric_type="L2"
)

# 插入数据
print("\n插入测试数据...")
vectors = np.random.random((10, 128)).tolist()
texts = [f"测试文本 {i}" for i in range(10)]
ids = [i for i in range(1, 11)]

entities = []
for i in range(10):
    entities.append({
        "id": ids[i],
        "vector": vectors[i],
        "text": texts[i]
    })

insert_result = client.insert(
    collection_name=collection_name,
    data=entities
)
print(f"插入结果: {insert_result}")

# 等待数据加载
time.sleep(2)

# 加载集合到内存
client.load_collection(collection_name=collection_name)

# 执行混合搜索测试
print("\n执行混合搜索测试...")
search_vector = np.random.random(128).tolist()
search_text = "测试"

try:
    # 尝试方法1: 使用向量和文本分开的方式
    hybrid_results = client.hybrid_search(
        collection_name=collection_name,
        reqs=[{
            "data": [search_vector],
            "field": "vector",
            "params": {"metric_type": "L2", "params": {"nprobe": 10}},
            "limit": 5
        }],
        ranker={"name": "BM25", "params": {"k": 10}},
        output_fields=["text"]
    )
    print("混合搜索结果 (方法1):", hybrid_results)
except Exception as e:
    print(f"混合搜索方法1失败: {str(e)}")
    
    try:
        # 尝试方法2: 使用简化的API
        hybrid_results = client.hybrid_search(
            collection_name=collection_name,
            vector_field="vector",
            vector_query=[search_vector],
            text_field="text",
            text_query=search_text,
            limit=5,
            output_fields=["text"]
        )
        print("混合搜索结果 (方法2):", hybrid_results)
    except Exception as e:
        print(f"混合搜索方法2失败: {str(e)}")
        print("注意: 您的Milvus版本可能不支持混合搜索，或者API格式已更改")
        print("请参考最新的Milvus文档: https://milvus.io/docs/hybrid_search.md")

# 清理资源
print(f"\n删除测试集合: {collection_name}")
client.drop_collection(collection_name)

print("\n测试完成!")