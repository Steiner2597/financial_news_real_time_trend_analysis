# 金融新闻实时趋势分析前端

这是金融新闻实时趋势分析系统的前端项目，基于 Vue 3 + Vite 构建。

## 快速启动

### 🚀 启动后端服务

#### 方法一：从项目根目录启动（推荐）

```bash
# 1. 进入项目根目录
cd D:\SE\workspace\CS5481-visualization

# 2. 激活虚拟环境（如果使用）
# Windows cmd:
.venv\Scripts\activate

# 3. 安装后端依赖（首次运行）
pip install fastapi "uvicorn[standard]" redis schedule websockets

# 4. 启动后端
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

#### 方法二：使用 run.py 启动

```bash
# 1. 进入项目根目录
cd D:\SE\workspace\CS5481-visualization

# 2. 设置 PYTHONPATH 环境变量
set PYTHONPATH=D:\SE\workspace\CS5481-visualization

# 3. 进入后端目录
cd backend

# 4. 运行启动脚本
python run.py
```

**后端服务地址**: http://127.0.0.1:8000

**验证后端是否启动成功**:
- 访问 http://127.0.0.1:8000/ （查看根路径）
- 访问 http://127.0.0.1:8000/health （健康检查）
- 访问 http://127.0.0.1:8000/api/v1/trends/health （趋势服务检查）

### 🎨 启动前端服务

```bash
# 1. 进入前端目录
cd D:\SE\workspace\CS5481-visualization\frontend

# 2. 安装依赖（首次运行）
npm install

# 3. 启动开发服务器
npm run dev
```

**前端服务地址**: http://localhost:5173 （Vite 默认端口）

浏览器会自动打开，如果没有自动打开，请手动访问上述地址。

### ⚙️ 环境要求

**后端**:
- Python 3.8+
- Redis 服务器（默认 localhost:6379）

**前端**:
- Node.js 14+
- npm 或 yarn

### 🔧 常见启动问题

#### 后端问题

**问题 1: ModuleNotFoundError: No module named 'backend'**
- **原因**: 从 backend 目录直接运行，Python 找不到 backend 包
- **解决**: 从项目根目录启动，或设置 PYTHONPATH（见上方方法二）

**问题 2: ModuleNotFoundError: No module named 'redis'**
- **解决**: `pip install redis`

**问题 3: Redis 连接失败**
- **检查**: Redis 服务是否启动（默认 localhost:6379）
- **配置**: 修改 `backend/app/config.py` 中的 Redis 配置

**问题 4: 端口 8000 被占用**
- **解决**: 修改启动命令的端口，例如 `--port 8080`
- **注意**: 同时修改前端 `src/services/api.js` 的 baseURL

#### 前端问题

**问题 1: 依赖安装失败**
```bash
# 清除缓存重新安装
rd /s /q node_modules
del package-lock.json
npm install
```

**问题 2: 端口被占用**
- 修改 `vite.config.js` 中的 port 配置

**问题 3: API 请求失败**
- 确认后端服务已启动
- 检查 `src/services/api.js` 中的 baseURL 配置（默认 http://localhost:8000）

## 技术栈

- **Vue 3** - 渐进式 JavaScript 框架
- **Vite** - 下一代前端构建工具
- **Pinia** - Vue 状态管理
- **Vue Router** - 官方路由
- **Axios** - HTTP 客户端
- **ECharts** - 数据可视化图表库
- **Vue-ECharts** - ECharts 的 Vue 组件封装

## 项目结构

```
frontend/
├── src/
│   ├── components/          # 可复用组件
│   │   ├── Layout.vue       # 布局组件
│   │   ├── NewsFeed.vue     # 新闻滚动组件
│   │   ├── SentimentBar.vue # 情感分析条组件
│   │   ├── TrendChart.vue   # 趋势图表组件
│   │   ├── TrendingKeywords.vue # 热词排行组件
│   │   └── WordCloud.vue    # 词云组件
│   ├── views/              # 页面视图
│   │   └── Dashboard.vue   # 仪表盘页面
│   ├── stores/             # Pinia 状态管理
│   │   └── trendStore.js   # 趋势数据 Store
│   ├── services/           # API 服务
│   │   └── api.js          # API 请求封装
│   ├── router/             # 路由配置
│   │   └── index.js        # 路由定义
│   ├── App.vue             # 根组件
│   ├── main.js             # 应用入口
│   └── style.css           # 全局样式
├── index.html              # HTML 模板
├── vite.config.js          # Vite 配置
└── package.json            # 项目依赖

