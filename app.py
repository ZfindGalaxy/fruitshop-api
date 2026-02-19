import config
from flask import request, Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
import os   #实现交互
from flask_migrate import Migrate # 迁移配置
from sqlalchemy import MetaData
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase



#初始化flask应用
app = Flask(__name__)
# 从config文件中读取大写字段配置
app.config.from_object(config)



#初始化数据库
db = SQLAlchemy(app, )  # sqlalchemy是一个类，用于创建一个数据库操作的接口，封装了原装数据库的复杂性，传入已经建好的flask实例app
migrate = Migrate(app, db)
#定义数据库模型
#对应的数据库user表
class User(db.Model):
    #主键具有唯一性和非空性，会自增
    # db.Column是定义数据库表字段（列）的核心工具
    __tablename__ = 'user'
    id: Mapped[int] = mapped_column(db.Integer, primary_key = True, autoincrement= True) # 定义一个名为id的列，（数据类型为整型，注定该列为主键）
    name: Mapped[str] = mapped_column(db.String(50), nullable = False) # 定义一个名为name的列，字符串类型，禁止为空
    # 若要求业务电话号码唯一，可加上约束条件 unique = Ture
    phone: Mapped[str] = mapped_column(db.String(11), nullable = False )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "phone": self.phone
        }

# 基础路由
# 根路径，返回字符串
@app.route('/')
def index():

    return jsonify({
        "message": "欢迎使用手机号管理API",
        "endpoints":{
            "Get/users":'获取所有用户',
            "POST/users":'添加新用户',
            "DELETE/users/<id>":'删除指定用户'
        }
    })


#路由，Get请求，带参数查询
@app.route('/users', methods = ['GET'])
def get_users():
    name = request.args.get('name','').strip()
    # 按姓名筛选查询数据库数据
    if name:
        #.filter（），添加过滤条件
        # User.name.like 名字的模糊查询
        users = User.query.filter(User.name.like(f'%{name}%')).all()
    else:
        users = User.query.all()
    return jsonify([user.to_dict() for user in users])

# 路由，Post请求，提交数据
# 只允许提交请求
@app.route('/add', methods = ['POST'])
def add():
    data = request.get_json()
# 简单判断，不为空就添加数据
    if not data or not data.get('name') or not data.get('phone'):
        return jsonify({'error':"姓名或手机号无能为空"}),400

    name = data['name'].strip()
    phone = data['phone'].strip()

    if len(phone) != 11 or not phone.isdigit():
        return jsonify({'error':"手机号必须为11位数字"}),400

    # 在数据库中查询是否有完全重合的{姓名+电话},如果找到第一条匹配的就返回
    existing_user = User.query.filter_by(name = name, phone = phone).first()
    if existing_user:
        return jsonify({
            'error':f"用户{name},(手机号{phone}已存在)",
            'user':existing_user.to_dict()
        }),409

    else:
        new_user = User(name = name, phone = phone)
        # db.session 是SQLAlchemy的会话对象，管理数据库的连接和事务
        # 必须使用commit（）才会真正写入数据库
        db.session.add(new_user)
        db.session.commit()
        return jsonify(new_user.to_dict()),201 # 创建


# 路由，简单删除
#拒绝非数字路径
@app.route('/delete/<int:user_id>', methods = ['DELETE'])
def delete(user_id):
    # 根据输入的id查询，如果查不到就返回提示None
    user = User.query.get(user_id)
    if not user:
        return jsonify({
            'error':'用户不存在'
        }),404
    else:
        db.session.delete(user)
        db.session.commit()
    return jsonify({
        'message':'删除成功',
        'deleted_id': user_id
    }), 200


# 初始化数据库（仅创建MySQL表）
with app.app_context():
    db.create_all()


    # 程序入口
if __name__ == '__main__':
    # 这里是配置debug mode的核心位置
    app.run(
        host='0.0.0.0',  # 允许外部访问
        port=5050,   # 运行端口
        debug=True       # 开启调试模式
    )