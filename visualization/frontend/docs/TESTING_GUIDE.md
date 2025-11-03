# 前后端集成测试指南

## 快速启动

### 1. 启动后端服务
```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirement.txt
python run.py
```

后端将在 `http://localhost:8000` 启动

### 2. 启动 Redis (如果需要)
```bash
# 使用 Docker
docker run -d -p 6379:6379 redis:latest

# 或使用本地安装的 Redis
redis-server
```

### 3. 启动前端开发服务器
```bash
cd frontend
npm install
npm run dev
```

前端将在 `http://localhost:5173` 启动

## 测试检查清单

### ✅ 基础连接测试

#### 1. 检查后端 API 可用性
在浏览器访问:
```
http://localhost:8000/docs
```
应该看到 FastAPI 自动生成的 Swagger 文档。

#### 2. 测试各个 API 端点
```bash
# 获取全部趋势数据
curl http://localhost:8000/api/trends/all

# 获取趋势关键词
curl http://localhost:8000/api/trends/keywords

# 获取历史数据
curl http://localhost:8000/api/trends/history

# 获取词云数据
curl http://localhost:8000/api/wordcloud

# 获取新闻数据
curl http://localhost:8000/api/news
```

#### 3. 检查数据格式
确认每个端点返回的数据符合以下格式:

**Sentiment**:
```json
{
  "positive": 45.5,
  "neutral": 35.2,
  "negative": 19.3,
  "total_comments": 1250
}
```

**Trending Keywords**:
```json
[
  {
    "keyword": "美联储",
    "rank": 1,
    "current_frequency": 156,
    "growth_rate": 23.5,
    "trend_score": 89.5,
    "sentiment": "positive"
  }
]
```

**History Data**:
```json
{
  "美联储": [
    {"timestamp": "2025-01-20 12:00:00", "frequency": 156},
    {"timestamp": "2025-01-20 12:30:00", "frequency": 178}
  ]
}
```

**News Feed**:
```json
[
  {
    "title": "美联储宣布降息25个基点",
    "source": "新华财经",
    "publish_time": "2025-01-20 14:30:00",
    "sentiment": "positive"
  }
]
```

### ✅ 前端组件测试

#### 1. SentimentBar (情感分析条)
打开浏览器开发者工具 → Console

**检查项**:
- [ ] 三个情感条(正面/中立/负面)正确显示
- [ ] 百分比数值显示正确(如 45%, 35%, 19%)
- [ ] 评论数量计算正确(如 568条, 440条, 242条)
- [ ] 总评论数显示正确(如 总计: 1250)
- [ ] 颜色渐变正常(绿色/灰色/红色)

**测试命令**:
```javascript
// 在浏览器控制台执行
console.log('Sentiment Data:', document.querySelector('.sentiment-bar-container'))
```

#### 2. TrendingKeywords (趋势关键词)
**检查项**:
- [ ] 显示前10个热门关键词
- [ ] 排名徽章正确(1-10)
- [ ] 关键词名称显示
- [ ] "频率" 统计值正确(current_frequency)
- [ ] 趋势图标正确:
  - 📈 增长率 > 0
  - 📉 增长率 < 0
  - ➡️ 增长率 = 0
- [ ] 情感徽章显示(positive/neutral/negative)
- [ ] 增长率百分比显示(如 +23.5%)

**测试数据验证**:
```javascript
// 检查第一个关键词数据
const firstKeyword = document.querySelector('.keyword-item')
console.log('First Keyword:', {
  name: firstKeyword.querySelector('.keyword-name').textContent,
  frequency: firstKeyword.querySelector('.stat-value').textContent,
  trend: firstKeyword.querySelector('.trend-indicator').textContent
})
```

#### 3. TrendChart (趋势图表)
**检查项**:
- [ ] ECharts 图表正确渲染
- [ ] 显示前5个热门关键词的曲线
- [ ] X轴显示24小时时间范围(48个点)
- [ ] Y轴显示频率值
- [ ] 时间格式正确(HH:MM)
- [ ] 鼠标悬停显示 tooltip
- [ ] 图例可以点击切换显示/隐藏
- [ ] 曲线平滑且颜色渐变
- [ ] 响应式调整大小

