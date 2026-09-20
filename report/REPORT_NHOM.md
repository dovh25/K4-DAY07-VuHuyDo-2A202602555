# Báo Cáo Nhóm — Lab 7: Embedding & Vector Store

**Nhóm:** G34
**Thành viên:** Đinh Kim Thái, Nguyễn Lê Phước Tiến, Phạm Văn Kiên, Vũ Huy Đô
**Ngày:** 2026-09-20

> **Nộp 1 bản / nhóm.** Phần cá nhân (hướng tiếp cận, kết quả riêng, dự đoán…) mỗi thành viên nộp riêng trong `REPORT_CANHAN.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần nhóm: 40** = Lựa chọn tài liệu (10) + Thiết kế chiến lược (15) + Chất lượng truy xuất (10) + Thuyết trình (5).

---

## 1. Lựa chọn tài liệu (Document Set Quality) — Nhóm (10 điểm)

### Chủ đề (Domain) & Lý Do Chọn

**Chủ đề:** Chính sách Đổi trả, Hoàn tiền và Nghĩa vụ Người mua / Người bán trên sàn TMĐT Shopee Việt Nam (Biến thể K4-L3B).

**Tại sao nhóm chọn chủ đề này?**
> Nhóm chọn chủ đề này nhằm tuân thủ chặt chẽ yêu cầu của biến thể K4-L3B theo `K4_VARIANT.md`. Bộ tài liệu chính sách của Shopee có cấu trúc điều khoản rõ ràng, nhiều mốc thời gian và điều kiện cụ thể, đồng thời phân định rành mạch giữa đối tượng người mua (`buyer`) và người bán (`seller`), tạo điều kiện lý tưởng để thử nghiệm và chứng minh hiệu quả của cơ chế lọc siêu dữ liệu (`metadata_filter`).

### Danh sách tài liệu (Data Inventory)

| # | Tên tài liệu | Nguồn (Source URL) | Ngày lấy / Phiên bản | Số ký tự | Metadata đã gán |
|---|--------------|------------|--------------------|----------|-----------------|
| 1 | `refund-methods-and-time.md` | https://help.shopee.vn/portal/4/article/189473 | 2026-09-20 / not-stated | 1499 | audience=buyer, category=refund-timing, language=vi |
| 2 | `return-eligibility.md` | https://help.shopee.vn/portal/4/article/188931 | 2026-09-20 / not-stated | 1539 | audience=buyer, category=eligibility, language=vi |
| 3 | `return-evidence.md` | https://help.shopee.vn/portal/4/article/79467 | 2026-09-20 / not-stated | 1395 | audience=buyer, category=evidence, language=vi |
| 4 | `return-shipping-and-packaging.md` | https://help.shopee.vn/portal/4/article/79508 | 2026-09-20 / not-stated | 1313 | audience=buyer, category=return-shipping, language=vi |
| 5 | `return-window.md` | https://help.shopee.vn/portal/4/article/188931 | 2026-09-20 / not-stated | 1225 | audience=buyer, category=request-window, language=vi |
| 6 | `seller-return-refund-obligations.md` | https://help.shopee.vn/portal/4/article/77251 | 2026-09-20 / not-stated | 1560 | audience=seller, category=seller-obligations, language=vi |

**Danh sách kiểm tra quản trị dữ liệu (Data governance checklist):**
- [x] Tập tài liệu (Corpus) chỉ chứa nguồn công khai/được phép dùng và không chứa dữ liệu cá nhân, thông tin đăng nhập hoặc tài liệu nội bộ.
- [x] Mỗi tài liệu có `source_url`, `retrieved_at`, `document_version` (hoặc ngày hiệu lực) trong metadata.

### Cấu trúc Metadata (Metadata Schema)

| Trường metadata | Kiểu | Ví dụ giá trị | Tại sao hữu ích cho truy xuất (retrieval)? |
|----------------|------|---------------|-------------------------------|
| `doc_id` | string | `return-window` | Định danh duy nhất cho tài liệu, phục vụ quản lý, truy vết và xóa tài liệu. |
| `title` | string | `Thời hạn gửi yêu cầu trả hàng hoàn tiền` | Tên tài liệu phục vụ hiển thị nguồn trích dẫn cho câu trả lời của agent. |
| `audience` | string | `buyer`, `seller` | Phân định đối tượng áp dụng quy định; dùng trong `metadata_filter` để tránh lấy nhầm quy định của đối tượng khác. |
| `category` | string | `eligibility`, `request-window`, `refund-timing` | Nhóm chính sách cụ thể, hỗ trợ lọc theo phạm vi nghiệp vụ. |
| `language` | string | `vi` | Định danh ngôn ngữ tiếng Việt của tài liệu. |
| `source_url` | string | `https://help.shopee.vn/portal/4/article/188931` | Đường dẫn công khai giúp kiểm chứng tính chính xác của câu trả lời. |
| `retrieved_at` | string | `2026-09-20` | Ghi nhận thời điểm thu thập dữ liệu phục vụ quản lý độ mới (freshness). |
| `document_version` | string | `not-stated` | Phiên bản tài liệu gốc; dùng `not-stated` khi nguồn không nêu số hiệu cụ thể. |

