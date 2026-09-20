from typing import Callable

from .store import EmbeddingStore


class KnowledgeBaseAgent:
    """
    An agent that answers questions using a vector knowledge base.

    Retrieval-augmented generation (RAG) pattern:
        1. Retrieve top-k relevant chunks from the store.
        2. Build a prompt with the chunks as context.
        3. Call the LLM to generate an answer.
    """

    def __init__(self, store: EmbeddingStore, llm_fn: Callable[[str], str]) -> None:
        self.store = store
        self.llm_fn = llm_fn

    def answer(self, question: str, top_k: int = 3) -> str:
        results = self.store.search(question, top_k=top_k)
        if not results:
            return "Không tìm thấy thông tin phù hợp trong cơ sở tri thức."

        context_blocks = []
        for i, res in enumerate(results, start=1):
            source = (
                res.get("metadata", {}).get("source")
                or res.get("metadata", {}).get("doc_id")
                or res.get("id", f"doc_{i}")
            )
            context_blocks.append(f"[{i}] (Nguồn: {source}):\n{res['content']}")
        context = "\n\n".join(context_blocks)

        prompt = (
            f"Bạn là trợ lý AI trả lời câu hỏi dựa trên tài liệu được cung cấp.\n"
            f"Chỉ sử dụng thông tin trong ngữ cảnh dưới đây để trả lời câu hỏi. "
            f"Nếu thông tin không có trong ngữ cảnh, hãy nêu rõ là không tìm thấy.\n\n"
            f"Ngữ cảnh:\n{context}\n\n"
            f"Câu hỏi: {question}\n\n"
            f"Trả lời:"
        )

        return self.llm_fn(prompt)
