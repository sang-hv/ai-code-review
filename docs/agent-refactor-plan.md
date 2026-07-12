# Plan: Refactor `argus_review` — CLI gọn + Agent loop kiểu Codex/Claude Code

> Tài liệu này là hướng dẫn thực thi CHI TIẾT cho một agent/model thực hiện refactor.
> Làm **tuần tự theo phase**. Sau mỗi phase phải chạy test và bảo đảm xanh trước khi sang phase kế.
> Mọi đường dẫn tính từ repo root: `/Users/hoangsang/Downloads/argus-code-review`.

## 0. Bối cảnh & mục tiêu

Vấn đề: lệnh `run-agent` review MR nhiều file (vd 33 file) bị `AgentLoopService` cắt cứng khi
`context_used >= max_total_context_chars` rồi force-final ra summary rỗng, 0 inline comment.

Mục tiêu:
1. **Cắt gọn CLI**: chỉ giữ 3 lệnh review chính `run-agent`, `run-agent-inline`, `run-agent-summary`,
   cộng 4 lệnh tiện ích **giữ lại**: `clear-inline`, `clear-summary`, `show-config`, `dump-schema`.
   Bỏ toàn bộ lệnh non-agent còn lại + code/test liên quan.
2. **Compaction** (giống auto-compact của Claude Code/Codex): khi context gần đầy, tóm tắt lịch sử
   thay vì cắt cứng, rồi tiếp tục loop.
3. **Chunking / map-reduce**: chia N file thành lô, mỗi lô 1 session context sạch, gom kết quả +
   1 bước reduce tổng hợp summary.

## Nguyên tắc thực thi

- Tạo branch: `git checkout -b refactor/agent-codex-style`.
- **Không** commit khi chưa được yêu cầu (theo git_safety). Chỉ code + test.
- Lệnh chạy test (BẮT BUỘC set env config, nếu không conftest sẽ lỗi thiếu `llm`/`vcs`):
  ```bash
  AI_REVIEW_CONFIG_FILE_YAML=./argus_review/tests/configs/config-test.yaml .venv/bin/python -m pytest -q
  ```
  Chạy cả lint nếu có: xem `.github/workflows/reusable-lint.yml` (ruff).
- Sau khi xóa symbol nào, **grep toàn repo** để xóa hết tham chiếu:
  ```bash
  # ví dụ
  rg -n "InlineReviewRunner" --glob '!**/__pycache__/**'
  ```
- Ràng buộc quan trọng — **KHÔNG được xóa** (dùng chung bởi 3 agent runner giữ lại):
  - `services/review/internal/inline/` (InlineCommentService + line_validator + schema)
  - `services/review/internal/summary/` (SummaryCommentService)
  - `services/review/internal/agent_combined/`
  - `services/review/gateway/*` (cả `review_direct_llm_gateway` vì là fallback của agent gateway)
  - `services/prompt/tools.py::format_trace*`, `AgentTraceSchema`
  - fixtures: `tests/fixtures/services/review/internal/{inline.py,summary.py,agent_combined.py}`
  - fixtures: `tests/fixtures/services/review/runner/{agent_combined.py,agent_inline.py,agent_summary.py}`
  - fixtures: `tests/fixtures/services/review/gateway/*`

---

## PHASE 1 — Cắt gọn CLI + xóa code chết

Kết quả mong muốn: chỉ còn 7 lệnh CLI (`run-agent`, `run-agent-inline`, `run-agent-summary`,
`clear-inline`, `clear-summary`, `show-config`, `dump-schema`); toàn bộ test xanh.

### 1A. `argus_review/cli/main.py`
Xóa hẳn 6 command function sau (cả decorator `@app.command(...)`):
- `run` (run-review)
- `run-inline` (`run_inline`)
- `run-context` (`run_context`)
- `run-summary` (`run_summary`)
- `run-inline-reply` (`run_inline_reply`)
- `run-summary-reply` (`run_summary_reply`)

GIỮ NGUYÊN: `run_agent`, `run_agent_inline`, `run_agent_summary`, `clear_inline`, `clear_summary`,
`show_config`, `dump_schema`.