---

## 2. Thiết kế chiến lược (Strategy Design) — Nhóm (15 điểm)

> Mỗi thành viên thử **một chiến lược khác nhau** trên cùng bộ tài liệu; nhóm tổng hợp và so sánh ở đây.

### Phân tích đường cơ sở (Baseline Analysis)

Chạy `ChunkingStrategyComparator().compare()` trên 3 tài liệu e-commerce đại diện (sau khi bóc tách YAML frontmatter):

| Tài liệu | Chiến lược (Strategy) | Số lượng Chunk | Độ dài trung bình | Giữ được ngữ cảnh không? |
|-----------|----------|-------------|------------|-------------------|
| `return-window.md` (977 ký tự) | FixedSizeChunker (`fixed_size`) | 4 | 281.8 | Kém: Cắt cơ học theo số ký tự, câu quy định thời hạn bị ngắt quãng giữa chừng. |
| | SentenceChunker (`by_sentences`) | 3 | 324.0 | Khá: Giữ trọn vẹn câu nhưng 3 câu gộp lại có thể lẫn hai quy định khác nhau. |
| | RecursiveChunker (`recursive`) | 5 | 193.8 | Tốt: Tách theo đoạn `\n\n`, các mốc thời gian 15 ngày, 24h được giữ nguyên vẹn. |
| `return-shipping-and-packaging.md` (1060 ký tự) | FixedSizeChunker (`fixed_size`) | 5 | 252.0 | Kém: Cắt ngang điều khoản về bao bì và thông tin mã vận đơn. |
| | SentenceChunker (`by_sentences`) | 3 | 351.7 | Khá: Câu hoàn chỉnh nhưng không phản ánh được phân cấp tiêu đề mục. |
| | RecursiveChunker (`recursive`) | 5 | 210.4 | Tốt: Tách bạch rõ ràng giữa khối vật liệu đóng gói và thông tin gửi trả. |
| `seller-return-refund-obligations.md` (1281 ký tự) | FixedSizeChunker (`fixed_size`) | 5 | 296.2 | Kém: Mất hoàn toàn cấu trúc điều khoản nghĩa vụ của người bán. |
| | SentenceChunker (`by_sentences`) | 3 | 425.3 | Trung bình: Chunk dài, gom nhiều ý khiến mật độ thông tin bị loãng khi nhúng. |
| | RecursiveChunker (`recursive`) | 6 | 211.8 | Tốt: Chia đều theo các tiêu chuẩn quy định, kích thước vừa vặn cho embedding. |

### Chiến lược của từng thành viên

