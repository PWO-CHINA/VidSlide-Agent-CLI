# 系统架构

## 总体流程

视频

↓

legacy-v041 提取

↓

不可变资产

↓

manifest + events

↓

确定性 QA

↓

AI review context

↓

recover / resolve

↓

export

## 模块职责

## Legacy Engine

负责： - 原始 PPT 提取

原则： 保持 v0.4.1 行为稳定。

## CLI

负责： - Agent 调用接口 - JSON/JSONL 输出 - 错误状态

## Manifest

表示当前状态。

## Event Log

记录为什么变成当前状态。

## QA

负责发现异常候选。

不负责重新实现提取算法。

## Review

给 AI 提供最小必要上下文。

避免 AI 全量扫描视频。
