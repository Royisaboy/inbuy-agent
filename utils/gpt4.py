from openai import OpenAI
import json
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from llama_index.llms.openai import OpenAI as llama_index_openai
from llama_index.core import Settings
from llama_index.vector_stores.pinecone import PineconeVectorStore
import os
from pinecone import Pinecone, ServerlessSpec
class chat:

    def __init__(self, key):
        self.client = OpenAI(api_key=key)
        Settings.llm = llama_index_openai(temperature=0.1, response_format={"type": "json_object"}, model="gpt-4-turbo")
        self.pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

    def get_response(self, text_prompt, urls=None):
        if urls is None:
            prompt = [{"role": "user", "content": text_prompt}]
        else:
            text_prompt = [{"type": "text", "text": text_prompt}]
            image_prompt = [{"type": "image_url", "image_url": {"url": url}} for url in urls]
            prompt = [{"role": "user", "content": text_prompt+image_prompt}]
        chat_response = self.client.chat.completions.create(
            model="gpt-4-turbo",
            response_format={"type": "json_object"},
            temperature=0.1,
            messages=prompt
        )
        latest_message = chat_response.choices[0].message
        return json.loads(latest_message.content)
    
    def get_rga_response(self, text_prompt, index_name):
        index = self.pc.Index(index_name)
        vector_store = PineconeVectorStore(pinecone_index=index)
        loaded_index = VectorStoreIndex.from_vector_store(vector_store=vector_store)
        query_engine = loaded_index.as_query_engine()
        response = query_engine.query(text_prompt)
        return json.loads(response.response)