### 1B. Xóa 6 command file
```
argus_review/cli/commands/run_review.py
argus_review/cli/commands/run_inline_review.py
argus_review/cli/commands/run_context_review.py
argus_review/cli/commands/run_summary_review.py
argus_review/cli/commands/run_inline_reply_review.py
argus_review/cli/commands/run_summary_reply_review.py
```
GIỮ: `run_agent_review.py`, `run_agent_inline_review.py`, `run_agent_summary_review.py`,
`run_clear_inline_review.py`, `run_clear_summary_review.py`.

### 1C. `argus_review/services/review/service.py`
Xóa import:
- `ContextReviewRunner`, `InlineReviewRunner`, `InlineReplyReviewRunner`, `SummaryReviewRunner`, `SummaryReplyReviewRunner`
- `InlineCommentReplyService`, `SummaryCommentReplyService`

Trong `__init__` xóa các dòng khởi tạo:
- `self.inline_comment_reply = ...`, `self.summary_comment_reply = ...`
- `self.inline_review_runner = InlineReviewRunner(...)`
- `self.context_review_runner = ContextReviewRunner(...)`
- `self.summary_review_runner = SummaryReviewRunner(...)`
- `self.inline_reply_review_runner = InlineReplyReviewRunner(...)`
- `self.summary_reply_review_runner = SummaryReplyReviewRunner(...)`

Xóa các method:
- `run_inline_review`, `run_context_review`, `run_summary_review`,
  `run_inline_reply_review`, `run_summary_reply_review`

GIỮ NGUYÊN: `review_direct_llm_gateway`, `review_agent_llm_gateway`, `review_llm_gateway`
(chỉ là selector attribute, giữ để 2 test gateway còn xanh), `review_comment_gateway`,
`inline_comment`, `summary_comment`, `agent_combined_result`, 3 agent runner, `run_agent_*`,
`run_clear_*`, `report_total_cost`.

### 1D. Xóa runner + internal reply
Xóa file:
```
argus_review/services/review/runner/inline.py
argus_review/services/review/runner/context.py
argus_review/services/review/runner/summary.py
argus_review/services/review/runner/inline_reply.py
argus_review/services/review/runner/summary_reply.py
argus_review/services/review/internal/inline_reply/   (cả thư mục)
argus_review/services/review/internal/summary_reply/  (cả thư mục)
```

### 1E. Dọn prompt layer (dead code sau khi bỏ runner non-agent)
`argus_review/services/prompt/service.py` — xóa các classmethod:
`build_inline_request`, `build_summary_request`, `build_context_request`,
`build_inline_reply_request`, `build_summary_reply_request`,
`build_system_inline_request`, `build_system_context_request`, `build_system_summary_request`,
`build_system_inline_reply_request`, `build_system_summary_reply_request`,
và `with_conventions` (chỉ 5 builder trên dùng — xác nhận bằng `rg -n "with_conventions"`).

`argus_review/services/prompt/types.py` — xóa khỏi Protocol các method tương ứng vừa xóa ở trên.

`argus_review/libs/config/prompt.py` — xóa field + `cached_property *_or_default` + `load_*`
cho: inline, context, summary, inline_reply, summary_reply (cả bản `system_*`).
GIỮ: agent, agent_light_{inline,summary,combined} và system tương ứng.

Xóa template không dùng trong `argus_review/prompts/`:
```
default_inline.md            default_system_inline.md
default_context.md           default_system_context.md
default_summary.md           default_system_summary.md
default_inline_reply.md      default_system_inline_reply.md
default_summary_reply.md     default_system_summary_reply.md
```
GIỮ: `default_agent.md`, `default_system_agent.md`, và toàn bộ `default_*agent_light*`.

`argus_review/tests/fixtures/services/prompt.py` — xóa các method fake tương ứng
(`build_inline_request`, `build_summary_request`, `build_context_request`, và các
`build_*_reply_request`, `build_system_*` non-agent nếu có).

### 1F. Xóa / sửa test + fixtures

