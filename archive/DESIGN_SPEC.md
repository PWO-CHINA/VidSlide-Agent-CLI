# VidSlide v0.4.1 Agent CLI 开发说明（AI-only 修订版）

> 面向多模态 AI Agent 的可靠 PPT 提取、质量审查、恢复与导出工作流设计  
> 基线仓库：`PWO-CHINA/VidSlide`  
> 可靠基线：`v0.4.1` / commit `66ec86808443509df86fbc8d82e5188d8eb90ffc`  
> 产品定位：**纯 AI Agent 使用的 headless CLI，不以人类直接操作为设计目标。**  
> 核心原则：**冻结 v0.4.1 的提取行为，不冻结可观测性和工程外壳；程序负责搜索异常，AI 负责少量语义判断；所有修改都必须可追溯、可回退、可复现。**

---

# 1. 项目目标

本项目不是重新开发一个 PPT 提取算法，也不是为现有 Flask GUI 再增加一层命令行入口。

最终产品应当是一个独立的 **Agent-native CLI**：由 Codex、Claude Code、本地多模态 Agent、未来的 MCP Adapter 或其他自动化系统直接调用，不要求用户理解内部参数，也不依赖浏览器、SSE、tkinter、网页会话或人工交互。

第一阶段目标：

1. **复用并锁定 v0.4.1 已验证可靠的提取行为**
   - v0.4.1 是当前真实使用场景中的可靠基线。
   - 第一阶段不主动优化其 scene change、stable frame、history pool、重复页过滤逻辑。
   - 不引入后续版本中改变抽帧语义的关键帧-only / `NONKEY` 策略。
   - 允许增加不改变提取结果的 instrumentation、日志、worker 隔离和 provenance 记录。

2. **提供无交互、稳定、机器可解析的 CLI**
   - 不启动浏览器。
   - 不弹文件选择框。
   - 不使用 MessageBox / Y-N prompt / overwrite prompt。
   - stdout 必须严格遵守 JSON / JSONL 协议。
   - stderr 只用于诊断信息，Agent 不应依赖 stderr 解析业务状态。
   - 每个命令都返回明确状态、错误码和可执行的 `next_actions`。

3. **建立可靠 provenance**
   - 每一张提取资产都必须拥有稳定 ID。
   - 每一张提取资产都记录来源视频、来源 frame、估算时间戳及其时间基准。
   - 后续 QA、动画中间帧判断、漏页恢复、替换、插入均基于原始视频证据，而不是 AI 凭空生成。

4. **建立导出前 QA 工作流**
   - v0.4.1 先完成正常提取。
   - 确定性算法先扫描整套结果并发现异常候选。
   - AI 只查看少量 flag、邻页、局部视频上下文和低成本 overview。
   - 不让 AI 重做 v0.4.1 已经承担的重复页检测。

5. **最终导出受 QA Gate 约束**
   - 默认只有 `QA_PASS` 才允许生成 final PDF/PPTX/ZIP。
   - 未解决异常时默认阻断导出。
   - `--force` 可以绕过，但必须永久写入事件日志和 manifest。

6. **资产不可变、顺序可变、决策可审计**
   - 原始提取图片一旦写入，不覆盖、不改名、不删除。
   - `insert / replace / remove` 修改的是 manifest 中的逻辑 sequence。
   - 所有行为追加到 `events.jsonl`。

---

# 2. 非目标（Non-goals）

第一阶段明确不做：

- 不保留 Flask 作为 CLI 的运行依赖。
- 不保留网页 GUI 作为主产品入口。
- 不保留 SSE 会话模型。
- 不使用 tkinter 文件选择器。
- 不为人类设计交互式菜单。
- 不让 AI 全量逐页高分辨率审阅。
- 不让 AI 自由扫描完整视频。
- 不让 AI 自由修改 `slides/` 或 assets 目录。
- 不让 AI 根据“看起来应该有一页”凭空补页。
- 不在第一阶段实现重型数据库、消息队列、HTTP 服务或 MCP Server。
- 不把 OCR 作为强制依赖。
- 不将 Turbo 作为可靠基线。

旧 GUI 可以在原 v0.4.1 分支中继续存在，但新的 Agent CLI 产品不应把 GUI 架构带入核心设计。

---

# 3. 最重要的设计原则

## 3.1 冻结“提取行为”，而不是冻结整个文件

需要锁定的是 `legacy-v041` 的输出行为，而不是要求 `extractor.py` 永远一字不动。

允许修改：

- 将 legacy extractor 放入独立 worker process。
- 捕获其 stdout/stderr。
- 增加不改变算法分支的事件观察。
- 记录 frame / timestamp / decoder metadata。
- 增加异常转换层。
- 增加外层取消、超时和进程退出管理。

不允许在 legacy engine 中改变：

- 抽帧间隔。
- scene threshold 语义。
- stable frame 判断逻辑。
- history pool 逻辑。
- 重复页过滤规则。
- ROI 计算方式。
- 比较分辨率。
- Turbo / Fast / Eco 的既有行为。

任何可能改变提取结果的修改都必须进入新的 experimental engine。

建议固定：

```text
engine_id = legacy-v041
baseline_commit = 66ec86808443509df86fbc8d82e5188d8eb90ffc
```

CI 必须对 legacy engine 做行为回归，而不是只比较源文件 hash。

---

## 3.2 `exporter.py` 不属于可靠性核心

v0.4.1 中真正需要视为可靠基线的是 **PPT 提取行为**。

PDF/PPTX/ZIP 打包逻辑属于基础设施，可以独立重构，只需保证：

- 页面顺序严格来自 manifest sequence。
- 每页导出内容与对应 asset 一致。
- 导出失败不会破坏 run 状态。
- 大型课件不会因为一次性加载全部图片而造成不必要的内存风险。

因此第一阶段不要求冻结原 `exporter.py`。

---

## 3.3 软件工程升级与提取算法升级必须分离

### 软件工程层允许演进

- CLI
- protocol
- worker isolation
- manifest
- event log
- atomic write
- resume
- provenance
- deterministic QA
- review context
- recovery
- export
- batch
- capabilities
- future MCP adapter

### 提取算法层必须单独版本化

- 抽帧策略
- stable frame 策略
- scene threshold 语义
- decoder strategy 对结果的影响
- GPU/CPU decode 行为差异
- animation handling
- 关键帧-only 策略

未来任何提取算法优化必须：

```text
new engine
    ↓
golden regression
    ↓
与 legacy-v041 对照
```

不能把工程重构和算法变化混在同一个不可区分的 commit 中。

---

## 3.4 默认可靠性优先

AI 自动化最危险的失败不是慢，而是：

```text
exit_code = 0
status = success
但最终 PDF 静默漏页
```

因此默认：

```text
engine = legacy-v041
profile = reliable
```

第一版不需要向 Agent 暴露大量速度档位。

Turbo 可以保留为显式实验能力，但绝不能由 Agent 默认选择。

---

## 3.5 原始资产不可变

严禁通过重命名文件来表达页序。

错误示例：

```text
slide_0022.jpg
slide_0023.jpg
slide_0024.jpg
```

如果在 22 和 23 之间插入一页，就必须批量重命名，导致 flag、日志、缓存、历史引用全部漂移。