```

## 安装依赖

```bash
npm install
```

或使用 yarn:

```bash
yarn install
```

## 开发模式

启动开发服务器（热重载）:

```bash
npm run dev
```

默认会在 http://localhost:5173 启动（Vite 默认端口）

**注意**: 启动前端前请确保后端服务已启动，参见上方"快速启动"章节。

## 生产构建

构建生产版本:

```bash
npm run build
```

构建产物会生成在 `dist/` 目录

## 预览生产构建

```bash
npm run preview
```

## 功能模块

### 1. 实时热词排行 (TrendingKeywords)
- 显示当前热门关键词
- 展示排名、热度分数、增长率
- 情感分析可视化
- 自动刷新机制

### 2. 词云分析 (WordCloud)
- 关键词词云可视化
- 基于 ECharts 气泡图实现
- 大小和颜色代表热度

### 3. 趋势图表 (TrendChart)
- 过去24小时趋势变化
- 多关键词对比
- 时间序列可视化

### 4. 新闻滚动 (NewsFeed)
- 最近一小时新闻
- 自动轮播
- 情感分析标记
- 手动翻页控制

### 5. 情感分析 (SentimentBar)
- 正面/中立/负面评论统计
- 进度条可视化
- 情感指数计算

## API 配置

前端 API 地址配置在 `src/services/api.js`:

```javascript
const api = axios.create({
  baseURL: 'http://localhost:8000/api/v1',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
})
```

**修改后端地址**: 如果后端运行在其他地址或端口，请修改上述 `baseURL`。

## 浏览器支持

- Chrome (最新版)
- Firefox (最新版)
- Safari (最新版)
- Edge (最新版)

## 注意事项

1. **后端服务**: 确保后端服务已启动（默认 http://localhost:8000）
2. **Redis 服务**: 后端依赖 Redis，确保 Redis 服务运行正常
3. **首次运行**: 需要先安装前后端依赖
4. **开发模式**: 支持热重载，修改代码后自动刷新
5. **生产构建**: 会进行代码压缩和优化

## 完整启动流程

### 第一次运行（完整流程）

```bash
# 1. 启动 Redis（如果未启动）
# Windows: 运行 redis-server.exe
# Linux/Mac: redis-server

# 2. 启动后端
cd D:\SE\workspace\CS5481-visualization
pip install fastapi "uvicorn[standard]" redis schedule websockets
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload

# 3. 新开一个终端，启动前端
cd D:\SE\workspace\CS5481-visualization\frontend
npm install
npm run dev

# 4. 打开浏览器访问 http://localhost:5173
```

### 日常开发（后续启动）

```bash
# 终端 1: 启动后端
cd D:\SE\workspace\CS5481-visualization
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload

# 终端 2: 启动前端
cd D:\SE\workspace\CS5481-visualization\frontend
npm run dev
```

## 常见问题

### 1. 依赖安装失败
尝试清除缓存后重新安装:
```bash
rm -rf node_modules package-lock.json
npm install
```

### 2. 端口被占用
修改 `vite.config.js` 中的端口号:
```javascript
server: {
  port: 3001  // 改为其他端口
}
```

### 3. API 请求失败
检查后端服务是否正常运行，确认 API 地址配置正确

## 开发指南

### 添加新组件
1. 在 `src/components/` 创建 `.vue` 文件
2. 在需要的地方 import 并使用

### 添加新页面
1. 在 `src/views/` 创建 `.vue` 文件
2. 在 `src/router/index.js` 添加路由配置

### 修改样式
- 全局样式: `src/style.css`
- 组件样式: 在组件的 `<style scoped>` 中定义

## License

MIT
