<div align="center">
  <img src="docs/assets/logo.png" width="120" alt="穿了么 LOGO">
  <h1>穿了么 · Hello Tryon</h1>
  <p>
    <a href="https://github.com/dkbnull/hello-tryon-server"><img src="https://img.shields.io/badge/GitHub-hello--tryon--server-181717?logo=github" alt="GitHub"></a>
    <a href="https://gitee.com/dkbnull/hello-tryon-server"><img src="https://img.shields.io/badge/Gitee-hello--tryon--server-C71D23?logo=gitee" alt="Gitee"></a>
    <a href="https://github.com/dkbnull/hello-tryon-web"><img src="https://img.shields.io/badge/Frontend-hello--tryon--web-4FC08D?logo=vuedotjs" alt="Frontend"></a>
    <a href="LICENSE"><img src="https://img.shields.io/badge/License-Apache_2.0-D22128?logo=apache" alt="Apache 2.0"></a>
  </p>
  <p>
    <img src="https://img.shields.io/badge/Python-3.11+-3776AB?logo=python" alt="Python 3.11+">
    <img src="https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi" alt="FastAPI 0.115+">
    <img src="https://img.shields.io/badge/SQLAlchemy-2.0-D71F00?logo=sqlalchemy" alt="SQLAlchemy 2.0">
    <img src="https://img.shields.io/badge/Pillow-10.3+-45B7D8?logo=pillow" alt="Pillow 10.3+">
    <img src="https://img.shields.io/badge/rembg-u2net-4CBB17" alt="rembg u2net">
  </p>
</div>

## 项目简介

「穿了么」后端服务：提供注册登录、衣物上传（AI 抠图/自动分类/手动旋转）、衣橱管理与静态图片托管。

- API 交互文档：启动后访问 <http://127.0.0.1:8000/docs>（Swagger UI）

## 技术栈

| 类别 | 选型 |
|------|------|
| 框架 | FastAPI |
| ORM / 数据库 | SQLAlchemy 2.0 / SQLite（默认），可切换 PostgreSQL |
| 认证 | JWT（PyJWT），密码 PBKDF2 哈希 |
| 图像处理 | Pillow + rembg（u2net 模型，Apache 2.0 许可，可商用） |

## 快速开始

### 环境要求

- Python ≥ 3.11
- Windows / Linux 均可

### 安装

```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 启动

```bash
.venv\Scripts\python run.py
```

服务监听 `http://127.0.0.1:8000`，开发模式带自动重载。

### AI 抠图模型

- 模型文件：`models/u2net.onnx`（约 176MB）
- 通过代码内设置 `U2NET_HOME` 指向项目内 `models/` 目录，无需配置系统环境变量
- rembg 未安装时自动降级为保留原图，接口行为不受影响
- 首次运行若目录内无模型文件，rembg 会自动下载

## 环境变量

所有配置均有开发默认值（见 [app/config.py](app/config.py)），生产环境通过环境变量覆盖：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DATABASE_URL` | `sqlite:///./hello_tryon.db` | 公网部署时切换 PostgreSQL |
| `JWT_SECRET` | 开发密钥 | **生产必须**注入强随机值 |
| `JWT_EXPIRE_HOURS` | `72` | 登录态有效期（小时） |
| `INVITE_CODE` | `TRYON2026` | 注册邀请码，不开放注册 |
| `UPLOAD_DIR` | `uploads` | 图片存储目录，衣物图片位于 `uploads/items/` |

## API 一览

所有业务接口需携带 `Authorization: Bearer <token>`。

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/register` | 注册（首位校验邀请码，无效返回 403） |
| POST | `/api/auth/login` | 登录，返回 token 与用户信息 |
| GET | `/api/auth/me` | 当前用户信息 |
| PATCH | `/api/auth/me` | 修改昵称 / 虚拟人物性别 |
| PATCH | `/api/auth/me/password` | 修改密码 |
| POST | `/api/items/process` | 上传原图，AI 抠图 + 自动分类，结果不落库 |
| POST | `/api/items` | 确认入库：应用手动旋转、命名、分类后落库 |
| GET | `/api/items` | 衣物列表，可选 `category` 过滤 |
| PATCH | `/api/items/{id}` | 修改名称 / 分类 |
| DELETE | `/api/items/{id}` | 删除衣物（含图片文件） |
| GET | `/api/health` | 健康检查 |
| GET | `/static/items/{file}` | 衣物图片静态托管 |

### 上传约束

- 格式：JPG / PNG（入库接口仅接受 PNG，即第一步的处理结果）
- 大小：≤ 10MB
- 处理流水线：EXIF 摆正 → AI 抠图 → 裁边缩放 → 角度摆正 → 衣架清除 → 落库

## 目录结构

```
app/
├── main.py          # FastAPI 入口：CORS、静态托管、路由注册
├── config.py        # 环境变量配置与业务常量
├── database.py      # SQLAlchemy 会话与建表
├── models.py        # User / ClothingItem 表模型
├── schemas.py       # Pydantic 请求/响应模型
├── security.py      # PBKDF2 密码哈希与 JWT 签发/校验
├── deps.py          # 依赖注入（登录态）
├── routers/
│   ├── auth.py      # 注册 / 登录 / 用户信息 / 修改密码
│   └── items.py     # 衣物上传 / 列表 / 编辑 / 删除
└── services/
    └── imaging.py   # 抠图、分类、旋转、文件名生成
models/              # u2net.onnx 模型文件
uploads/items/       # 衣物图片
run.py               # 开发启动脚本
```

## 演示账号

```
账号：demo@tryon.cn
密码：Demo@12345
```
