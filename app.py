"""
果蔬信息管理系统 - Flask API 后端
功能：用户认证、果蔬 CRUD、模糊搜索
作者：zqy
"""


from flask import request, Flask, jsonify, g
from flask_sqlalchemy import SQLAlchemy
import os   #实现交互
from models import db
from flask_migrate import Migrate
from dotenv import load_dotenv
from datetime import timedelta
import redis   # 用于连接和操作 Redis 数据库
from sms import random, verify_sms_code, send_sms_code

#初始化flask应用
app = Flask(__name__)
load_dotenv()  # 自动从 .env 读取变量到 os.environ 

# 配置信息
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY'  ) 

db_url = os.environ.get('DATABASE_URL')
if not db_url:
    raise ValueError("❌ 错误：未找到 DATABASE_URL 环境变量！请检查 .env 文件或 Docker 容器状态。")
    
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['DEBUG'] = os.environ.get('DEBUG', 'False').lower() == 'true'
# reids配置信息
redis_host = os.environ.get('REDIS_HOST')
redis_port = int(os.environ.get('REDIS_PORT'))
redis_password = os.environ.get('REDIS_PASSWORD')  # 从 .env 获取密码
# redis连接情况
try:
    redis_client = redis.Redis(
        host=redis_host,
        port=redis_port,
        password=redis_password,  # 传入密码
        decode_responses=True,
        socket_connect_timeout=5
    )
    # 启动时测试连接
    if redis_client.ping():
        print(f"✅ Redis 连接成功: {redis_host}:{redis_port}")
    else:
        print("⚠️ Redis Ping 无响应")
        redis_client = None
except Exception as e:
    print(f"❌ Redis 连接失败: {e}")
    redis_client = None


#初始化数据库
db.init_app(app) # 复用models.py中的db实例
migrate = Migrate(app, db)
from models import Users, FruitVariety, Details 

# Flask-Login 和 密码安全
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash   # 密码加密和安全
from sqlalchemy import or_
import re

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

# 密码验证函数设计
"""
数字、大写字母、小写字母的混合,而且字符数要等于8个
新增一个验证函数validate_password
"""
def validate_password(password:str)->bool:
    if not re.search(r'\d', password):
        return False
    if not re.search(r'[a-z]', password):
        return False
    if not re.search(r'[A-Z]', password):
        return False
    if len(password) != 8:
        return False
    return True



# 全局钩子，用于在每一次请求的时候验证token
@app.before_request
def check_auth_token():
    # 跳过公开接口和登录注册等接口
    if request.path in [
       '/api/login', '/api/register', 
       '/api/fruits', '/api/search'
    ]:
        return None
    auth_header = request.headers.get('Authorization')
    token = None
    
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
    else:
        # 兼容自定义 Header
        token = request.headers.get('X-Session-Token')

    if not token:   
     return error('无认证', 401)    
    
    redis_key = f"session:{token}"
    try:
        # 在redis中查找对应内容，得到对应的唯一id
        user_id_str = redis_client.get(redis_key)
    except Exception as e:
        print(f"[Error] Redis 读取失败: {e}")
        return error('服务器内部错误', 500)
    
    try:
        user_id = int(user_id_str)
        user = Users.query.get(user_id)
        if not user:
            # 数据库中没有该用户（可能被删除），清理 Redis
            redis_client.delete(redis_key)
            return error('用户不存在', 401)
        
        # 将当前用户挂载到 flask.g 对象，供后续路由使用
        g.current_user = user
    except Exception as e:
        return error('认证解析失败', 401)

    return None


# 路由设计

