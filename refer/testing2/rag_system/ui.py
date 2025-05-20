import random
from typing import Optional, List
import chainlit as cl
from chainlit.element import ElementBased
from chainlit.types import ThreadDict
from llama_index.core.base.llms.types import ChatMessage
from llama_index.core.chat_engine import SimpleChatEngine
from llama_index.core.chat_engine.types import ChatMode
from llama_index.core.memory import ChatMemoryBuffer
from rag.document import DocumentRAGV1, BaseRAG, DocumentRAGV2
import utils.utils_ui as ui_utils

# 初始化聊天记录存储持久层
from utils import settings
from persistent.minio_storage_client import MinioStorageClient
from rag_system.persistent.postgresql_data_layer import PostGreSQLDataLayer
# storage_client = MinioStorageClient()
# cl_data._data_layer = PostGreSQLDataLayer(conninfo=settings.configuration.pg_connection_string, storage_provider=storage_client)

async def view_pdf(elements: List[ElementBased]):
    """查看PDF文件"""
    files = []
    contents = []
    for element in elements:
        if element.name.endswith(".pdf"):
            pdf = cl.Pdf(name=element.name, display="side", path=element.path)
            files.append(pdf)
            contents.append(element.name)
    if len(files) == 0:
        return
    await cl.Message(content=f"查看PDF文件：" + "，".join(contents), elements=files).send()


@cl.on_chat_start
async def start():
    kb_name = cl.user_session.get("chat_profile")
    # 选择默认知识库，是与大模型直接对话
    if kb_name is None or kb_name == "default" or kb_name == "大模型对话" or kb_name == "数据库对话":
        memory = ChatMemoryBuffer.from_defaults(token_limit=1024)
        chat_engine = SimpleChatEngine.from_defaults(memory=memory)
    else:
        index = await DocumentRAGV1.load_remote_index(collection_name=kb_name)
        chat_engine = index.as_chat_engine(chat_mode=ChatMode.CONTEXT)

    cl.user_session.set("chat_engine", chat_engine)

@cl.set_chat_profiles
async def chat_profile(current_user: cl.User):
    from utils.milvus import list_collections
    # # 知识库信息最后存储在关系数据库中:名称，描述，图标
    kb_list = list_collections()
    profiles = [
        cl.ChatProfile(
            name="default",
            markdown_description=f"大模型对话",
            icon=f"/public/kbs/model.png",
        ),
        cl.ChatProfile(
            name="数据库对话",
            markdown_description=f"数据库对话",
            icon=f"/public/kbs/db.jpg",
        )
    ]
    for kb_name in kb_list:
        profiles.append(
            cl.ChatProfile(
                name=kb_name,
                markdown_description=f"{kb_name} 知识库",
                icon=f"/public/kbs/{random.randint(1, 3)}.jpg",
            )
        )
    return profiles

@cl.set_starters
async def set_starters():
    starters = [
        cl.Starter(
            label="大模型提高软件测试效率",
            message="详细介绍如何借助大语言模型提高软件测试效率。",
            icon="/public/apidog.svg",
        ),
        cl.Starter(
            label="自动化测试思路",
            message="详细描述一下接口及UI自动化测试的基本思路。",
            icon="/public/pulumi.svg",
        ),
        cl.Starter(
            label="性能测试分析及瓶颈定位思路",
            message="详细描述一下软件性能测试分析及瓶颈定位的核心思路。",
            icon="/public/godot_engine.svg",
        )
    ]

    return starters

@cl.password_auth_callback
def auth_callback(username: str, password: str) -> Optional[cl.User]:
    # 可以对接第三方认证
    if (username, password) == ("admin", "admin"):
        return cl.User(identifier="admin",
                       metadata={"role": "admin", "provider": "credentials"})
    else:
        return None


@cl.on_chat_resume
async def on_chat_resume(thread: ThreadDict):
    chat_engine = SimpleChatEngine.from_defaults()
    for message in thread.get("steps", []):
        if message["type"] == "user_message":
            chat_engine.chat_history.append(ChatMessage(content=message["output"], role="user"))
        elif message["type"] == "assistant_message":
            chat_engine.chat_history.append(ChatMessage(content=message["output"], role="assistant"))
    cl.user_session.set("chat_engine", chat_engine)

@cl.on_message
async def main(message: cl.Message):
    msg = cl.Message(content="", author="Assistant")
    chat_mode = cl.user_session.get("chat_profile", "大模型对话")

    if chat_mode == "大模型对话" or chat_mode == "default":
        await view_pdf(message.elements)
        files = []
        # 获取用户上传的文件（包含图片）
        for element in message.elements:
            if isinstance(element, cl.File) or isinstance(element, cl.Image):
                files.append(element.path)

        if len(files) > 0:
            rag = DocumentRAGV2(files=files)
            index = await rag.create_local_index()
            chat_engine = index.as_chat_engine(chat_mode=ChatMode.CONTEXT, similarity_top_k=3)
            cl.user_session.set("chat_engine", chat_engine)
    elif chat_mode == "数据库对话":
        # await ui_utils.train()
        sql = await ui_utils.generate_sql(message.content)
        is_valid = await ui_utils.is_sql_valid(sql)
        if is_valid:
            df = await ui_utils.execute_query(sql)
            # 展示数据表格
            await cl.Message(content=df.to_markdown(index=False), author="Assistant").send()

            fig = await ui_utils.plot(human_query=message.content, sql=sql, df=df)
            elements = [cl.Plotly(name="chart", figure=fig, display="inline")]
            await cl.Message(content="生成的图表如下：", elements=elements, author="Assistant").send()
            return

    chat_engine = cl.user_session.get("chat_engine")
    res = await cl.make_async(chat_engine.stream_chat)(message.content)

    # 显示图片
    for source_node in res.source_nodes:
        if source_node.metadata.get("type") == "image":
            msg.elements.append(
                cl.Image(path=source_node.metadata["image"],
                         name=source_node.metadata["source"],
                         display="inline"))

    # 流式界面输出
    for token in res.response_gen:
        await msg.stream_token(token)


    # 如果当前对话是知识库对话，则显示数据来源
    if not isinstance(chat_engine, SimpleChatEngine):
        source_names = []
        for idx, node_with_score in enumerate(res.source_nodes):
            node = node_with_score.node
            source_name = f"source_{idx}"
            source_names.append(source_name)
            msg.elements.append(
                cl.Text(content=node.get_text(),
                        name=source_name,
                        display="side")
            )
        await msg.stream_token(f"\n\n **数据来源**: {', '.join(source_names)}")

    await msg.send()
