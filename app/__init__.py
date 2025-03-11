import os

from flask import Flask
from .config import Config
from .extensions import db, scheduler, migrate
from .routes import main_bp

# 直接创建应用实例
app = Flask(__name__,
            template_folder='../templates',
            static_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), '../static'),
            static_url_path='/',
            )
app.config['JSON_AS_ASCII'] = False  # 新增配置支持中文
app.config.from_object(Config)

# 初始化扩展
db.init_app(app)
migrate.init_app(app, db)  # 添加migrate初始化

# 注册蓝图
app.register_blueprint(main_bp)

# 显式添加静态文件路由
@app.route('/static/<path:filename>')
def static_files(filename):
    return app.send_static_file(filename)

# 初始化数据库
# 确保上传目录存在
with app.app_context():
    upload_dir = app.config['UPLOAD_FOLDER']
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir, exist_ok=True)
        app.logger.info(f'创建上传目录: {upload_dir}')
    else:
        app.logger.info(f'上传目录已存在: {upload_dir}')
    db.create_all()
