# model
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData,Text, Float,ForeignKey
from datetime import datetime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


# 定义命名约定的Base类
class Base(DeclarativeBase):
    metadata = MetaData(naming_convention={
        # ix: index，索引。
        "ix": 'ix_%(column_0_label)s',
        # un：unique，唯一约束
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        # ck：Check，检查约束
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        # fk：Foreign Key，外键约束
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        # pk：Primary Key，主键约束
        "pk": "pk_%(table_name)s"
    })
db = SQLAlchemy(model_class=Base)

# 设计表格，表格一：用户数据，用于登录，注册，修改，注销等功能的实现对应表格，用于储存用户账号和密码
# users：Password and Account
class Users(db.Model):
    __tablename__ = 'users'
    id:Mapped[int] = mapped_column(db.Integer,primary_key = True, autoincrement= True)
    account:Mapped[str] = mapped_column(db.String(11),nullable=False,unique=True)
    password:Mapped[str] = mapped_column(db.String(200),nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'account': self.account
        }

# 设计表格，表格二：果蔬种类，用于查询果蔬信息，添加果蔬种类与详情，删除果蔬种类与详情，修改内容
# FruitVariety：Category具体品种如富士山，Name大类如苹果
class FruitVariety(db.Model):
    __tablename__ = 'fruit_varieties'
    id:Mapped[int] = mapped_column(db.Integer,primary_key = True, autoincrement= True)
    category:Mapped[str] = mapped_column(db.String(100),nullable=False)
    name:Mapped[str] = mapped_column(db.String(100),nullable=False)

    # 关联设计
    detail: Mapped["Details"] = relationship("Details", back_populates="variety", uselist=False)

    def to_dict(self):
        return {
            'id': self.id,
            'category': self.category,
            'name': self.name,
            'detail': self.detail.to_dict() if self.detail else None
        }


# 设计表格，表格三：果蔬详情，通过与表二的id相关联获取详情
# detail：  variety_id，origin产地，introduction介绍，price_per_kg单价，created_at
class Details(db.Model):
    __tablename__ = 'details'
    id:Mapped[int] = mapped_column(db.Integer, primary_key=True)
    variety_id:Mapped[int] = mapped_column(db.Integer, db.ForeignKey('fruit_varieties.id'), unique=True, nullable=False)
    origin:Mapped[str] = mapped_column(db.String(100))        # 产地
    introduction:Mapped[str] = mapped_column(db.Text)         # 介绍
    price_per_kg:Mapped[float] = mapped_column(db.Float)        # 单价（可选）
    created_at:Mapped[datetime] = mapped_column(db.DateTime, default=datetime.utcnow)
    # 关联设计
    variety: Mapped["FruitVariety"] = relationship("FruitVariety", back_populates="detail")

    def to_dict(self):
        return {
            'id': self.id,
            'variety_id': self.variety_id,  # 关键：只返回ID
            'origin': self.origin,
            'introduction': self.introduction,
            'price_per_kg': self.price_per_kg,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }