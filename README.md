# WatchYourBehind-Server

后端基于 Flask，支持设备数据上报、自动建表、MySQL远程连接。

## 项目结构
```
WatchYourBehind-Server/
├── app.py
├── models.py
├── config.py
├── requirements.txt
└── README.md
```

## 快速启动
1. 安装依赖
   ```
   pip install -r requirements.txt
   ```
2. 配置数据库连接（编辑 config.py）
3. 启动服务
   ```
   python app.py
   ```

## 主要文件说明
- app.py：主入口，API路由
- models.py：数据库模型
- config.py：数据库连接配置
- requirements.txt：依赖列表

## API 示例
- POST /api/v1/device/sync
  - 设备数据上报接口
  - 请求体示例：
    ```json
    {
      "device_mac": "AA:BB:CC:DD:EE:FF",
      "targets": [
        {"x":100,"y":200,"speed":10,"resolution":360},
        {"x":300,"y":400,"speed":20,"resolution":360}
      ]
    }
    ```
  - 响应示例：
    ```json
    {
      "code": 200,
      "data": {
        "next_interval": 1000,
        "server_time": 1715000000,
        "pending_cmd": null
      }
    }
    ```