正确设计：

```text
asset_id = s_01K...
```

页面顺序单独保存在：

```json
"sequence": ["s_a", "s_b", "s_c"]
```

插页只是修改 sequence，不修改已有 asset。

---

## 3.6 Snapshot + Event Log

`manifest.json` 表示当前状态快照。

`events.jsonl` 表示不可变操作历史。

两者缺一不可：

```text
manifest.json = 现在是什么状态
events.jsonl  = 为什么变成这个状态
```

manifest 必须原子写入：

```text
manifest.json.tmp
    ↓
flush / fsync
    ↓
atomic rename
    ↓
manifest.json
```

避免 Agent / 系统中断时留下半个 JSON。

---

# 4. 与 v0.4.1 仓库的关系

v0.4.1 当前主要结构：

```text
app.py
extractor.py
exporter.py
static/
templates/
```

其中：

- `extractor.py`：可靠提取行为来源。
- `app.py`：GUI、Flask、SSE、多会话、资源监控、人工交互外壳。
- `exporter.py`：打包基础设施。

Agent CLI 不应继续围绕 `app.py` 构建。

推荐做法：

```text
从 v0.4.1 提取 legacy engine
        ↓
建立全新的 vidslide package
        ↓
CLI 直接调用内部 service / worker
```

旧 GUI 如果仍需保留，可继续在原产品中维护，但与新的 Agent CLI 解耦。

---

# 5. 推荐项目结构

```text
VidSlide/
│
├── pyproject.toml
├── README.md
│
├── vidslide/
│   ├── __init__.py
│   ├── cli.py
│   ├── protocol.py
│   ├── errors.py
│   ├── state.py
│   ├── manifest.py
│   ├── events.py
│   ├── ids.py
│   │
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── legacy_v041.py
│   │   ├── legacy_worker.py
│   │   └── experimental.py
│   │
│   ├── video/
│   │   ├── probe.py
│   │   ├── decode.py
│   │   └── frames.py
│   │
│   ├── qa/
│   │   ├── audit.py
│   │   ├── content.py
│   │   ├── temporal.py
│   │   ├── sequence.py
│   │   └── page_number.py      # optional capability
│   │
│   ├── review/
│   │   ├── overview.py
│   │   ├── context.py
│   │   └── contact_sheet.py
│   │
│   ├── recovery.py
│   ├── resolver.py
│   ├── exporter.py
│   ├── doctor.py
│   └── capabilities.py
│
├── tests/
│   ├── unit/
│   ├── synthetic/
│   ├── integration/
│   └── golden/
│       ├── expected/
│       └── metadata/
│
└── docs/
    └── agent-cli-development.md
```

新的 Agent CLI 产品中不需要：

```text
Flask
static/
templates/
SSE
BroadcastChannel
tkinter
浏览器自动打开
GUI session
```

---

# 6. CLI 总体设计

主程序：

```bash
vidslide
```

Windows 可打包为：

```text
VidSlideCLI.exe
```

第一版核心命令：

```text
vidslide probe VIDEO
vidslide extract VIDEO
vidslide audit RUN
vidslide overview RUN
vidslide context RUN --flag FLAG_ID
vidslide recover RUN --flag FLAG_ID
vidslide resolve RUN --action-json JSON
vidslide export RUN
vidslide run VIDEO
```

元命令：

```text
vidslide doctor
vidslide capabilities
vidslide version
```

第一版不再使用同一个 `inspect` 同时表示“视频预检”和“视觉审查”。

原因：对 Agent 而言，一个命令应当只有一个明确语义。

---

# 7. `vidslide probe`

用途：

- 检查视频存在且可读取。
- 做少量 decode smoke test。
- 获取基础元信息。
- 给 extract / run 提供前置检查。

示例：

```bash
vidslide probe lecture01.mp4
```

最终 stdout：

```json
{
  "protocol_version": 1,
  "command": "probe",
  "status": "ok",
  "input": {
    "path": "D:\\course\\lecture01.mp4",
    "size_bytes": 123456789,
    "sha256": "..."
  },
  "video": {
    "duration_seconds": 5421.3,
    "fps_reported": 25.0,
    "width": 1920,
    "height": 1080,
    "frame_count_reported": 135532,
    "codec": "h264"
  },
  "recommended_engine": "legacy-v041",
  "next_actions": [
    {
      "command": "extract",
      "args": ["lecture01.mp4"]
    }
  ]
}
```

`probe` 不做完整提取。

---

# 8. `legacy-v041` 可靠 profile

不能只写“复用 v0.4.1”，必须明确实际运行 profile。

v0.4.1 应锁定的默认可靠配置：

```json
{
  "engine": "legacy-v041",
  "engine_source_commit": "66ec86808443509df86fbc8d82e5188d8eb90ffc",
  "profile": "reliable",
  "parameters": {
    "threshold": 5.0,
    "enable_history": true,
    "max_history": 5,
    "use_roi": true,
    "fast_mode": true,
    "speed_mode": "fast",
    "decoder": "auto"
  }
}
```

说明：

- v0.4.1 中 `Fast` 与 `Eco` 的核心检测采样逻辑一致。
- Fast 主要减少节流，不改变 1 s 主采样、480 px 比较宽度和 0.5 s × 2 稳定确认。
- Turbo 会改变抽样间隔、比较分辨率和稳定帧策略，存在漏页风险。

因此 Agent 默认可靠 profile 应使用 v0.4.1 Fast 行为，而不是 Turbo。

如果未来需要：

```text
experimental-turbo
experimental-v042
...
```

必须作为独立 engine/profile 暴露。

---

# 9. Legacy worker 隔离

这是 Agent CLI 的关键工程要求。

v0.4.1 `extractor.py` 内部存在直接 `print()` 输出。

如果在 CLI 主进程直接调用 legacy extractor，会污染 stdout JSON 协议。

因此推荐：

```text
Agent
  │
  ▼
vidslide CLI parent
  │
  ├── stdout: protocol JSONL only
  ├── stderr: diagnostic only
  │
  └── legacy worker process
       ├── 调用 v0.4.1 extractor
       ├── 捕获 legacy print
       ├── legacy stdout/stderr → logs/legacy-worker.log
       └── structured IPC → parent
```

worker 与 parent 之间可以使用：

- multiprocessing Pipe
- multiprocessing Queue
- 本地临时 JSONL pipe

第一版优先使用 Python 标准库方案，不引入额外 RPC 框架。

worker 必须向 parent 发送：

```text
WORKER_STARTED
PROGRESS
SLIDE_SAVED
WORKER_DONE
WORKER_ERROR
WORKER_CANCELLED
```

主进程再转换为公开 protocol。

---

# 10. stdout / stderr 协议

## 10.1 stdout

stdout 必须严格只包含机器可解析 JSON / JSONL。

禁止出现：

```text
正在提取……
成功！
[GPU] ...
[DEBUG] ...
```

长任务默认输出 JSONL：

```jsonl
{"protocol_version":1,"type":"start","command":"extract","run_id":"01K..."}
{"protocol_version":1,"type":"progress","progress":12.4,"slides":5}
{"protocol_version":1,"type":"asset","asset_id":"s_01K...","source_frame":23420}
{"protocol_version":1,"type":"progress","progress":37.8,"slides":19}
{"protocol_version":1,"type":"result","status":"ok","state":"EXTRACTED"}
```

