# Legacy Engine 集成计划（已更新）

> **重要发现：** 经过详细分析，legacy_v041_original.py **不需要任何修改**。
> 
> 之前的假设（Flask 依赖、需要重构）是错误的。引擎已经使用纯回调接口。

---

## 关键发现

**subagent 分析结果 (2026-10-02):**

1. ✅ **无 Flask 依赖** - 引擎只有 cv2, numpy, psutil（可选）
2. ✅ **纯回调接口** - `on_progress(saved, pct, msg, eta, elapsed, frame)` 和 `should_cancel()`
3. ✅ **与 v0.4.1 完全一致** - CRLF 正规化后与 commit 66ec868 字节相同
4. ✅ **print() 通过 stdout 重定向隔离** - 无需修改引擎

**SHA256 (LF-normalized):**
```
b558496290b9dd4af4e277af8736a274200d30d72a99c3393e46dfc429bbc3b4
```

---

## 正确的集成方法

### 不要做

❌ 创建 legacy_v041.py 副本  
❌ 修改引擎代码  
❌ 移除 print() 语句  
❌ 添加 message_queue 参数

### 应该做

✅ 保持引擎文件不变（字节一致）  
✅ 在 worker.py 中编写适配器  
✅ 使用 fd 级 stdout/stderr 重定向  
✅ 实现回调转消息队列

---

## 函数签名（实际）

```python
def extract_slides(
    video_path,           # 视频路径
    output_dir,          # 输出目录（必须已存在）
    threshold=5.0,       # 场景变化阈值
    enable_history=False,  # ⚠️ 默认 False（profile 要求 True）
    max_history=5,
    use_roi=True,
    fast_mode=True,
    use_gpu=True,        # ⚠️ profile 用 decoder: auto
    speed_mode='eco',    # ⚠️ 默认 eco（profile 要求 fast）
    on_progress=None,    # 回调：(saved, pct, msg, eta, elapsed, frame)
    should_cancel=None,  # 轮询：() -> bool（必须粘性）
    start_frame=0,       # resume only
    saved_offset=0       # resume only
):
    """返回: (status, message, saved)
    status: 'done' | 'cancelled' | 'error'
    """
```

**关键：** 必须显式传递所有参数，不能依赖默认值。

---

## 修改清单

### 1. worker.py - 引擎调用适配器 (~100 行)

```python
def _worker_process(video_path, output_dir, params, message_queue, log_file):
    # 1. fd 级重定向 stdout/stderr
    # 2. lazy import extract_slides
    # 3. 创建 on_progress 适配器（检测 SLIDE_SAVED）
    # 4. 创建粘性 cancel_event
    # 5. 参数映射（decoder → use_gpu, 白名单 speed_mode）
    # 6. 调用 extract_slides
    # 7. 映射返回值到消息
```

**风险点：**
- 参数映射错误会改变输出（中）
- on_progress 异常会中止提取（中）
- Windows spawn 下 fd 重定向（中）

### 2. extract.py - 消息处理完善 (~50 行)

```python
# 当前问题：while worker.is_alive() 可能过早退出
# 修复：drain 消息直到 DONE/ERROR/CANCELLED

while True:
    msg = worker.get_message(timeout=0.5)
    if msg:
        if msg["type"] == "SLIDE_SAVED":
            # manifest.add_asset(...)
            # events.append(ASSET_CREATED)
        elif msg["type"] == "DONE":
            break
        # ...
    elif not worker.is_alive():
        # worker 退出但没有终止消息 = crash
        raise WorkerCrashedError(...)
```

### 3. probe.py - pre-flight 检查 (~6 行)

```python
# 添加与 GUI 一致的检查
if fps <= 0 or frame_count < 10:
    raise ProbeFailedError("Invalid video: too short or invalid fps")
```

### 4. tests - 重写和 golden test (~150 行)