Xóa test file:
```
argus_review/tests/suites/services/review/runner/test_inline.py
argus_review/tests/suites/services/review/runner/test_context.py
argus_review/tests/suites/services/review/runner/test_summary.py
argus_review/tests/suites/services/review/runner/test_inline_reply.py
argus_review/tests/suites/services/review/runner/test_summary_reply.py
argus_review/tests/suites/services/review/internal/inline_reply/   (cả thư mục)
argus_review/tests/suites/services/review/internal/summary_reply/  (cả thư mục)
argus_review/tests/suites/services/prompt/test_conventions_integration.py
```
> Với `test_language_integration.py` và `test_service.py` trong `tests/suites/services/prompt/`:
> chúng gọi `build_inline_request`/`build_summary_request`. Sửa lại để dùng builder còn tồn tại
> (vd `build_agent_light_combined_request`) hoặc xóa các test-case dựa trên builder đã bỏ.
> Sau khi sửa phải chạy được. Nếu file chỉ toàn test builder đã bỏ → xóa cả file.

Xóa fixtures:
```
argus_review/tests/fixtures/services/review/runner/inline.py
argus_review/tests/fixtures/services/review/runner/context.py
argus_review/tests/fixtures/services/review/runner/summary.py
argus_review/tests/fixtures/services/review/runner/inline_reply.py
argus_review/tests/fixtures/services/review/runner/summary_reply.py
argus_review/tests/fixtures/services/review/internal/inline_reply.py
argus_review/tests/fixtures/services/review/internal/summary_reply.py
```
GIỮ fixtures: `runner/{agent_combined,agent_inline,agent_summary}.py`,
`internal/{inline,summary,agent_combined}.py`.

`conftest.py` (repo root) — trong tuple `pytest_plugins` xóa mọi dòng trỏ tới fixture vừa xóa
(vd `...review.runner.inline`, `...review.runner.context`, `...review.internal.inline_reply`, ...).
Chạy `rg -n "runner.inline|runner.context|runner.summary\b|inline_reply|summary_reply" conftest.py`.

`argus_review/tests/fixtures/services/review/base.py` — sửa fixture `review_service`:
- Bỏ tham số: `fake_inline_review_runner`, `fake_context_review_runner`, `fake_summary_review_runner`,
  `fake_inline_reply_review_runner`, `fake_summary_reply_review_runner`.
- Bỏ các `monkeypatch.setattr(... InlineReviewRunner/ContextReviewRunner/SummaryReviewRunner/
  InlineReplyReviewRunner/SummaryReplyReviewRunner ...)`.
- GIỮ 3 monkeypatch cho `AgentInlineReviewRunner`, `AgentSummaryReviewRunner`, `AgentReviewRunner`
  và `CostService`.

`argus_review/tests/suites/services/review/test_service.py` — xóa import fixture đã bỏ và 5 test:
`test_run_inline_review_invokes_runner`, `test_run_context_review_invokes_runner`,
`test_run_summary_review_invokes_runner`, `test_run_inline_reply_review_invokes_runner`,
`test_run_summary_reply_review_invokes_runner`. GIỮ các test agent + gateway + cost.

`argus_review/tests/suites/cli/test_main.py` — sửa:
- Trong `dummy_review_service`: bỏ 6 dòng monkeypatch trỏ tới command module đã xóa
  (`run_review`, `run_inline_review`, `run_context_review`, `run_summary_review`,
  `run_inline_reply_review`, `run_summary_reply_review`). GIỮ 3 dòng agent.
- Trong `@pytest.mark.parametrize`: bỏ các case `["run"]`, `["run-inline"]`, `["run-context"]`,
  `["run-summary"]`, `["run-inline-reply"]`, `["run-summary-reply"]`. GIỮ 3 case agent.
- GIỮ `test_show_config_outputs_json` và `test_cli_module_import_...`.