最后一行必须永远是 `type=result` 或 `type=error`。

这样 Agent 即使忽略中间进度，也能稳定读取最终结果。

## 10.2 stderr

stderr 可记录诊断信息，但：

- Agent 不应依赖其中内容判断业务状态。
- 所有重要业务错误必须同时进入 stdout structured error。
- 完整日志写入 run 目录。

---

# 11. Protocol 通用 envelope

所有命令最终结果建议统一：

```json
{
  "protocol_version": 1,
  "command": "audit",
  "request_id": "req_01K...",
  "run_id": "run_01K...",
  "status": "ok",
  "state": "REVIEW_REQUIRED",
  "result": {},
  "warnings": [],
  "next_actions": []
}
```

错误统一：

```json
{
  "protocol_version": 1,
  "command": "extract",
  "status": "error",
  "error": {
    "code": "VIDEO_DECODE_FAILED",
    "message": "Unable to decode input video",
    "retryable": true
  },
  "next_actions": [
    {
      "command": "probe"
    },
    {
      "command": "extract",
      "options": {"decoder":"cpu"}
    }
  ]
}
```

`next_actions` 是 Agent-native 设计的重要组成部分。

CLI 不只报告发生了什么，还应明确下一步哪些动作是合法的。

---

# 12. 稳定错误码

建议：

```text
0    success
2    invalid arguments
10   input not found
11   unsupported video
12   video decode failed
13   probe failed
20   extraction failed
21   cancelled
22   worker crashed
23   resume incompatible
30   export failed
31   qa execution failed
32   unresolved qa flags
33   invalid resolution action
34   candidate not found
35   manifest conflict
36   state transition invalid
40   insufficient disk space
41   output exists
50   internal error
```

机器错误名：

```text
INPUT_NOT_FOUND
UNSUPPORTED_VIDEO
VIDEO_DECODE_FAILED
EXTRACTION_FAILED
WORKER_CRASHED
UNRESOLVED_QA_FLAGS
INVALID_RESOLUTION_ACTION
MANIFEST_CONFLICT
INVALID_STATE_TRANSITION
INSUFFICIENT_DISK_SPACE
OUTPUT_EXISTS
INTERNAL_ERROR
```

Agent 优先依据机器错误名，而不是解析 message。

---

# 13. 完全 non-interactive

CLI 模式禁止：

- 文件选择窗口
- 浏览器
- MessageBox
- Y/N
- overwrite prompt
- “按任意键继续”

文件已存在：

```json
{
  "status": "error",
  "error": {
    "code": "OUTPUT_EXISTS"
  }
}
```

显式参数：

```text
--overwrite
--resume
--skip-existing
```

所有 destructive action 必须显式参数化。

---

# 14. Run 目录结构

推荐：

```text
lecture01.vidslide/
│
├── manifest.json
├── events.jsonl
│
├── assets/
│   ├── s_01KABC....jpg
│   ├── s_01KABD....jpg
│   └── ...
│
├── candidates/
│   ├── c_01K....jpg
│   └── ...
│
├── review/
│   ├── overview/
│   └── context/
│
├── qa/
│   └── audit.json
│
├── logs/
│   ├── cli.log
│   └── legacy-worker.log
│
└── exports/
    ├── lecture01.pdf
    └── ...
```

不再使用可变编号文件名作为主 identity。

---

# 15. Stable ID 设计

建议 ID：

```text
run_01K...
s_01K...      # extracted slide asset
c_01K...      # recovery candidate
f_01K...      # QA flag
a_01K...      # resolution action
exp_01K...    # export artifact
```

可以使用 ULID / UUIDv7 等可排序 ID。

要求：

- ID 创建后永久稳定。
- 页序变化不改变 ID。
- flag 引用 asset_id，不引用易漂移页码。
- CLI 输出中同时可以提供当前 `ordinal` 方便视觉理解，但 ordinal 不是 identity。

---

# 16. Manifest 设计

示例：

```json
{
  "schema_version": 1,
  "protocol_version": 1,
  "run_id": "run_01K...",
  "created_at": "2026-10-02T09:00:00Z",
  "updated_at": "2026-10-02T09:12:00Z",

  "engine": {
    "id": "legacy-v041",
    "source_commit": "66ec86808443509df86fbc8d82e5188d8eb90ffc",
    "profile": "reliable"
  },

  "input": {
    "path": "D:\\course\\lecture01.mp4",
    "sha256": "...",
    "size_bytes": 123456789
  },

  "parameters": {
    "threshold": 5.0,
    "enable_history": true,
    "max_history": 5,
    "use_roi": true,
    "fast_mode": true,
    "speed_mode": "fast",
    "decoder": "auto"
  },

  "video": {
    "fps_reported": 25.0,
    "frame_count_reported": 135532,
    "duration_seconds": 5421.3,
    "width": 1920,
    "height": 1080,
    "codec": "h264"
  },

  "assets": {
    "s_01KA": {
      "path": "assets/s_01KA.jpg",
      "sha256": "...",
      "source_frame": 83452,
      "source_time_seconds": 3338.08,
      "time_basis": "fps_derived",
      "timestamp_accuracy": "estimated",
      "origin": "legacy-v041"
    }
  },

  "sequence": [
    "s_01KA",
    "s_01KB",
    "s_01KC"
  ],

  "qa": {
    "status": "PENDING",
    "audit_revision": 0,
    "open_flags": []
  },

  "state": "EXTRACTED"
}
```

---

# 17. Provenance：frame 与 timestamp

每一张 asset 必须至少记录：

```json
{
  "source_frame": 83452,
  "source_time_seconds": 3338.08,
  "time_basis": "fps_derived",
  "timestamp_accuracy": "estimated"
}
```

第一版中：

```text
source_time_seconds = source_frame / fps_reported
```

但必须明确这是 **估算值**。

原因：

- OpenCV 报告的 FPS 不一定代表每帧真实 presentation timestamp。
- VFR 视频尤其不能把 `frame/fps` 当成绝对真实时间。

因此不能简单把字段命名成“精确 timestamp”。

未来如果增加真实 PTS 采集，可写：

```json
{
  "source_pts_seconds": 3338.041,
  "time_basis": "decoder_pts",
  "timestamp_accuracy": "decoder"
}
```

legacy engine 的行为不需要因此改变。

---

# 18. Event Log

`events.jsonl` 只追加，不回写历史。

示例：

```jsonl
{"event_id":"evt_01","type":"RUN_CREATED","at":"..."}
{"event_id":"evt_02","type":"EXTRACTION_STARTED","at":"..."}
{"event_id":"evt_03","type":"ASSET_CREATED","asset_id":"s_01KA","source_frame":10020}
{"event_id":"evt_04","type":"EXTRACTION_COMPLETED","slides":83}
{"event_id":"evt_05","type":"QA_FLAG_CREATED","flag_id":"f_01K..."}
{"event_id":"evt_06","type":"CANDIDATE_CREATED","candidate_id":"c_01K..."}
{"event_id":"evt_07","type":"SEQUENCE_CHANGED","action_id":"a_01K..."}
{"event_id":"evt_08","type":"QA_PASSED"}
{"event_id":"evt_09","type":"EXPORT_CREATED","export_id":"exp_01K..."}
```

