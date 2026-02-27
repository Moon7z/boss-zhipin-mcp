# Boss直聘 MCP 服务器

让OpenClaw在BOSS直聘上根据个人上传的简历自动找寻合适的岗位并打招呼沟通。

## 功能特性

- 📄 **简历解析**：支持PDF和DOCX格式，自动提取姓名、电话、邮箱、技能、工作经验等信息
- 🔍 **智能岗位搜索**：根据简历信息搜索匹配的工作岗位
- 🎯 **智能匹配**：基于技能、经验、学历等维度计算岗位匹配度分数
- 🤝 **自动打招呼**：批量向匹配的HR发送打招呼消息
- 🔐 **登录管理**：支持BOSS直聘账号登录，保存cookies避免重复登录
- 🛡️ **反机器人检测**：内置多重防护机制，降低被封禁风险

### 反检测功能

| 功能 | 说明 |
|------|------|
| 浏览器指纹随机化 | 随机化User-Agent、视口大小 |
| 行为模拟 | 人类鼠标移动、滚动、点击模式 |
| 请求频率限制 | 可配置的速率限制器 |
| 智能延时 | 随机化操作间隔 |
| 验证码检测 | 自动检测滑块验证码 |
| 代理IP支持 | 支持代理IP池轮换 |
| 错误重试机制 | 自动处理错误并重试 |

## 安装

```bash
cd Project1

# 使用 pip 安装依赖
pip install -e .

# 安装 Playwright 浏览器
playwright install chromium
```

## 配置

1. 复制环境配置模板：
```bash
cp .env.example .env
```

2. 编辑 `.env` 文件，填入BOSS直聘账号：
```
BOSS_PHONE=你的手机号
BOSS_PASSWORD=你的密码
```

## 使用方法

### 在OpenClaw中配置MCP

在OpenClaw的配置文件中添加：

```json
{
  "mcpServers": {
    "boss-zhipin": {
      "command": "python",
      "args": [
        "-m",
        "boss_mcp.server"
      ],
      "cwd": "你的项目路径/Project1/src"
    }
  }
}
```

### 工具函数说明

#### 1. boss_login
登录BOSS直聘账号（支持反机器人检测）

**参数：**
- `phone`: 手机号
- `password`: 密码
- `headless`: 是否无头模式运行浏览器（默认false）
- `use_proxy`: 是否使用代理IP（默认false）
- `enable_anti_detection`: 是否启用反检测功能（默认true，推荐开启）
- `max_requests_per_minute`: 每分钟最大请求数（默认8）

#### 2. load_resume
解析本地简历文件

**参数：**
- `resume_path`: 简历文件路径（支持PDF和DOCX）

#### 3. search_jobs
搜索岗位

**参数：**
- `keyword`: 搜索关键词
- `city`: 期望城市
- `experience`: 工作经验要求
- `education`: 学历要求
- `salary`: 薪资范围
- `page_count`: 搜索页数（默认3）

#### 4. match_and_greet
根据简历匹配岗位并打招呼

**参数：**
- `keyword`: 搜索关键词
- `min_score`: 最低匹配分数阈值（0-100，默认30）
- `max_count`: 最多打招呼数量（默认10）
- `custom_message`: 自定义打招呼消息

#### 5. get_recommended_jobs
根据简历智能推荐岗位

**参数：**
- `keyword`: 搜索关键词
- `min_score`: 最低匹配分数（默认50）
- `max_count`: 返回的最大数量（默认20）

#### 6. get_resume_info
获取已加载的简历信息

#### 7. close_browser
关闭浏览器会话

## 示例对话

```
用户：帮我登录BOSS直聘
OpenClaw：调用 boss_login 工具

用户：解析我的简历 c:/users/xxx/简历.pdf
OpenClaw：调用 load_resume 工具，解析并显示简历信息

用户：帮我找Python开发的工作
OpenClaw：调用 search_jobs 工具，搜索并展示岗位列表

用户：给我推荐匹配度最高的工作
OpenClaw：调用 get_recommended_jobs 工具，展示推荐岗位

用户：向这些公司打招呼
OpenClaw：调用 match_and_greet 工具，自动打招呼
```

## 注意事项

1. 首次使用需要手动登录BOSS直聘，之后会保存cookies
2. 建议使用headless=false模式首次登录，以便处理验证码
3. 打招呼频率不要太高，避免被封号
4.BOSS 遵守直聘平台规则，不要滥用自动化功能
