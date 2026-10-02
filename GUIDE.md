# VidSlide Agent CLI 开发指南

## 1. 项目定位

### 这是什么

一个面向 AI Agent 的 VidSlide CLI 工具。

**主要使用者：**
- Claude Code
- Codex
- 本地多模态 Agent
- 自动化工作流

**不是：**
- 人类使用的 GUI 工具
- 新的视频理解算法研究
- 通用视频处理平台
- 企业级基础设施

### 核心目标

在保持 VidSlide v0.4.1 提取可靠性的基础上，提供：
- 稳定的命令行接口
- 清晰的状态管理
- 可追踪的操作历史
- 可自动化的工作流

---

## 2. 架构设计

### 总体流程

```
视频输入
  ↓
legacy-v041 提取（锁定可靠行为）
  ↓
不可变资产 (immutable assets)
  ↓
manifest + events（状态快照 + 操作历史）
  ↓
确定性 QA（程序检测异常）
  ↓
AI review context（只看异常候选）
  ↓
recover / resolve（基于证据恢复）
  ↓
export（受 QA Gate 约束）
```

### 模块职责

**Legacy Engine (legacy-v041)**
- 负责：原始 PPT 提取
- 原则：保持 v0.4.1 行为稳定，不改变提取算法

**CLI**
- 负责：Agent 调用接口、JSON 输出、错误状态
- 输出：stdout 严格 JSON/JSONL，stderr 仅诊断

**Manifest**
- 表示：当前状态快照
- 内容：资产列表、页面顺序、QA 状态

**Event Log**
- 记录：不可变操作历史
- 作用：审计、回退、问题定位

**QA**
- 负责：发现异常候选（确定性算法）
- 不负责：重新实现提取算法、重复 v0.4.1 已做的工作

**Review**
- 给 AI 提供：最小必要上下文
- 避免：AI 全量扫描视频或逐页审阅

---

## 3. 核心原则

### 3.1 可靠优先

**优先保证：**
- 行为稳定
- 状态清晰
- 错误可理解
- 修改可回退

**不要：**
- 为了"更完整"主动增加复杂功能
- 追求架构"优雅"而大规模重构
- 在没有实际需求时增加抽象层

### 3.2 锁定提取行为，而非整个文件

**需要锁定的：** legacy-v041 的输出行为
**不需要锁定的：** 具体实现文件

**允许修改：**
- 将 legacy extractor 放入独立 worker process
- 增加日志、provenance、状态管理
- 改进错误处理和外层包装

**不允许修改：**
- 抽帧间隔、scene threshold 语义
- stable frame 判断逻辑
- history pool 逻辑
- 重复页过滤规则
- ROI 计算方式

任何可能改变提取结果的修改，必须进入新的 experimental engine。

### 3.3 原始资产不可变

**错误做法：**
```
assets/slide_0022.jpg
assets/slide_0023.jpg  ← 插入新页时需要批量重命名
assets/slide_0024.jpg
```

**正确做法：**
```
assets/s_01KA.jpg  ← 稳定 ID，永不改名
assets/s_01KB.jpg
assets/s_01KC.jpg

manifest.json:
{
  "sequence": ["s_01KA", "s_01KB", "s_01KC"]  ← 页面顺序独立管理
}
```

- 原始提取资产一旦写入，不覆盖、不改名、不删除
- 插入、替换、删除只修改 manifest 中的逻辑顺序
- 所有操作追加到 events.jsonl

### 3.4 Snapshot + Event Log

```
manifest.json  = 现在是什么状态
events.jsonl   = 为什么变成这个状态
```

**manifest 原子写入：**
```
manifest.json.tmp
  ↓
flush / fsync
  ↓
atomic rename
  ↓
manifest.json
```

避免 Agent/系统中断时留下半个 JSON。

### 3.5 程序负责搜索，AI 负责判断

**程序负责：**
- 扫描全部提取结果
- 发现异常候选
- 保存证据
- 管理状态

**AI 负责：**
- 少量视觉语义判断
- 根据证据做决策

**不要让 AI：**
- 全量扫描视频
- 逐页审阅 PPT
- 重复 v0.4.1 已完成的重复页检测
- 凭空生成或补充页面