任何：

```text
replace
insert
remove
force export
manual parameter override
resume
```

都必须追加 event。

---

# 19. `vidslide extract`

用途：

只完成提取，不自动进行 AI 审查，也不生成 final PDF。

示例：

```bash
vidslide extract lecture01.mp4 --output lecture01.vidslide
```

流程：

```text
probe
  ↓
create run
  ↓
spawn legacy worker
  ↓
legacy-v041 extraction
  ↓
immutable assets
  ↓
manifest + events
  ↓
state = EXTRACTED
```

最终结果：

```json
{
  "command": "extract",
  "status": "ok",
  "run_id": "run_01K...",
  "state": "EXTRACTED",
  "slides": 83,
  "run_dir": "lecture01.vidslide",
  "next_actions": [
    {
      "command": "audit",
      "run": "lecture01.vidslide"
    }
  ]
}
```

---

# 20. Resume / 中断恢复设计

v0.4.1 虽然已经提供 `start_frame` / `saved_offset`，但 **不能直接把它等同于可靠的断点续传**。

原因来自现有 extractor 行为：

- `enable_history=true` 时，history pool 只存在于当前进程内存。
- 续传重新进入 `extract_slides()` 后，history pool 会从新的起始帧重新初始化。
- 之前最多 `max_history` 张已接受页面不会自动恢复到原 history pool。
- `prev_gray` 等内部比较状态也没有完整持久化。

因此：

```text
v0.4.1 existing resume
≠
uninterrupted legacy-v041 extraction
```

如果直接沿用现有 resume，续传后可能重新接受此前已见过的历史页面，产生 silent behavioral drift。

## 20.1 第一版可靠策略

对 `legacy-v041 / reliable`，第一版优先保证结果一致，而不是追求断点速度。

建议：

```text
任务中断
  ↓
保留 incomplete run + event history
  ↓
--resume
  ↓
从原视频起点重新执行 legacy-v041 到新的 staging extraction
  ↓
通过 golden-style consistency checks / 完整成功
  ↓
原子提交新的 extracted state
```

也就是说，第一版 `--resume` 更准确地说是 **safe restart**。

它可以复用已有 probe/hash/run metadata，但不应调用当前 v0.4.1 的近似 checkpoint continuation 来冒充完全等价续传。

## 20.2 未来精确 checkpoint resume

只有当下列 legacy state 被明确持久化或可精确重建后，才启用真正的 checkpoint resume：

```text
current frame position
last comparison state / prev_gray semantics
last accepted history pool
max_history
ROI / resize parameters
decoder/profile identity
```

history pool 可以从此前已接受的 immutable assets 按同样 ROI / grayscale / resize 规则重建，但必须通过专门 regression 验证其与不中断运行等价。

在此之前：

```text
checkpoint_resume_available = false
safe_restart_available = true
```

`capabilities` 必须如实暴露这一点。

## 20.3 恢复前一致性检查

无论 safe restart 还是未来 checkpoint resume，都必须检查：

- 输入视频 sha256 是否一致。
- engine/profile 是否一致。
- manifest revision 是否有效。
- 已提交 assets 是否可读且 hash 正确。
- 中断原因和 worker exit 状态是否已记录。

不兼容时返回：

```text
RESUME_INCOMPATIBLE
```

禁止静默从不可靠断点继续。

---

# 21. Pre-export QA 总体流程

推荐：

```text
原视频
  │
  ▼
legacy-v041 extraction
  │
  ├── immutable assets
  ├── provenance
  └── manifest
       │
       ▼
Deterministic Audit
       │
       ├── content anomaly
       ├── unusual temporal gap
       ├── post-save temporal stability
       └── optional page-number signal
       │
       ▼
flags
       │
       ├── 0 flags ─────────────┐
       │                        │
       └── flags > 0            │
               │                │
               ▼                ▼
        context / recover   overview sanity
               │                │
               └──────┬─────────┘
                      ▼
                 resolve if needed
                      │
                      ▼
                  audit again
                      │
                      ▼
                    QA_PASS
                      │
                      ▼
                    export
```

核心原则：

> 确定性算法负责在 100 页里搜索异常；AI 负责理解少量候选；overview 负责兜底 deterministic false negative。

---

# 22. 明确不重复 v0.4.1 已完成的工作

legacy-v041 已负责：

- scene change detection
- stable frame detection
- history pool
- 相邻/历史重复页过滤

因此 QA 默认不重新做 duplicate detection。

`audit.json` 中明确：

```json
{
  "checks": {
    "duplicate_detection": {
      "status": "delegated",
      "handled_by": "legacy-v041"
    }
  }
}
```

`overview` 的 AI prompt 也必须写明：

```text
不要重新逐页检查重复页。
只有在出现明显结构异常时才提出新的 review request。
```

---

# 23. `vidslide audit`

`audit` 第一版完全 deterministic，不调用 AI。

示例：

```bash
vidslide audit lecture01.vidslide
```

输出：

```json
{
  "command": "audit",
  "status": "ok",
  "run_id": "run_01K...",
  "state": "REVIEW_REQUIRED",
  "checks": {
    "duplicate_detection": "delegated",
    "content_anomaly": "passed",
    "temporal_gap": "warning",
    "post_save_stability": "warning",
    "page_number": "unavailable"
  },
  "flags": [
    {
      "flag_id": "f_01KA",
      "reason": "POSSIBLE_ANIMATION_INTERMEDIATE",
      "asset_id": "s_01KQ",
      "ordinal": 27,
      "score": 0.91
    },
    {
      "flag_id": "f_01KB",
      "reason": "UNUSUAL_TIME_GAP",
      "between": ["s_01KX", "s_01KY"],
      "ordinals": [52,53],
      "gap_seconds": 215
    }
  ],
  "next_actions": [
    {
      "command": "context",
      "flag_id": "f_01KA"
    },
    {
      "command": "recover",
      "flag_id": "f_01KB"
    }
  ]
}
```

---

# 24. QA：信息量异常

目标：

发现明显不像正常 PPT 的页面。

可用指标：

- foreground coverage
- edge density
- entropy
- connected component count
- brightness distribution
- optional text-like density

不要使用：

```text
white_pixels > 80% => bad
```

因为标题页、章节页本来可能很空。

应基于当前 deck 的分布做相对异常检测，例如：

```text
median content coverage = 0.42
asset s_X = 0.04
z / robust score = extreme
→ LOW_CONTENT
```

输出：

```json
{
  "flag_id": "f_01K...",
  "reason": "LOW_CONTENT",
  "asset_id": "s_01K...",
  "ordinal": 37,
  "score": 0.94
}
```

该 flag 表示“值得看”，不是“确定错误”。

---

# 25. QA：时间跨度异常

根据当前 sequence 中相邻 asset 的 provenance 估算停留时间。

例如：

```text
median slide gap ≈ 43 s

ordinal 10 → t=1273 s
ordinal 11 → t=1488 s

gap = 215 s
```

产生：

