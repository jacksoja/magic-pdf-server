from flask_sqlalchemy import SQLAlchemy
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from concurrent.futures import ThreadPoolExecutor
from flask_migrate import Migrate

# 初始化数据库扩展
db = SQLAlchemy()

# 初始化定时任务调度器
scheduler = BackgroundScheduler({
    'default': SQLAlchemyJobStore(url='sqlite:///scheduler.db')
})
scheduler.start()

# 初始化线程池
executor = ThreadPoolExecutor(max_workers=4)

# 初始化其他扩展
migrate = Migrate()