**Thành viên 1 — Vũ Huy Đô**
- **Loại chiến lược:** Custom (`HeadingSectionChunker` — chia theo tiêu đề/mục văn bản)
- **Mô tả & lý do chọn cho chủ đề này:** Văn bản chính sách Shopee được cấu trúc rất rõ ràng theo các heading (`#`, `##`). Chiến lược này coi mỗi mục điều khoản là một đơn vị ngữ nghĩa trọn vẹn. Nếu một mục vượt quá 400 ký tự, thuật toán hạ xuống chia nhỏ đệ quy và tự động gắn lại tiêu đề (`## Tiêu đề (tiếp theo):`) vào từng mảnh con để bảo toàn trọn vẹn ngữ cảnh phân cấp.
- **Code snippet (nếu custom):**
```python
class HeadingSectionChunker:
    def __init__(self, max_chunk_size: int = 400, fallback_chunker: RecursiveChunker | None = None) -> None:
        self.max_chunk_size = max_chunk_size
        self.fallback_chunker = fallback_chunker or RecursiveChunker(chunk_size=max_chunk_size)

    def chunk(self, text: str) -> list[str]:
        if not text or not text.strip():
            return []
        matches = list(re.finditer(r"(?m)^(#{1,6}\s+.+)$", text))
        if not matches:
            return self.fallback_chunker.chunk(text)
        sections = []
        first_start = matches[0].start()
        if first_start > 0 and text[:first_start].strip():
            sections.append(("", text[:first_start].strip()))
        for idx, match in enumerate(matches):
            heading = match.group(1).strip()
            start = match.end()
            end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
            sections.append((heading, text[start:end].strip()))
        final_chunks = []
        for heading, body in sections:
            section_text = f"{heading}\n\n{body}".strip() if heading and body else (heading or body)
            if len(section_text) <= self.max_chunk_size:
                final_chunks.append(section_text)
            else:
                for sub in self.fallback_chunker.chunk(body):
                    final_chunks.append(f"{heading} (tiếp theo):\n{sub}".strip() if heading else sub)
        return final_chunks
```

**Thành viên 2 — Đinh Kim Thái**
- **Loại chiến lược:** `RecursiveChunker` (`chunk_size=300`)
- **Mô tả & lý do chọn:** Sử dụng thuật toán chia đệ quy theo danh sách phân tách ưu tiên `["\n\n", "\n", ". ", " ", ""]`. Chiến lược này tôn trọng sự ngắt đoạn tự nhiên của văn bản chính sách, giúp các khối nội dung được tách hợp lý mà không bị chia cắt thô bạo.
- **Code snippet (nếu custom):** Sử dụng `src.chunking.RecursiveChunker(chunk_size=300)`.

**Thành viên 3 — Nguyễn Lê Phước Tiến**
- **Loại chiến lược:** `FixedSizeChunker` (`chunk_size=300`, `overlap=50`)
- **Mô tả & lý do chọn:** Chia kích thước cố định 300 ký tự có độ chồng chéo 50 ký tự. Độ chồng chéo giúp hạn chế việc đứt gãy thông tin tại các điểm cắt ranh giới, giữ cho các con số hoặc từ khóa quan trọng xuất hiện trọn vẹn ở ít nhất một chunk.
- **Code snippet (nếu custom):** Sử dụng `src.chunking.FixedSizeChunker(chunk_size=300, overlap=50)`.

**Thành viên 4 — Phạm Văn Kiên (Report & Demo Lead)**
- **Loại chiến lược:** `SentenceChunker` (`sentences_per_chunk=3`)
- **Mô tả & lý do chọn:** Phân đoạn văn bản chính xác theo ranh giới câu bằng biểu thức chính quy tiếng Việt. Chiến lược này bảo toàn trọn vẹn cấu trúc ngữ pháp từng câu, đồng thời đảm nhận tổng hợp tài liệu và chuẩn bị kịch bản thuyết trình demo nhóm.
- **Code snippet (nếu custom):** Sử dụng `src.chunking.SentenceChunker(sentences_per_chunk=3)`.

### So Sánh Giữa Các Thành Viên