# 根路由
# 根路由
@app.route('/')
def index():
    return jsonify({
        'message': "欢迎来到果蔬信息管理系统！",
        'status': "running",
        'endpoints': {
            # 用户相关
            "register": "/api/register (POST)",
            "login": "/api/login (POST)",
            "logout": "/api/logout (POST) [需登录]",
            "change_password": "/api/change-password (PATCH) [需登录]",
            
            # 短信验证 (新增)
            "sms_send": "/api/sms/send (POST) [需登录] - 发送验证码",
            "sms_verify": "/api/sms/verify (POST) [需登录] - 验证验证码",
            
            # 果蔬管理
            "fruits_list": "/api/fruits (GET) - 分页获取所有果蔬",
            "fruits_create": "/api/fruits (POST) [需登录] - 添加新果蔬",
            "fruit_detail": "/api/fruits/<id> (GET) [需登录] - 查看详情",
            "fruit_update": "/api/fruits/<id> (PATCH) [需登录] - 更新信息",
            "fruit_delete": "/api/fruits/<id> (DELETE) [需登录] - 删除果蔬",
            
            # 搜索
            "search": "/api/search?q=关键词 (GET) - 模糊搜索名称或类别"
        },
        "tip": "需登录接口请在 Header 中携带: Authorization: Bearer <token>"
    })

import secrets
# 登录功能
@app.route('/api/login', methods = ['POST'])
def login():
    data = request.get_json()
    account_1 = data.get('account')
    password_1 = data.get('password')

    user = Users.query.filter_by(account = account_1).first()
    if user and check_password_hash(user.password, password_1):
        # 如果用户存在并且密码匹配正确
        # 生成 32 位随机 Token
        session_token = secrets.token_hex(16)
        # 存入到redis中
        redis_key = f'session:{session_token}'
        # 设置七天有效期
        try:
            redis_client.setex(redis_key, 7*24*3600,str(user.id) )
        except Exception as e:
            print(f"[Error] Redis 存储 Token 失败: {e}")
            return error('服务器会话存储故障', 500)
        
        #返回 Token 给前端，不返回数据库 ID
        return success({
            'token': session_token,
            'expires_in': '7 days',
        }, '登录成功')
        

                 
                
# 注册功能
@app.route('/api/register',methods = ['POST'])
def register():
    data = request.get_json()
    account = data.get('account')
    password = data.get('password')

    if not account or not password:
        return error('账号和密码不能为空',400)
    if len(account) != 11 or not account.isdigit():
        return error("账号必须是11位数字", 400)
    if not validate_password(password):
        return error("密码必须为8位，且包含大小写字母和数字", 400)
    if Users.query.filter_by(account=account).first():
        return error("账号已存在", 409)        
             
    hashed_pw = generate_password_hash(password)
    new_user = Users(account=account, password=hashed_pw)
    db.session.add(new_user)
    db.session.commit()
    return success(message="注册成功")

    
# 登出功能
@app.route('/api/logout', methods = ['POST'])
def logout():
    # 前端需要在 Header 中带上 Token
    auth_header = request.headers.get('Authorization')
    token = None
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
    else:
        token = request.headers.get('X-Session-Token')

    if token:
        redis_key = f"session:{token}"
        try:
            redis_client.delete(redis_key)
        except Exception as e:
            print(f"[Warning] 删除 Token 失败: {e}")
    
    return success(message='已登出')           
           

# 验证码发送功能   
@app.route('/api/sms/send', methods = ['POST'])
def send_sms():
    if not g.current_user or not  hasattr(g, 'current_user'):
        return error(message='请先登录', code=401)
    current_phone = g.current_user.account

    debug_mode = os.environ.get('DEBUG', 'False').lower() == 'true'
    result = send_sms_code(phone=current_phone, redis_client=redis_client, debug_mode=debug_mode)
    if result['success']:
        return success(data={'debug_code': result.get('debug_code')}, message=result['message'])
    else:
        # 失败则返回对应的错误码（如 400 或 500）
        # 这里简单处理，统一返回 400，你也可以根据具体 message 区分
        return error(result['message'], 400)

# 验证码检查功能
@app.route('/api/sms/verify', methods=['POST'])
def verify_sms():
    if not hasattr(g, 'current_user') or not g.current_user:
        return error(message='请先登录', code=401)
    """
    校验短信验证码接口
    通常用于注册、找回密码等场景
    """
    data = request.get_json()
    if not data:
        return error('请求数据不能为空', 400)
        
    phone = g.current_user.account
    code = data.get('code')
    
    if not code:
        return error('验证码不能为空', 400)

    # 调用 sms.py 中的校验逻辑
    result = verify_sms_code(phone=phone, input_code=code, redis_client=redis_client)
    
    if result['success']:
        return success(message=result['message'])
    else:
        return error(result['message'], 400)



