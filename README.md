# 饮食自我认知应用

## 项目概述
这是一个帮助用户记录和分析个人饮食情况的Web应用。用户可以记录每日饮食摄入的热量，查看统计数据和图表，并根据个人信息计算基础代谢率(BMR)，从而更好地了解自己的饮食习惯。

## 功能特点
- 用户注册与登录（基于用户名）
- 个人信息设置（体重、身高、年龄、性别）
- 基础代谢率(BMR)自动计算
- 每日饮食记录（早餐、午餐、晚餐、零食的热量）
- 饮食统计数据可视化（图表展示）
- 历史记录查询
- 连续打卡天数跟踪
- 热量缺口分析

## 技术栈
- 后端：FastAPI (Python)
- 数据库：SQLite
- 前端：HTML, CSS, JavaScript (使用Jinja2模板)
- 部署：Docker, Docker Compose

## 项目结构
```
Diet-Self-Perception/
├── .github/
├── .gitignore
├── Dockerfile
├── app/
│   ├── main.py          # 应用主文件
│   ├── static/          # 静态文件
│   └── templates/       # HTML模板
├── data/                # 数据库文件目录
├── data.db.example      # 数据库示例文件
└── docker-compose.yml   # Docker Compose配置
```

## 安装与部署

### 前提条件
- Docker 和 Docker Compose 已安装

### 使用Docker Compose部署
1. 克隆本仓库
   ```bash
   git clone https://github.com/yourusername/Diet-Self-Perception.git
   cd Diet-Self-Perception
   ```

2. 启动服务
   ```bash
   docker-compose up -d
   ```

3. 访问应用
   打开浏览器，访问 http://localhost:8000/u/你的用户名
   > 首次访问时，系统会自动创建用户

### 本地开发运行
1. 安装依赖
   ```bash
   pip install fastapi uvicorn sqlalchemy jinja2 python-multipart
   ```

2. 运行应用
   ```bash
   cd app
   uvicorn main:app --reload
   ```

3. 访问应用
   打开浏览器，访问 http://localhost:8000/u/你的用户名

## 使用说明
1. **首次使用**：访问 http://localhost:8000/u/你的用户名，系统会引导你设置个人信息
2. **个人设置**：填写体重、身高、年龄和性别，系统会计算你的基础代谢率(BMR)
3. **每日记录**：选择"吃多了"或"没吃多"，然后记录各餐的热量摄入
4. **查看统计**：点击"统计总览"查看你的饮食统计数据
5. **图表分析**：点击"图表可视化"查看你的饮食趋势图表
6. **历史记录**：点击"历史记录"查看过去的饮食记录

## 数据库结构
应用使用SQLite数据库，包含以下表：

1. **users**：用户信息
   - id: 主键
   - username: 用户名
   - weight: 体重(kg)
   - height: 身高(cm)
   - age: 年龄
   - gender: 性别
   - bmr: 基础代谢率

2. **food_records**：饮食记录
   - id: 主键
   - user_id: 用户ID
   - record_date: 记录日期
   - breakfast: 早餐热量
   - lunch: 午餐热量
   - dinner: 晚餐热量
   - snack: 零食热量
   - total_calories: 总热量

3. **records**：每日打卡记录
   - id: 主键
   - user_id: 用户ID
   - record_date: 记录日期
   - choice: 选择("eat_much"或"not_eat_much")

## 贡献指南
1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开Pull Request

## 许可证
本项目采用MIT许可证 - 详见LICENSE文件

## 联系方式
如有问题或建议，请联系 [your.email@example.com]