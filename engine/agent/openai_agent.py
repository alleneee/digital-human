from agents import Agent, InputGuardrail, GuardrailFunctionOutput, Runner, WebSearchTool, FileSearchTool, function_tool, handoff
from pydantic import BaseModel
import asyncio
from typing import List, Dict, Any
import os
import chromadb
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.document_loaders import DirectoryLoader, TextLoader

# 创建自定义RAG搜索工具的输入输出模型
class RAGSearchInput(BaseModel):
    query: str
    max_results: int = 3

class RAGSearchOutput(BaseModel):
    documents: List[Dict[str, Any]]
    
# 初始化向量数据库(只需要在程序启动时执行一次)
def initialize_vector_db(documents_dir="./data/documents"):
    """初始化并加载向量数据库"""
    # 设置OpenAI API密钥(如果尚未设置)
    os.environ["OPENAI_API_KEY"] = os.environ.get("OPENAI_API_KEY", "你的OpenAI API密钥")
    
    # 加载文档
    loader = DirectoryLoader(documents_dir, glob="**/*.txt", loader_cls=TextLoader)
    documents = loader.load()
    
    # 文本分割
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    chunks = text_splitter.split_documents(documents)
    
    # 创建向量存储
    embeddings = OpenAIEmbeddings()
    vector_db = Chroma.from_documents(
        documents=chunks, 
        embedding=embeddings,
        persist_directory="./data/chroma_db"
    )
    
    print(f"已成功加载 {len(chunks)} 个文档片段到向量数据库")
    return vector_db

# 全局变量存储向量数据库实例
VECTOR_DB = None

# 修改后的RAG搜索函数
@function_tool 
def custom_rag_search(input: RAGSearchInput) -> RAGSearchOutput:
    """
    在知识库中搜索相关文档
    """
    global VECTOR_DB
    
    # 如果向量数据库还未初始化，则初始化它
    if VECTOR_DB is None:
        try:
            # 尝试加载已有数据库
            embeddings = OpenAIEmbeddings()
            VECTOR_DB = Chroma(
                persist_directory="./data/chroma_db",
                embedding_function=embeddings
            )
            print("已加载现有向量数据库")
        except Exception as e:
            print(f"加载现有数据库失败: {e}，创建新数据库")
            VECTOR_DB = initialize_vector_db()
    
    # 执行相似性搜索
    results = VECTOR_DB.similarity_search_with_relevance_scores(
        input.query, 
        k=input.max_results
    )
    
    # 格式化结果
    documents = []
    for doc, score in results:
        documents.append({
            "content": doc.page_content,
            "source": doc.metadata.get("source", "未知"),
            "relevance": float(score)
        })
    
    return RAGSearchOutput(documents=documents)

# 首先定义子Agent
# 创建Web搜索Agent
web_search_agent = Agent(
    name="WebSearchAgent",
    instructions="你是负责网络搜索的Agent。请搜索给定的查询并提供相关信息。",
    tools=[WebSearchTool()]
)

# 创建RAG搜索Agent，使用自定义函数工具
rag_search_agent = Agent(
    name="RAGSearchAgent",
    instructions="你是负责检索内部文档的Agent。请使用RAG方法在向量存储中搜索相关信息。",
    tools=[custom_rag_search]
)

# 然后定义整合Agent
integration_agent = Agent(
    name="IntegrationAgent",
    instructions="""
    你是负责整合信息的Agent。
    你将接收来自网络搜索和RAG搜索的信息，并提供一个综合全面的回答。
    确保回答既考虑到公开的网络信息，也包含内部知识库的相关内容。
    """,
    handoffs=[
        web_search_agent,
        rag_search_agent
    ]
)

async def main():
    # 初始化向量数据库(如果需要)
    # initialize_vector_db("./path/to/your/documents")
    
    user_query = "马斯克的出生年月日"  # 替换为实际的用户查询
    
    result = await Runner.run(
        integration_agent, 
        f"请回答以下问题，同时使用网络搜索和内部知识库: {user_query}"
    )
    
    print(result.final_output)

if __name__ == "__main__":
    asyncio.run(main())