**调试命令**:
```javascript
// 检查图表实例
const chart = echarts.getInstanceByDom(document.querySelector('.trend-chart'))
console.log('Chart Option:', chart.getOption())

// 查看处理后的数据
console.log('Chart Series:', chart.getOption().series)
console.log('Chart XAxis:', chart.getOption().xAxis[0].data)
```

#### 4. NewsFeed (新闻动态)
**检查项**:
- [ ] 显示最近一小时的新闻
- [ ] 新闻标题显示完整
- [ ] 来源显示(或 "未知来源")
- [ ] 时间格式化正确:
  - "刚刚" (< 1分钟)
  - "X 分钟前" (< 1小时)
  - "X 小时前" (< 1天)
  - "MM-DD HH:MM" (>= 1天)
- [ ] 情感标签显示:
  - 👍 正面
  - ➡️ 中立
  - 👎 负面
- [ ] 分类图标显示(默认 📰)
- [ ] 自动滚动功能正常(5秒切换)
- [ ] 手动切换按钮可用(▲▼)
- [ ] 进度条显示当前位置
- [ ] 关键词标签显示(如果有)

**测试滚动**:
```javascript
// 检查新闻数据
const newsFeed = document.querySelector('.news-feed-container')
console.log('News Count:', newsFeed.querySelector('.feed-count').textContent)

// 触发手动切换
document.querySelector('.control-btn:last-child').click()
```

#### 5. WordCloud (词云)
**检查项**:
- [ ] 词云渲染正常
- [ ] 词语大小反映权重
- [ ] 词语颜色渐变
- [ ] 鼠标悬停高亮
- [ ] 响应式调整大小

### ✅ 数据流测试

#### 1. 初始数据加载
打开浏览器开发者工具 → Network 标签

**检查项**:
- [ ] `/api/trends/all` 请求成功(200)
- [ ] 响应数据包含所有字段:
  - trending_keywords
  - history_data
  - word_cloud
  - news
  - sentiment
  - last_update

**验证命令**:
```javascript
// 检查 Pinia Store 状态
import { useTrendStore } from '@/stores/trendStore'
const store = useTrendStore()
console.log('Store State:', store.$state)
```

#### 2. WebSocket 实时更新(如果实现)
打开浏览器开发者工具 → Network 标签 → WS

**检查项**:
- [ ] WebSocket 连接建立成功
- [ ] 定期接收更新消息
- [ ] 组件数据自动刷新
- [ ] 无连接错误或断开

#### 3. 错误处理
**测试场景**:
1. **后端未启动**: 停止后端,刷新前端
   - [ ] 显示友好错误提示
   - [ ] 不会白屏或崩溃

2. **网络延迟**: 使用浏览器开发者工具限速
   - [ ] 显示加载状态
   - [ ] 数据最终加载成功

3. **空数据**: 修改后端返回空数组/对象
   - [ ] 显示 "暂无数据" 提示
   - [ ] 布局不错乱

### ✅ 性能测试

#### 1. 页面加载性能
打开浏览器开发者工具 → Performance 标签

**检查项**:
- [ ] 首次内容绘制(FCP) < 1.5s
- [ ] 最大内容绘制(LCP) < 2.5s
- [ ] 交互时间(TTI) < 3.0s
- [ ] 累积布局偏移(CLS) < 0.1

#### 2. 运行时性能
**检查项**:
- [ ] 图表动画流畅(60fps)
- [ ] 新闻滚动无卡顿
- [ ] 内存使用稳定(< 100MB)
- [ ] CPU 使用合理(< 30%)

**监控命令**:
```javascript
// 监控渲染性能
const observer = new PerformanceObserver((list) => {
  for (const entry of list.getEntries()) {
    console.log(entry.name, entry.duration)
  }
})
observer.observe({ entryTypes: ['measure'] })
```

### ✅ 浏览器兼容性测试

#### 测试浏览器列表
- [ ] Chrome 90+ (推荐)
- [ ] Firefox 88+
- [ ] Edge 90+
- [ ] Safari 14+

