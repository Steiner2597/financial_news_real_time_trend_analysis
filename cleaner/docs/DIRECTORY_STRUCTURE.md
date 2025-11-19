# 清洗器目录结构

## 📁 完整目录树

```
cleaner/
│
├── 📂 event_driven/                           # 事件驱动模块（新）⭐
│   ├── 📄 __init__.py                         # 模块初始化
│   ├── 📄 cleaner.py                          # 主清洗器类 (250 行)
│   ├── 📄 redis_manager.py                    # Redis 连接管理 (130 行)
│   ├── 📄 notification_handler.py             # 消息通知处理 (150 行)
│   ├── 📄 cache_manager.py                    # ID 缓存管理 (120 行)
│   ├── 📄 signal_handler.py                   # 信号处理 (50 行)
│   ├── 📖 README.md                           # 使用说明
│   ├── 📖 ARCHITECTURE.md                     # 架构文档
│   └── 📖 REFACTOR_SUMMARY.md                 # 重构总结
│
├── 📄 data_cleaner_event_driven_v2.py         # 新入口文件 ⭐
├── 📄 data_cleaner_module.py                  # 核心清洗逻辑
├── 📄 test_event_driven_modules.py            # 模块测试 ⭐
│
├── 🔧 config_processing.yaml                  # 配置文件
├── 🔧 config_processing_dl.yaml               # 深度学习配置
│
├── 🚀 start_cleaner.bat                       # 原启动脚本
├── 🚀 start_cleaner_with_choice.bat           # 新启动脚本 ⭐
│
├── 🧹 clear_id_cache.py                       # 清空缓存工具
├── 🧹 manage_id_cache.py                      # 缓存管理工具
├── 🧹 trigger_cleaner_test.py                 # 触发测试工具
│
├── 📂 logs/                                   # 日志目录
│   └── event_driven_cleaner.log               # 事件驱动日志
│
├── 📂 output/                                 # 输出目录
│   ├── cleaned_2025-10-28.jsonl
│   └── cleaned_2025-11-01.jsonl
│
└── 📂 samples/                                # 样例目录
    ├── sample_clean.jsonl
    └── sample_raw.jsonl
```

## 🎯 文件说明

### 核心模块（event_driven/）

| 文件 | 大小 | 职责 | 依赖 |
|-----|------|------|------|
| `__init__.py` | 7 行 | 模块初始化，导出主类 | - |
| `cleaner.py` | 250 行 | 主控制器，协调各模块 | 所有其他模块 |
| `redis_manager.py` | 130 行 | Redis 连接生命周期管理 | redis |
| `notification_handler.py` | 150 行 | 消息解析、发送、日志 | redis, json |
| `cache_manager.py` | 120 行 | 缓存状态查询、清理 | redis, time |
| `signal_handler.py` | 50 行 | 信号捕获、回调触发 | signal |

### 文档文件

| 文件 | 内容 |
|-----|------|
| `README.md` | 模块使用说明、API 文档、迁移指南 |
| `ARCHITECTURE.md` | 架构图、数据流、类关系、设计思想 |
| `REFACTOR_SUMMARY.md` | 重构总结、改进亮点、性能对比 |

### 入口文件

| 文件 | 说明 | 推荐 |
|-----|------|------|
| `data_cleaner_event_driven.py` | 原版本（460 行单文件） | 兼容旧系统 |
| `data_cleaner_event_driven_v2.py` | 新版本（使用模块化） | ⭐ 推荐使用 |

### 工具脚本

| 文件 | 功能 |
|-----|------|
| `test_event_driven_modules.py` | 测试所有模块是否正常工作 |
| `clear_id_cache.py` | 清空 Redis ID 缓存 |
| `manage_id_cache.py` | 管理和分析 ID 缓存 |
| `trigger_cleaner_test.py` | 手动触发清洗任务 |

### 启动脚本

| 文件 | 功能 |
|-----|------|
| `start_cleaner.bat` | 启动原版本清洗器 |
| `start_cleaner_with_choice.bat` | 选择运行版本（新/旧/测试） ⭐ |

## 🔀 文件关系图