```json
{
  "reason": "UNUSUAL_TIME_GAP",
  "between": ["s_A", "s_B"],
  "gap_seconds": 215,
  "score": 0.86
}
```

它不是“漏页事实”，只是触发 recover 的信号。

需要使用 robust statistics，避免：

- 开场长等待
- 老师长时间讲同一页
- 视频暂停
- 章节停留时间天然不均匀

造成大量误报。

---

# 26. QA：动画中间帧嫌疑

这是第一版最重要的 QA 之一。

对于 asset 的保存时间 `t`，读取局部视频：

```text
t - 1.0
t - 0.5
t
t + 0.5
t + 1.0
t + 1.5
```

程序计算局部 temporal difference 和 layout similarity。

如果同时满足：

- 当前保存 asset 之后画面仍继续变化。
- 后续出现新的稳定 plateau。
- 后续稳定帧与当前页整体 layout 高度相似。

产生：

```json
{
  "reason": "POSSIBLE_ANIMATION_INTERMEDIATE",
  "asset_id": "s_01K...",
  "source_time_seconds": 15.0,
  "later_stable_time_seconds": 16.5,
  "score": 0.91
}
```

然后交给多模态 Agent 判断：

> 后续稳定帧是同一张 PPT 的动画完成态，还是下一张真正的 PPT。

程序负责候选搜索，AI 不自行扫描整个视频。

---

# 27. QA：页码连续性（可选能力）

页码 OCR 不作为第一版强制能力。

原因：

- v0.4.1 当前没有 OCR 依赖。
- OCR 本身有 footer、章节重置、罗马数字、遮挡等误差。
- 为一个 heuristic 引入重型 OCR 依赖可能不划算。

第一版 capabilities 可返回：

```json
{
  "page_number_detection": {
    "available": false
  }
}
```

未来加入 OCR backend 后，可对页脚小区域做轻量识别：

```text
13
14
16
```

触发：

```json
{
  "reason": "PAGE_NUMBER_GAP",
  "observed": [14,16],
  "confidence": 0.87
}
```

OCR 结果永远只是触发 review/recover 的信号，不是最终事实。

---

# 28. `vidslide overview`

这是修订版新增的全局视觉兜底。

目的不是让 AI 全量审阅，而是以极低视觉成本发现 deterministic QA 没定义到的明显异常。

示例：

```bash
vidslide overview lecture01.vidslide
```

生成：

```text
review/overview/overview_001.jpg   # 1-16
review/overview/overview_002.jpg   # 17-32
...
```

每个 thumbnail 标记：

```text
ordinal
asset_id short form
source_time
```

输出：

```json
{
  "command": "overview",
  "status": "ok",
  "sheets": [
    {
      "path": "review/overview/overview_001.jpg",
      "ordinals": [1,16]
    }
  ],
  "review_policy": {
    "purpose": "deck_level_sanity_only",
    "duplicate_detection": "do_not_repeat"
  }
}
```

AI 在 overview 阶段只关注：

- 明显混入播放器/桌面/黑屏。
- 明显截到半个页面。
- 某页信息量与整个 deck 极端不一致。
- 明显顺序断裂。
- 疑似错误视频画面。

AI 不应在 overview 阶段重新逐页判断相邻重复。

---

# 29. `vidslide context`

`context` 是多模态 Agent 的主要局部视觉入口。

只接受明确目标：

```bash
vidslide context lecture01.vidslide --flag f_01KA
```

程序根据 flag 自动决定需要构造什么上下文。

例如 LOW_CONTENT：

```text
ordinal 35 | 36 | [37] | 38 | 39
```

例如 POSSIBLE_ANIMATION_INTERMEDIATE：

```text
t-1.0 | t-0.5 | saved | t+0.5 | t+1.0 | later-stable
```

返回：

```json
{
  "command": "context",
  "status": "ok",
  "flag_id": "f_01KA",
  "context_type": "video_temporal",
  "artifacts": [
    {
      "path": "review/context/f_01KA.jpg"
    }
  ],
  "allowed_conclusions": [
    "accept",
    "replace_candidate",
    "request_recover",
    "unresolved"
  ]
}
```

Agent 不应该自己进入 assets 文件夹随意选图。

---

# 30. `vidslide recover`

Agent 不应在视频中漫无目的搜索漏页。

recover 必须由明确 flag 或明确相邻资产触发。

优先：

```bash
vidslide recover lecture01.vidslide --flag f_01KB
```

系统从 flag 得到：

```text
left_asset
right_asset
left_source_time
right_source_time
```

在该窗口内进行局部高密度扫描。

第一版建议：

```text
base sampling = 0.25 s
```

可以根据窗口大小自适应，但不得退化成全视频扫描。

局部流程：

```text
dense sampling
   ↓
stable frame grouping
   ↓
candidate clustering
   ↓
obvious duplicates removal
   ↓
write immutable candidate assets
```

输出：

```json
{
  "command": "recover",
  "status": "ok",
  "flag_id": "f_01KB",
  "candidates": [
    {
      "candidate_id": "c_01KA",
      "source_time_seconds": 1902.3,
      "path": "candidates/c_01KA.jpg"
    },
    {
      "candidate_id": "c_01KB",
      "source_time_seconds": 1931.8,
      "path": "candidates/c_01KB.jpg"
    }
  ],
  "next_actions": [
    {
      "command": "context",
      "candidate_ids": ["c_01KA","c_01KB"]
    }
  ]
}
```

AI 再判断候选是否是真正遗漏的 PPT。

---

# 31. Candidate 也是不可变资产

recover 产生的 candidate 不要直接写进最终 sequence。

candidate 有自己的 provenance：

```json
{
  "candidate_id": "c_01KA",
  "path": "candidates/c_01KA.jpg",
  "source_frame": 47558,
  "source_time_seconds": 1902.3,
  "time_basis": "fps_derived",
  "created_by": "recover",
  "trigger_flag": "f_01KB"
}
```

只有 `resolve insert` 后才晋升为 sequence 中的 slide asset。

可以：

- 复制为新的 `s_*` asset；或
- 在资产模型中保留相同 immutable blob，创建新的 slide record。

第一版优先采用逻辑简单、审计清楚的方案。

---

# 32. `vidslide resolve`

AI 不允许自由修改文件目录。

第一版只允许：

```text
accept_flag
replace_asset
insert_candidate
remove_from_sequence
mark_unresolved
```

不再使用 `needs-human`。

`unresolved` 的含义：

> 当前证据不足，CLI 不执行破坏性动作；由上层 Agent 决定扩大 recover、改变审查策略、终止任务或显式 force export。

推荐使用 JSON action，避免复杂命令行 positional 参数：

```bash
vidslide resolve lecture01.vidslide \
  --action-json resolve.json
```

`resolve.json`：

```json
{
  "action": "insert_candidate",
  "flag_id": "f_01KB",
  "candidate_id": "c_01KA",
  "after_asset_id": "s_01KX",
  "reason": "recovered_missing_slide",
  "actor": {
    "type": "agent",
    "name": "codex"
  }
}
```

执行前必须校验：

- flag 仍然 open。
- candidate 存在。
- referenced asset 仍在当前 sequence。
- manifest revision 与 action 生成时一致（如 action 提供 expected_revision）。

成功后：

