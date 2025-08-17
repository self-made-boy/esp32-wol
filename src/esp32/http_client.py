# HTTP客户端模块 - 简化版
# Simplified HTTP client for ESP32

import urequests
import ujson
import time
from config import (
    SERVER_HOST, SERVER_PORT, SERVER_PROTOCOL,
    API_POLL_ENDPOINT, API_REGISTER_ENDPOINT,
    REQUEST_TIMEOUT, DEBUG, API_KEY
)

class HTTPClient:
    def __init__(self):
        self.server_host = SERVER_HOST
        self.server_port = SERVER_PORT
        self.server_protocol = SERVER_PROTOCOL
        # 使用MAC地址作为设备ID
        self.device_id = self._get_mac_address()
        self.base_url = self.server_protocol + "://" + self.server_host + ":" + str(self.server_port)
        self.headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'ESP32-WOL-Client/1.0',
            'X-API-Key': API_KEY
        }
    
    def _get_mac_address(self):
        """获取ESP32的MAC地址作为设备ID"""
        import network
        wlan = network.WLAN(network.STA_IF)
        mac_bytes = wlan.config('mac')
        mac_address = ':'.join(['%02x' % b for b in mac_bytes])
        return mac_address
    
    def _make_request(self, method, endpoint, data=None, params=None):
        """发送HTTP请求的通用方法"""
        try:
            # 构造URL
            url = self.base_url + endpoint
            
            # 添加查询参数
            if params:
                query_string = '&'.join([str(k) + "=" + str(v) for k, v in params.items()])
                url += "?" + query_string
            
            if DEBUG:
                print("Making " + method + " request to: " + url)
            
            # 发送请求
            if method.upper() == 'GET':
                response = urequests.get(url, headers=self.headers, timeout=REQUEST_TIMEOUT)
            elif method.upper() == 'POST':
                json_data = ujson.dumps(data) if data else None
                response = urequests.post(url, data=json_data, headers=self.headers, timeout=REQUEST_TIMEOUT)
            else:
                raise ValueError("Unsupported HTTP method: " + method)
            
            # 检查响应状态
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    response.close()
                    return response_data, None
                except:
                    response_text = response.text
                    response.close()
                    return response_text, None
            else:
                error_msg = "HTTP " + str(response.status_code) + ": " + response.text
                response.close()
                return None, error_msg
                
        except Exception as e:
            error_msg = "Request error: " + str(e)
            if DEBUG:
                print(error_msg)
            return None, error_msg
    
    def poll_for_messages(self):
        """轮询服务器获取唤醒消息"""
        try:
            params = {
                'device_id': self.device_id
            }
            
            response_data, error = self._make_request('GET', API_POLL_ENDPOINT, params=params)
            
            if error:
                if DEBUG:
                    print("Poll request failed: " + str(error))
                return None, error
            
            # 解析响应 - 服务器返回PollResponse格式
            if isinstance(response_data, dict):
                messages = response_data.get('messages', [])
                total = response_data.get('total', 0)
                
                if total > 0 and len(messages) > 0:
                    # 返回第一条消息
                    first_message = messages[0]
                    message = {
                        'id': first_message.get('id', ''),
                        'target_mac': first_message.get('target_mac', ''),
                        'created_at': first_message.get('created_at', '')
                    }
                    if DEBUG:
                        print("Received WOL message: " + str(message))
                        print("Total messages: " + str(total))
                    return message, None
                else:
                    if DEBUG:
                        print("No pending messages")
                    return None, None
            else:
                if DEBUG:
                    print("Invalid response format")
                return None, "Invalid response format"
                
        except Exception as e:
            error_msg = "Poll error: " + str(e)
            if DEBUG:
                print(error_msg)
            return None, error_msg
    
    def register_device(self, device_info=None):
        """向服务器注册设备"""
        try:
            # 构造注册请求数据，使用MAC地址作为设备ID
            data = {
                'name': 'ESP32-' + self.device_id,
                'mac_address': self.device_id,  # device_id就是MAC地址
                'description': 'ESP32 WOL Device',
                'version': '1.0'
            }
            
            # 如果提供了额外的设备信息，更新数据
            if device_info:
                data.update(device_info)
            
            response_data, error = self._make_request('POST', API_REGISTER_ENDPOINT, data=data)
            
            if error:
                if DEBUG:
                    print("Device registration failed: " + str(error))
                return False, error
            
            if DEBUG:
                print("Device registered successfully: " + self.device_id)
                print("MAC Address: " + self.device_id)
            return True, None
            
        except Exception as e:
            error_msg = "Device registration error: " + str(e)
            if DEBUG:
                print(error_msg)
            return False, error_msg