// Layui上传组件初始化
layui.use(['upload', 'table', 'layer'], function(){
    var upload = layui.upload;
    var table = layui.table;
    var layer = layui.layer;

    // 初始化表格
    // 分页文本配置
    table.render({
        lang: 'en',
        elem: '#taskTable',
        url: '/api/tasks',
        parseData: function(res){
            return {
                "code": 0,
                "msg": "",
                "count": res.length,
                "data": res
            };
        },
        autoSort: false,
        page: true
    });

    // 初始化上传组件
    upload.render({
        elem: '#dropZone',
        url: '/api/upload',
        accept: 'file',
        size: 200*1024,
        exts: 'pdf',
        done: function(res){
            if(res.code === 0){
                layer.msg(res.msg, {time: 2000});
                table.reload('taskTable');
                layer.closeAll('msg'); // 关闭所有消息层
                window.$('.layui-upload-file').val(''); // 清空文件选择框
            } else {
                layer.msg('上传失败：'+ res.msg);
            }
        },
        error: function(res){
            layer.msg('请求失败：'+ (res.msg || '网络异常'));
        }
    });

    // 表格操作事件
    // 删除事件处理已迁移到表格配置的done回调中
});


// 更新任务列表
const updateTaskList = async () => {
  try {
    const response = await fetch('/api/tasks');
    const tasks = await response.json();
    
    const taskList = document.getElementById('taskList');
    taskList.innerHTML = tasks.map(task => `
      <div class="task-item">
        <div>
          <span>${task.filename}</span>
          <span class="status ${task.status}">${task.status}</span>
        </div>
        ${task.status === 'completed' ? 
          `<div>
            <button onclick="downloadTask('${task.uid}')">Download</button>
            <button onclick="deleteTask('${task.uid}')">删除</button>
          </div>` : ''}
      </div>
    `).join('');
  } catch (error) {
    console.error('获取任务列表失败:', error);
  }
};

// 下载任务
const downloadTask = (uid) => {
  window.location.href = `/api/download/${uid}`;
};

// 删除任务
const deleteTask = async (uid) => {
  if (!confirm('确认删除该任务？')) return;
  
  try {
    const response = await fetch(`/api/tasks/${uid}`, { method: 'DELETE' });
    if (response.ok) {
      updateTaskList();
    }
  } catch (error) {
    alert('删除任务失败');
  }
};

// 初始化
document.addEventListener('DOMContentLoaded', () => {
  initUploader();
  setInterval(updateTaskList, 5000);
  updateTaskList();
});