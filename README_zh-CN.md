magic-pdf-server

# 基于 MinerU 的 magic-pdf cli 实现的一个 PDF 转 Markdown 服务

## 如何使用？

### 1. 启动服务

```shell
# 克隆代码
git clone https://github.com/soja/pdf-to-markdown.git
# 启动服务
cd pdf-to-markdown/
docker-compose up -d
```

### 2. 页面效果
![demo-page.png](readme/img/demo-page.png)


## MinerU 使用参考

https://github.com/opendatalab/MinerU/blob/master/README_zh-CN.md#%E4%BD%BF%E7%94%A8GPU

### 1.确认 cuda 环境
```bash
nvidia-smi
```

### 2.下载安装
```bash
wget https://gcore.jsdelivr.net/gh/opendatalab/MinerU@master/docker/china/Dockerfile -O Dockerfile
docker build -t mineru:latest .
docker run -it --name mineru --gpus=all mineru:latest /bin/bash -c "echo 'source /opt/mineru_venv/bin/activate' >> ~/.bashrc && exec bash"
magic-pdf --help
```



#### MinerU Dockerfile 内容参考

```Dockerfile
# Use the official Ubuntu base image
FROM ubuntu:22.04

# Set environment variables to non-interactive to avoid prompts during installation
ENV DEBIAN_FRONTEND=noninteractive

# Update the package list and install necessary packages
RUN apt-get update && \
    apt-get install -y \
        software-properties-common && \
    add-apt-repository ppa:deadsnakes/ppa && \
    apt-get update && \
    apt-get install -y \
        python3.10 \
        python3.10-venv \
        python3.10-distutils \
        python3-pip \
        wget \
        git \
        libgl1 \
        libglib2.0-0 \
        && rm -rf /var/lib/apt/lists/*

# Set Python 3.10 as the default python3
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1

# Create a virtual environment for MinerU
RUN python3 -m venv /opt/mineru_venv

# Activate the virtual environment and install necessary Python packages
RUN /bin/bash -c "source /opt/mineru_venv/bin/activate"
RUN /bin/bash -c "pip3 install --upgrade pip -i https://mirrors.aliyun.com/pypi/simple"
RUN /bin/bash -c "wget https://gcore.jsdelivr.net/gh/opendatalab/MinerU@master/docker/china/requirements.txt -O requirements.txt"
RUN /bin/bash -c "pip3 install -r requirements.txt --extra-index-url https://wheels.myhloli.com --ignore-installed"
RUN /bin/bash -c "pip3 install paddlepaddle-gpu==3.0.0rc1 -i https://www.paddlepaddle.org.cn/packages/stable/cu118/"

# Copy the configuration file template and install magic-pdf latest
RUN /bin/bash -c "wget https://gcore.jsdelivr.net/gh/opendatalab/MinerU@master/magic-pdf.template.json"
RUN /bin/bash -c "cp magic-pdf.template.json /root/magic-pdf.json"
RUN /bin/bash -c "source /opt/mineru_venv/bin/activate"
RUN /bin/bash -c "pip3 install -U magic-pdf -i https://mirrors.aliyun.com/pypi/simple"

# Download models and update the configuration file
RUN /bin/bash -c "pip3 install modelscope"
RUN /bin/bash -c "wget https://gcore.jsdelivr.net/gh/opendatalab/MinerU@master/scripts/download_models.py -O download_models.py"
RUN /bin/bash -c "python3 download_models.py"
RUN /bin/bash -c "sed -i 's|cpu|cuda|g' /root/magic-pdf.json"

# Set the entry point to activate the virtual environment and run the command line tool
ENTRYPOINT ["/bin/bash", "-c", "source /opt/mineru_venv/bin/activate && exec \"$@\"", "--"]

```

#### minerU requirements.txt 内容参考

```requirements
boto3>=1.28.43
Brotli>=1.1.0
click>=8.1.7
PyMuPDF>=1.24.9,<=1.24.14
loguru>=0.6.0
numpy>=1.21.6,<2.0.0
fast-langdetect>=0.2.3,<0.3.0
scikit-learn>=1.0.2
pdfminer.six==20231228
unimernet==0.2.3
torch>=2.2.2,<=2.3.1
torchvision>=0.17.2,<=0.18.1
matplotlib
ultralytics>=8.3.48
paddleocr==2.7.3
struct-eqtable==0.3.2
einops
accelerate
rapidocr-paddle>=1.4.5,<2.0.0
rapidocr-onnxruntime>=1.4.4,<2.0.0
rapid-table>=1.0.3,<2.0.0
doclayout-yolo==0.0.2b1
openai
detectron2

```

#### download_models.py 内容参考
```python
import json
import os

import requests
from modelscope import snapshot_download


def download_json(url):
    # 下载JSON文件
    response = requests.get(url)
    response.raise_for_status()  # 检查请求是否成功
    return response.json()


def download_and_modify_json(url, local_filename, modifications):
    if os.path.exists(local_filename):
        data = json.load(open(local_filename))
        config_version = data.get('config_version', '0.0.0')
        if config_version < '1.1.1':
            data = download_json(url)
    else:
        data = download_json(url)

    # 修改内容
    for key, value in modifications.items():
        data[key] = value

    # 保存修改后的内容
    with open(local_filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


if __name__ == '__main__':
    mineru_patterns = [
        "models/Layout/LayoutLMv3/*",
        "models/Layout/YOLO/*",
        "models/MFD/YOLO/*",
        "models/MFR/unimernet_small_2501/*",
        "models/TabRec/TableMaster/*",
        "models/TabRec/StructEqTable/*",
    ]
    model_dir = snapshot_download('opendatalab/PDF-Extract-Kit-1.0', allow_patterns=mineru_patterns)
    layoutreader_model_dir = snapshot_download('ppaanngggg/layoutreader')
    model_dir = model_dir + '/models'
    print(f'model_dir is: {model_dir}')
    print(f'layoutreader_model_dir is: {layoutreader_model_dir}')

    json_url = 'https://gcore.jsdelivr.net/gh/opendatalab/MinerU@master/magic-pdf.template.json'
    config_file_name = 'magic-pdf.json'
    home_dir = os.path.expanduser('~')
    config_file = os.path.join(home_dir, config_file_name)

    json_mods = {
        'models-dir': model_dir,
        'layoutreader-model-dir': layoutreader_model_dir,
    }

    download_and_modify_json(json_url, config_file, json_mods)
    print(f'The configuration file has been configured successfully, the path is: {config_file}')
```