### Verify Phase 1
```bash
rg -n "InlineReviewRunner|ContextReviewRunner|SummaryReviewRunner|InlineReplyReviewRunner|SummaryReplyReviewRunner|InlineCommentReplyService|SummaryCommentReplyService|build_inline_request|build_summary_request|build_context_request|with_conventions" --glob '!**/__pycache__/**'
# => không còn kết quả nào (ngoài chính tài liệu plan này)
AI_REVIEW_CONFIG_FILE_YAML=./argus_review/tests/configs/config-test.yaml .venv/bin/python -m pytest -q
# => toàn bộ xanh
```

---

## PHASE 2 — Compaction trong `AgentLoopService`

Ý tưởng (giống auto-compact Claude Code/Codex): khi tổng context tool-output vượt ngưỡng
`compaction_threshold_ratio * max_total_context_chars`, gọi 1 lượt LLM tóm tắt các trace cũ thành
"progress summary", bỏ trace thô, gộp summary vào prompt các vòng sau, rồi **tiếp tục loop** thay vì
force-final. Nhờ đó agent không mất phát hiện và có thêm budget để đọc tiếp.

### 2A. Config — `argus_review/libs/config/agent.py`
Thêm 2 field vào `AgentConfig`:
```python
    # Compaction: khi context tool-output đạt ngưỡng, tóm tắt lịch sử thay vì cắt cứng.
    compaction_enabled: bool = True
    compaction_threshold_ratio: float = Field(default=0.8, ge=0.1, le=1.0)
```
Cập nhật test mặc định: `argus_review/tests/suites/libs/config/test_agent.py` thêm assert
`config.compaction_enabled is True` và `config.compaction_threshold_ratio == 0.8`.

### 2B. Prompt tóm tắt
Thêm template `argus_review/prompts/default_agent_compaction.md` (system) với nội dung đại ý:
"Bạn là bộ nén ngữ cảnh. Cho lịch sử các bước agent (lệnh + output), hãy cô đọng thành ghi chú
ngắn gọn giữ lại: file đã xem, phát hiện/nghi vấn, việc còn phải làm. Không bịa. Trả về text thuần."

`argus_review/libs/config/prompt.py`:
- thêm field `agent_compaction_prompt_files: list[FilePath] | None = None`
- thêm `agent_compaction_prompt_files_or_default` -> `resolve_prompt_files(..., "default_agent_compaction.md")`
- thêm `load_agent_compaction()`.

`argus_review/services/prompt/service.py` + `types.py`: thêm
```python
def build_agent_compaction_request(self, traces: list[AgentTraceSchema], prior_summary: str = "") -> str: ...
def build_system_agent_compaction_request(self) -> str: ...
```
`build_agent_compaction_request` render `format_traces(traces, max_chars=None)` + `prior_summary`
(nếu có) thành 1 prompt. `build_system_agent_compaction_request` load `load_agent_compaction()`.

Cập nhật fake ở `argus_review/tests/fixtures/services/prompt.py` để có 2 method này (trả chuỗi cố định
và ghi `self.calls`).

### 2C. `build_agent_request` nhận thêm `compaction_summary`
`argus_review/services/prompt/service.py::build_agent_request` thêm tham số
`compaction_summary: str = ""`. Nếu có, chèn 1 mục `## Progress summary (compacted)\n{...}` ngay
trước `## Agent history`. Cập nhật `types.py` và fake tương ứng (thêm param mặc định "").

### 2D. `argus_review/services/agent/loop/service.py`
Thêm state trong `__init__`:
```python
self.compaction_enabled = settings.agent.compaction_enabled
self.compaction_threshold = int(settings.agent.max_total_context_chars * settings.agent.compaction_threshold_ratio)
self.compaction_summary = ""
```
`clear()` reset thêm `self.compaction_summary = ""`.

Thêm coroutine:
```python
async def compact(self) -> None:
    logger.info(f"Compacting agent history: {len(self.traces)} traces, context_used={self.context_used}")
    prompt = self.prompt.build_agent_compaction_request(self.traces, prior_summary=self.compaction_summary)
    prompt_system = self.prompt.build_system_agent_compaction_request()
    result = await self.llm.chat(prompt=prompt, prompt_system=prompt_system)
    self.compaction_summary = (result.text or "").strip() or self.compaction_summary
    self.tokens_used += result.total_tokens or 0
    # Giữ lại trace force-final/summary? -> bỏ hết trace thô, chỉ giữ summary.
    self.traces = []
    self.context_used = 0
    logger.info(f"Compaction done: summary_chars={len(self.compaction_summary)}")
```