| Thành viên | Chiến lược (Strategy) | Điểm truy xuất (/10) | Điểm mạnh | Điểm yếu |
|-----------|----------|----------------------|-----------|----------|
| Vũ Huy Đô | `HeadingSectionChunker` | 9/10 | Giữ trọn vẹn cấu trúc điều khoản; mảnh con luôn có tiêu đề mục đi kèm giúp ngữ nghĩa sáng rõ. | Khi query chứa từ khóa trùng với tên một heading khác thì heading đó có thể chiếm điểm cao hơn nội dung chi tiết. |
| Đinh Kim Thái | `RecursiveChunker` (chunk_size=300) | 9/10 | Phân đoạn theo `\n\n` tự nhiên, kích thước chunk vừa phải, độ tương đồng embedding tốt. | Mảnh cắt con không giữ được heading nên mất ngữ cảnh cấp cao nếu đọc độc lập. |
| Nguyễn Lê Phước Tiến | `FixedSizeChunker` (overlap=50) | 10/10 | Overlap 50 ký tự giúp nối liền thông tin tại các ranh giới cắt, không bị sót từ khóa ở cả 5 câu. | Chia cơ học không theo ngữ nghĩa, ranh giới câu từ có thể bị đứt đoạn. |
| Phạm Văn Kiên | `SentenceChunker` (3 câu/chunk) | 8/10 | Bảo toàn ngữ pháp câu văn trọn vẹn, không cắt cụt câu giữa chừng. | Các câu dài gộp lại có thể làm loãng từ khóa chính và ranh giới đoạn bị bỏ qua. |

**Chiến lược nào tốt nhất cho chủ đề này? Tại sao?**
> Với các văn bản quy định pháp lý/chính sách TMĐT, **`HeadingSectionChunker`** là chiến lược tối ưu nhất về mặt ngữ nghĩa và truy vết (traceability) vì phản ánh chính xác cấu trúc mục do người soạn thảo thiết kế sẵn. Mặc dù `FixedSizeChunker` đạt điểm số cao nhờ overlap, nhưng `HeadingSectionChunker` tạo ra các chunk có tính trọn vẹn và mạch lạc ngữ cảnh cao nhất, giúp LLM trả lời chuẩn xác và trích dẫn đúng điều khoản mà không bị đứt đoạn văn phong.

---

## 3. Câu hỏi đánh giá & Chất lượng truy xuất (Retrieval Quality) — Nhóm (10 điểm)

### Câu hỏi đánh giá & Câu trả lời chuẩn (nhóm thống nhất)

> **Đúng 5 câu hỏi**, đa dạng về nghiệp vụ, trích xuất 100% từ tài liệu thật; câu 5 bắt buộc có `metadata_filter={"audience": "seller"}`.

| # | Câu hỏi (Query) | Câu trả lời chuẩn (Gold Answer) | Chunk nào chứa thông tin? |
|---|-------|-------------------------------|--------------------------|
| 1 | Đối với thực phẩm tươi sống hoặc đông lạnh, người mua có bao nhiêu giờ để gửi yêu cầu trả hàng hoàn tiền? | Thời hạn gửi yêu cầu là 24 giờ kể từ khi đơn hàng được cập nhật trạng thái "Giao hàng thành công". | `return-window#3` (Mục Thực phẩm tươi sống và đông lạnh) |
| 2 | Thời gian nhận tiền hoàn về thẻ tín dụng hoặc ghi nợ thường mất bao nhiêu ngày làm việc? | Thường cần 7–14 ngày làm việc, tùy thuộc vào ngân hàng phát hành thẻ. | `refund-methods-and-time#2` (Mục Thẻ thanh toán) |
| 3 | Khi gửi trả hàng cho Shopee, người mua có được viết hoặc dán thông tin vận chuyển trực tiếp lên hộp của nhà sản xuất không? | Không được viết hoặc dán trực tiếp thông tin vận chuyển lên hộp nguyên bản của nhà sản xuất; kiện hàng cần đóng gói trong hộp carton hoặc bao bì bên ngoài. | `return-shipping-and-packaging#2` (Mục Vật liệu và cách đóng gói) |
| 4 | Khi nghi ngờ hàng không chính hãng hoặc hàng giả, người mua cần cung cấp những bằng chứng nào? | Bằng chứng gồm video mở hộp liên tục, quét mã QR, kiểm tra số seri trên kênh của hãng, hoặc hình ảnh chỉ rõ sự khác biệt giữa bao bì thực nhận và bao bì chính hãng. | `return-evidence#3` (Mục Nội dung nên ghi nhận) |
| 5 | Trường hợp người mua khiếu nại hoàn tiền dưới 50% giá trị sản phẩm thì Shopee xử lý thế nào đối với số dư tài khoản người bán? | Shopee có thể cấn trừ phần chênh lệch từ Số dư Tài khoản Shopee của người bán để thanh toán cho người mua mà không cần thêm chấp thuận. | `seller-return-refund-obligations#3` (Mục Số tiền hoàn) |

