import time
import shlex

from flask import Blueprint, request, send_file, jsonify, current_app, abort, render_template
from app.models import ConversionTask
from app.extensions import db, scheduler
import os
import subprocess
import tarfile
import datetime
import uuid
import shutil
import pytz

main_bp = Blueprint('main', __name__)


@main_bp.route('/api/upload', methods=['POST'])
def handle_upload():
    if 'file' not in request.files:
        return jsonify({'code': 1, 'msg': '未上传文件'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'code': 2, 'msg': '文件名不能为空'}), 400

    # 验证文件类型
    if not file.filename.lower().endswith('.pdf'):
        return jsonify({'code': 3, 'msg': '仅支持PDF格式文件'}), 400

    # 生成唯一ID并创建上传目录
    uid = str(uuid.uuid4().hex)[0:8]
    upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], uid)
    os.makedirs(upload_dir, exist_ok=True)
    current_app.logger.debug(f'生成上传目录 | UID: {uid} | 路径: {upload_dir}')

    # 保存上传文件
    filename = file.filename  # 禁用secure_filename的ASCII过滤
    # filename = secure_filename(file.filename)
    file_path = os.path.join(upload_dir, filename)
    # 添加路径安全检查
    if not os.path.abspath(file_path).startswith(os.path.abspath(upload_dir)):
        raise ValueError('非法文件存储路径')
    file.save(file_path)
    current_app.logger.info(f'文件上传成功 | 路径: {file_path} | 大小: {os.path.getsize(file_path)}字节')

    # 创建数据库记录
    new_task = ConversionTask(
        uid=uid,
        filename=filename,
        status='pending',
        created_at=datetime.datetime.now(pytz.timezone('Asia/Shanghai'))
    )
    db.session.add(new_task)
    db.session.commit()
    current_app.logger.info(f'任务创建成功 | UID: {uid} | 状态: 等待中')
    current_app.logger.debug(f'数据库记录验证 | 任务是否存在: {ConversionTask.query.get(uid) is not None}')

    # 添加定时任务
    scheduler.add_job(
        id=uid,
        func=convert_pdf_task,
        args=[uid, file_path],
        trigger='date',
        run_date=None  # 立即执行
    )
    current_app.logger.info(f'定时任务已安排 | 任务ID: {uid} | 执行间隔: 5秒')
    current_app.logger.debug(f'调度器任务验证 | 任务存在: {scheduler.get_job(uid) is not None}')

    return jsonify({'code': 0, 'msg': '上传成功', 'data': {'uid': uid}})


@main_bp.route('/api/status/<uid>')
def check_status(uid):
    task = ConversionTask.query.get(uid)
    if not task:
        return {'error': 'Task not found'}, 404

    return {
        'uid': uid,
        'status': task.status,
        'progress': task.progress,
        'download_url': f'/api/download/{uid}' if task.status == 'completed' else None,
        'error': task.error_message if task.status == 'failed' else None
    }


@main_bp.route('/api/tasks/batch', methods=['DELETE'])
def batch_delete_tasks():
    uids = request.json.get('uids', [])
    if not uids:
        return jsonify({'code': 1, 'msg': '未选择任务'}), 400

    success_count = 0
    for uid in uids:
        task = ConversionTask.query.get(uid)
        if task:
            # 删除文件目录
            upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], uid)
            if os.path.exists(upload_dir):
                shutil.rmtree(upload_dir)
            # 删除数据库记录
            db.session.delete(task)
            success_count += 1
    
    db.session.commit()
    return jsonify({'code': 0, 'msg': f'成功删除{success_count}个任务'})

@main_bp.route('/api/tasks/<uid>', methods=['DELETE'])
def delete_task(uid):
    task = ConversionTask.query.get(uid)
    if not task:
        abort(404)

    # 删除文件目录
    upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], uid)
    if os.path.exists(upload_dir):
        shutil.rmtree(upload_dir)

    # 删除数据库记录
    db.session.delete(task)
    db.session.commit()
    return jsonify({'code': 0, 'msg': '删除成功'})


