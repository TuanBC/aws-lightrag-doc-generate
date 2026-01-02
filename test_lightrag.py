"""Test with same config as raganything_service.py."""

import asyncio

import numpy as np
from lightrag import LightRAG
from lightrag.utils import EmbeddingFunc


async def dummy_llm(prompt, **kwargs):
    return "test response"


async def dummy_embed(texts):
    return np.random.rand(len(texts), 1024)


async def test():
    rag = LightRAG(
        working_dir="./test_rag_service",
        llm_model_func=dummy_llm,
        llm_model_name="amazon.nova-pro-v1:0",
        embedding_func=EmbeddingFunc(
            embedding_dim=1024,
            max_token_size=8192,
            func=dummy_embed,
        ),
        # Same config as service
        kv_storage="JsonKVStorage",
        vector_storage="NanoVectorDBStorage",
        graph_storage="NetworkXStorage",
        doc_status_storage="JsonDocStatusStorage",
    )

    print("1. Calling initialize_storages...")
    await rag.initialize_storages()
    print("2. Storages initialized")

    # Check if pipeline_status exists
    print("3. Checking namespaces...")
    if hasattr(rag, "doc_status") and rag.doc_status:
        print(f"   doc_status type: {type(rag.doc_status)}")

    print("4. Trying ainsert...")
    try:
        await rag.ainsert(
            "FastAPI is a modern Python framework for building APIs. It uses type hints."
        )
        print("5. Insert OK!")
    except Exception as e:
        print(f"5. Insert FAILED: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test())
