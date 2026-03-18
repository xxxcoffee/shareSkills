# eChecker Config 模块

`echecker.config` 是 eChecker 项目的配置管理包，负责加载、解析和管理中央配置文件（echecker.yaml）以及规则文件。

## 主要类和函数

### 数据模型 (schema.py)

#### `RuleFile`
规则文件引用数据类。

| 属性 | 类型 | 说明 |
|------|------|------|
| `path` | `Path` | 规则文件路径 |
| `is_global` | `bool` | 是否为全局规则文件 |

#### `ProjectConfig`
项目配置数据类。

| 属性 | 类型 | 说明 |
|------|------|------|
| `name` | `str` | 项目名称 |
| `excel` | `Path` | Excel 文件路径 |
| `rules` | `Dict[str, str]` | 规则文件映射 |

方法：
- `get_global_rule()` → `Optional[Path]`: 获取全局规则文件路径
- `get_local_rule()` → `Optional[Path]`: 获取本地规则文件路径

#### `CentralConfig`
中央配置数据类，管理多个项目。

| 属性 | 类型 | 说明 |
|------|------|------|
| `projects` | `List[ProjectConfig]` | 项目配置列表 |

方法：
- `get_project(name: str)` → `Optional[ProjectConfig]`: 根据名称获取项目配置
- `list_projects()` → `List[str]`: 获取所有项目名称列表

### 配置管理器 (manager.py)

#### `ConfigManager`
配置管理器，负责加载和管理中央配置及规则文件。

**主要方法**

| 方法 | 返回值 | 说明 |
|------|--------|------|
| `load_central_config(path)` | `CentralConfig` | 加载中央配置文件 (echecker.yaml) |
| `resolve_rules(excel_path)` | `List[RuleFile]` | 解析与指定 Excel 相关的所有规则文件 |
| `merge_rules(global_rules, local_rules)` | `List[RuleDict]` | 合并全局规则和本地规则 |
| `get_config()` | `Optional[CentralConfig]` | 获取已加载的配置 |

## 与其他模块的关系

```
┌─────────────────────────────────────────────────────────┐
│                    echecker.config                       │
├─────────────────────────────────────────────────────────┤
│  schema.py          │  manager.py                        │
│  - RuleFile         │  - ConfigManager                   │
│  - ProjectConfig    │    - load_central_config()         │
│  - CentralConfig    │    - resolve_rules()               │
│                     │    - merge_rules()                 │
└──────────┬──────────┴────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────┐
│                    被使用于                              │
├─────────────────────────────────────────────────────────┤
│  echecker.core.engine_v3    V3 Pipeline引擎初始化       │
│  CLI 入口                   命令行工具加载配置          │
└─────────────────────────────────────────────────────────┘
```

### 配置加载流程

```
echecker.yaml
    │
    ▼
ConfigManager.load_central_config()
    │
    ▼
CentralConfig (包含多个 ProjectConfig)
    │
    ├── resolve_rules(excel_path) ──► List[RuleFile]
    │
    └── 规则引擎使用规则文件进行验证
```

### 典型 echecker.yaml 配置格式

```yaml
projects:
  - name: "Project1"
    excel: "data/project1.xlsx"
    rules:
      global: "rules/global_rules.yaml"
      local: "rules/project1_rules.yaml"
```

## 注意事项

1. **路径处理**: `ConfigManager` 会自动处理相对路径，相对于 `base_path` 或当前工作目录解析
2. **规则合并**: 合并规则时，本地规则不会覆盖全局规则中相同 `id` 的规则
3. **类型安全**: 使用 `dataclass` 和类型注解确保配置数据的类型安全
4. **错误处理**: 配置文件不存在时会抛出 `FileNotFoundError`