```text
append event
   ↓
atomic update manifest
   ↓
flag resolved / superseded
   ↓
qa.status = DIRTY
```

之后必须重新 audit。

---

# 33. Replace 的正确语义

不要覆盖旧图片。

错误：

```text
assets/s_A.jpg ← 新帧覆盖旧帧
```

正确：

```text
old = s_A
new = s_B

sequence:
[..., s_A, ...]
       ↓
[..., s_B, ...]
```

事件：

```json
{
  "type": "SEQUENCE_CHANGED",
  "action": "replace_asset",
  "old_asset_id": "s_A",
  "new_asset_id": "s_B",
  "flag_id": "f_01K...",
  "reason": "animation_intermediate"
}
```

旧 asset 仍然保留，可以完整回退。

---

# 34. Remove 的正确语义

`remove_from_sequence` 只移除逻辑引用，不删除原始 asset。

例如：

```text
sequence before = [s_A, s_B, s_C]
sequence after  = [s_A, s_C]
```

`s_B` 仍保留在 assets 中，并标记：

```json
{
  "sequence_status": "removed",
  "removed_by_action": "a_01K..."
}
```

这样可以回退。

---

# 35. QA Flag 生命周期

建议：

```text
OPEN
  ↓
UNDER_REVIEW
  ↓
RESOLVED
```

或者：

```text
OPEN
  ↓
UNRESOLVED
```

任何 sequence 变化后：

```text
qa.status = DIRTY
```

旧 audit 的 flag 不一定继续有效。

重新 audit 后：

- 仍成立的异常创建/保留新的有效 flag。
- 已不存在的异常被标记 superseded / cleared。

不要假设旧 ordinal 永久稳定。

---

# 36. QA Gate

状态判定：

```text
open blocking flags = 0
AND latest audit applies to current manifest revision
AND overview policy satisfied
        ↓
QA_PASS
```

否则：

```text
REVIEW_REQUIRED
```

默认 `export` 只允许：

```text
state = READY_TO_EXPORT
qa.status = PASS
```

---

# 37. `vidslide export`

示例：

```bash
vidslide export lecture01.vidslide --format pdf
```

导出顺序必须严格读取 manifest：

```text
sequence
  ↓
asset paths
  ↓
exporter
```

不能通过 `sorted(os.listdir(...))` 推断页序。

未通过 QA：

```json
{
  "status": "error",
  "error": {
    "code": "UNRESOLVED_QA_FLAGS"
  }
}
```

允许显式：

```bash
vidslide export lecture01.vidslide --format pdf --force
```

但必须写入：

```json
{
  "qa_bypassed": true,
  "bypass_reason": "force_export",
  "manifest_revision": 12
}
```

并追加 `FORCE_EXPORT` event。

---

# 38. 导出器要求

新的 exporter 可以重构，不受旧 `exporter.py` 文件实现约束。

要求：

- 支持 PDF。
- 支持 PPTX。
- 支持 ZIP images。
- 对空 sequence 返回结构化错误。
- 对缺失 asset 返回结构化错误。
- 尽量避免一次性把所有大图同时常驻内存。
- 导出文件先写临时文件，再 atomic rename 到最终文件名。
- 导出结果计算 sha256。
- export artifact 写入 manifest / events。

---

# 39. `vidslide run`

`run` 是 Agent 的默认一站式入口，但它不应擅自调用多模态模型。

```bash
vidslide run lecture01.mp4 --format pdf
```

推荐自动流程：

```text
probe
  ↓
extract
  ↓
audit
  ↓
overview generation
  ↓
if deterministic flags == 0:
    stop at READY_FOR_OVERVIEW_REVIEW
else:
    stop at REVIEW_REQUIRED
```

这里有两种部署模式。

### 模式 A：CLI 不知道 AI

CLI 只生成工具输出，由上层 Agent 自己读取 overview/context 并调用 resolve。

推荐作为第一版。

### 模式 B：未来 Agent adapter

上层 adapter 可以：

```text
run
  ↓
读取 next_actions
  ↓
多模态 review
  ↓
resolve
  ↓
audit again
  ↓
export
```

CLI core 本身仍不绑定任何模型 API。

---

# 40. Overview Gate

因为 deterministic QA 可能 false negative，不能简单使用：

```text
flags == 0
→ 直接 export
```

修订版要求：

```text
flags == 0
→ overview ready
→ 上层多模态 Agent 做一次 deck-level sanity review
→ 如果无新增问题，标记 overview accepted
→ QA_PASS
```

这不是逐页高分辨率审阅。

一个 80 页 deck 可以压缩成 5 张 4×4 contact sheet，让模型快速确认整体异常。

如果 Agent 从 overview 发现问题，应创建新的 review request，再调用 `context` / `recover`。

---

# 41. Overview 审查结果记录

上层 Agent 对 overview 的结果必须回写，例如：

```bash
vidslide resolve lecture01.vidslide --action-json overview-accept.json
```

```json
{
  "action": "accept_overview",
  "manifest_revision": 8,
  "reviewed_sheets": [
    "overview_001.jpg",
    "overview_002.jpg"
  ],
  "result": "no_additional_anomaly",
  "actor": {
    "type": "agent",
    "name": "multimodal-agent"
  }
}
```

只有针对当前 manifest revision 的 overview accepted 才有效。

sequence 一旦变化，overview acceptance 失效，需要重新生成/复核。

---

# 42. Agent 权限边界

Agent 可以：

- 调用公开 CLI。
- 查看 CLI 返回的 review artifact。
- 对候选进行语义判断。
- 提交结构化 resolve action。
- 请求扩大 recover 窗口。
- 标记 unresolved。
- 在上层策略允许时显式 force export。

Agent 不可以：

- 直接编辑 manifest。
- 直接删除 assets。
- 直接覆盖 JPEG。
- 自己使用 ffmpeg 对完整视频漫无目的截图。
- 根据页码逻辑凭空生成 PPT。
- 在没有原视频 candidate 的情况下 insert missing page。
- 无视 state machine 直接 export。

---

# 43. AI 对不同问题的工具映射

用户可能给上层 Agent 的自然语言：

```text
“检查有没有漏页”
“看看是不是截到动画中间”
“这一页是不是不完整”
“前后页码是不是对不上”
“最终导出前整体看一遍”
```

Agent 应映射为：

```text
漏页
→ audit temporal/page-number signals
→ recover flagged interval
→ context candidates
→ resolve insert if evidence exists

动画中间帧
→ audit post-save stability
→ context temporal sheet
→ replace only with real source frame

空白/异常页
→ content anomaly
→ context neighbor sheet

错页/顺序异常
→ overview
→ context local sequence
→ recover source evidence if needed

最终整体看一遍
→ overview
→ do not repeat duplicate detection
```

自然语言 prompt 只决定关注方向，不替代工具搜索。

---

# 44. 最终状态机

建议：

```text
NEW
 │
 ▼
PROBED
 │
 ▼
EXTRACTING
 │
 ├── error → FAILED
 │
 ▼
EXTRACTED
 │
 ▼
AUDITING
 │
 ├───────────────┐
 │               │
 ▼               ▼
AUDIT_CLEAN   REVIEW_REQUIRED
 │               │
 ▼               ├─ context
OVERVIEW_READY    ├─ recover
 │               ├─ resolve
 ▼               └─ audit again
OVERVIEW_REVIEWED       │
 │                      │
 └──────────────┬───────┘
                ▼
              QA_PASS
                │
                ▼
        READY_TO_EXPORT
                │
                ▼
            EXPORTING
                │
                ▼
             EXPORTED
```