@main_bp.route('/api/tasks')
def get_all_tasks():
    tasks = ConversionTask.query.order_by(ConversionTask.created_at.desc()).all()
    return jsonify({
        "code": 0,
        "msg": "",
        "count": len(tasks),
        "data": [{
            'uid': task.uid,
            'filename': task.filename,
            'status': task.status,
            'created_at': task.created_at.isoformat(),
            'progress': task.progress
        } for task in tasks]
    })


@main_bp.route('/')
def serve_index():
    return render_template('index.html')


@main_bp.route('/<path:path>')
def catch_all(path):
    return render_template('index.html')


@main_bp.route('/api/download/<uid>')
def download_package(uid):
    base_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], uid)
    if not os.path.exists(base_dir):
        return {'error': 'Resource not found'}, 404

    # 直接使用预生成的压缩包
    output_path = os.path.join(base_dir, f'{uid}.tar.gz')

    # 重试机制（最多5次，每次间隔1秒）
    max_retries = 5
    for i in range(max_retries):
        if os.path.exists(output_path):
            break
        current_app.logger.info(f'压缩包未就绪，等待重试 ({i + 1}/{max_retries}) | UID: {uid}')
        time.sleep(1)
    else:
        current_app.logger.error(f'压缩包生成超时 | UID: {uid}')
        return {'error': 'Package generation timeout'}, 504

    current_app.logger.info(f'压缩包已就绪 | 路径: {output_path} | 大小: {os.path.getsize(output_path)}字节')

    return send_file(
        output_path,
        as_attachment=True,
        download_name=f'{uid}.tar.gz'
    )


def convert_pdf_task(uid, file_path):
    from app import app  # 添加应用导入

    with app.app_context():  # 包装应用上下文
        try:
            # 获取任务实例
            task = ConversionTask.query.get(uid)
            if not task:
                app.logger.error(f'Task {uid} not found')
                return

            # 更新任务状态为处理中
            task.status = 'processing'
            db.session.commit()
            app.logger.info(f'任务开始处理 | UID: {uid} | 文件: {os.path.basename(file_path)}')

            # 执行转换命令
            output_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], uid, 'output')
            cmd = f'magic-pdf -p {shlex.quote(file_path)} -o {shlex.quote(output_dir)} -m auto'
            app.logger.info(f'执行转换命令 | 命令: {cmd}')

            # 本地调试模式处理
            if os.environ.get('LOCAL_DEBUG', 'false').lower() == 'true':
                app.logger.info('本地调试模式 | 跳过实际转换，生成模拟输出')
                # 创建模拟输出目录结构
                os.makedirs(output_dir, exist_ok=True)
                # 生成模拟输出文件
                with open(os.path.join(output_dir, 'output.txt'), 'w') as f:
                    f.write('模拟转换输出内容')
                # 更新任务状态
                task.status = 'completed'
                task.progress = 100
            else:
                # 实际执行转换命令
                subprocess.run(cmd, shell=True, check=True)

            # 更新任务状态
            task.status = 'completed'
            task.progress = 100

            # 创建压缩包
            output_path = os.path.join(current_app.config['UPLOAD_FOLDER'], uid, f'{uid}.tar.gz')
            # 验证压缩包存储路径
            if os.path.commonpath([output_path, current_app.config['UPLOAD_FOLDER']]) \
                    != current_app.config['UPLOAD_FOLDER']:
                raise RuntimeError('压缩包生成路径异常')
            with tarfile.open(output_path, 'w:gz') as tar:
                tar.add(output_dir, arcname=os.path.basename(output_dir))

            db.session.commit()
            app.logger.info(
                f'任务处理完成 | UID: {uid} | 耗时: {datetime.datetime.utcnow() - task.created_at} | 压缩包: {output_path}')

        except Exception as e:
            app.logger.error(f'任务处理失败 | UID: {uid} | 错误: {str(e)}', exc_info=True)
            task = ConversionTask.query.get(uid)
            if task:
                task.status = 'failed'
                task.error_message = str(e)
                db.session.commit()
            app.logger.error(f'Task {uid} failed: {str(e)}')