### 3.6 避免过度工程化

除非当前需求明确要求，否则不要引入：
- 数据库
- 消息队列
- HTTP 服务
- 复杂插件系统
- 企业级部署架构
- 过度抽象层
- 大规模测试体系

---

## 4. 关键决策

### ADR-001: 以 legacy-v041 作为可靠提取基线

**决定：** 锁定 v0.4.1 (commit 66ec86808443509df86fbc8d82e5188d8eb90ffc) 的提取行为

**原因：**
- v0.4.1 是当前真实使用场景中的可靠基线
- 提取算法可靠性优先于新特性

**影响：**
- CLI 工程改进不能混入算法变化
- 软件工程升级与提取算法升级必须分离
- 任何新算法必须作为独立 engine 与 legacy-v041 对照验证

### ADR-002: 原始资产不可变

**决定：** 提取的资产文件一旦写入，不覆盖、不改名、不删除

**原因：**
- 需要支持回退和审计
- 避免 ID 漂移导致的引用失效
- 保证 provenance 可追溯

**影响：**
- 页面顺序由 manifest sequence 管理
- replace/insert/remove 只修改逻辑引用
- 需要设计稳定的 ID 系统

### ADR-003: 确定性程序优先，AI 辅助判断

**决定：** 确定性算法负责搜索异常，AI 只查看少量候选

**原因：**
- 程序更稳定、更可复现
- 降低 AI 成本
- 避免 AI 随意性影响结果一致性

**影响：**
- 需要设计 deterministic QA 系统
- AI 不应绕过程序直接扫描视频或修改文件
- review context 由程序生成，AI 不自由探索

### ADR-004: 保持工程规模克制

**决定：** 项目保持简单，避免过度工程化

**原因：**
- 当前目标是个人 AI 工具，而不是商业平台
- 复杂度会增加维护成本
- 简单系统更容易理解和调试

**影响：**
- 第一版不实现数据库、消息队列等重型组件
- 功能按需添加，不提前设计未来系统
- 测试围绕风险，不追求覆盖率

---

## 5. CLI 设计概要

### 核心命令（第一版）

```bash
vidslide probe VIDEO           # 检查视频可读性
vidslide extract VIDEO         # 提取 PPT
vidslide audit RUN             # 确定性 QA 检查
vidslide overview RUN          # 生成全局预览
vidslide context RUN --flag ID # 生成异常上下文
vidslide recover RUN --flag ID # 局部恢复候选
vidslide resolve RUN --action  # 应用决策
vidslide export RUN            # 导出最终结果
vidslide run VIDEO             # 一站式执行

vidslide doctor                # 环境检查
vidslide capabilities          # 能力自描述
```

### 输出协议

**stdout：** 严格 JSON/JSONL
```jsonl
{"protocol_version":1,"type":"start","command":"extract","run_id":"01K..."}
{"protocol_version":1,"type":"progress","progress":12.4,"slides":5}
{"protocol_version":1,"type":"result","status":"ok","state":"EXTRACTED"}
```

**stderr：** 仅诊断信息，不包含业务状态

### Run 目录结构

```
lecture01.vidslide/
├── manifest.json          # 状态快照
├── events.jsonl          # 操作历史
├── assets/               # 不可变提取资产
│   ├── s_01KA.jpg
│   └── s_01KB.jpg
├── candidates/           # 恢复候选
│   └── c_01KA.jpg
├── review/              # AI 审查上下文
│   ├── overview/
│   └── context/
├── qa/                  # QA 报告
│   └── audit.json
└── logs/                # 诊断日志
    ├── cli.log
    └── legacy-worker.log
```

---

## 6. 开发工作流

### 开始开发前

1. 阅读本文档（GUIDE.md）
2. 阅读 AGENTS.md（Agent 行为约束）
3. 查看 CURRENT_TASK.md（当前阶段任务）

### 修改前考虑

1. 这是当前真实需求吗？
2. 是否可以用更简单方式解决？
3. 是否会增加长期维护成本？
4. 是否破坏已有可靠行为？

### 测试策略

**测试目标：** 保护关键行为，不追求覆盖率

