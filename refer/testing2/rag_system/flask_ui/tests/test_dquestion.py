from dquestion.openai import OpenAI_Chat
from dquestion.dquestiondb import DQuestionDB_VectorStore
from dquestion.mistral import Mistral
from dquestion.dquestion import DQuestionChat

import os

try:
    print("Trying to load .env")
    from dotenv import load_dotenv

    load_dotenv()
except Exception as e:
    print(f"Failed to load .env {e}")
    pass

MY_DQUESTION_MODEL = 'chinook'
MY_DQUESTION_API_KEY = os.environ['DQUESTION_API_KEY']
OPENAI_API_KEY = os.environ['OPENAI_API_KEY']
MISTRAL_API_KEY = os.environ['MISTRAL_API_KEY']


class DQuestionOpenAI(DQuestionDB_VectorStore, OpenAI_Chat):
    def __init__(self, config=None):
        DQuestionDB_VectorStore.__init__(self, model=MY_DQUESTION_MODEL, api_key=MY_DQUESTION_API_KEY, config=config)
        OpenAI_Chat.__init__(self, config=config)


dq_openai = DQuestionOpenAI(config={'api_key': OPENAI_API_KEY, 'model': 'gpt-3.5-turbo'})
dq_openai.connect_to_sqlite('https://danwenai.cn/Chinook.sqlite')


def test_dquestion_openai():
    sql = dq_openai.generate_sql("What are the top 4 customers by sales?")
    df = dq_openai.run_sql(sql)
    assert len(df) == 4


class DQuestionMistral(DQuestionDB_VectorStore, Mistral):
    def __init__(self, config=None):
        DQuestionDB_VectorStore.__init__(self, model=MY_DQUESTION_MODEL, api_key=MY_DQUESTION_API_KEY, config=config)
        Mistral.__init__(self, config={'api_key': MISTRAL_API_KEY, 'model': 'mistral-tiny'})


dq_mistral = DQuestionMistral()
dq_mistral.connect_to_sqlite('https://danwenai.cn/Chinook.sqlite')


def test_vn_mistral():
    sql = dq_mistral.generate_sql("What are the top 5 customers by sales?")
    df = dq_mistral.run_sql(sql)
    assert len(df) == 5


vn_default = DQuestionChat(model=MY_DQUESTION_MODEL, api_key=MY_DQUESTION_API_KEY)
vn_default.connect_to_sqlite('https://danwenai.cn/Chinook.sqlite')


def test_vn_default():
    sql = vn_default.generate_sql("What are the top 6 customers by sales?")
    df = vn_default.run_sql(sql)
    assert len(df) == 6


from dquestion.openai import OpenAI_Chat
from dquestion.chromadb.chromadb_vector import ChromaDB_VectorStore


class MyDQuestion(ChromaDB_VectorStore, OpenAI_Chat):
    def __init__(self, config=None):
        ChromaDB_VectorStore.__init__(self, config=config)
        OpenAI_Chat.__init__(self, config=config)


dq_chroma = MyDQuestion(config={'api_key': OPENAI_API_KEY, 'model': 'gpt-3.5-turbo'})
dq_chroma.connect_to_sqlite('https://danwenai.cn/Chinook.sqlite')


def test_dq_chroma():
    df_ddl = dq_chroma.run_sql("SELECT type, sql FROM sqlite_master WHERE sql is not null")

    for ddl in df_ddl['sql'].to_list():
        dq_chroma.train(ddl=ddl)

    sql = dq_chroma.generate_sql("What are the top 7 customers by sales?")
    df = dq_chroma.run_sql(sql)
    assert len(df) == 7
