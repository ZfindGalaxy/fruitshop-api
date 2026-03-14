# 🍎 智能果蔬管理系统 (后端核心版)

> 一个基于 **Flask** 的高性能果蔬管理后端服务。
> 集成 **Redis** 缓存、**JWT** 鉴权及 **短信验证** 机制，提供完整的 RESTful API。
> *注：本项目专注于后端逻辑与数据架构，前端仅为内部测试用途，不包含在此文档中。*

## ✨ 核心功能模块

- 🔐 **认证与安全 (Auth & Security)**
  - 用户注册/登录/登出
  - 密码加密存储 (Werkzeug `generate_password_hash`)
  - **短信验证码系统**：基于 Redis 存储验证码，支持过期自动清除
  - JWT Token 生成与校验，保护敏感接口

- 🥦 **业务逻辑 (Business Logic)**
  - **果蔬 CRUD**：完整的增删改查接口
  - **分页查询**：后端实现高效分页 (`page`, `per_page`)
  - **模糊搜索**：支持按名称、类别多字段检索
  - **数据校验**：请求参数自动验证

- 🛠️ **技术栈**
  - **框架**: Python Flask
  - **ORM**: Flask-SQLAlchemy + Flask-Migrate
  - **缓存**: Redis (短信验证码、临时状态)
  - **安全**: PyJWT, python-dotenv
  - **数据库**: SQLite (开发环境) / MySQL (生产环境)

## 🚀 本地开发与运行

### 1. 前置要求
- Python 3.8+
- **Redis 服务** (必须启动，用于短信验证码)
  ```bash
  # Mac/Linux
  redis-server
  # Windows (需安装 Redis 或使用 WSL)