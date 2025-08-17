# ESP32 Wake-on-LAN 系统

一个基于ESP32的Wake-on-LAN远程唤醒系统，支持通过HTTP API远程唤醒局域网内的计算机。

## 系统架构

- **ESP32设备**: 连接WiFi，轮询服务器获取唤醒指令，发送WOL魔术包
- **Go服务器**: 提供HTTP API，管理设备注册和消息队列
- **控制端**: 通过HTTP API发送唤醒指令

## 快速开始

### 1. 服务器端

```bash
cd src/server

# 使用命令行参数启动
go run main.go -api-key "your-secret-key" -port 8080

# 或使用环境变量
export ESP32_API_KEY="your-secret-key"
go run main.go -port 8080
```

### 2. ESP32端配置

安装 MircoPython 烧录到 ESP32 设备中：
* 可以借助 Tonny 烧录，简单方便；
* pycharm 中可以使用 MicroPython Tools (https://plugins.jetbrains.com/plugin/12220-micropython-tools) 插件进行开发调试；


编辑 `src/esp32/config.py`：

```python
# WiFi配置
WIFI_SSID = "your-wifi-name"
WIFI_PASSWORD = "your-wifi-password"

# 服务器配置
SERVER_HOST = "192.168.1.100"  # 你的服务器IP
SERVER_PORT = 8080

# API密钥（与服务器端保持一致）
API_KEY = "your-secret-key"
```

将代码上传到ESP32设备并运行 `main.py`。

### 3. 发送唤醒指令

```bash
# 获取已注册的设备列表
curl -H "X-API-Key: your-secret-key" http://your-server:8080/api/devices

# 发送WOL指令
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-key" \
  -d '{
    "device_id": "aa:bb:cc:dd:ee:ff",
    "target_mac": "00:11:22:33:44:55"
  }' \
  http://your-server:8080/api/wol/send
```

## API接口

### 健康检查
- `GET /health` - 服务器状态检查（无需认证）

### 设备管理
- `POST /api/devices/register` - 设备注册（ESP32自动调用）

### WOL功能
- `POST /api/wol/send` - 发送唤醒指令（控制端调用）
- `GET /api/wol/poll` - 轮询唤醒消息（ESP32自动调用）

## 配置说明

### 服务器配置
- API密钥支持命令行参数 `-api-key` 或环境变量 `ESP32_API_KEY`
- 服务器端口默认8080，可通过 `-port` 参数修改

### ESP32配置
- 修改 `config.py` 中的WiFi和服务器信息
- 确保API密钥与服务器端一致
- 支持调试模式，设置 `DEBUG = True`

## 注意事项

1. **网络要求**: ESP32和目标计算机需要在同一局域网内
2. **目标设备**: 确保目标计算机支持并启用了Wake-on-LAN功能
3. **防火墙**: 确保服务器端口（默认8080）和WOL端口（9）未被防火墙阻止
4. **API密钥**: 使用足够复杂的API密钥，并定期更换

## 文件结构

```
src/
├── esp32/          # ESP32 MicroPython代码
│   ├── config.py   # 配置文件
│   ├── main.py     # 主程序
│   ├── wifi_manager.py    # WiFi管理
│   ├── http_client.py     # HTTP客户端
│   └── wol_sender.py      # WOL发送器
└── server/         # Go服务器代码
    └── main.go     # 服务器主程序
```
