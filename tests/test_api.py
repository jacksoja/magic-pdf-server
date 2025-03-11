import os
import sys
import uuid

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
import pytest

from app.models import ConversionTask
from app import db
from io import BytesIO

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def client():
    # 从全局导入应用实例
    from app import app

    # 应用测试配置
    app.config.update({
        'TESTING': True,
        'UPLOAD_FOLDER': 'tmp_uploads',
        'SCHEDULER_JOBSTORES': {'default': SQLAlchemyJobStore(url='sqlite:///:memory:')},
        'SCHEDULER_EXECUTORS': {'default': {'type': 'threadpool', 'max_workers': 20}},
        'SCHEDULER_JOB_DEFAULTS': {'coalesce': False, 'max_instances': 3}
    })

    # 初始化数据库
    with app.app_context():
        db.drop_all()
        db.create_all()

    # 创建测试客户端
    return app.test_client()


def test_file_upload_success(client, tmpdir):
    # Test normal PDF file upload
    data = {
        'file': (open(os.path.join(os.path.dirname(__file__), 'test.pdf'), 'rb'), 'test.pdf')
    }

    # Check test file exists
    assert response.status_code == 200

    # Test no file uploaded
    response = client.post('/api/upload')

    # Test empty filename
    data = {'file': (BytesIO(b''), '')}

    # Create test directory and files
    test_dir = tmpdir.mkdir('test_dir')

    # Test valid UID
    test_file = (BytesIO(b'PDF content'), 'test.pdf')
    upload_response = client.post('/upload', data={'file': test_file}, content_type='multipart/form-data')

    # Test pending status
    assert status_response.json['status'] == 'pending'

    # Test invalid UID
    invalid_response = client.get('/status/invalid_uid')
    assert invalid_response.status_code == 404

    # 测试completed状态
    task = ConversionTask.query.get(uid)
    task.status = 'completed'
    db.session.commit()
    completed_response = client.get(f'/status/{uid}')
    assert completed_response.json['download_url'] is not None

    # 测试failed状态
    task.status = 'failed'
    db.session.commit()
    failed_response = client.get(f'/status/{uid}')
    assert failed_response.json['status'] == 'failed'