```
start_cleaner_with_choice.bat
         │
         ├─→ [1] data_cleaner_event_driven_v2.py
         │            ↓
         │   event_driven/cleaner.py (主)
         │            ↓
         │   ┌────────┴────────┐
         │   ▼                 ▼
         │   redis_manager     notification_handler
         │   cache_manager     signal_handler
         │
         ├─→ [2] data_cleaner_event_driven.py
         │         (原版本，单文件)
         │
         └─→ [3] test_event_driven_modules.py
                   (测试所有模块)
```

## 📊 代码量对比

### 原架构
```
data_cleaner_event_driven.py: 460 行
└── 所有功能混在一起
```

### 新架构
```
event_driven/
├── cleaner.py:              250 行  (54%)
├── redis_manager.py:        130 行  (28%)
├── notification_handler.py: 150 行  (33%)
├── cache_manager.py:        120 行  (26%)
└── signal_handler.py:        50 行  (11%)
─────────────────────────────────────
总计:                        700 行  (152%)

代码量增加: +52%
原因: 完善的文档注释、类型提示、错误处理
```

## 🎨 模块颜色编码

```
🟢 核心模块 (event_driven/)
   - 负责主要业务逻辑
   - 模块化、可测试、可维护

🔵 入口文件
   - data_cleaner_event_driven_v2.py (推荐)
   - data_cleaner_event_driven.py (兼容)

🟡 工具脚本
   - test_event_driven_modules.py
   - clear_id_cache.py
   - manage_id_cache.py

🟠 配置文件
   - config_processing.yaml
   - config_processing_dl.yaml

🔴 启动脚本
   - start_cleaner_with_choice.bat (推荐)
   - start_cleaner.bat
```

## 📦 依赖关系

```
外部依赖:
├── redis (Redis 客户端)
├── yaml (配置解析)
├── logging (日志记录)
└── signal (信号处理)

内部依赖:
event_driven/cleaner.py
├── 依赖 → event_driven/redis_manager.py
├── 依赖 → event_driven/notification_handler.py
├── 依赖 → event_driven/cache_manager.py
├── 依赖 → event_driven/signal_handler.py
└── 依赖 → data_cleaner_module.py (原有逻辑)
```

## 🚀 快速导航

### 我想...

**运行新版本**
→ `start_cleaner_with_choice.bat` → 选择 [1]

**测试模块**
→ `python test_event_driven_modules.py`

**了解架构**
→ `event_driven/ARCHITECTURE.md`

**查看使用说明**
→ `event_driven/README.md`

**了解改进内容**
→ `event_driven/REFACTOR_SUMMARY.md`

**修改 Redis 连接**
→ `event_driven/redis_manager.py`

**自定义消息处理**
→ `event_driven/notification_handler.py`

**管理缓存**
→ `event_driven/cache_manager.py`

**调整信号处理**
→ `event_driven/signal_handler.py`

## 📝 版本历史

| 版本 | 文件 | 说明 |
|-----|------|------|
| v1.0 | `data_cleaner_event_driven.py` | 原版本（单文件） |
| v2.0 | `event_driven/` + `data_cleaner_event_driven_v2.py` | 模块化重构 ⭐ |

## 🎓 学习路径

1. **快速上手**: `event_driven/README.md`
2. **理解架构**: `event_driven/ARCHITECTURE.md`
3. **深入代码**: `event_driven/cleaner.py`
4. **学习组件**: 
   - `redis_manager.py` (连接管理)
   - `notification_handler.py` (消息处理)
   - `cache_manager.py` (缓存管理)
   - `signal_handler.py` (信号处理)

## 🔍 文件搜索索引

- **主控制器**: `event_driven/cleaner.py`
- **Redis 连接**: `event_driven/redis_manager.py`
- **消息处理**: `event_driven/notification_handler.py`
- **缓存管理**: `event_driven/cache_manager.py`
- **信号处理**: `event_driven/signal_handler.py`
- **配置文件**: `config_processing.yaml`
- **启动脚本**: `start_cleaner_with_choice.bat`
- **测试脚本**: `test_event_driven_modules.py`