Trong `run()`:
- Mọi lời gọi `build_agent_request(...)` (cả trong vòng lặp) truyền thêm
  `compaction_summary=self.compaction_summary`.
- Thay khối check context limit ở cuối mỗi iteration:
```python
if self.context_used >= self.max_context_chars:
    if self.compaction_enabled:
        await self.compact()
        # tiếp tục loop, KHÔNG break
    else:
        logger.info("Agent context limit reached, forcing final response")
        break
elif self.compaction_enabled and self.context_used >= self.compaction_threshold:
    await self.compact()
if self.max_total_tokens and self.tokens_used >= self.max_total_tokens:
    logger.info("Agent token budget reached, forcing final response")
    break
```
- `force_final(...)` cũng truyền `compaction_summary=self.compaction_summary` vào `build_agent_request`.

Lưu ý an toàn: đừng để compaction lặp vô hạn — vì `signatures` (chống lặp lệnh) KHÔNG bị reset trong
`compact()`, agent sẽ không đọc lại đúng lệnh cũ. Vẫn còn `max_iterations` là chặn cuối.

### 2E. Test Phase 2 — `argus_review/tests/suites/services/agent/loop/test_service.py`
Thêm test (dùng `FakeLLMClient`/`FakeAgentToolService`/`FakePromptService` sẵn có):
- `test_compaction_triggered_when_threshold_reached`: set `compaction_enabled=True`,
  `max_context_chars` nhỏ + `compaction_threshold` nhỏ; ép tool trả output dài; khẳng định
  `build_agent_compaction_request` được gọi và loop KHÔNG dừng ngay (tiếp tục tới FINAL/max_iter).
- `test_compaction_disabled_forces_final`: `compaction_enabled=False` → hành vi cũ (force-final).
- `test_compact_resets_context_and_sets_summary`: gọi trực tiếp `await loop.compact()` và assert
  `loop.compaction_summary` != "" và `loop.context_used == 0`.

### Verify Phase 2
```bash
AI_REVIEW_CONFIG_FILE_YAML=./argus_review/tests/configs/config-test.yaml .venv/bin/python -m pytest -q
```

---

## PHASE 3 — Chunking / map-reduce theo file trong agent runner

Ý tưởng: khi số file thay đổi vượt `max_files_per_chunk`, chia thành các lô. Mỗi lô chạy 1 agent
session context sạch (map) → gom inline comments + summary từng lô; cuối cùng 1 lượt reduce hợp nhất
summary. Mỗi session lô vẫn hưởng compaction từ Phase 2.

### 3A. Config — `argus_review/libs/config/agent.py`
Thêm:
```python
    # 0 = tắt chunking (một session cho toàn bộ file như hiện tại).
    max_files_per_chunk: int = Field(default=0, ge=0, le=1000)
```
Cập nhật `test_agent.py`: assert mặc định `== 0`.

### 3B. `argus_review/services/review/runner/agent_combined.py` (`run-agent`)
Tách phần "chạy 1 session cho một tập file" thành helper, rồi lặp theo lô.

Phác thảo:
```python
def _chunk(self, files: list[str], size: int) -> list[list[str]]:
    if size <= 0 or len(files) <= size:
        return [files]
    return [files[i:i + size] for i in range(0, len(files), size)]

async def _review_chunk(self, review_info, files, inventory) -> AgentCombinedResultSchema:
    review_info = review_info.model_copy(deep=True)
    review_info.changed_files = files
    prompt_context = build_prompt_context_from_review_info(review_info)
    prompt = self.prompt.build_agent_light_combined_request(
        context=prompt_context, base_sha=review_info.base_sha,
        head_sha=review_info.head_sha, conventions_inventory=inventory,
    )
    prompt_system = self.prompt.build_system_agent_light_combined_request()
    prompt_result = await self.review_agent_llm_gateway.ask(prompt, prompt_system)
    return self.agent_combined_result.parse_model_output(prompt_result)
```

