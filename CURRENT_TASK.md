# CURRENT_TASK

## 当前开发阶段

**Phase 1: Baseline Lock + Agent-native CLI Core**

---

## 目标

建立 VidSlide Agent CLI 的基础：
1. 锁定 v0.4.1 可靠提取行为作为 baseline
2. 实现 Agent 友好的 CLI 接口
3. 建立不可变资产和状态管理机制

---

## 范围

### 做什么

**1. Baseline Lock**
- 固定 v0.4.1 (commit 66ec86808443509df86fbc8d82e5188d8eb90ffc) 行为
- 确认 reliable profile 参数
- 建立 golden test corpus（synthetic + 实际视频样本）
- 记录 baseline 行为作为回归对照

**2. CLI 核心命令**
- `vidslide probe VIDEO` - 检查视频可读性
- `vidslide extract VIDEO` - 执行提取
- `vidslide capabilities` - 能力自描述
- `vidslide doctor` - 环境检查

**3. 协议与输出**
- stdout 严格 JSONL 协议
- stderr 仅诊断信息
- 稳定错误码和错误名
- 结构化的 `next_actions` 建议

**4. 状态管理**
- Run 目录结构（manifest.json, events.jsonl, assets/, logs/）
- 不可变资产（stable ID，永不改名/覆盖/删除）
- manifest: 状态快照
- events: 不可变操作历史
- 原子写入机制

**5. Worker 隔离**
- Legacy extractor 运行在独立进程
- 捕获 legacy print() 输出到 logs
- 结构化 IPC（进度、资产、错误）
- stdout 不被 legacy 输出污染

**6. Provenance**
- 每个资产记录 source_frame
- 估算 source_time_seconds（标记为 fps_derived）
- 记录 time_basis 和 timestamp_accuracy

### 不做什么

**本阶段不实现：**
- QA 系统（Phase 4）
- overview / context / recover（Phase 5）
- resolve 和状态变更（Phase 5）
- export 命令（Phase 3）
- `run` 一站式命令（Phase 3）
- 任何改变 v0.4.1 提取算法的修改
- GUI、Flask、SSE、网页交互
- 数据库、消息队列、HTTP 服务

---

## 约束

### 不可改变的行为

**来自 v0.4.1 的提取行为：**
- 抽帧间隔
- scene threshold 语义
- stable frame 判断逻辑
- history pool 逻辑
- 重复页过滤规则
- ROI 计算方式
- 比较分辨率

**Profile 锁定为：**
```json
{
  "engine": "legacy-v041",
  "profile": "reliable",
  "parameters": {
    "threshold": 5.0,
    "enable_history": true,
    "max_history": 5,
    "use_roi": true,
    "fast_mode": true,
    "speed_mode": "fast"
  }
}
```

### 不应引入的复杂度

- 不引入数据库
- 不实现复杂配置系统
- 不过早抽象
- 不为未来功能预留复杂接口
- 不实现完整的 resume 机制（第一版只需 safe restart）

---

## 验收标准

### 功能验收

1. **Baseline 可复现**
   - 同一 golden video，CLI 输出与 v0.4.1 baseline 一致
   - asset count, perceptual hash, source_frame 匹配预期
   - golden tests 全部通过

2. **CLI 协议稳定**
   - stdout 严格 JSON/JSONL，无意外文本
   - 所有命令返回明确 status (ok/error)
   - 错误包含 code, message, retryable
   - next_actions 建议正确

3. **状态管理可靠**
   - manifest.json 原子写入
   - events.jsonl 只追加
   - 资产文件名稳定（ID 不变）
   - 中断后 run 目录完整可读

4. **Worker 隔离成功**
   - legacy print() 不污染 stdout
   - legacy 崩溃时主进程返回结构化错误
   - 进度事件正确传递

5. **Provenance 完整**
   - 每个 asset 有 source_frame
   - 每个 asset 有 source_time_seconds（标记为估算）
   - manifest 记录 video metadata（fps, duration 等）

### 工程验收

- 代码风格一致
- 关键路径有单元测试
- Golden regression tests 建立
- 错误情况有测试覆盖
- 文档更新（如果 API 确定）

### 不要求的验收标准

- 测试覆盖率数字
- 性能基准测试
- 完整的用户文档
- 复杂的 CI/CD pipeline

---

## 推荐开发顺序

### Step 1: 项目结构和基础
- 建立 `vidslide/` package
- CLI entrypoint (`vidslide` 命令)
- `capabilities` 和 `doctor` 命令（不依赖提取）
- 基础错误定义和协议模型

### Step 2: Baseline Lock
- 从 v0.4.1 复制 legacy extractor
- 建立 golden test 框架
- 记录 baseline 行为
- 确认 reliable profile 参数

### Step 3: Run 目录和状态
- Run 目录结构
- Stable ID 生成（ULID / UUIDv7）
- manifest.json 原子写入
- events.jsonl 追加写入

### Step 4: Worker 隔离
- Legacy worker 进程包装
- stdout/stderr 捕获
- 结构化 IPC
- 进度事件转发

### Step 5: probe 命令
- 视频存在性检查
- ffprobe / OpenCV 基础信息
- smoke test decode
- JSONL 输出

### Step 6: extract 命令
- 调用 legacy worker
- 写入不可变 assets
- 更新 manifest
- 追加 events
- Provenance 记录

### Step 7: Golden Regression
- 完善 golden tests
- CI 集成
- 验证 baseline 一致性

---

## 注意事项

- **先有 baseline，再有重构** - 不要边改边测，容易漂移
- **简单优先** - 第一版能用即可，不追求完美
- **协议优先** - stdout 协议是 Agent 的核心接口
- **频繁验证** - 每个小步骤都跑 golden tests

---

## 完成标志

当以下都满足时，Phase 1 完成：

✅ Golden tests 全部通过  
✅ `vidslide extract VIDEO` 输出与 v0.4.1 baseline 一致  
✅ stdout 严格 JSON/JSONL，无污染  
✅ manifest + events 正确记录状态  
✅ 资产 ID 稳定，provenance 完整  
✅ Worker 隔离成功，legacy print 不泄漏

**下一阶段：** Phase 2 - Reliable State & Export
