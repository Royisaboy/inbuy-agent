import os.path
from llama_index.core import (
    VectorStoreIndex,
    SimpleDirectoryReader,
    StorageContext,
    load_index_from_storage,
)
import openai
import os
from pinecone import Pinecone, ServerlessSpec
from llama_index.vector_stores.pinecone import PineconeVectorStore


openai.api_key = os.getenv("OPENAI_API_KEY")
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
pc.create_index(
    name="inbuy",
    dimension=1536,
    metric="euclidean",
    spec=ServerlessSpec(cloud="aws", region="us-west-2"),
)
pinecone_index = pc.Index("quickstart")

documents = SimpleDirectoryReader("data/source").load_data()
vector_store = PineconeVectorStore(pinecone_index=pinecone_index)
storage_context = StorageContext.from_defaults(vector_store=vector_store)
index = VectorStoreIndex.from_documents(
    documents, storage_context=storage_context
)