# 注销(删除账号)功能
@app.route('/api/delete-account', methods = ['DELETE'])
def delete_account():
    if not hasattr(g, 'current_user') or not g.current_user:
        return error(message='请先登录', code=401)
    data  = request.get_json()
    verify_method = data.get('verify_method')# password 或者sms

    user_delete = g.current_user

    if not user_delete:
        return error(message='用户不存在', code=404)
    # 分支验证
    verify = False
    if verify_method == 'password':
        password = data.get('password')
        # 密码验证
        if not password :
            return error(message= '请输入密码', code = 400)
        if check_password_hash(user_delete.password, password):
            verify = True
        else:
            return error(message='密码错误，验证失败', code=400)

        
    elif verify_method == 'sms':
        sms_code = data.get('sms_code')
        if not sms_code:
            return error(message= '请输入验证码', code = 400)
        else:
            sms_result = verify_sms_code(
            phone=g.current_user.account, 
            input_code=sms_code, 
            redis_client=redis_client
        )
        
        if sms_result.get('success'):
            verify = True
        else:
            return error(message=sms_result.get('message', '验证码无效'), code=400)
        
    else:
        return error(message='不支持的验证方式 (仅支持 password 或 sms)', code=400)     
       
    if verify:
    # 尝试删除账号
        try:
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                redis_client.delete(f"session:{token}")
            db.session.delete(user_delete)
            db.session.commit()
            return success(message='账号注销成功')
        except Exception as e:
            db.session.rollback() # 撤销工作台里所有未提交的操作，恢复到操作前的状态
            return error(message=f'账号注销失败:{str(e)}',code = 500)
            
    
    


# 密码修改功能
@app.route('/api/change-password',methods = ['PATCH'])
def change_password():
    if not hasattr(g, 'current_user') or not g.current_user:
        return error(message='请先登录', code=401)
    data = request.get_json()
    new_password = data.get('new_password')
    verify_method = data.get('verify_method')# password 或者sms
    
    # 密码验证
    if not new_password:
        return error(message= '新密码不能为空', code = 400)
    if not validate_password(new_password):
        return error(message= '密码必须为8位，且包含大小写字母和数字', code = 400)

    # 分支验证
    verify = False
    user = g.current_user
    if not user:
        return error(message='用户不存在', code=404)
    if verify_method == 'password':
        old_password = data.get('old_password')
        # 密码验证
        if not old_password :
            return error(message= '请输入旧密码', code = 400)
        if check_password_hash(user.password, old_password):
            verify = True
        else:
            return error(message='密码错误，验证失败', code=400)

        
    elif verify_method == 'sms':
        sms_code = data.get('sms_code')
        if not sms_code:
            return error(message= '请输入验证码', code = 400)
        else:
            sms_result = verify_sms_code(
            phone=user.account, 
            input_code=sms_code, 
            redis_client=redis_client
        )
        
        if sms_result.get('success'):
            verify = True
        else:
            return error(message=sms_result.get('message', '验证码无效'), code=400)
        
    else:
        return error(message='不支持的验证方式 (仅支持 password 或 sms)', code=400)     
       
    if verify:
    
        try:  # 异常捕获
            user.password = generate_password_hash(new_password)
            db.session.commit()
            # 删除已有的token要求重新登录
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                redis_client.delete(f"session:{token}")
            return success(message='密码修改成功，请重新登录')
        except Exception as e:
            db.session.rollback()
            return error(message=f'密码修改失败', code=500)





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
@app.route('/api/fruits/<int:fruit_id>', methods = ['GET'])
def fruit_details(fruit_id):
    if not hasattr(g, 'current_user') or not g.current_user:
        return error(message='请先登录', code=401)
    fruit = FruitVariety.query.get_or_404(fruit_id)
    data = fruit.to_dict()
    return success(data)


