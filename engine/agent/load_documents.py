from langchain.document_loaders import DirectoryLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Chroma
import os

def load_documents(docs_dir="./data/documents", db_dir="./data/chroma_db"):
    """加载文档到向量数据库"""
    # 确保目录存在
    os.makedirs(docs_dir, exist_ok=True)
    os.makedirs(db_dir, exist_ok=True)
    
    # 加载文档
    loader = DirectoryLoader(docs_dir, glob="**/*.txt", loader_cls=TextLoader)
    documents = loader.load()
    print(f"已加载 {len(documents)} 个文档")
    
    # 文本分割
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    chunks = text_splitter.split_documents(documents)
    print(f"已处理成 {len(chunks)} 个文本块")
    
    # 创建向量存储
    embeddings = OpenAIEmbeddings()
    vector_db = Chroma.from_documents(
        documents=chunks, 
        embedding=embeddings,
        persist_directory=db_dir
    )
    
    print(f"已成功将所有文档加载到向量数据库，位置: {db_dir}")
    return vector_db

if __name__ == "__main__":
    load_documents()
