# ShareSkills

[English](./README.md) | 简体中文

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

可复用的 Claude Code Skills 集合，提升开发效率。

## Skills 概览

### ali-log

阿里云日志服务（SLS）查询工具，支持日志拉取、分析、查询构建器和 SQL 模板。

**功能特性：**
- 拉取原始日志 (pull_logs)
- 查询分析日志 (query_logs)
- 通过时间获取游标 (get_cursor)
- 查询构建器，便捷的查询语句构造
- SQL 分析构建器，支持链式调用
- 常用场景查询模板
- 完整的 SQL 函数参考手册

[查看详情](./skills/ali-log/)

## 安装方式

### 方式 1：克隆并复制

```bash
# 克隆仓库
git clone git@github.com:xxxcoffee/shareSkills.git

# 复制 skills 到 Claude Code skills 目录
cp -r shareSkills/skills/ali-log ~/.claude/skills/
```

### 方式 2：直接下载

```bash
# 创建 skills 目录（如果不存在）
mkdir -p ~/.claude/skills

# 下载并解压指定 skill
cd ~/.claude/skills
git clone --depth 1 --filter=blob:none --sparse git@github.com:xxxcoffee/shareSkills.git temp
cd temp
git sparse-checkout set skills/ali-log
cp -r skills/ali-log ../
cd ..
rm -rf temp
```

### 方式 3：使用 npx（即将推出）

```bash
# 安装所有 skills
npx shareskills install

# 安装指定 skill
npx shareskills install ali-log
```

## Skill 结构

```
~/.claude/skills/
└── ali-log/
    ├── SKILL.md              # Skill 文档
    ├── ali_log.py           # 核心实现
    ├── query_builder.py     # 查询/SQL 构建器
    ├── QUERY_REFERENCE.md   # 函数参考手册
    ├── README.md            # Skill 说明（英文）
    ├── README_CN.md         # Skill 说明（中文）
    └── requirements.txt     # 依赖项
```

## 开发指南

### 添加新 Skill

1. 在 `skills/` 目录下创建新目录
2. 添加 `SKILL.md` 定义 skill
3. 实现 skill 逻辑
4. 添加文档和示例
5. 更新主 README.md

### Skill 规范

- Skill 应该是自包含的
- 在 `SKILL.md` 中包含清晰的文档
- 提供使用示例
- 在 `requirements.txt` 中列出所有依赖
- 遵循现有代码风格

## 贡献指南

欢迎贡献！请随时提交 Pull Request。

1. Fork 本仓库
2. 创建你的功能分支 (`git checkout -b feature/amazing-skill`)
3. 提交你的更改 (`git commit -m '添加某个 amazing skill'`)
4. 推送到分支 (`git push origin feature/amazing-skill`)
5. 打开 Pull Request

## 开源协议

本项目采用 MIT 协议开源 - 查看 [LICENSE](./LICENSE) 文件了解详情。

## 技术支持

如果遇到问题或有疑问：

- 在 GitHub 上提交 Issue
- 查看具体 skill 的 README 了解使用详情
- 查看 QUERY_REFERENCE.md 了解 SQL 函数文档

## 致谢

- 为 [Claude Code](https://claude.ai/code) 构建
- 基于阿里云日志服务 SDK
- 灵感来自 Claude Code 社区