**优先测试：**
- CLI 输出协议
- manifest 正确性
- 状态转换
- 核心流程回归（golden tests）

**不需要测试：**
- 简单包装函数
- 第三方库本身
- 没有实际风险的代码路径

### 推荐开发阶段

**Phase 1: Baseline Lock**
- 固定 v0.4.1 commit
- 确认 reliable profile 参数
- 建立 golden test corpus

**Phase 2: Agent-native CLI Core**
- probe, extract 命令
- JSONL protocol
- run directory
- immutable assets
- stable IDs
- manifest + events
- worker isolation

**验收：** 同一 golden video，CLI 输出与 v0.4.1 baseline 一致

**Phase 3: State & Export**
- manifest revision
- atomic write
- export
- doctor, capabilities

**Phase 4: QA**
- deterministic audit
- flag lifecycle
- QA gate

**Phase 5: Review & Recovery**
- overview, context
- recover
- resolve
- re-audit

---

## 7. Agent 使用指南

### Agent 权限边界

**Agent 可以：**
- 调用公开 CLI 命令
- 查看 CLI 返回的 review artifact
- 对候选进行语义判断
- 提交结构化 resolve action

**Agent 不可以：**
- 直接编辑 manifest.json
- 直接删除或覆盖 assets
- 自己使用 ffmpeg 扫描整个视频
- 根据页码逻辑凭空生成 PPT
- 在没有原视频 candidate 的情况下插入页面

### 推荐工作流

```bash
# 1. 检查能力
vidslide capabilities

# 2. 执行提取和初步检查
vidslide run VIDEO

# 3. 如果 state = REVIEW_REQUIRED
vidslide context RUN --flag f_01K...  # 查看异常上下文
vidslide recover RUN --flag f_01K... # 恢复候选
vidslide resolve RUN --action-json resolve.json

# 4. 如果 state = OVERVIEW_READY
# 查看 overview，确认无额外异常
vidslide resolve RUN --action-json accept-overview.json

# 5. 导出
vidslide export RUN --format pdf
```

### 不要做的事

- 默认遍历整个 assets 目录
- 默认重新检查重复页（v0.4.1 已做）
- 默认自己调用 ffmpeg 扫整个视频
- 在没有 source evidence 的情况下补页
- 无视 state machine 直接 export

---

## 8. 参考信息

### v0.4.1 基线

**仓库：** https://github.com/PWO-CHINA/VidSlide  
**版本：** v0.4.1  
**Commit：** 66ec86808443509df86fbc8d82e5188d8eb90ffc  
**Engine ID：** legacy-v041

**锁定配置：**
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

### 关键约束

1. legacy-v041 提取行为不可静默变化
2. stdout 必须严格结构化（JSON/JSONL）
3. 原始 slide/candidate asset 不覆盖、不改名、不删除
4. 页面顺序只由 manifest sequence 决定
5. manifest 使用 atomic write
6. 操作历史写入 append-only events.jsonl
7. AI 不重新做 v0.4.1 已完成的 duplicate detection
8. AI 不凭空补页；insert 必须来自 recover 的真实视频候选
9. sequence 修改后，旧 QA 结论自动失效
10. export 默认必须通过 QA Gate

---

## 9. 与 v0.4.1 的关系

### 复用的部分

- **提取算法：** extractor.py 的核心逻辑
- **可靠行为：** scene change, stable frame, history pool, 重复页过滤

### 不复用的部分

- **GUI：** Flask, SSE, 浏览器交互
- **交互式：** tkinter 文件选择，Y/N prompt
- **会话模型：** 多会话管理，网页会话

### 新增的部分

- **CLI 协议：** JSON/JSONL 输出
- **状态管理：** manifest + events
- **稳定 ID：** 不依赖文件名编号
- **QA 系统：** 确定性异常检测
- **Review 工具：** overview, context, recover
- **原子操作：** atomic write, event log

### 推荐做法

```
从 v0.4.1 提取 legacy engine
      ↓
建立全新的 vidslide package
      ↓
CLI 直接调用内部 service / worker
```

旧 GUI 如果仍需保留，可继续在原产品中维护，与新的 Agent CLI 解耦。