- 修复 test_worker.py（当前使用不存在的 /test/video.mp4）
- 创建 synthetic 测试视频（10fps, A-5s, fade-1s, B-5s, C-5s, A-5s, D-0.8s）
- Golden 测试：history on = 3 slides, history off = 4 slides
- 验证 provenance (source_frame)

---

## 实施步骤

### Step 1: 修改 worker.py (1-2 小时)

**优先级：高**

1. fd 级 stdout/stderr 重定向
2. lazy import extract_slides
3. on_progress 适配器（检测 saved 增加）
4. 粘性 cancel via mp.Event
5. 参数映射和验证
6. 返回值映射

### Step 2: 完善 extract.py (30 分钟)

**优先级：高**

1. 修复消息处理循环
2. SLIDE_SAVED → manifest.add_asset
3. 处理 CANCELLED 状态
4. 要求空 assets/ 目录

### Step 3: probe.py pre-flight (15 分钟)

**优先级：中**

添加 fps/frame_count 检查

### Step 4: 测试 (2-3 小时)

**优先级：高**

1. 创建 synthetic 视频
2. 端到端测试
3. Golden regression
4. 验证 provenance

---

## 决策点

### 1. decoder 设置

**问题：** manifest 有 `decoder: "auto"`，引擎有 `use_gpu: bool`

**决定：**
```python
use_gpu = (params.get("decoder", "auto") != "cpu")
# auto → True, cpu → False, gpu → True
```

### 2. speed_mode 白名单

**问题：** 引擎不验证，无效值变 eco

**决定：**
```python
speed_mode = params.get("speed_mode", "fast")
if speed_mode not in ("eco", "fast"):
    speed_mode = "fast"
# 禁止 turbo（不同算法）
```

### 3. 依赖版本

**问题：** pyproject.toml 无上限，不同 OpenCV 可能不同输出

**决定：**
- Golden test 记录 cv2.__version__
- 不强制 pin（允许升级）
- 如果 golden 失败，记录新版本

---

## 时间预估

- Step 1: worker.py - 1.5 小时
- Step 2: extract.py - 0.5 小时
- Step 3: probe.py - 0.25 小时
- Step 4: 测试 - 2 小时

**总计：** 4-5 小时

---

## 验收标准

### 必须满足

- ✅ 引擎文件字节一致（LF-normalized SHA256）
- ✅ extract 命令完整运行
- ✅ manifest.json 正确记录 assets
- ✅ provenance 正确（source_frame, source_time_seconds）
- ✅ stdout 严格 JSON（无 print() 泄漏）
- ✅ 错误处理完整

### 应该满足

- ✅ Golden test 通过（与预期 slide 数量一致）
- ✅ 支持取消（Ctrl-C）
- ✅ 处理损坏视频

### 可以延后

- ⏳ Resume 功能
- ⏳ GPU decode 验证
- ⏳ 性能优化

---

_更新时间：2026-10-02 20:45_  
_分析者：Sonnet subagent (193k tokens, 38 tool uses)_

---

## 分析 legacy_v041_original.py

### 核心函数

从 docs/reference/original-gui/DEVNOTES.md 了解：

```python
def extract_slides(
    video_path,
    output_folder,
    threshold=5.0,
    enable_history=True,
    max_history=5,
    use_roi=True,
    fast_mode=True,
    progress_callback=None  # Flask callback
):
    """主提取函数"""
```

### 需要移除的依赖

- Flask progress callback
- print() 输出
- 任何 GUI 相关导入

### 需要保留的核心逻辑

- scene change detection
- stable frame detection
- history pool
- 重复页过滤
- ROI 计算

---

## 重构策略

### 方案 A: 最小修改（推荐）

**步骤：**
1. 复制 legacy_v041_original.py → legacy_v041.py
2. 移除 Flask callback，替换为简单函数参数
3. 将 progress_callback 改为消息队列
4. 保持所有算法逻辑不变

**优点：**
- 最小化风险
- 容易验证行为一致性
- 快速完成

