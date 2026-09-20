# Báo Cáo Cá Nhân — Lab 7: Embedding & Vector Store

**Họ tên:** Vũ Huy Đô
**Nhóm:** G34
**Ngày:** 2026-09-20

> **Nộp 1 bản / sinh viên.** Phần nhóm (lựa chọn tài liệu, thiết kế chiến lược, bộ câu hỏi đánh giá, demo) nộp chung 1 bản trong `REPORT_NHOM.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần cá nhân: 60** = Khởi động (5) + Hướng tiếp cận (10) + Hoàn thiện code (30) + Dự đoán độ tương tự (5) + Kết quả truy xuất của tôi (10).

---

## 1. Khởi động (Warm-up) — Cá nhân (5 điểm)

### Độ tương tự Cosine (Cosine Similarity) (Bài tập 1.1)

**Độ tương tự cosine cao (High cosine similarity) nghĩa là gì?**
> Độ tương tự cosine cao (tiệm cận 1.0) nghĩa là góc giữa hai vector embedding trong không gian đa chiều rất nhỏ, biểu thị hai đoạn văn bản có sự tương đồng lớn về mặt ngữ nghĩa và ngữ cảnh, bất kể độ dài ngắn hay số lượng từ vựng của chúng khác nhau.

**Ví dụ có độ tương tự CAO:**
- Câu A: "Tôi rất thích nuôi một chú chó con làm thú cưng trong nhà."
- Câu B: "Cún cưng là người bạn bốn chân trung thành và thân thiết nhất của con người."
- Tại sao tương đồng: Cả hai câu đều nói về mối quan hệ tình cảm gắn bó giữa người và chó cưng, cùng chia sẻ trường nghĩa về động vật nuôi trong gia đình.

**Ví dụ có độ tương tự THẤP:**
- Câu A: "Thuật toán sắp xếp nhanh QuickSort có độ phức tạp trung bình là O(n log n)."
- Câu B: "Thời tiết hôm nay nắng ráo, bãi biển có sóng êm và rất đẹp."
- Tại sao khác: Hai câu thuộc hai lĩnh vực hoàn toàn tách biệt (khoa học máy tính vs thời tiết/du lịch), không chia sẻ ngữ cảnh hay ý nghĩa liên quan nào.

**Tại sao độ tương tự cosine (cosine similarity) được ưu tiên hơn khoảng cách Euclid (Euclidean distance) cho text embeddings?**
> Khoảng cách Euclid đo độ dài hình học tuyệt đối nên bị chi phối mạnh bởi độ dài văn bản (văn bản dài sinh vector có độ lớn lớn hơn). Trong khi đó, cosine similarity chỉ đo góc giữa các vector (hướng ngữ nghĩa), giúp phản ánh chính xác sự tương đồng về nội dung mà không bị sai lệch bởi độ dài tài liệu.

### Bài toán tính toán Chunking (Bài tập 1.2)

**Tài liệu 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**
> *Trình bày phép tính:*
> Công thức: số_chunk = ceil((độ_dài - độ_chồng_chéo) / (kích_thước - độ_chồng_chéo))
> = ceil((10,000 - 50) / (500 - 50)) = ceil(9,950 / 450) = ceil(22.111...) = 23
> *Đáp án:* 23 chunks.

**Nếu độ chồng chéo (overlap) tăng lên 100, số lượng chunk thay đổi thế nào? Tại sao muốn độ chồng chéo nhiều hơn?**
> Khi overlap tăng lên 100, số lượng chunk = ceil((10,000 - 100) / (500 - 100)) = ceil(9,900 / 400) = ceil(24.75) = 25 chunks (tăng thêm 2 chunks). Tăng độ chồng chéo giúp bảo toàn ngữ cảnh tại các điểm ranh giới chia cắt, hạn chế việc câu văn hoặc điều khoản quan trọng bị cắt đôi khiến retriever bỏ sót thông tin.

---

## 2. Hướng tiếp cận của tôi (My Approach) — Cá nhân (10 điểm)

Giải thích cách tiếp cận của bạn khi lập trình (implement) các phần chính trong gói `src`.

### Các hàm chia nhỏ (Chunking Functions)

**`SentenceChunker.chunk`** — hướng tiếp cận:
> Dùng biểu thức chính quy Lookbehind `(?<=[.!?])\s+` để tách ranh giới câu mà vẫn bảo toàn dấu câu (`.`, `!`, `?` và `.\n`). Các câu được gom nhóm tuần tự tối đa `max_sentences_per_chunk` câu và làm sạch khoảng trắng thừa. Edge case nhận diện: từ viết tắt (như `TS.`, `v.v.`) hoặc số thập phân (như `3.14`) có thể bị cắt nhầm thành câu riêng biệt.

**`RecursiveChunker.chunk` / `_split`** — hướng tiếp cận:
> Triển khai thuật toán đệ quy 2 chiều: (1) Chiều chia xuống duyệt danh sách separator ưu tiên `["\n\n", "\n", ". ", " ", ""]`, mảnh nào dài hơn `chunk_size` sẽ đệ quy với separator cấp thấp hơn; (2) Chiều gom lên ghép các mảnh nhỏ liền kề lại cho tới khi chạm ngưỡng `chunk_size` để tránh sinh chunk vụn. Base cases gồm văn bản rỗng, văn bản $\le$ `chunk_size`, và trường hợp hết separator (`separators=[]`) thì chia đều theo kích thước ký tự cố định.

### Lớp EmbeddingStore

**`add_documents` + `search`** — hướng tiếp cận:
> Lưu trữ in-memory danh sách các bản ghi gồm `id`, `content`, `metadata` và vector `embedding` được tạo từ `embedding_fn`. Khi tìm kiếm, `search` vector hóa query, tính tích vô hướng (dot product/cosine similarity) với toàn bộ vector lưu trữ, sắp xếp giảm dần theo điểm `score` và trả về `top_k` kết quả (lược bỏ vector thô để giữ output gọn gàng).

**`search_with_filter` + `delete_document`** — hướng tiếp cận:
> `search_with_filter` thực hiện tiền lọc (pre-filter) các bản ghi trong kho thỏa mãn toàn bộ cặp key-value của `metadata_filter` trước, sau đó mới chạy similarity search trên tập đã lọc, tránh việc tài liệu sai đối tượng chiếm dụng các vị trí trong `top_k`. `delete_document` lọc bỏ toàn bộ các chunk có `metadata["doc_id"] == doc_id` hoặc `id == doc_id` và trả về `True` nếu số lượng phần tử giảm đi.

### Tác tử KnowledgeBaseAgent

**`answer`** — hướng tiếp cận:
> Truy xuất `top_k` chunks liên quan từ `EmbeddingStore`, sau đó ghép thành khối ngữ cảnh có đánh số `[1] (Nguồn: ...)` kèm nội dung. Prompt được cấu trúc với chỉ dẫn rõ ràng yêu cầu LLM chỉ trả lời dựa trên ngữ cảnh được cung cấp, nêu rõ nếu không tìm thấy và xử lý trường hợp kho dữ liệu rỗng mà không bị crash hay gọi LLM vô ích.

---

## 3. Hoàn thiện code (Core Implementation) — Cá nhân (30 điểm)

Vượt qua bộ kiểm thử là điều kiện tính điểm phần này.

### Kết Quả Kiểm Thử (Test Results)

```text
tests/test_solution.py::TestProjectStructure::test_root_main_entrypoint_exists PASSED                                                                                                  [  2%]
tests/test_solution.py::TestProjectStructure::test_src_package_exists PASSED                                                                                                           [  4%]
tests/test_solution.py::TestClassBasedInterfaces::test_chunker_classes_exist PASSED                                                                                                    [  7%]
tests/test_solution.py::TestClassBasedInterfaces::test_mock_embedder_exists PASSED                                                                                                      [  9%]
tests/test_solution.py::TestFixedSizeChunker::test_chunks_respect_size PASSED                                                                                                          [ 11%]
tests/test_solution.py::TestFixedSizeChunker::test_correct_number_of_chunks_no_overlap PASSED                                                                                          [ 14%]
tests/test_solution.py::TestFixedSizeChunker::test_empty_text_returns_empty_list PASSED                                                                                                [ 16%]
tests/test_solution.py::TestFixedSizeChunker::test_no_overlap_no_shared_content PASSED                                                                                                 [ 19%]
tests/test_solution.py::TestFixedSizeChunker::test_overlap_creates_shared_content PASSED                                                                                               [ 21%]
tests/test_solution.py::TestFixedSizeChunker::test_returns_list PASSED                                                                                                                 [ 23%]
tests/test_solution.py::TestFixedSizeChunker::test_single_chunk_if_text_shorter PASSED                                                                                                 [ 26%]
tests/test_solution.py::TestSentenceChunker::test_chunks_are_strings PASSED                                                                                                            [ 28%]
tests/test_solution.py::TestSentenceChunker::test_respects_max_sentences PASSED                                                                                                        [ 30%]
tests/test_solution.py::TestSentenceChunker::test_returns_list PASSED                                                                                                                  [ 33%]
tests/test_solution.py::TestSentenceChunker::test_single_sentence_max_gives_many_chunks PASSED                                                                                         [ 35%]
tests/test_solution.py::TestRecursiveChunker::test_chunks_within_size_when_possible PASSED                                                                                             [ 38%]
tests/test_solution.py::TestRecursiveChunker::test_empty_separators_falls_back_gracefully PASSED                                                                                       [ 40%]
tests/test_solution.py::TestRecursiveChunker::test_handles_double_newline_separator PASSED                                                                                             [ 42%]
tests/test_solution.py::TestRecursiveChunker::test_returns_list PASSED                                                                                                                 [ 45%]
tests/test_solution.py::TestEmbeddingStore::test_add_documents_increases_size PASSED                                                                                                   [ 47%]
tests/test_solution.py::TestEmbeddingStore::test_add_more_increases_further PASSED                                                                                                     [ 50%]
tests/test_solution.py::TestEmbeddingStore::test_initial_size_is_zero PASSED                                                                                                           [ 52%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_content_key PASSED                                                                                                [ 54%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_score_key PASSED                                                                                                  [ 57%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_sorted_by_score_descending PASSED                                                                                      [ 59%]
tests/test_solution.py::TestEmbeddingStore::test_search_returns_at_most_top_k PASSED                                                                                                   [ 61%]
tests/test_solution.py::TestEmbeddingStore::test_search_returns_list PASSED                                                                                                            [ 64%]
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_non_empty PASSED                                                                                                           [ 66%]
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_returns_string PASSED                                                                                                      [ 69%]
tests/test_solution.py::TestComputeSimilarity::test_identical_vectors_return_1 PASSED                                                                                                  [ 71%]
tests/test_solution.py::TestComputeSimilarity::test_opposite_vectors_return_minus_1 PASSED                                                                                             [ 73%]
tests/test_solution.py::TestComputeSimilarity::test_orthogonal_vectors_return_0 PASSED                                                                                                 [ 76%]
tests/test_solution.py::TestComputeSimilarity::test_zero_vector_returns_0 PASSED                                                                                                       [ 78%]
tests/test_solution.py::TestCompareChunkingStrategies::test_counts_are_positive PASSED                                                                                                 [ 80%]
tests/test_solution.py::TestCompareChunkingStrategies::test_each_strategy_has_count_and_avg_length PASSED                                                                              [ 83%]
tests/test_solution.py::TestCompareChunkingStrategies::test_returns_three_strategies PASSED                                                                                            [ 85%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_filter_by_department PASSED                                                                                           [ 88%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_no_filter_returns_all_candidates PASSED                                                                               [ 90%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_returns_at_most_top_k PASSED                                                                                          [ 92%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_reduces_collection_size PASSED                                                                                   [ 95%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_false_for_nonexistent_doc PASSED                                                                         [ 97%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_true_for_existing_doc PASSED                                                                             [100%]

============================================================================================== 42 passed in 0.16s ==============================================================================================
```

**Số lượng bài test vượt qua (pass):** 42 / 42

---

## 4. Dự đoán độ tương tự (Similarity Predictions) — Cá nhân (5 điểm)

| Cặp | Câu A | Câu B | Dự đoán | Điểm thực tế | Đúng? |
|------|-----------|-----------|---------|--------------|-------|
| 1 | Người mua có 24 giờ để gửi yêu cầu trả hàng đối với thực phẩm tươi sống. | Đối với đồ đông lạnh và tươi sống, thời hạn khiếu nại hoàn tiền là 1 ngày kể từ khi giao hàng. | cao | 0.8449 | Đúng |
| 2 | Tiền hoàn về thẻ tín dụng mất từ 7 đến 14 ngày làm việc. | Thời gian xử lý hoàn trả tiền vào thẻ Visa hoặc Mastercard kéo dài khoảng một đến hai tuần. | cao | 0.8162 | Đúng |
| 3 | Người bán có nghĩa vụ đóng gói hàng hóa cẩn thận trước khi bàn giao cho bưu tá. | Người mua có thể yêu cầu trả hàng nếu sản phẩm bị vỡ hoặc hư hỏng do vận chuyển. | cao | 0.7164 | Đúng |
| 4 | Không được dán trực tiếp phiếu gửi hàng lên vỏ hộp của nhà sản xuất. | Khách hàng có thể thanh toán đơn hàng bằng ví ShopeePay hoặc thẻ tín dụng. | thấp | 0.5594 | Đúng |
| 5 | Chính sách bảo hành áp dụng cho các thiết bị điện tử gia dụng. | Hôm nay trời nắng đẹp thích hợp cho các hoạt động dã ngoại ngoài trời. | thấp | 0.5433 | Đúng |

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn ý nghĩa?**
> Điểm số ở Cặp 5 (0.5433) gây bất ngờ nhất vì hai câu có chủ đề hoàn toàn không liên quan nhưng điểm cosine vẫn trên 0.5 thay vì tiệm cận 0. Điều này giải thích rằng các mô hình embedding hiện đại (như Gemini) đặt toàn bộ biểu diễn ngôn ngữ tự nhiên vào một nón không gian hẹp (narrow cone problem); đồng thời cho thấy embedding đánh giá sự tương đồng không chỉ dựa trên từ khóa bề mặt mà dựa trên cấu trúc ngữ pháp và thuộc tính văn bản của ngôn ngữ.

---

## 5. Kết quả truy xuất của tôi (Competition Results) — Cá nhân (10 điểm)

Chạy **5 câu hỏi đánh giá của nhóm** trên mã nguồn cá nhân của bạn trong gói `src`. **5 câu hỏi này phải trùng với các thành viên cùng nhóm** (xem `REPORT_NHOM.md`).

| # | Câu hỏi (Query) | Top-1 Chunk truy xuất được (tóm tắt) | Điểm Score | Có liên quan không? (Relevant) | Câu trả lời của Agent (tóm tắt) |
|---|-------|--------------------------------|-------|-----------|------------------------|
| 1 | Thời hạn yêu cầu hàng tươi sống | `return-window#3`: Đối với thực phẩm tươi sống hoặc đông lạnh, thời hạn gửi yêu cầu ngắn hơn: 24 giờ kể từ khi đơn được cập nhật "Giao hàng thành công". | 0.8877 | Có (Relevant) | [DEMO LLM] Người mua có thời hạn 24 giờ kể từ khi đơn hàng giao thành công để gửi yêu cầu trả hàng/hoàn tiền đối với thực phẩm tươi sống. |
| 2 | Thời gian hoàn tiền thẻ tín dụng | `refund-methods-and-time#0`: Thời gian được tính sau khi Shopee chấp nhận hoàn tiền và phụ thuộc phương thức thanh toán ban đầu... | 0.7794 | Có (Relevant) | [DEMO LLM] Thời gian nhận tiền hoàn phụ thuộc vào phương thức thanh toán; thẻ tín dụng/ghi nợ mất từ 7–14 ngày làm việc. |
| 3 | Dán nhãn lên hộp nhà sản xuất | `return-shipping-and-packaging#4`: Nếu chọn tự sắp xếp vận chuyển, người mua ghi "Trả hàng Shopee" trên hộp vận chuyển và gửi đến đúng địa chỉ... | 0.8448 | Có (cùng tài liệu) | [DEMO LLM] Người mua cần đóng gói sản phẩm trong hộp carton hoặc bao bì phù hợp, không dán đè trực tiếp lên hộp gốc của nhà sản xuất. |
| 4 | Bằng chứng hàng giả / nhái | `return-evidence#3`: Khi nghi ngờ hàng không chính hãng, bằng chứng có thể gồm quá trình quét mã QR, kiểm tra số seri trên kênh của hãng... | 0.8199 | Có (Relevant) | [DEMO LLM] Người mua cần cung cấp video mở hộp liên tục, quét mã QR hoặc số seri trên kênh của hãng để đối chiếu bao bì chính hãng. |
| 5 | Xử lý số dư tài khoản người bán | `seller-return-refund-obligations#3`: Khi có phương án hoàn tiền... nếu người mua khiếu nại hoàn dưới 50%, Shopee có thể cấn trừ phần chênh lệch từ Số dư Tài khoản... | 0.8896 | Có (Relevant) | [DEMO LLM] Shopee có thể tự động cấn trừ phần chênh lệch từ Số dư Tài khoản Shopee của người bán nếu người bán hoàn dưới 50% giá trị sản phẩm. |

**Bao nhiêu câu hỏi trả về chunk có liên quan trong top-3?** 5 / 5

**Điều hay nhất tôi học được từ thành viên khác / nhóm khác (qua demo):**
> Khi tài liệu có cấu trúc phân mục rõ ràng, việc kết hợp giữa chia theo Heading và gán lại tiêu đề cha cho các mảnh con giúp mô hình không bị mất ngữ cảnh. Đồng thời, việc lọc metadata trước khi tìm kiếm (pre-filtering) là chìa khóa để phân tách quyền hạn giữa các đối tượng người mua và người bán, ngăn chặn triệt để hiện tượng sai lệch thông tin trong hệ thống RAG.

---

## Tự Đánh Giá (Phần Cá Nhân)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Khởi động (Warm-up) | 5 / 5 |
| Hướng tiếp cận của tôi (My Approach) | 10 / 10 |
| Hoàn thiện code (Core Implementation — tests) | 30 / 30 |
| Dự đoán độ tương tự (Similarity Predictions) | 5 / 5 |
| Kết quả truy xuất của tôi (Competition Results) | 10 / 10 |
| **Tổng phần cá nhân** | **60 / 60** |
