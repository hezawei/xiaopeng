import os

from pymilvus import MilvusClient
from . import settings
client = MilvusClient(uri=settings.configuration.milvus_uri)
def list_collections():
    return client.list_collections()
def drop_collection(collection_name):
    return client.drop_collection(collection_name=collection_name)