Trong `run()` sau khi có `changed_files`:
```python
chunk_size = settings.agent.max_files_per_chunk
chunks = self._chunk(changed_files, chunk_size)
logger.info(f"Agent review: {len(changed_files)} files in {len(chunks)} chunk(s)")

all_comments: list[InlineCommentSchema] = []
summaries: list[str] = []
for idx, files in enumerate(chunks, 1):
    logger.info(f"Reviewing chunk {idx}/{len(chunks)} ({len(files)} files)")
    result = await self._review_chunk(review_info, files, inventory)
    all_comments.extend(result.comments)
    if result.summary and result.summary.strip():
        summaries.append(result.summary.strip())
```

Reduce summary:
- Nếu `len(summaries) <= 1`: dùng luôn (hoặc "").
- Nếu nhiều: gọi 1 lượt reduce. Thêm prompt `build_agent_light_reduce_request(summaries)` +
  system `build_system_agent_light_summary_request()` (tái dùng) qua gateway `.ask(...)`, parse bằng
  `self.summary_comment` -> nhưng combined runner hiện không có `summary_comment`. Cách đơn giản, ít
  rủi ro: nối các summary lô có tiêu đề, KHÔNG gọi thêm LLM:
  ```python
  final_summary = "\n\n".join(summaries) if summaries else ""
  ```
  (Bản reduce-bằng-LLM để lại như enhancement tùy chọn; ưu tiên bản nối để đơn giản + tiết kiệm quota.)

Phần post inline/summary giữ nguyên logic hiện tại nhưng dùng `all_comments` và `final_summary`:
- `comments = InlineCommentListSchema(root=all_comments).dedupe()`
- validate line + policy như cũ
- `SummaryCommentSchema(text=final_summary)` nếu không rỗng.

Chú ý: `skip_inline`/`skip_summary` (khi đã có comment cũ) giữ nguyên ở đầu `run()`.
Import thêm: `from argus_review.config import settings`.

### 3C. `agent_inline.py` (tùy chọn, nếu muốn `run-agent-inline` cũng chunk)
Áp dụng cùng mẫu `_chunk` + vòng lặp gom `parsed.root` rồi validate 1 lần cuối. Nếu muốn giữ đơn
giản, có thể để `run-agent-inline` và `run-agent-summary` KHÔNG chunk (chỉ `run-agent` chunk). Ghi rõ
lựa chọn trong docstring. Khuyến nghị: chunk cả 3 để nhất quán, dùng chung helper `_chunk`.

### 3D. Test Phase 3 — `tests/suites/services/review/runner/test_agent_combined.py`
Thêm:
- `test_no_chunking_when_disabled`: `max_files_per_chunk=0`, N file → gateway `.ask` gọi đúng 1 lần.
- `test_chunks_when_over_limit`: monkeypatch `settings.agent.max_files_per_chunk=2`, review_info có
  5 file → `.ask` gọi 3 lần; inline comments các lô được gộp; summary được nối.
- `test_chunk_helper_splits_correctly`: unit test `_chunk([...], 2)`.

Dùng fixture sẵn có `fake_review_agent_llm_gateway`, `fake_agent_combined_result`, ... (xem
`tests/fixtures/services/review/`). Nếu fake gateway trả cùng 1 kết quả mỗi lần, chỉnh fake để trả
comments khác nhau theo file để kiểm tra gộp.

### Verify Phase 3
```bash
AI_REVIEW_CONFIG_FILE_YAML=./argus_review/tests/configs/config-test.yaml .venv/bin/python -m pytest -q
```

---

## Checklist tổng & verify cuối

