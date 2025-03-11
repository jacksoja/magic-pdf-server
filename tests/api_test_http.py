import os
import requests
import time


def upload_file(url, file_path):
    # 打开文件以二进制模式读取
    with open(os.path.join(os.path.dirname(__file__), file_path), 'rb') as file:
        # 创建文件字典，用于上传
        files = {'file': (os.path.basename(file_path), file)}

        # 发送POST请求
        response = requests.post(url, files=files)

        # 检查响应状态码
        if response.status_code == 200:
            print("文件上传成功！")
            print("响应内容:", response.json())
            return response.json().get('data').get('uid')
        else:
            print("文件上传失败！")
            print("状态码:", response.status_code)
            print("错误信息:", response.text)
            return None


def download_file(url, uid, download_path):
    # 构建下载URL
    download_url = f"{url}/{uid}"

    # 发送GET请求
    response = requests.get(download_url)

    # 检查响应状态码
    if response.status_code == 200:
        print("文件下载成功！")
        # 保存文件到指定路径
        with open(download_path, 'wb') as file:
            file.write(response.content)
    else:
        print("文件下载失败！")
        print("状态码:", response.status_code)
        print("错误信息:", response.json())


def test_status_check(url, uid):
    # 查询任务状态
    status_url = f"{url}/{uid}"
    response = requests.get(status_url)

    # 验证基本响应格式
    assert response.status_code in [200, 404], f"无效状态码: {response.status_code}"

    if response.status_code == 200:
        data = response.json()
        assert 'status' in data, "响应缺少status字段"
        assert data['status'] in ['pending', 'completed', 'failed'], "无效的任务状态"

    return response.json()


if __name__ == "__main__":
    is_download = False
    is_local_debug = True
    if is_local_debug:
        server_url = "http://127.0.0.1:5001"
    else:
        server_url = "http://{your_gpu_server}:8081"

    if is_download:
        # 下载接口路径
        download_endpoint = "/api/download"
        # 完整的下载URL
        download_url = server_url + download_endpoint
        uid = "65511d2fa7464318a68623adfce421cc"
        # 下载文件保存路径
        download_path = f"./tmp_downloads/{uid}.tar.gz"
        # 调用下载函数
        download_file(download_url, uid, download_path)
    else:
        # 服务器地址和端口
        # 上传接口路径
        upload_endpoint = "/api/upload"
        # 完整的上传URL
        upload_url = server_url + upload_endpoint
        # 要上传的文件路径
        file_to_upload = "./test.pdf"

        # 调用上传函数
        uid = upload_file(upload_url, file_to_upload)

        # 添加延时查询逻辑
        print("\n等待2秒后查询状态...")

        time.sleep(2)
        test_status_check_url = server_url + "/api/status"
        # 执行状态查询
        print(f"\n开始查询转换状态：{uid}")
        status_response = test_status_check(test_status_check_url, uid)
        print(f"状态查询结果: {status_response.get('status')}")