#### 检查项
- [ ] 布局正常显示
- [ ] ECharts 图表渲染
- [ ] CSS 样式一致
- [ ] 交互功能正常
- [ ] 无 Console 错误

### ✅ 响应式设计测试

#### 屏幕尺寸测试
- [ ] **桌面**: 1920×1080 (正常)
- [ ] **笔记本**: 1366×768 (正常)
- [ ] **平板**: 768×1024 (适配)
- [ ] **手机**: 375×667 (适配)

#### 检查项
- [ ] 组件自动调整大小
- [ ] 文字可读性良好
- [ ] 图表响应式缩放
- [ ] 滚动和交互正常

## 常见问题排查

### 问题1: 后端数据未加载
**症状**: 前端组件显示空状态

**排查步骤**:
1. 检查后端服务是否运行: `http://localhost:8000/docs`
2. 检查 API 请求状态: 浏览器开发者工具 → Network
3. 检查 CORS 配置: 确认后端允许前端域名
4. 检查 API 端点路径: 确认 `vite.config.js` 代理配置

### 问题2: 图表不显示
**症状**: TrendChart 区域空白

**排查步骤**:
1. 检查 ECharts 是否加载: `console.log(echarts)`
2. 检查历史数据格式: 确认是数组格式 `[{timestamp, frequency}]`
3. 检查容器尺寸: 确保容器有明确的高度
4. 检查 Console 错误: 查看是否有数据解析错误

### 问题3: 时间格式错误
**症状**: 新闻时间显示 "Invalid Date"

**排查步骤**:
1. 检查时间字段: 确认使用 `publish_time` 或 `timestamp`
2. 检查时间格式: 确认为 "YYYY-MM-DD HH:MM:SS"
3. 检查时区: 确认前后端时区一致

### 问题4: WebSocket 连接失败
**症状**: 实时更新不工作

**排查步骤**:
1. 检查 WebSocket URL: 确认端口和路径正确
2. 检查网络防火墙: 允许 WebSocket 连接
3. 检查后端 WebSocket 服务: 确认已启动
4. 检查浏览器兼容性: 某些老版本不支持 WebSocket

## 性能基准

### 预期性能指标
- **API 响应时间**: < 200ms
- **首屏加载时间**: < 2s
- **图表渲染时间**: < 500ms
- **内存占用**: < 100MB
- **CPU 使用率**: < 30%

### 数据量限制
- **趋势关键词**: 10-50 个
- **历史数据点**: 48 个/关键词
- **新闻条数**: 20-50 条
- **词云词汇**: 50-100 个

## 自动化测试(可选)

### 单元测试
```bash
# 运行组件单元测试
npm run test:unit
```

### E2E 测试
```bash
# 运行端到端测试
npm run test:e2e
```

### 代码覆盖率
```bash
# 生成覆盖率报告
npm run test:coverage
```

## 测试报告模板

### 测试结果记录
```markdown
## 测试日期: YYYY-MM-DD
## 测试人员: [姓名]

### 环境信息
- OS: Windows 10 / macOS / Linux
- 浏览器: Chrome 120.0
- Node.js: v18.17.0
- Python: 3.9.0

### 测试结果
#### 基础连接 ✅
- [ ] 后端 API 可用
- [ ] 前端服务启动
- [ ] 数据格式正确

#### 组件功能 ✅
- [ ] SentimentBar 正常
- [ ] TrendingKeywords 正常
- [ ] TrendChart 正常
- [ ] NewsFeed 正常
- [ ] WordCloud 正常

#### 数据流 ✅
- [ ] 初始加载正常
- [ ] 实时更新正常
- [ ] 错误处理正常

#### 性能 ✅
- [ ] 加载时间 < 2s
- [ ] 运行流畅
- [ ] 内存稳定

### 发现的问题
1. [问题描述]
   - 严重程度: 高/中/低
   - 复现步骤: ...
   - 解决方案: ...

### 总结
整体测试结果: 通过 / 部分通过 / 未通过
```

---

**测试完成后,请填写测试报告并反馈问题!** 🎯