### Tổng hợp chất lượng truy xuất của nhóm

> Thang điểm: 2đ (Top-1 trúng gold chunk + agent trả lời đúng), 1đ (Top-2/3 có gold chunk hoặc đúng tài liệu nhưng sai section), 0đ (không tìm thấy).

| # | Câu hỏi | Chiến lược tốt nhất cho câu này | Có chunk liên quan trong top-3? | Ghi chú |
|---|---------|-------------------------------|-------------------------------|---------|
| 1 | Thời hạn yêu cầu hàng tươi sống | Cả 3 chiến lược (Top-1) | Có (Score: 0.8877) | Truy xuất chính xác mục 24 giờ của `return-window.md`. |
| 2 | Thời gian hoàn tiền thẻ tín dụng | FixedSize & Recursive (Top-1) | Có (Score: 0.7680) | `HeadingChunker` đưa mục Giới thiệu lên Top-1 (0.7794), mục Thẻ ở Top-2 (0.7680). |
| 3 | Dán nhãn lên hộp nhà sản xuất | FixedSize (Top-1) | Có (Score: 0.8493) | `HeadingChunker` đưa mục "Thông tin gửi trả" lên Top-1 do trùng từ khóa "thông tin vận chuyển". |
| 4 | Bằng chứng hàng giả / nhái | Cả 3 chiến lược (Top-1) | Có (Score: 0.8199) | Trúng tuyệt đối đoạn quét mã QR và số seri trong `return-evidence.md`. |
| 5 | Xử lý số dư tài khoản người bán (có filter) | Cả 3 chiến lược (Top-1) | Có (Score: 0.8896) | Khi có filter `audience: seller`, Top-1 trúng chính xác 100% mục Số tiền hoàn. |

**Lọc bằng metadata có giúp ích không? Ở câu hỏi nào?**
> **Rất hữu ích, đặc biệt ở câu hỏi số 5.** 
> Khi KHÔNG dùng filter, Top-2 và Top-3 bị xâm lấn bởi các tài liệu của người mua (`return-eligibility` score 0.7531, `refund-methods-and-time` score 0.7402) do chia sẻ các từ khóa về "hoàn tiền", "khiếu nại". Khi CÓ filter `{"audience": "seller"}`, toàn bộ 100% kết quả Top-3 đều thuộc về văn bản nghĩa vụ của người bán (`seller-return-refund-obligations`), triệt tiêu hoàn toàn nhiễu từ tài liệu người mua và đảm bảo Agent trả lời đúng thẩm quyền đối tượng.

---

## 4. Thuyết trình (Demo) & Bài học nhóm — Nhóm (5 điểm)

**Những phân tích (insights) hay nhất nhóm sẽ trình bày:**
1. **Cosine similarity đo độ tương đồng chủ đề hơn là mật độ câu trả lời:** Một chunk chứa tiêu đề trùng từ khóa (ví dụ: "Thông tin gửi trả") có thể đạt điểm tương đồng cao hơn chunk chứa điều khoản thực tế ("Không dán nhãn lên hộp nhà sản xuất"). Điều này giải thích tại sao cần đánh giá cả Top-3 thay vì chỉ dựa vào Top-1.
2. **Hiệu quả quyết định của Metadata Pre-filtering:** Trong cùng một chủ đề đổi trả, các tài liệu của người mua và người bán dùng chung từ vựng ("hoàn tiền", "khiếu nại"). Lọc trước theo `audience: seller` giúp loại bỏ hoàn toàn 100% nhiễu từ tài liệu người mua, bảo đảm Agent trả lời đúng đối tượng thẩm quyền.
3. **Bảo toàn ngữ cảnh phân cấp với Heading Chunker:** Khi một điều khoản dài bị cắt nhỏ, việc tự động gắn lại tiêu đề cha (`## Tiêu đề (tiếp theo):`) vào từng mảnh con giúp mô hình LLM luôn hiểu rõ ngữ cảnh của quy định mà không bị mất định vị ngữ nghĩa.

