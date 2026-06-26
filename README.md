# PPT 智造

AI 驱动的智能 PPT 生成系统 —— 上传文档或输入主题，自动规划大纲、选择风格、生成可编辑的 PPTX 文件。

## 功能特性

- **多源输入** — 支持 PDF / DOCX 文件上传 + 文字输入同时使用
- **智能规划** — LLM 自动分析文档结构，生成逻辑清晰的 PPT 大纲
- **智能页数推荐** — 基于文档标题层级和数据密度自动推荐页数
- **8 套视觉模板** — 经典、现代、科技、创意、极简、优雅、彩色、深色
- **卡片布局** — 并列内容自动采用卡片式呈现
- **自动多栏排版** — 要点较多时自动拆分为双栏或三栏
- **大纲预览编辑** — 拖拽排序、修改标题、增删页面
- **一键换风格** — 生成后随时切换模板风格
- **增量修改** — 生成后继续用文字描述调整内容
- **WebSocket 实时进度** — 生成过程可视化
- **图表支持** — 柱状图、折线图、饼图自动生成

## 项目结构

```
├── backend/                  # FastAPI 后端
│   ├── main.py               # API 服务入口（端口 3000）
│   ├── config.py             # 全局配置（支持 .env）
│   ├── requirements.txt      # Python 依赖
│   ├── core/
│   │   ├── parser.py         # PDF/DOCX 文本提取
│   │   ├── content_analyzer.py # 文档结构分析 & 智能页数推荐
│   │   ├── planner.py        # LLM 内容规划
│   │   ├── polisher.py       # LLM 文案润色
│   │   ├── designer.py       # 模板选择
│   │   └── renderer.py       # PPT 渲染
│   ├── models/
│   │   ├── schemas.py        # Pydantic 数据模型
│   │   └── enums.py          # 枚举类型
│   ├── services/
│   │   ├── llm_client.py     # LLM API 客户端
│   │   ├── task_manager.py   # WebSocket 任务管理
│   │   └── file_service.py   # 文件 I/O
│   └── templates/            # 8 套模板
│       ├── base.py           # 模板基类
│       ├── modern.py         # 现代简约
│       ├── classic.py        # 商务经典
│       ├── tech.py           # 科技感
│       ├── creative.py       # 创意
│       ├── minimal.py        # 极简
│       ├── elegant.py        # 优雅高端
│       ├── colorful.py       # 彩色活泼
│       └── dark.py           # 深色
│
├── frontend-html/            # 纯前端（HTML+CSS+JS）
│   ├── index.html            # 主页面
│   ├── css/style.css         # 样式（Gamma/Notion 风格）
│   ├── js/api.js             # API 客户端
│   ├── js/app.js             # 应用逻辑
│   ├── serve.py              # Python 开发服务器
│   └── vite.config.js        # Vite 代理配置（可选）
│
├── .env.example              # 环境变量模板
└── .gitignore
```

## 快速开始

### 1. 安装后端依赖

```bash
cd backend
pip install -r requirements.txt
```

### 2. 配置 LLM

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env，填入你的 LLM API 信息
LLM_API_URL=http://your-llm-endpoint/v1
LLM_API_KEY=your-api-key-here
LLM_MODEL=your-model-name
```

支持任何兼容 OpenAI API 格式的 LLM 服务。

### 3. 启动后端

```bash
cd backend
python main.py
```

服务运行在 `http://localhost:3000`

### 4. 启动前端

**方式一：Python（推荐，自动处理跨域）**

```bash
cd frontend-html
python serve.py
```

访问 `http://localhost:5174`





## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/templates` | 获取模板列表 |
| POST | `/api/recommend-pages` | 智能推荐页数 |
| POST | `/api/generate/upload` | 上传文件+文字生成 PPT |
| POST | `/api/generate/outline` | 确认大纲并渲染 |
| POST | `/api/modify` | 增量修改 |
| POST | `/api/restyle` | 一键换风格 |
| GET | `/api/download/{task_id}` | 下载 PPTX 文件 |
| GET | `/api/task/{task_id}` | 查询任务状态 |
| POST | `/api/cancel/{task_id}` | 取消任务 |
| WS | `/ws/task/{task_id}` | WebSocket 实时进度 |

## 使用流程

1. **输入内容** — 上传 PDF/DOCX 文件 + 输入文字描述
2. **设置参数** — 点击"生成 PPT"，在弹出的对话框中选择风格、页数、详细程度
3. **预览大纲** — 系统生成大纲后可以拖拽排序、编辑标题、删减页面
4. **生成 PPT** — 确认后渲染生成，左侧预览面板实时展示
5. **修改调整** — 继续输入文字进行增量修改，或点击换风格切换模板
6. **下载** — 点击下载按钮保存 .pptx 文件，可用 PowerPoint / WPS 打开编辑

## 内容生成模式

LLM 自动根据输入类型切换：

- **主题模式**（如"吉他基础教学"）— 自主创作，靠知识生成内容
- **输入模式**（有文档内容/具体数据）— 只提炼、润色、结构化，不编造事实

内容优先级：**产品功能 > 客户案例 > 财务数据 > 战略规划 > 公司背景**

## 技术栈

- **后端** — Python 3.13, FastAPI, python-pptx, PyMuPDF, OpenAI SDK
- **前端** — 纯 HTML5 + CSS3 + JavaScript（无框架依赖）
- **LLM** — 兼容 OpenAI API 格式（支持 Qwen / DeepSeek / Claude / GPT 等）
- **通信** — REST API + WebSocket

## 许可证

（请根据实际情况补充许可证信息）
