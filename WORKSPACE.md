# VidSlide Agent CLI 工作区结构

> 最后更新：2026-10-02

---

## 工作区概览

```
VidSlide_Agent_Workspace_Docs_CN/
├── AGENTS.md              # Agent 行为约束和项目定位
├── GUIDE.md               # 完整开发指南（架构、原则、工作流）
├── CURRENT_TASK.md        # 当前阶段任务（Phase 1）
├── PROGRESS.md            # 开发进度跟踪
├── LICENSE                # MIT 许可证
│
├── src/                   # 源代码
│   └── vidslide/
│       ├── engine/
│       │   └── legacy_v041_original.py  # 原始提取引擎（需重构）
│       └── export/
│           └── packager.py              # 导出模块（PDF/PPTX/ZIP）
│
├── docs/                  # 文档
│   └── reference/
│       └── original-gui/
│           ├── README.md           # 原 GUI 用户指南
│           ├── DEVNOTES.md         # 原开发笔记
│           ├── requirements.txt    # 原依赖清单
│           └── version.txt         # 版本元数据
│
└── archive/               # 已归档文档
    ├── DESIGN_SPEC.md     # 过度详细的设计规范（2860行）
    └── docs/              # 旧的分散文档
```

---

## 文件说明

### 核心文档（必读）

**[AGENTS.md](AGENTS.md)** - Agent 入口
- 项目定位：面向 AI Agent 的 CLI 工具
- 核心原则：可靠优先、避免过度工程化
- Agent 行为限制
- 快速参考

**[GUIDE.md](GUIDE.md)** - 开发指南
- 架构设计（总体流程、模块职责）
- 核心原则（不可变资产、状态管理、程序/AI 分工）
- 关键决策（ADR-001 至 ADR-004）
- CLI 设计概要
- 开发工作流和测试策略
- Agent 使用指南

**[CURRENT_TASK.md](CURRENT_TASK.md)** - 当前任务
- Phase 1 目标：Baseline Lock + CLI Core
- 明确的范围（做什么 / 不做什么）
- 验收标准
- 推荐开发顺序

**[PROGRESS.md](PROGRESS.md)** - 进度跟踪
- 已完成任务记录
- 当前进行中的工作
- 遇到的问题和决策

---

## 源代码

### src/vidslide/engine/

**legacy_v041_original.py** (13KB, 310行)
- 从工程区复制的原始提取引擎
- 包含：scene detection, stable frame, history pool
- **状态：** 需要重构，移除 Flask 依赖
- **用途：** 理解算法逻辑，作为 legacy-v041 引擎的基础

### src/vidslide/export/

**packager.py** (4.4KB, 147行)
- 从工程区复制的导出模块
- 支持：PDF, PPTX, ZIP
- **状态：** 基本可用，已经模块化
- **用途：** 可直接集成到 CLI，略微调整接口

---

## 参考文档

### docs/reference/original-gui/

从工程区复制的原始 GUI 项目文档：

**README.md** (20KB)
- VidSlide v0.4.1 GUI 用户指南
- 功能特性、使用方法、技术说明

**DEVNOTES.md** (16KB)
- GUI 项目的开发笔记
- 架构决策、技术细节、已知问题

**requirements.txt**
- Flask, OpenCV, numpy, pillow, python-pptx, psutil, pyinstaller

**version.txt**
- EXE 版本元数据格式

---

## 归档文档

### archive/

**DESIGN_SPEC.md** (52KB, 2860行)
- 过度详细的设计规范
- 包含62条工程约束、完整 CLI 协议设计
- **归档原因：** 过早约束实现细节，与"避免过度工程化"原则冲突

**archive/docs/**
- 旧的分散文档（已整合进 GUIDE.md）
- PRODUCT_SPEC.md, ARCHITECTURE.md, DECISIONS.md, DEVELOPMENT_GUIDE.md, VIDSLIDE_V041_REFERENCE.md

---

## 工程区（未移动到工作区）

**位置：** `../工程区/`

**保留内容：**
- `.git/` (232MB) - 完整版本历史
- `venv/` (203MB) - Python 虚拟环境
- `app.py` - Flask 服务器（GUI 专用）
- `templates/`, `static/` - Web UI 资源
- `build.bat`, `start_dev.bat` - GUI 构建和启动脚本

**已从工程区删除（已复制到工作区）：**
- README.md, DEVNOTES.md, LICENSE, version.txt
- extractor.py, exporter.py (已复制为源代码)

---

## v0.4.1 基线信息

**仓库：** https://github.com/PWO-CHINA/VidSlide  
**版本：** v0.4.1  
**Commit：** 66ec86808443509df86fbc8d82e5188d8eb90ffc  
**分支：** dev/0.4.3（工程区当前）  
**Engine ID：** legacy-v041

**可靠配置：**
```json
{
  "threshold": 5.0,
  "enable_history": true,
  "max_history": 5,
  "use_roi": true,
  "fast_mode": true,
  "speed_mode": "fast"
}
```

---

## 当前状态

**阶段：** Phase 1 - Baseline Lock + CLI Core  
**进度：** 项目结构建立，文档就绪，源码已复制  
**下一步：** 
1. 建立 Python package 基础（`pyproject.toml`, `__init__.py`）
2. 提取 CLI 所需依赖
3. 重构 `legacy_v041_original.py` 移除 Flask 依赖
4. 实现 `capabilities` 和 `doctor` 命令

---

## 开发建议

1. **阅读顺序：** AGENTS.md → GUIDE.md → CURRENT_TASK.md → PROGRESS.md
2. **修改前检查：** 是否符合核心原则，是否过度工程化
3. **记录进度：** 每完成一个任务，更新 PROGRESS.md
4. **参考原始：** docs/reference/original-gui/ 了解 v0.4.1 行为
5. **保持简单：** 第一版能用即可，不追求完美

---

## 联系与支持

**License：** MIT  
**目标用户：** AI Agent (Claude Code, Codex, 本地多模态 Agent)  
**不适用于：** 人类 GUI 用户
