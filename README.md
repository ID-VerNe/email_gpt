# EmailGPT - 智能邮件管理系统

EmailGPT 是一个基于 Python Flask 后端和 React 前端构建的智能邮件管理系统。它能够从 IMAP 邮件服务器获取邮件，利用 OpenAI 的 AI 能力对邮件内容进行智能分析（包括摘要、紧急程度评估和行动项提取），并将邮件及其分析结果存储在 SQLite 数据库中。用户可以通过直观的 Web 界面浏览邮件、查看 AI 分析结果，并管理系统设置。

## 主要功能

*   **邮件获取**: 从配置的 IMAP 服务器安全地获取最新邮件。
*   **AI 智能分析**:
    *   **邮件摘要**: 自动生成邮件内容的简洁摘要。
    *   **紧急程度评估**: 根据邮件内容判断其紧急程度（高、中、低）。
    *   **行动项提取**: 识别邮件中包含的待办事项或行动指令。
*   **数据存储**: 使用 SQLite 数据库存储原始邮件内容和 AI 分析结果。
*   **Web 用户界面**: 提供一个响应式前端界面，方便用户浏览、筛选和查看邮件详情及分析结果。
*   **配置管理**: 通过 Web 界面动态更新 IMAP 和 OpenAI API 配置。
*   **后台同步**: 支持手动触发邮件同步和数据库整理操作。

## 技术栈

*   **后端**:
    *   Python 3.10
    *   Flask (Web 框架)
    *   SQLite (数据库)
    *   `python-dotenv` (环境变量管理)
    *   `openai` (OpenAI API 交互)
    *   `beautifulsoup4` (邮件内容处理)
*   **前端**:
    *   React.js (UI 库)
    *   HTML/CSS
    *   `marked` (Markdown 渲染)
*   **其他**:
    *   IMAP 协议 (邮件获取)

## 安装与运行

### 先决条件

*   Python 3.10+
*   Node.js 和 npm (或 yarn)

### 后端设置

1.  **克隆仓库**:
    ```bash
    git clone https://github.com/ID-VerNe/email_gpt.git
    cd email_gpt
    ```
2.  **创建并激活虚拟环境**:
    ```powershell
    python -m venv .venv
    .venv\Scripts\activate.bat
    ```
3.  **安装后端依赖**:
    ```powershell
    .venv\Scripts\activate.bat; pip install -r backend/email_server/requirements.txt
    ```
4.  **配置环境变量**:
    复制 `.env.example` 文件并重命名为 `.env`：
    ```powershell
    Copy-Item .env.example .env
    ```
    编辑 `.env` 文件，填入您的 IMAP 服务器信息、邮箱凭据和 OpenAI API 密钥。
    ```ini
    # IMAP Server Configuration
    IMAP_SERVER=YOUR_IMAP_SERVER_ADDRESS
    IMAP_PORT=993
    IMAP_USERNAME=YOUR_IMAP_USERNAME
    IMAP_PASSWORD=YOUR_IMAP_PASSWORD
    MAILBOX=YOUR_IMAP_MAILBOX # 例如: INBOX

    # OpenAI Configuration
    OPENAI_API_KEY=YOUR_OPENAI_API_KEY
    OPENAI_MODEL=gpt-4o # 或 gpt-3.5-turbo 等
    OPENAI_BASE_URL=https://api.openai.com/v1/ # 默认值，如果使用其他服务商请修改

    # Application Configuration
    DB_PATH=emails.db # 数据库文件路径，默认为项目根目录下的 emails.db
    FETCH_DAYS_AGO=10 # 每次同步获取过去多少天的邮件
    ```
    **注意**: `OPENAI_BASE_URL` 默认是 OpenAI 的官方 API 地址。如果您使用其他兼容 OpenAI API 的服务（如本地 LLM），请修改此地址。

### 前端设置

1.  **进入前端目录**:
    ```powershell
    cd frontend
    ```
2.  **安装前端依赖**:
    ```powershell
    npm install
    ```
3.  **构建前端应用**:
    ```powershell
    npm run build
    ```
    这将在 `frontend/build` 目录下生成静态文件，后端 Flask 应用将负责提供这些文件。

### 运行应用

1.  **返回项目根目录**:
    ```powershell
    cd ..
    ```
2.  **启动后端 API 服务器**:
    ```powershell
    .venv\Scripts\activate.bat; python backend/api_server.py
    ```
    后端服务器将运行在 `http://localhost:5001`。

3.  **访问应用**:
    在浏览器中打开 `http://localhost:5001` 即可访问 EmailGPT 应用。

## API 文档 (简要)

后端提供以下 API 端点：

*   `GET /api/emails`: 获取所有已存储的邮件及其分析结果。
*   `POST /api/sync-emails`: 触发邮件同步和数据库整理流程。
*   `GET /api/settings`: 获取当前 `.env` 文件中的配置。
*   `POST /api/settings`: 更新 `.env` 文件中的配置并尝试重启后端服务。
*   `GET /api/mailboxes`: 获取 IMAP 服务器上的邮箱列表。

## 项目结构

```
email_gpt/
├── .env                 # 环境变量配置文件 (从 .env.example 复制并修改)
├── .env.example         # 环境变量示例文件
├── EmailGPT.cmd         # (可选) 启动脚本
├── emails.db            # SQLite 数据库文件 (运行时自动生成)
├── README.md            # 项目说明文件
├── LICENSE              # 项目许可证文件
├── backend/
│   ├── api_server.py    # Flask 后端 API 服务器
│   ├── organize_database.py # 数据库整理脚本
│   ├── update_emails.py # 邮件同步和分析脚本
│   ├── chatgpt_handlers/ # AI 分析相关模块
│   │   ├── email_analyzer.py
│   │   └── prompts/     # 存储 AI 提示词模板
│   ├── data_storage/    # 数据存储相关模块
│   │   └── email_data_manager.py
│   └── email_server/    # 邮件获取和处理模块
│       ├── email_fetcher.py
│       ├── email_processor.py
│       ├── requirements.txt # 后端 Python 依赖
│       └── ...
└── frontend/
    ├── public/          # 前端静态资源
    ├── src/             # 前端 React 源码
    │   ├── App.js       # 主应用组件
    │   ├── SettingsPage.js # 设置页面组件
    │   ├── App.css
    │   ├── index.js
    │   └── ...
    ├── package.json     # 前端依赖配置
    ├── package-lock.json
    └── README.md        # 前端项目说明 (Create React App 默认)
```

## 许可证

本项目采用 MIT 许可证。详情请参阅 `LICENSE` 文件。