# 根据果蔬名称模糊查询功能
@app.route('/api/search', methods = ['GET'])
def search():
    # 从前端获取要查询的果蔬名称关键词
    q = request.args.get('q','').strip()
    page = request.args.get('page',1,type=int)
    per_page = request.args.get('per_page',10,type = int)

    if not q:
        return success({
            'results': [],
            'current_page':page,
            'pages':0,
            'total':0,
            'has_next': False,   
            'has_prev': False 
            })
    results = FruitVariety.query.filter(
        or_(
        FruitVariety.name.like(f"%{q}%"),
        FruitVariety.category.like(f"%{q}%")
        )
    )
    # 对搜索出来的结果进行分页
    pagination = results.paginate(page = page, per_page = per_page, error_out = False)
    return success({
        'results':[r.to_dict() for r in pagination.items],
        'current_page':page,
        'pages':pagination.pages,
        'total':pagination.total,
        'has_next': pagination.has_next,
        'has_prev': pagination.has_prev    
        })

# 种类添加功能
@app.route('/api/fruits', methods = ['POST'])
def add_fruits():
    if not hasattr(g, 'current_user') or not g.current_user:
        return error(message='请先登录', code=401)

    data = request.get_json()
    category = data.get('category')
    name = data.get('name')
    detail_data = data.get('detail',{})

    if not category or not name:
        return error("大类和品种名不能为空")
    try:
        new_fruit = FruitVariety(category = category, name = name)
        db.session.add(new_fruit)
        db.session.flush() # 获取ID

        detail = Details(
            variety_id=new_fruit.id,
            origin=detail_data.get('origin'),
            introduction=detail_data.get('introduction'),
            price_per_kg=detail_data.get('price_per_kg')

        )
        
        db.session.add(detail)
        db.session.commit()
        return success(new_fruit.to_dict(),'添加成功')
    except Exception as e:
        db.session.rollback()
        return error(message='种类添加失败，请重试', code=500)

# 种类删除功能
@app.route('/api/fruits/<int:fruit_id>', methods = ['DELETE'])
def delete_fruit(fruit_id):
    if not hasattr(g, 'current_user') or not g.current_user:
        return error(message='请先登录', code=401)
    fruit = FruitVariety.query.get_or_404(fruit_id)
    try:
        if fruit.detail:
            db.session.delete(fruit.detail) # 删除从表信息
        db.session.delete(fruit)    # 删除主表信息
        db.session.commit()
        return success()
    except Exception as e:
        db.session.rollback() # 撤销工作台里所有未提交的操作，恢复到操作前的状态
        return error(message=f'品种删除失败',code = 500)


# 种类内容修改功能
@app.route('/api/fruits/<int:fruit_id>',methods = ['PATCH'])
def change_detail(fruit_id):
    if not hasattr(g, 'current_user') or not g.current_user:
        return error(message='请先登录', code=401)
    fruit = FruitVariety.query.get_or_404(fruit_id)
    data = request.get_json()

    # 主信息部分修改
    if 'category' in data:
        fruit.category = data['category']
    if 'name' in data:
        fruit.name = data['name']

    # 详情信息部分修改
    detail_data = data.get('detail')
    # 检查用户是否传入详情信息
    if detail_data is not None:
        # 如果本来的果蔬种类fruit有对应的详情信息，要做的是更改
        if fruit.detail:
                for key in ['origin', 'introduction', 'price_per_kg']:
                    if key in detail_data:
                        setattr(fruit.detail, key, detail_data[key])
        else:   # 如果没有，就按照用户上传的信息创建
            fruit.detail = Details(
            variety_id=fruit.id,
            origin=detail_data.get('origin'),
            introduction=detail_data.get('introduction'),
            price_per_kg=detail_data.get('price_per_kg')
            )
            db.session.add(fruit.detail)
    
    try:
        db.session.commit()
        return success(message='信息修改成功')
    except Exception as e:
        db.session.rollback()
        return error(message=f'信息修改失败：{str(e)}', code=500)

    # 程序入口
if __name__ == '__main__':
    # 这里是配置debug mode的核心位置
    app.run(
        host='0.0.0.0',  # 允许外部访问
        port=5050,   # 运行端口
        debug=os.environ.get("DEBUG", "False").lower() == "true"      # 开启调试模式
    )