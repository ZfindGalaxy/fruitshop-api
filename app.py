from flask import request, Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
import os   #实现交互
from models import db
from flask_migrate import Migrate
from dotenv import load_dotenv
from datetime import timedelta

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
# 用户一小时为操作自动登出
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=1) 

#初始化数据库
db.init_app(app) # 复用models.py中的db实例
migrate = Migrate(app, db)
from models import Users, FruitVariety, Details 

# Flask-Login 和 密码安全
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash   # 密码加密和安全
from sqlalchemy import or_

login_manager = LoginManager()
login_manager.init_app(app) # 初始化登录功能，绑定到flask——app
login_manager.login_view = 'login'  # 未登录时重定向到login视图函数

# 把函数 load_user 注册为 Flask-Login 的“用户加载回调函数”.每当 Flask-Login 需要 从 Session 中恢复用户身份 时，就会自动调用这个函数
@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))

# 工具函数
def success(data = None, message = "Success"):
    return jsonify({
        'code':200 , # 成功
        'message' :message,
        'data': data
    })

def error(message = 'Error', code = 400):
    return jsonify({
        'code':code,
        'message':message
    }),code

# 路由设计

# 根路由
@app.route('/')
def index():
    return jsonify({
        'message':"欢迎来到果蔬信息管理系统！",
        'status':"running",
        'endpoints':{
            'users':"api/users",    # 预留位
            'fruits':"api/fruits"   # 预留位
        }
    })

# 登录功能
@app.route('/api/login', methods = ['POST'])
def login():
    data = request.get_json()
    account_1 = data.get('account')
    password_1 = data.get('password')

    user = Users.query.filter_by(account = account_1).first()
    if user and check_password_hash(user.password, password_1):
        # 如果用户存在并且密码匹配正确
        login_user(user)
        return success({'user':user.to_dict()},'登录成功')
    return error('账号或者密码错误',401)
                 
                
# 注册功能
@app.route('/api/register',methods = ['POST'])
def register():
    data = request.get_json()
    account_2 = data.get('account')
    password_2 = data.get('password')

    if not account_2 or not password_2:
        return error('账号和密码不能未空',400)
    if len(account_2) != 11 or not account_2.isdigit():
        return error("账号必须是11位数字", 400)
    if Users.query.filter_by(account=account_2).first():
        return error("账号已存在", 409)        
             
    hashed_pw = generate_password_hash(password_2)
    new_user = Users(account=account, password=hashed_pw)
    db.session.add(new_user)
    db.session.commit()
    return success(message="注册成功")

    
# 登出功能
@app.route('/api/logout', methods = ['POST'])
# 装饰器：必须登录才可以范文的路由，未登陆就进行跳转
@login_required
def logout():
    logout_user()
    return success(message='已登出')

# 注销(删除账号)功能
@app.route('/api/delete-account')
@login_required
def delete_account():
    data = request.get_json()
    password_3 = data.get('password')

    # 密码验证
    if not password_3 or not check_password_hash(current_user.password, password_3):
        return error(message= '密码验证失败，无法注销账号', code = 400)
    # 验证成功后，先登出后清理账号
    logout_user()
    # 尝试删除账号
    try:
        db.session.delete(current_user)
        db.session.commit()
        return success(message='账号注销成功')
    except Exception as e:
        db.session.rollback() # 撤销工作台里所有未提交的操作，恢复到操作前的状态
        return error(message=f'账号注销失败:{str(e)}',code = 500)


# 密码修改功能
@app.route('/api/change-password',methods = ['PATCH'])
@login_required
def change_password():
    data = request.get_json()
    old_password = data.get('old_password')
    new_password = data.get('new_password')
    # 密码验证
    if not new_password:
        return error(message= '新密码不能为空', code = 400)
    if not old_password or not check_password_hash(current_user.password, old_password):
        return error(message= '密码验证失败，无法修改密码', code = 400)
    current_user.password = generate_password_hash(new_password)
    db.session.commit()
    logout_user()
    return success(message='密码修改成功，请重新登录')

# 果蔬首页——已（未）登录
@app.route('/api/fruits', methods = ['GET'])
def get_fruits_and_vegetables():
    per_page = 10 # 每一页10条信息
    # 页码信息
    page = request.args.get('page',1 , type=int)
    # 分页查询
    pagination = FruitVariety.query.paginate(page=page, per_page=per_page, error_out=False)
    # 转字典
    fruits = [f.to_dict() for f in pagination.items]
    return success({
        'fruits': fruits,
        'total': pagination.total,  # 总记录数
        'pages': pagination.pages,  # 总页数
        'current_page': page,  # 当前页码
        'has_next': pagination.has_next,   # 是否有下一页（True/False）
        'has_prev': pagination.has_prev    # 是否有上一页
    })

# 果蔬详情页



# 根据果蔬名称模糊查询功能
# 种类添加功能
# 种类删除功能
# 种类内容修改功能


    # 程序入口
if __name__ == '__main__':
    # 这里是配置debug mode的核心位置
    app.run(
        host='0.0.0.0',  # 允许外部访问
        port=5050,   # 运行端口
        debug=os.environ.get("DEBUG", "False").lower() == "true"      # 开启调试模式
    )