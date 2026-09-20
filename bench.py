#!/usr/bin/env python3
"""
bench.py — Công cụ đo lường và đánh giá Retrieval cho bài Lab 07 (Biến thể K4-L3B).

Chức năng:
1. Đọc và bóc tách frontmatter của toàn bộ file markdown trong data/ecommerce/.
2. Thực hiện chunking bên ngoài store bằng chiến lược được chọn.
3. Đóng gói Document và nạp vào EmbeddingStore với metadata được bảo toàn trên từng chunk.
4. Chạy 5 benchmark queries (bao gồm A/B testing metadata filter cho query 5).
5. Đánh giá Top-3 kết quả truy xuất và lưu báo cáo vào ket_qua_benchmark.txt.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

# Đảm bảo import được module src
ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

from src.chunking import (
    FixedSizeChunker,
    RecursiveChunker,
    SentenceChunker,
)
from src.embeddings import (
    GeminiEmbedder,
    MockEmbedder,
    _mock_embed,
)
from src.models import Document
from src.store import EmbeddingStore


class HeadingSectionChunker:
    """
    Chiến lược chia nhỏ tùy chỉnh cho văn bản chính sách/điều khoản TMĐT (K4-L3B).
    - Tách theo các heading Markdown (#, ##, ###).
    - Giữ nguyên cấu trúc section như một đơn vị ngữ nghĩa trọn vẹn.
    - Với các section dài vượt quá max_chunk_size: chia nhỏ đệ quy và gắn lại heading vào từng mảnh con.
    """

    def __init__(self, max_chunk_size: int = 400, fallback_chunker: RecursiveChunker | None = None) -> None:
        self.max_chunk_size = max_chunk_size
        self.fallback_chunker = fallback_chunker or RecursiveChunker(chunk_size=max_chunk_size)

    def chunk(self, text: str) -> list[str]:
        if not text or not text.strip():
            return []

        heading_pattern = r"(?m)^(#{1,6}\s+.+)$"
        matches = list(re.finditer(heading_pattern, text))

        if not matches:
            return self.fallback_chunker.chunk(text)

        sections: list[tuple[str, str]] = []
        first_start = matches[0].start()
        if first_start > 0:
            preamble = text[:first_start].strip()
            if preamble:
                sections.append(("", preamble))

        for idx, match in enumerate(matches):
            heading = match.group(1).strip()
            start = match.end()
            end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
            body = text[start:end].strip()
            sections.append((heading, body))

        final_chunks: list[str] = []
        for heading, body in sections:
            if not body and not heading:
                continue
            section_text = f"{heading}\n\n{body}".strip() if heading and body else (heading or body)

            if len(section_text) <= self.max_chunk_size:
                final_chunks.append(section_text)
            else:
                sub_chunks = self.fallback_chunker.chunk(body)
                for sub in sub_chunks:
                    if heading:
                        prefixed_chunk = f"{heading} (tiếp theo):\n{sub}".strip()
                        final_chunks.append(prefixed_chunk)
                    else:
                        final_chunks.append(sub)

        return final_chunks


def parse_markdown_file(path: Path) -> tuple[dict, str]:
    """Tách frontmatter và nội dung phần thân của file markdown."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}, text.strip()

    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text.strip()

    raw_yaml = parts[1]
    body = parts[2].strip()

    metadata = {}
    for line in raw_yaml.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, val = line.split(":", 1)
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            metadata[key] = val

    if "doc_id" not in metadata:
        metadata["doc_id"] = path.stem

    return metadata, body


BENCHMARK_QUERIES = [
    {
        "id": 1,
        "query": "Đối với thực phẩm tươi sống hoặc đông lạnh, người mua có bao nhiêu giờ để gửi yêu cầu trả hàng hoàn tiền?",
        "gold_answer": "Thời hạn gửi yêu cầu ngắn hơn: 24 giờ kể từ khi đơn được cập nhật 'Giao hàng thành công'.",
        "target_doc": "return-window",
        "expected_keywords": ["24 giờ", "thực phẩm tươi sống"],
        "metadata_filter": None,
    },
    {
        "id": 2,
        "query": "Thời gian nhận tiền hoàn về thẻ tín dụng hoặc ghi nợ thường mất bao nhiêu ngày làm việc?",
        "gold_answer": "Thẻ tín dụng hoặc ghi nợ thường cần 7–14 ngày làm việc, tùy ngân hàng phát hành.",
        "target_doc": "refund-methods-and-time",
        "expected_keywords": ["7–14 ngày làm việc", "thẻ tín dụng"],
        "metadata_filter": None,
    },
    {
        "id": 3,
        "query": "Khi gửi trả hàng cho Shopee, người mua có được viết hoặc dán thông tin vận chuyển trực tiếp lên hộp của nhà sản xuất không?",
        "gold_answer": "Không viết hoặc dán trực tiếp thông tin vận chuyển lên hộp nguyên bản của nhà sản xuất; kiện hàng cần có hộp carton hoặc bao bì bên ngoài.",
        "target_doc": "return-shipping-and-packaging",
        "expected_keywords": ["Không viết hoặc dán trực tiếp", "nhà sản xuất"],
        "metadata_filter": None,
    },
    {
        "id": 4,
        "query": "Khi nghi ngờ hàng không chính hãng hoặc hàng giả, người mua cần cung cấp những bằng chứng nào?",
        "gold_answer": "Bằng chứng gồm quét mã QR, kiểm tra số seri trên kênh của hãng, khác biệt bao bì thực nhận và bao bì chính hãng, hoặc video mở hộp liên tục.",
        "target_doc": "return-evidence",
        "expected_keywords": ["quét mã QR", "số seri", "video mở hộp"],
        "metadata_filter": None,
    },
    {
        "id": 5,
        "query": "Trường hợp người mua khiếu nại hoàn tiền dưới 50% giá trị sản phẩm thì Shopee xử lý thế nào đối với số dư tài khoản người bán?",
        "gold_answer": "Shopee có thể cấn trừ phần chênh lệch từ Số dư Tài khoản Shopee của người bán để thanh toán cho người mua mà không cần thêm chấp thuận.",
        "target_doc": "seller-return-refund-obligations",
        "expected_keywords": ["cấn trừ phần chênh lệch", "Số dư Tài khoản Shopee", "50%"],
        "metadata_filter": {"audience": "seller"},
    },
]


def build_chunker(strategy: str):
    if strategy == "heading":
        return HeadingSectionChunker(max_chunk_size=400)
    elif strategy == "fixed_size":
        return FixedSizeChunker(chunk_size=300, overlap=50)
    elif strategy == "sentence":
        return SentenceChunker(max_sentences_per_chunk=3)
    elif strategy == "recursive":
        return RecursiveChunker(chunk_size=300)
    else:
        raise ValueError(f"Chiến lược không hợp lệ: {strategy}")


def run_benchmark(strategy_name: str = "heading", provider_name: str = "gemini", data_dir: str = "data/ecommerce", output_file: str = "ket_qua_benchmark.txt"):
    load_dotenv()
    data_path = Path(data_dir)
    md_files = sorted(data_path.glob("*.md"))

    if not md_files:
        print(f"[ERROR] Không tìm thấy file .md nào trong thư mục {data_dir}")
        return 1

    chunker = build_chunker(strategy_name)

    # Khởi tạo embedder
    if provider_name.lower() == "gemini":
        try:
            embedder = GeminiEmbedder()
            backend_label = "Gemini API (gemini-embedding-001)"
        except Exception as e:
            print(f"[WARNING] Không khởi tạo được GeminiEmbedder ({e}). Chuyển sang MockEmbedder.")
            embedder = _mock_embed
            backend_label = "MockEmbedder fallback"
    elif provider_name.lower() == "mock":
        embedder = _mock_embed
        backend_label = "MockEmbedder"
    else:
        embedder = _mock_embed
        backend_label = f"MockEmbedder (không hỗ trợ provider: {provider_name})"

    # Tạo Documents từ các chunk
    documents: list[Document] = []
    chunk_counts = {}

    for path in md_files:
        meta, body = parse_markdown_file(path)
        chunks = chunker.chunk(body)
        chunk_counts[path.stem] = len(chunks)
        for idx, c in enumerate(chunks):
            chunk_id = f"{path.stem}#{idx}"
            # Quan trọng: metadata phải trải đều vào mọi chunk
            chunk_meta = {**meta, "doc_id": path.stem, "chunk_idx": idx}
            documents.append(Document(id=chunk_id, content=c, metadata=chunk_meta))

    store = EmbeddingStore(collection_name=f"bench_{strategy_name}", embedding_fn=embedder)
    store.add_documents(documents)

    out_lines = []
    def log(msg: str = ""):
        print(msg)
        out_lines.append(msg)

    log("=" * 80)
    log(f"KẾT QUẢ BENCHMARK RETRIEVAL — LAB 07 (K4-L3B)")
    log(f"Chiến lược chia nhỏ (Chunker): {strategy_name}")
    log(f"Embedding Backend: {backend_label}")
    log(f"Số tài liệu nguồn: {len(md_files)} file | Tổng số chunks nạp: {store.get_collection_size()} chunks")
    for doc_name, cnt in chunk_counts.items():
        log(f"  • {doc_name:35}: {cnt:2} chunks")
    log("=" * 80)

    total_score = 0
    top3_relevant_count = 0

    for item in BENCHMARK_QUERIES:
        qid = item["id"]
        query = item["query"]
        target = item["target_doc"]
        meta_filter = item["metadata_filter"]
        gold = item["gold_answer"]
        keywords = item["expected_keywords"]

        log(f"\n[QUERY {qid}] {query}")
        log(f"  Target Document : {target}.md")
        log(f"  Metadata Filter : {meta_filter}")
        log(f"  Gold Answer     : {gold}")

        # Tìm kiếm với filter (nếu có)
        results = store.search_with_filter(query, top_k=3, metadata_filter=meta_filter)

        log("  --- Top-3 Retrieval Results ---")
        has_relevant_chunk = False
        gold_rank = None
        has_keywords = False

        for rank, res in enumerate(results, start=1):
            r_doc = res["metadata"].get("doc_id", "unknown")
            score = res["score"]
            content = res["content"].replace("\n", " ")
            preview = content[:140] + ("..." if len(content) > 140 else "")

            # Kiểm tra chứa keywords
            contains_kw = any(kw.lower() in content.lower() for kw in keywords)
            if r_doc == target:
                if gold_rank is None:
                    gold_rank = rank
                if contains_kw:
                    has_relevant_chunk = True
                    has_keywords = True

            mark = "★ [GOLD MATCH]" if (r_doc == target and contains_kw) else ("✔ [SAME DOC]" if r_doc == target else "  ")
            log(f"    {rank}. score={score:.4f} {mark} id={res['id']} | {preview}")

        # Đánh giá điểm câu hỏi theo SCORING.md:
        # 2 điểm: Top-3 chứa chunk liên quan + đáp án trúng
        # 1 điểm: Top-3 có tài liệu liên quan nhưng không ở top-1 hoặc thiếu chi tiết
        # 0 điểm: Không tìm thấy
        if has_relevant_chunk and gold_rank == 1:
            q_score = 2
        elif has_relevant_chunk or gold_rank is not None:
            q_score = 1
        else:
            q_score = 0

        total_score += q_score
        if has_relevant_chunk:
            top3_relevant_count += 1

        log(f"  --> Đánh giá: {q_score}/2 điểm (Chứa chunk chuẩn: {has_relevant_chunk}, Gold Rank: {gold_rank})")

    # Kiểm tra A/B cho câu 5 (có filter vs không filter)
    q5 = BENCHMARK_QUERIES[4]
    log("\n" + "-" * 80)
    log("[A/B TESTING DÀNH CHO CÂU HỎI 5 — HIỆU QUẢ CỦA METADATA FILTERING]")
    log(f"Query: {q5['query']}")
    log("\n1. Khi KHÔNG dùng filter (metadata_filter=None):")
    res_no_filter = store.search_with_filter(q5["query"], top_k=3, metadata_filter=None)
    for r, res in enumerate(res_no_filter, start=1):
        log(f"   {r}. doc_id={res['metadata'].get('doc_id')} (aud={res['metadata'].get('audience')}) score={res['score']:.4f} | {res['content'][:100]}...")

    log("\n2. Khi CÓ filter (metadata_filter={'audience': 'seller'}):")
    res_with_filter = store.search_with_filter(q5["query"], top_k=3, metadata_filter={"audience": "seller"})
    for r, res in enumerate(res_with_filter, start=1):
        log(f"   {r}. doc_id={res['metadata'].get('doc_id')} (aud={res['metadata'].get('audience')}) score={res['score']:.4f} | {res['content'][:100]}...")

    log("=" * 80)
    log(f"TỔNG KẾT: Điểm chất lượng truy xuất: {total_score}/10 điểm")
    log(f"Số câu hỏi có chunk liên quan trong Top-3: {top3_relevant_count}/5 câu")
    log("=" * 80)

    # Ghi file kết quả
    out_path = Path(output_file)
    out_path.write_text("\n".join(out_lines), encoding="utf-8")
    print(f"\n[INFO] Đã xuất kết quả chi tiết ra file: {output_file}")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Chạy benchmark retrieval cho Lab 07")
    parser.add_argument("--strategy", choices=["heading", "fixed_size", "sentence", "recursive"], default="heading", help="Chiến lược chunking cần đánh giá")
    parser.add_argument("--provider", default=os.getenv("EMBEDDING_PROVIDER", "gemini"), help="Embedding provider (gemini / mock)")
    parser.add_argument("--data-dir", default="data/ecommerce", help="Thư mục chứa các tài liệu .md")
    parser.add_argument("--output", default="ket_qua_benchmark.txt", help="File xuất kết quả benchmark")

    args = parser.parse_args()
    return run_benchmark(strategy_name=args.strategy, provider_name=args.provider, data_dir=args.data_dir, output_file=args.output)


if __name__ == "__main__":
    raise SystemExit(main())
