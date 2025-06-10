from pymilvus import MilvusClient
import numpy as np
import time

# 连接到Docker中运行的Milvus服务
client = MilvusClient(uri="http://10.193.200.230:19530")
print(f"已连接到Milvus服务: 10.193.200.230:19530")

# 列出所有集合
collections = client.list_collections()
print("现有集合:", collections)

# 创建一个测试集合
collection_name = f"test_collection_{int(time.time())}"  # 添加时间戳避免名称冲突
print(f"创建测试集合: {collection_name}")

# 创建集合
client.create_collection(
    collection_name=collection_name,
    dimension=128,
    metric_type="L2"
)

# 验证集合是否创建成功
collections = client.list_collections()
print("创建后的集合列表:", collections)
print(f"集合 '{collection_name}' 是否存在:", collection_name in collections)

# 插入向量数据
print("\n插入测试数据...")
# 生成随机向量
vectors = np.random.random((10, 128)).tolist()
# 生成随机文本
texts = [f"测试文本 {i}" for i in range(10)]
# 生成ID
ids = [i for i in range(1, 11)]

# 插入数据
entities = []
for i in range(10):
    entities.append({
        "id": ids[i],
        "vector": vectors[i],
        "text": texts[i]
    })

# 插入数据
insert_result = client.insert(
    collection_name=collection_name,
    data=entities
)
print(f"插入结果: {insert_result}")

# 等待数据加载完成
print("\n等待数据加载...")
time.sleep(2)  # 添加短暂延迟，确保数据被加载

# 创建索引以提高搜索性能
print("\n创建索引...")
try:
    # 检查集合是否已有索引
    has_index = False
    try:
        # 尝试获取索引信息
        index_info = client.describe_index(collection_name=collection_name)
        if index_info:
            has_index = True
            print(f"集合已有索引: {index_info}")
    except Exception:
        # 如果describe_index失败，假设没有索引
        pass
    
    # 如果没有索引，则创建
    if not has_index:
        index_params = client.prepare_index_params()
        index_params.add_index(
            field_name="vector",
            index_name="vector_index",
            index_type="IVF_FLAT",
            metric_type="L2",
            params={"nlist": 128}
        )
        client.create_index(
            collection_name=collection_name,
            index_params=index_params
        )
        print("索引创建成功")
    else:
        print("使用现有索引")
except Exception as e:
    if "creating multiple indexes on same field is not supported" in str(e):
        print("集合已有索引，继续执行...")
    else:
        print(f"创建索引时出现未预期的错误: {str(e)}")

# 加载集合到内存
print("\n加载集合到内存...")
client.load_collection(
    collection_name=collection_name
)

# 获取集合统计信息
stats = client.get_collection_stats(collection_name=collection_name)
print(f"\n集合统计信息: {stats}")

# 执行向量搜索
print("\n执行向量搜索...")
search_vector = np.random.random(128).tolist()
try:
    results = client.search(
        collection_name=collection_name,
        data=[search_vector],
        limit=5,
        output_fields=["text"]
    )
    
    print("\n搜索结果:")
    if results and len(results) > 0 and len(results[0]) > 0:
        for i, result in enumerate(results[0]):
            print(f"结果 {i+1}:")
            print(f"  ID: {result['id']}")
            print(f"  距离: {result['distance']}")
            print(f"  文本: {result['entity']['text']}")
    else:
        print("没有找到匹配的结果")
except Exception as e:
    print(f"搜索失败: {str(e)}")


# 清理资源
print(f"\n删除测试集合: {collection_name}")
client.drop_collection(collection_name)

# 验证集合是否删除成功
collections = client.list_collections()
print("删除后的集合列表:", collections)
print(f"集合 '{collection_name}' 是否已删除:", collection_name not in collections)

print("\n测试完成!")