特殊状态：

```text
CANCELLED
INTERRUPTED
UNRESOLVED
FAILED
```

sequence 修改后必须：

```text
QA_PASS → DIRTY / REVIEW_REQUIRED
```

不能保留旧 QA 结论。

---

# 45. Manifest Revision

manifest 每次状态变更递增：

```json
{
  "revision": 12
}
```

resolve action 可以声明：

```json
{
  "expected_revision": 12
}
```

如果实际已经变为 13：

```text
MANIFEST_CONFLICT
```

这对多 Agent / retry / 自动恢复非常重要。

---

# 46. Atomicity 与事件提交语义

仅仅“先写 event 再写 manifest”仍可能在崩溃时产生一条看似已执行、实际上未提交的事件。

因此会改变状态的操作建议采用轻量 write-ahead 语义。

## 创建 asset

```text
write tmp image
→ flush / fsync
→ atomic rename to final asset path
→ append ASSET_CREATED
→ atomic manifest update
```

asset 文件本身已经存在时，即使 manifest 更新前崩溃，也可以由 `doctor` 识别为 orphan asset，而不会破坏已有 sequence。

## resolve / sequence mutation

推荐：

```text
validate action + expected_revision
→ prepare next manifest snapshot in memory
→ append ACTION_INTENT(action_id, from_revision, to_revision)
→ write manifest.tmp + fsync
→ atomic rename manifest.json
→ append ACTION_COMMITTED(action_id, to_revision)
```

manifest 同时记录：

```json
{
  "revision": 13,
  "last_action_id": "a_01K..."
}
```

如果崩溃发生在 `ACTION_INTENT` 与 `ACTION_COMMITTED` 之间，`doctor` 可以根据当前 manifest revision / `last_action_id` 判断该 action 是否已经实际提交。

第一版不一定要自动 repair，但必须能检测并返回：

```text
RUN_INTEGRITY_WARNING
```

绝不能把半完成事务静默当作成功。

---

# 47. `vidslide doctor`

用途：

- 检查运行环境。
- 检查视频解码能力。
- 检查磁盘空间。
- 检查写权限。
- 检查可选 OCR backend。
- 检查特定 run 的 manifest/files 一致性。

示例：

```bash
vidslide doctor
```

或：

```bash
vidslide doctor lecture01.vidslide
```

输出：

```json
{
  "status": "ok",
  "python": "3.12.7",
  "opencv": "4.11.0",
  "video_decode": true,
  "gpu_decode_available": true,
  "write_permission": true,
  "free_disk_gb": 183.2,
  "ocr": {
    "available": false
  },
  "run_integrity": {
    "checked": true,
    "manifest_valid": true,
    "missing_assets": 0,
    "orphan_assets": 0
  }
}
```

---

# 48. `vidslide capabilities`

让工具自描述，供 Agent 动态适配。

```bash
vidslide capabilities
```

示例：

```json
{
  "protocol_version": 1,
  "commands": [
    "probe",
    "extract",
    "audit",
    "overview",
    "context",
    "recover",
    "resolve",
    "export",
    "run",
    "doctor"
  ],
  "engines": [
    {
      "id": "legacy-v041",
      "recommended": true
    }
  ],
  "export_formats": ["pdf","pptx","zip"],
  "optional_capabilities": {
    "page_number_ocr": false
  }
}
```

未来 MCP / Python SDK / HTTP wrapper 都围绕同一 protocol adapter，而不是重新发明业务逻辑。

---

# 49. Config 文件

可以支持：

```bash
vidslide run lecture01.mp4 --config config.json
```

但配置文件只允许覆盖公开参数。

示例：

```json
{
  "engine": "legacy-v041",
  "decoder": "auto",
  "export_format": "pdf",
  "qa": {
    "overview": true,
    "page_number_ocr": "auto"
  }
}
```

不建议在第一版让 Agent 随意调：

```text
threshold
stable_need
sampling interval
history behavior
```

因为这会破坏 legacy baseline 的可复现性。

如果确实开放底层参数，manifest 必须完整记录，并将 profile 标记为 custom。

---

# 50. Decoder 策略

生产默认：

```text
decoder = auto
```

允许 GPU hardware decode 自动回退 CPU。

但是 golden regression 中建议：

```text
decoder = cpu
```

原因：

- 不同机器 GPU backend 不一致。
- CI 环境通常没有稳定硬解环境。
- 行为 baseline 应尽量减少硬件变量。

如果未来发现 GPU / CPU decode 在特定视频上导致不同 frame 输出，需要把 decoder 纳入 engine regression 维度。

---

# 51. Golden Regression Tests

这是整个项目的最高优先级质量保障之一。

不能只测试“命令能跑”。

至少比较：

- asset count
- perceptual hash
- source frame
- source time estimate
- image dimensions
- sequence
- representative thumbnails

例如：

```json
{
  "case": "animation-heavy",
  "expected_assets": 34,
  "assets": [
    {
      "ordinal": 1,
      "phash": "...",
      "source_frame": 0
    }
  ]
}
```

---

# 52. Golden 数据集分两层

## 52.1 Public/Synthetic CI corpus

放进仓库：

```text
tests/synthetic/
```

使用人工生成的短视频：

- normal-transition.mp4
- animation-heavy.mp4
- rapid-pages.mp4
- repeated-slide.mp4
- sparse-page.mp4
- long-static.mp4
- temporary-overlay.mp4
- short-lived-page.mp4

每个 10～60 秒，行为完全可控。

用于 GitHub Actions / 本地快速回归。

## 52.2 Private real-world corpus

不进 Git：

- 实际延河课堂 VGA 录播。
- 已人工确认的真实课程。
- 覆盖动画多、翻页快、长静态、复杂 footer 等情况。

用于发布前 regression。

这比直接把真实长课堂视频塞进仓库更合理。

---

# 53. CI Gate

对 legacy engine：

```text
synthetic golden
+ selected private golden
```

必须通过。

纯 CLI / manifest / protocol 改动应满足：

```text
legacy-v041 extracted sequence unchanged
```

如果核心行为变化：

```text
BASELINE_CHANGED
```

必须明确说明为什么变化，不能静默更新 golden。

---

# 54. QA Tests

QA 本身也需要 synthetic cases。

例如：

```text
animation-intermediate.mp4
→ 应触发 POSSIBLE_ANIMATION_INTERMEDIATE

long-static.mp4
→ 不应因为长 gap 自动判定 missing page

sparse-title-slide.mp4
→ 不应仅因白色区域大就判定 invalid

short-missing-page.mp4
→ recover 应找到候选
```

QA 测试关注：

- recall
- false positive
- candidate count
- recovery window correctness

不要只验证函数不报错。

---

# 55. 性能与资源约束

AI-only 不意味着可以无限消耗资源。

需要：

