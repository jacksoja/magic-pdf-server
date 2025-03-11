import os
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore


class Config:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(os.path.dirname(os.path.abspath(__file__)), '../db.sqlite3')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(BASE_DIR, '../.uploads')
    MAX_CONTENT_LENGTH = 200 * 1024 * 1024
    SCHEDULER_JOB_STORES = {
        'default': SQLAlchemyJobStore(url=SQLALCHEMY_DATABASE_URI)
    }
    SCHEDULER_API_ENABLED = False