**示例：**
```python
def extract_slides(
    video_path,
    output_folder,
    threshold=5.0,
    enable_history=True,
    max_history=5,
    use_roi=True,
    fast_mode=True,
    message_queue=None  # 替代 progress_callback
):
    # 原有逻辑
    # 进度报告改为：
    if message_queue:
        message_queue.put({
            "type": "PROGRESS",
            "progress": progress_pct,
            "message": "Processing..."
        })
```

### 方案 B: 完全重构

不推荐，风险太大，可能改变提取行为。

---

## 实施步骤

### Step 1: 分析依赖 (30分钟)

```bash
# 读取 legacy_v041_original.py
# 识别所有外部依赖
# 确认 Flask 相关代码位置
```

### Step 2: 创建适配层 (1小时)

创建 `src/vidslide/engine/legacy_v041.py`:
- 复制原始代码
- 移除 Flask callback
- 添加 message_queue 参数
- 保持算法逻辑完全一致

### Step 3: 集成到 worker (1小时)

修改 `src/vidslide/worker.py`:
```python
def _worker_process(...):
    from vidslide.engine.legacy_v041 import extract_slides
    
    extract_slides(
        video_path=video_path,
        output_folder=output_dir,
        message_queue=message_queue,
        **params
    )
```

### Step 4: 测试验证 (1-2小时)

1. 单元测试：测试消息传递
2. 集成测试：完整提取流程
3. 对比验证：与 v0.4.1 GUI 输出对比

---

## 测试计划

### 单元测试

```python
def test_legacy_engine_without_video():
    """测试引擎可以导入和调用"""
    from vidslide.engine.legacy_v041 import extract_slides
    # 验证函数签名
```

### 集成测试

```bash
# 需要真实视频文件
./vidslide.sh extract test_video.mp4 --output test.vidslide

# 验证：
# 1. manifest.json 生成
# 2. assets/ 有图片
# 3. events.jsonl 记录完整
# 4. 无 stdout 污染
```

### Golden Test（关键）

```bash
# 使用相同视频
# 对比 GUI v0.4.1 和 CLI 输出
# 验证提取结果一致
```

---

## 风险控制

### 高风险点

1. **算法改变** - 可能无意中修改提取逻辑
   - 缓解：小步修改，频繁验证
   - 使用 git diff 检查每次改动

2. **依赖缺失** - 移除 Flask 后可能遗漏其他依赖
   - 缓解：先在隔离环境测试导入

3. **进度报告失效** - message_queue 可能阻塞或丢失
   - 缓解：添加超时和错误处理

### 回退策略

- 每个步骤 git commit
- 保留 legacy_v041_original.py 不动
- 如果失败，回退到 worker 模拟实现

---

## 验收标准

### 必须满足

- ✅ extract 命令可以运行
- ✅ 生成 manifest.json 和 events.jsonl
- ✅ assets/ 目录有提取图片
- ✅ stdout 严格 JSON，无 print() 污染
- ✅ 进度事件正确传递

### 应该满足

- ✅ 提取结果与 v0.4.1 GUI 一致
- ✅ 处理错误情况（视频打不开等）
- ✅ 支持 Ctrl-C 取消

### 可以延后

- ⏳ Resume 功能
- ⏳ 性能优化
- ⏳ GPU 硬解支持

---

## 时间预估

- Step 1: 分析依赖 - 30分钟
- Step 2: 创建适配层 - 1小时
- Step 3: 集成到 worker - 1小时
- Step 4: 测试验证 - 1-2小时

**总计：** 3.5-4.5 小时

---

## 下一步行动

**立即执行：**

1. 使用 subagent 分析 legacy_v041_original.py
   - 识别所有 Flask 依赖
   - 列出需要修改的位置
   - 评估风险

2. 创建 legacy_v041.py 适配层

3. 测试集成

**推荐使用 subagent：**
- 分析任务简单但繁琐
- 节省主 agent token
- 可以并行处理

---

_创建时间：2026-10-02 20:30_
