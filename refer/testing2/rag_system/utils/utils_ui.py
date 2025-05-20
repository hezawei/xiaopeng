import chainlit as cl
from dotenv import load_dotenv
from llama_index.core import Settings

load_dotenv()
from rag_system.persistent.minio_storage_client import MinioStorageClient
from rag_system.persistent.postgresql_data_layer import PostGreSQLDataLayer
from rag_system.utils import settings

from rag_system.rag.database import SQLiteDatabase, MySQLDatabase

Settings.llm = settings.deepseek_llm()
# 实现聊天数据持久化
# storage_client = MinioStorageClient()
# cl_data._data_layer = PostGreSQLDataLayer(conninfo=settings.configuration.pg_connection_string, storage_provider=storage_client)
# 创建数据RAG对象
# rag = SQLiteDatabase()
rag = MySQLDatabase()
async def is_sql_valid(sql):
    return rag.is_sql_valid(sql)
async def train():
    await rag.train_init_data()

@cl.step(language="sql", name="SQL生成助手", show_input="text")
async def generate_sql(human_query: str, **kwargs):
    current_step = cl.context.current_step
    current_step.input = human_query
    sql = rag.generate_sql(human_query, allow_llm_to_see_data=True, **kwargs)
    current_step.output = sql
    return sql


@cl.step(name="SQL执行助手", show_input="sql")
async def execute_query(sql):
    current_step = cl.context.current_step
    current_step.input = sql
    df = rag.run_sql(sql)
    current_step.output = df.to_markdown(index=False)
    return df

@cl.step(name="智能体分析助手", language="python")
async def plot(human_query, sql, df):
    current_step = cl.context.current_step
    plotly_code = rag.generate_plotly_code(question=human_query, sql=sql, df_metadata=df)
    fig = rag.get_plotly_figure(plotly_code=plotly_code, df=df)

    current_step.output = plotly_code
    return fig