- overview thumbnail 尽量低分辨率。
- context 只生成与 flag 相关的局部图。
- recover 限制时间窗口。
- 不把整视频预先解码到内存。
- 不让 exporter 一次性加载全部超大图。
- worker 崩溃后主进程仍能返回结构化错误。

可以在 manifest 记录：

```text
elapsed_seconds
peak_memory_mb
worker_exit_code
```

但不是第一阶段强制。

---

# 56. 安全与路径约束

即使只有 Agent 使用，也必须防止错误参数破坏文件系统。

要求：

- run 内引用路径使用相对路径。
- resolve 不接受任意目标路径覆盖。
- candidate/asset path 由程序生成。
- export 输出目录做规范化。
- 不允许 `../` 穿越 run root。
- destructive action 只作用于当前 run 的逻辑状态。

“AI-only”不等于“可以信任所有输入”。

---

# 57. 推荐开发阶段

## Phase 0 — Baseline Lock

先完成：

- 固定 v0.4.1 commit。
- 确认 reliable profile 参数。
- 建立 synthetic golden corpus。
- 记录真实 baseline。

没有 baseline，不开始大规模重构。

---

## Phase 1 — Agent-native CLI Core

实现：

- Python package / CLI entrypoint
- `probe`
- `extract`
- strict JSONL protocol
- stable errors
- run directory
- immutable assets
- stable IDs
- manifest
- events
- worker isolation
- provenance

这一阶段不做 QA。

验收标准：

```text
同一 golden video
legacy CLI output
≈ v0.4.1 baseline
```

---

## Phase 2 — Reliable State & Export

实现：

- manifest revision
- atomic write
- resume validation
- `export`
- `doctor`
- `capabilities`
- `run`

重点是可靠状态管理，不是增加 AI 能力。

---

## Phase 3 — Deterministic QA

实现：

- content anomaly
- temporal gap
- post-save temporal stability
- audit report
- flag lifecycle
- QA dirty/pass 状态

页码 OCR 仍可以不做。

---

## Phase 4 — Multimodal Review Artifacts

实现：

- `overview`
- neighbor contact sheet
- temporal context sheet
- `context`
- review artifact metadata

AI 仍由上层 Agent 提供，不内嵌模型 API。

---

## Phase 5 — Recovery + Resolution

实现：

- local dense recover
- candidates
- structured resolve
- immutable replace / insert / remove
- overview acceptance
- action audit trail
- re-audit after mutation

---

## Phase 6 — Agent Adapter

CLI 稳定后再增加：

```text
MCP Server
Python SDK
HTTP wrapper
```

这些只是 adapter。

底层仍使用同一：

```text
protocol
state machine
manifest
engine
QA
resolver
```

---

# 58. 第一阶段最优先实现的五件事

如果现在开始开发，优先顺序：

## 1. Golden baseline

先锁住 v0.4.1 真实行为。

## 2. Worker-isolated CLI

先保证：

```text
stdout 永远不被 legacy print 污染
```

## 3. Immutable asset + stable ID

在任何 QA 之前先解决 identity。

## 4. Manifest + events

保证所有状态可恢复、可审计。

## 5. Provenance

确保每张 slide 能回到真实原视频证据。

完成这五项后，再做：

```text
audit
→ overview/context
→ recover
→ resolve
→ export gate
```

---

# 59. 推荐 Agent 行为

Agent 首次使用工具：

```text
vidslide capabilities
```

然后通常：

```text
vidslide run VIDEO
```

如果：

```text
state = REVIEW_REQUIRED
```

Agent 根据 `next_actions` 调用：

```text
context
recover
resolve
```

如果：

```text
state = AUDIT_CLEAN / OVERVIEW_READY
```

Agent 查看 overview，提交 overview acceptance。

最后：

```text
audit / gate
→ export
```

不要：

- 默认遍历整个 assets 目录。
- 默认重新检查 duplicate。
- 默认自己调用 ffmpeg 扫整个视频。
- 默认自行改变 threshold。
- 在没有 source evidence 的情况下补页。

---

# 60. 推荐最终成功路径

理想工作流不是：

```text
AI 从头到尾逐页看完整 PPT
```

而是：

```text
legacy-v041 提取
      ↓
immutable assets + provenance
      ↓
deterministic audit 扫描 100 页
      ↓
只产生少量 flags
      ↓
AI 精查 flags
      ↓
必要时局部 recover
      ↓
AI resolve
      ↓
重新 audit
      ↓
overview contact sheets
      ↓
AI 做 deck-level sanity check
      ↓
QA PASS
      ↓
manifest sequence → final PDF/PPTX
```

这样同时获得：

- v0.4.1 的可靠提取能力
- 不受 legacy `print()` 污染的机器协议
- 稳定 asset identity
- deterministic QA 的稳定性
- 多模态模型的语义理解能力
- 对 false negative 的 overview 兜底
- 较低视觉 token 成本
- 可复现
- 可审计
- 可回退
- 可恢复
- 可持续开发

---

# 61. 版本建议

第一版命名建议：

```text
v0.4.1-agent.1
```

可靠引擎固定：

```text
engine = legacy-v041
```

即使未来主项目发展到：

```text
v1.x
v2.x
```

仍应允许：

```bash
vidslide run input.mp4 --engine legacy-v041
```

并继续维持 golden regression。

---

# 62. 最终工程约束摘要

以下条款可以视为实现时的硬约束：

1. `legacy-v041` 提取行为不可静默变化。
2. legacy extractor 不得直接污染公开 stdout。
3. stdout 必须严格结构化。
4. CLI 命令不得一词多义；视频预检叫 `probe`，视觉上下文叫 `context`。
5. 原始 slide/candidate asset 不覆盖、不改名、不删除。
6. 页面顺序只由 manifest sequence 决定。
7. flag/action 必须引用 stable ID，而不是依赖页码身份。
8. manifest 使用 atomic write。
9. 操作历史写入 append-only `events.jsonl`。
10. `source_time = frame/fps` 必须标记为估算时间基准。
11. AI 不重新做 v0.4.1 已完成的 duplicate detection。
12. AI 不凭空补页；insert 必须来自 recover 的真实视频候选。
13. deterministic QA 之后仍保留低成本 overview 视觉兜底。
14. sequence 一旦修改，旧 QA PASS / overview acceptance 自动失效。
15. export 默认必须通过当前 manifest revision 的 QA Gate。
16. `needs-human` 不进入核心协议；证据不足统一使用 `unresolved`。
17. OCR 为 optional capability，不作为第一版阻塞项。
18. GUI、Flask、SSE、tkinter 不属于新的 Agent CLI 产品架构。
19. MCP/HTTP/SDK 必须晚于 CLI protocol 稳定。
20. 所有新 engine 必须与 `legacy-v041` 做回归比较。

---

# 63. 参考基线

项目：

```text
https://github.com/PWO-CHINA/VidSlide
```

可靠基线：

```text
v0.4.1
commit 66ec86808443509df86fbc8d82e5188d8eb90ffc
```

设计阶段应始终把 `legacy-v041` 视为 **长期可调用的可靠行为基线**，而不是等待被新算法替换的旧版本。

新的 Agent CLI 应围绕这个基线建立一个更严格的机器协议、不可变数据模型、QA 状态机和证据驱动的多模态审查工作流。