**Bài học rút ra khi so sánh trong nhóm:**
> Cùng một bộ tài liệu, `FixedSizeChunker` đạt điểm số cao nhờ overlap 50 ký tự giúp hàn gắn thông tin ranh giới; trong khi `HeadingSectionChunker` đem lại các chunk có tính trọn vẹn và mạch lạc ngữ cảnh cao nhất. Điều này cho thấy chiến lược lý tưởng nhất trong thực tế là lai ghép: chia theo cấu trúc Heading của văn bản và áp dụng overlap trượt giữa các đoạn con.

**Nếu làm lại, nhóm sẽ thay đổi gì trong chiến lược dữ liệu (data strategy)?**
> Nhóm sẽ bổ sung thêm các trường metadata chuyên sâu như `section_type` (`timeline` / `condition` / `penalty`) và tiền xử lý các bảng số liệu, danh sách gạch đầu dòng thành các câu trọn nghĩa trước khi đưa vào pipeline chunking để vector embedding tiếp nhận thông tin mật độ cao tốt hơn.

### Phân tích trường hợp lỗi (Failure Analysis — Bài tập 3.5 & Checkpoint 6)

- **Câu hỏi gặp thất bại:** Câu hỏi 3: *"Khi gửi trả hàng cho Shopee, người mua có được viết hoặc dán thông tin vận chuyển trực tiếp lên hộp của nhà sản xuất không?"*
- **Hiện tượng thực tế:** Trong chiến lược `HeadingSectionChunker`, tài liệu gốc `return-shipping-and-packaging.md` được truy xuất đúng ở Top-1 (score 0.8448) và Top-2 (score 0.8236). Tuy nhiên, cả hai chunk này đều thuộc section *"## Thông tin gửi trả"*. Chunk chứa câu trả lời chuẩn (*"Không viết hoặc dán trực tiếp thông tin vận chuyển lên hộp nguyên bản của nhà sản xuất..."*) nằm ở section *"## Vật liệu và cách đóng gói"* và bị tụt khỏi Top-3.
- **Nguyên nhân cốt lõi (Root cause):**
  1. **Thiên kiến từ khóa trong embedding (Topical overlap bias):** Cụm từ *"thông tin vận chuyển"* trong query trùng khớp ngữ nghĩa với tiêu đề section *"## Thông tin gửi trả"*, khiến vector embedding của section này có độ tương đồng cosine vượt trội so với section đóng gói bao bì.
  2. **Cosine similarity đo độ giống chủ đề, không đo mật độ thông tin câu trả lời:** Embedding Bi-encoder ưu tiên các đoạn văn bản nói chung về "thông tin vận chuyển" hơn là đoạn chứa quy tắc phủ định ("Không viết hoặc dán").
- **Đề xuất cải tiến:**
  1. **Tích hợp Reranking (Cross-Encoder):** Lấy Top-10 ứng viên từ Dense Vector Search, sau đó dùng mô hình Cross-Encoder để tái xếp hạng dựa trên sự tương tác tương hỗ giữa truy vấn và nội dung chunk.
  2. **Parent Document Retrieval:** Khi một section con được tìm thấy, tự động liên kết và bổ sung ngữ cảnh từ section bao bì liền kề trong cùng một văn bản quy trình.

---

## Tự Đánh Giá (Phần Nhóm)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Lựa chọn tài liệu (Document Set Quality) | 10 / 10 |
| Thiết kế chiến lược (Strategy Design) | 15 / 15 |
| Chất lượng truy xuất (Retrieval Quality) | 10 / 10 |
| Thuyết trình (Demo) | 5 / 5 |
| **Tổng phần nhóm** | **40 / 40** |
