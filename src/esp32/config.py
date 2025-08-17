# ESP32 WOL系统配置文件 - 简化版
# Simplified configuration file for ESP32 WOL system

# WiFi配置
WIFI_SSID = "xx"  # 替换为你的WiFi名称
WIFI_PASSWORD = "xx"  # 替换为你的WiFi密码

# 服务器配置
SERVER_HOST = "192.168.1.11"  # 替换为你的服务器IP地址
SERVER_PORT = 8080  # 服务器端口
SERVER_PROTOCOL = "http"  # 协议类型

# 设备配置
# 设备ID直接使用ESP32的MAC地址，无需配置

# 轮询配置
POLL_INTERVAL = 5  # 轮询间隔（秒）
REQUEST_TIMEOUT = 125  # 请求超时时间（秒）

# WOL配置
WOL_PORT = 9  # WOL魔术包端口
BROADCAST_IP = "255.255.255.255"  # 广播地址

# 调试配置
DEBUG = True  # 是否启用调试输出

# API认证配置
API_KEY = "esp32-wol-2024"  # API密钥

# API端点
API_POLL_ENDPOINT = "/api/wol/poll"  # 轮询端点
API_REGISTER_ENDPOINT = "/api/devices/register"  # 设备注册端点

# 网络配置
WIFI_CONNECT_TIMEOUT = 30  # WiFi连接超时时间（秒）
WIFI_RETRY_COUNT = 100  # WiFi连接重试次数