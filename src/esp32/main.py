# ESP32 WOL系统主程序 - 简化版
# Simplified ESP32 Wake-on-LAN system

import time
import gc
from machine import reset
from wifi_manager import WiFiManager
from wol_sender import WOLSender
from http_client import HTTPClient
from config import POLL_INTERVAL, DEBUG

class ESP32WOLSystem:
    def __init__(self):
        self.wifi_manager = WiFiManager()
        self.wol_sender = WOLSender()
        self.http_client = HTTPClient()
        self.is_running = True
        
        if DEBUG:
            print("ESP32 WOL System initialized - Device ID: " + self.http_client.device_id)
    
    def initialize_system(self):
        """初始化系统"""
        try:
            if DEBUG:
                print("Initializing ESP32 WOL System...")
            
            # 连接WiFi
            if not self.wifi_manager.connect():
                if DEBUG:
                    print("Failed to connect to WiFi")
                return False
            
            # 注册设备
            if DEBUG:
                print("Registering device...")
            
            device_info = {
                'ip_address': self.wifi_manager.get_ip(),
                'network_info': self.wifi_manager.get_network_info()
            }
            
            success, error = self.http_client.register_device(device_info)
            if not success:
                if DEBUG:
                    print("Device registration failed: " + str(error))
            
            if DEBUG:
                print("System initialization completed")
            
            return True
            
        except Exception as e:
            if DEBUG:
                print("System initialization error: " + str(e))
            return False
    
    def process_wol_message(self, message):
        """处理WOL消息"""
        try:
            target_mac = message.get('target_mac')
            
            if not target_mac:
                if DEBUG:
                    print("No target MAC address in message")
                return False
            
            if DEBUG:
                print("Processing WOL message for MAC: " + target_mac)
            
            # 发送WOL包
            success = self.wol_sender.send_wol_packet(target_mac)
            
            if success:
                if DEBUG:
                    print("WOL packet sent successfully to " + target_mac)
                return True
            else:
                if DEBUG:
                    print("Failed to send WOL packet to " + target_mac)
                return False
                
        except Exception as e:
            if DEBUG:
                print("WOL message processing error: " + str(e))
            return False
    
    def poll_server(self):
        """轮询服务器获取消息"""
        try:
            # 检查WiFi连接
            if not self.wifi_manager.auto_reconnect():
                if DEBUG:
                    print("WiFi connection lost, skipping poll")
                return False
            
            # 轮询消息
            message, error = self.http_client.poll_for_messages()
            
            if error:
                if DEBUG:
                    print("Poll error: " + str(error))
                return False
            
            # 处理消息
            if message:
                return self.process_wol_message(message)
            
            return True
            
        except Exception as e:
            if DEBUG:
                print("Poll server error: " + str(e))
            return False
    
    def run(self):
        """主运行循环"""
        try:
            if DEBUG:
                print("Starting ESP32 WOL System...")
            
            # 初始化系统
            if not self.initialize_system():
                if DEBUG:
                    print("System initialization failed")
                return
            
            # 主循环
            last_poll_time = 0  # 初始化轮询时间
            while self.is_running:
                try:
                    current_time = time.time()
                    
                    # 检查是否到了轮询时间
                    if current_time - last_poll_time >= POLL_INTERVAL:
                        self.poll_server()
                        last_poll_time = current_time
                    
                    # 内存清理
                    gc.collect()
                    
                    # 短暂休眠
                    time.sleep(1)
                except KeyboardInterrupt:
                    if DEBUG:
                        print("\nReceived interrupt signal, shutting down...")
                    self.is_running = False
                    break
                    
                except Exception as e:
                    if DEBUG:
                        print("Main loop error: " + str(e))
                    time.sleep(5)
            
        except Exception as e:
            if DEBUG:
                print("System error: " + str(e))
        finally:
            self.shutdown()
    
    def shutdown(self):
        """系统关闭清理"""
        try:
            if DEBUG:
                print("Shutting down ESP32 WOL System...")
            
            # 断开WiFi
            self.wifi_manager.disconnect()
            
            if DEBUG:
                print("System shutdown completed")
                
        except Exception as e:
            if DEBUG:
                print("Shutdown error: " + str(e))

def main():
    """主函数"""
    try:
        wol_system = ESP32WOLSystem()
        wol_system.run()
        
    except Exception as e:
        if DEBUG:
            print("Main function error: " + str(e))
        time.sleep(10)
        reset()

if __name__ == '__main__':
    main()