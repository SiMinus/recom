from flask import Flask, url_for, render_template, jsonify, Config, request
from flask_migrate import Migrate
from flask_security import Security
from flask_security.utils import encrypt_password
from flask_admin import helpers as admin_helpers
from adminlte.admin import AdminLte, admins_store, admin_db
from adminlte.models import Role, User
from adminlte.views import FaLink, AdminsView

from flask_admin import menu

from models import db
from models.message import Message
from models.data_source import DataSource
from models.data_table import DataTable
from models.data_feature import DataFeature
from models.portrait_user import PortraitUser
from models.model_admin import ModelAdmin
from models.model_train import ModelTrain
from models.model_pub import ModelPub
from models.model_output import ModelOutput
from models.model_strategy import ModelStrategy
from models.model_monitor import ModelMonitor

from views.index import IndexView
from views.message import MessageView
from views.data_source import DataSourceView
from views.data_table import DataTableView
from views.data_feature import DataFeatureView
from views.portrait_user import PortraitUserView
from views.model_admin import ModelAdminView
from views.model_train import ModelTrainView
from views.model_pub import ModelPubView
from views.model_output import ModelOutputView
from views.model_strategy import ModelStrategyView
from views.model_monitor import ModelMonitorView

from tools.utils import *
from ml.model import utils as ai
import requests
import time
import asyncio
from datetime import datetime


app = Flask(__name__)
# app.config.from_pyfile('config.ini')
# 需要后台调用，所以使用 configparser 读取
# 注意 working directory
conf_ini = read_flask_config()
app.config.from_mapping(conf_ini)

sys_conf = {'title': 'KnifeREC', 'author': 'zergskj'}

# 存储 token 和过期时间
token_data = {
    "token": None,
    "expiry_time": None
}

# 获取 token 的函数，检查是否过期，若过期则重新获取
def get_token():
    global token_data
    current_time = time.time()  # 获取当前时间戳（秒）

    # 检查 token 是否有效
    if token_data["token"] is None or token_data["expiry_time"] is None or current_time > token_data["expiry_time"]:
        # Token 不存在或已经过期，重新获取
        print("Token expired or not found. Fetching a new token...")

        # Token 获取请求
        url = "https://iam.cn-southwest-2.myhuaweicloud.com/v3/auth/tokens"
        headers = {'Content-Type': 'application/json'}
        data = {
            "auth": {
                "identity": {
                    "methods": ["password"],
                    "password": {
                        "user": {
                            "domain": {"name": "wh_morumbit"},
                            "name": "zhanglisheng",
                            "password": "TJ@123456"
                        }
                    }
                },
                "scope": {
                    "project": {"name": "cn-southwest-2"}
                }
            }
        }

        response = requests.post(url, json=data, headers=headers)
        if response.status_code == 201:
            data = response.json()
            auth_token = response.headers.get('X-Subject-Token', None)
            token_data["token"] = auth_token
            print("Token retrieved:", token_data["token"])

            # 获取expires_at（例如 '2024-11-29T09:25:19.241000Z'）
            expires_at_str = data['token']['expires_at']

            # 解析expires_at字符串为datetime对象
            expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))  # 处理时区标志'Z'为'+00:00'
            
            # 转换为Unix时间戳（秒）
            token_data["expiry_time"] = expires_at.timestamp()  # 设置过期时间
            print("Token expiry time:", token_data["expiry_time"])

            return token_data["token"]
        else:
            print("Failed to fetch token. Status code:", response.status_code)
            return None
    else:
        print("Token is valid, no need to fetch a new one.")
        return token_data["token"]




@app.route('/')
def index():
    return render_template("index.html", sys=sys_conf)

