from flask import request, Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
import os   #实现交互
from models import db
from flask_migrate import Migrate
from dotenv import load_dotenv

#初始化flask应用
app = Flask(__name__)
load_dotenv()  # 自动从 .env 读取变量到 os.environ 

# 配置信息
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY'  ) 
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL',
    'sqlite:///FruitAndVegertable.db'  # 如果没设置 DATABASE_URL，默认用 SQLite
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['DEBUG'] = os.environ.get('DEBUG', 'False').lower() == 'true'


#初始化数据库
db.init_app(app) # 复用models.py中的db实例
migrate = Migrate(app, db)
from models import Users, FruitVariety, Details 
# 路由设计
@app.route('/')
def index():
    return jsonify({
        "message": "欢迎使用果蔬管理系统 API！",
        "status": "running",
        "endpoints": {
            "users": "/api/users",
            "fruits": "/api/fruits"
        }
    })


    # 程序入口
if __name__ == '__main__':
    # 这里是配置debug mode的核心位置
    # 在 app.run() 之前加：
    print(">>> 当前数据库 URI:", app.config['SQLALCHEMY_DATABASE_URI'])
    app.run(
        host='0.0.0.0',  # 允许外部访问
        port=5050,   # 运行端口
        debug=os.environ.get("DEBUG", "False").lower() == "true"      # 开启调试模式
    )