- [ ] Phase 1: CLI còn 7 lệnh; grep không còn symbol đã xóa; test xanh.
- [ ] Phase 2: compaction chạy khi đạt ngưỡng; config mới có test; test xanh.
- [ ] Phase 3: chunking theo `max_files_per_chunk`; reduce/nối summary; test xanh.
- [ ] Lint (ruff) sạch: `.venv/bin/python -m ruff check argus_review`.
- [ ] Chạy full test lần cuối:
  ```bash
  AI_REVIEW_CONFIG_FILE_YAML=./argus_review/tests/configs/config-test.yaml .venv/bin/python -m pytest -q
  ```
- [ ] Cân nhắc bump version `pyproject.toml` (vd 0.3.0 vì có breaking change: bỏ lệnh CLI) và cập
      nhật `README.md` phần liệt kê lệnh CLI.
- [ ] Đề xuất giá trị config cho MR lớn trong file config CI:
  ```yaml
  agent:
    enabled: true
    max_total_context_chars: 300000
    max_command_output_chars: 80000
    max_history_chars: 120000
    compaction_enabled: true
    compaction_threshold_ratio: 0.8
    max_files_per_chunk: 10
  ```

## Ghi chú rủi ro
- Compaction thêm 1 LLM call mỗi lần nén; chunking thêm 1 session/lô → tốn quota hơn. Đây là đánh đổi
  để review được MR lớn. Điều chỉnh `max_files_per_chunk` để cân bằng chất lượng vs quota.
- Model phải có context window đủ lớn cho prompt (system + history + summary). Kiểm tra window của
  model đang dùng (`deepseek-v4-pro`) trước khi nâng `max_total_context_chars`.
- Đây là thay đổi breaking cho CLI (bỏ nhiều lệnh) → kiểm tra pipeline `.github/workflows/*` và
  `action.yml` xem có gọi lệnh nào bị xóa không; nếu có phải cập nhật.

---

## PHASE 1.5 — Cập nhật entrypoint CI/Action & docs (BẮT BUỘC, dễ quên)

Các file NGOÀI code Python cũng liệt kê/gọi lệnh sắp bị xóa. Phải sửa, nếu không GitHub Action/CI
sẽ hỏng khi ai đó chọn lệnh cũ.

- `action.yml`:
  - input `review-command` mô tả và whitelist trong `case "$REVIEW_COMMAND" in ... )` đang liệt kê
    `run|run-inline|run-context|run-summary|run-inline-reply|run-summary-reply|...`.
    Bỏ các lệnh đã xóa, chỉ giữ: `run-agent|run-agent-inline|run-agent-summary|clear-inline|clear-summary`.
  - đổi `default: 'run'` → `default: 'run-agent'`.
  - cập nhật `description` liệt kê lệnh cho khớp.
- `.github/workflows/workflow-review-self.yml`: `choice` options bỏ các lệnh đã xóa; `default: 'run'`
  → `'run-agent'`.
- `.github/workflows/reusable-review-self.yml`: `default: "run"` → `"run-agent"`.
- `README.md`: cập nhật phần liệt kê lệnh CLI (dòng `argus-review run-inline`, `run-context`,
  `run-summary`, `run-inline-reply`, `run-summary-reply`, và ghi chú `argus-review run ...`) — thay
  bằng 3 lệnh agent + 4 lệnh tiện ích. Cập nhật cả block CI ví dụ (`choice` options) và
  `docker run ... run-summary`.
- `docs/configs/README.md`: đoạn nói `agent.enabled: true` biến `run/run-inline/run-summary/run-context`
  thành ReAct loop — viết lại cho khớp (chỉ còn agent commands). Bổ sung mô tả config mới
  (`compaction_enabled`, `compaction_threshold_ratio`, `max_files_per_chunk`).
- Chạy lại grep để chắc không còn tham chiếu lệnh đã xóa trong file cấu hình/doc:
  ```bash
  rg -n "run-inline-reply|run-summary-reply|run-context\b|\brun-inline\b|\brun-summary\b" \
     --glob '!**/__pycache__/**' --glob '!docs/agent-refactor-plan.md'
  ```
- Kiểm tra `Dockerfile`/`.dockerignore` xem có CMD/ENTRYPOINT gọi lệnh cũ không (grep `run-`).