@app.route('/recommend', methods=['POST'])
def recommend():
    url = 'https://infer-modelarts-cn-southwest-2.myhuaweicloud.com/v1/infers/22132a9e-2f02-4c5d-973b-e15abc537368/recommend'

    # 获取表单数据
    user_id = request.form.get('id').strip()
    print(f"Received user_id: {user_id}")
    if user_id:
        try:
            # 将 ID 转换为整数
            user_id = int(user_id)
            
        except ValueError:
            result = "请输入有效的数字！"
            return render_template('index.html', result=result, sys=sys_conf)
        # 获取 token
        token = get_token()  # 不再需要 async/await

        if token is None:
            result = "无法获取有效的 Token，请稍后再试。"
            return render_template('index.html', result=result, sys=sys_conf)

        # 发送推荐请求
        headers = {'Content-Type': 'application/json', 'X-Auth-Token': token}
        body = {"itemID": user_id, "K": 5}

        response = requests.post(url, json=body, headers=headers)  # 调用推荐逻辑

        if response.status_code == 200:
            result = response.json()  # 获取并解析推荐结果
            return render_template('index.html', result=result, sys=sys_conf)  # 返回结果到首页
        else:
            result = f"推荐请求失败，错误代码：{response.status_code}"
            return render_template('index.html', result=result, sys=sys_conf)
        
    else:
        result = "请输入 ID！"
        return render_template('index.html', result=result, sys=sys_conf)




@app.route('/predict')
def predict(type='sort'):
    # todo 返回预测结果
    result = {'user_id': '1', 'prod_id': ''}
    try:
        result = ai.model_predict()
    except Exception as e:
        print(e)
    return jsonify(result)


db.init_app(app)
db.app = app
migrate = Migrate(app, db)
admin_migrate = Migrate(app, admin_db)

security = Security(app, admins_store)

admin = AdminLte(app, skin='green', name='KnifeREC', index_view=IndexView(endpoint=None), short_name="<b>K</b>R",
                 long_name=u"<b>KnifeREC</b>推荐系统")


def create_menu():
    admin.add_view(DataSourceView(DataSource, db.session, name=u'数据源', menu_icon_value='fa-database'))
    admin.add_view(DataTableView(DataTable, db.session, name=u"数据表", menu_icon_value='fa-table'))
    admin.add_view(DataFeatureView(DataFeature, db.session, name=u"特征工程", menu_icon_value='fa-filter'))

    admin.add_view(MessageView(Message, db.session, name=u"商家画像", menu_icon_value='fa-user-circle'))
    admin.add_view(PortraitUserView(PortraitUser, db.session, name=u"用户画像", menu_icon_value='fa-user'))

    admin.add_view(ModelAdminView(ModelAdmin, db.session, name=u"模型管理", menu_icon_value='fa-cube'))
    admin.add_view(ModelTrainView(ModelTrain, db.session, name=u"模型训练", menu_icon_value='fa-retweet'))
    admin.add_view(ModelOutputView(ModelOutput, db.session, name=u"模型输出", menu_icon_value='fa-rocket'))
    admin.add_view(ModelStrategyView(ModelStrategy, db.session, name=u"策略设置", menu_icon_value='fa-gears'))

    admin.add_view(ModelPubView(ModelPub, db.session, name=u"模型部署", menu_icon_value='fa-tasks'))
    admin.add_view(ModelMonitorView(ModelMonitor, db.session, name=u"模型监控", menu_icon_value='fa-laptop'))

    # admin.add_view(AdminsView(User, admin_db.session, name=u"管理员", menu_icon_value='fa-user-secret'))
    admin.set_category_icon(name='Author', icon_value='fa-address-card')


create_menu()

@security.context_processor
def security_context_processor():
    return dict(
        admin_base_template=admin.base_template,
        admin_view=admin.index_view,
        h=admin_helpers,
        get_url=url_for
    )


@app.cli.command()
def build_sample_db():
    """
    Populate a small db with some example entries.
    """
    admin_db.drop_all()
    admin_db.create_all()

    with app.app_context():
        super_admin_role = Role(name='superadmin')
        admin_role = Role(name='admin')
        admin_db.session.add(super_admin_role)
        admin_db.session.add(admin_role)
        admin_db.session.commit()

        test_user = admins_store.create_user(
            first_name='kejia',
            last_name='shao',
            email='admin@admin.com',
            password=encrypt_password('admin'),
            roles=[super_admin_role, admin_role]
        )
        admin_db.session.add(test_user)
        admin_db.session.commit()
    return


if __name__ == '__main__':
    app.run()
