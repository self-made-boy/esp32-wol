# WiFi连接管理模块
# WiFi connection manager for ESP32

import network
import time
from config import WIFI_SSID, WIFI_PASSWORD, WIFI_CONNECT_TIMEOUT, DEBUG, WIFI_RETRY_COUNT


class WiFiManager:
    def __init__(self):
        self.wlan = network.WLAN(network.STA_IF)
        self.is_connected = False
        
    def connect(self):
        """连接到WiFi网络"""
        if self.is_connected:
            if DEBUG:
                print("WiFi already connected")
            return True
            
        # 激活WiFi接口
        self.wlan.active(True)
        
        # 检查是否已经连接
        if self.wlan.isconnected():
            self.is_connected = True
            if DEBUG:
                print("WiFi already connected to: " + str(self.wlan.config('essid')))
                print("IP address: " + str(self.wlan.ifconfig()[0]))
            return True
        
        # 尝试连接WiFi
        retry_count = 0
        while retry_count < WIFI_RETRY_COUNT:
            try:
                if DEBUG:
                    print("Connecting to WiFi: " + WIFI_SSID + " (attempt " + str(retry_count + 1) + "/" + str(WIFI_RETRY_COUNT) + ")")
                
                self.wlan.connect(WIFI_SSID, WIFI_PASSWORD)
                
                # 等待连接
                start_time = time.time()
                while not self.wlan.isconnected():
                    if time.time() - start_time > WIFI_CONNECT_TIMEOUT:
                        if DEBUG:
                            print("WiFi connection timeout")
                        break
                    time.sleep(1)
                
                if self.wlan.isconnected():
                    self.is_connected = True
                    if DEBUG:
                        print("WiFi connected successfully!")
                        print("Network config: " + str(self.wlan.ifconfig()))
                        print("IP address: " + str(self.wlan.ifconfig()[0]))
                        print("Subnet mask: " + str(self.wlan.ifconfig()[1]))
                        print("Gateway: " + str(self.wlan.ifconfig()[2]))
                        print("DNS: " + str(self.wlan.ifconfig()[3]))
                    return True
                else:
                    if DEBUG:
                        print("Failed to connect to WiFi (attempt " + str(retry_count + 1) + ")")
                    
            except Exception as e:
                if DEBUG:
                    print("WiFi connection error: " + str(e))
            
            retry_count += 1
            if retry_count < WIFI_RETRY_COUNT:
                time.sleep(2)
        
        if DEBUG:
            print("Failed to connect to WiFi after " + str(WIFI_RETRY_COUNT) + " attempts")
        return False
    
    def disconnect(self):
        """断开WiFi连接"""
        if self.wlan.isconnected():
            self.wlan.disconnect()
            if DEBUG:
                print("WiFi disconnected")
        self.is_connected = False
    
    def check_connection(self):
        """检查WiFi连接状态"""
        connected = self.wlan.isconnected()
        if connected != self.is_connected:
            self.is_connected = connected
            if DEBUG:
                if connected:
                    print("WiFi connection restored")
                    print("IP address: " + str(self.wlan.ifconfig()[0]))
                else:
                    print("WiFi connection lost")
        return connected
    
    def get_ip(self):
        """获取IP地址"""
        if self.wlan.isconnected():
            return self.wlan.ifconfig()[0]
        return None
    
    def get_network_info(self):
        """获取网络信息"""
        if self.wlan.isconnected():
            config = self.wlan.ifconfig()
            return {
                'ip': config[0],
                'subnet': config[1],
                'gateway': config[2],
                'dns': config[3],
                'ssid': self.wlan.config('essid')
            }
        return None
    
    def get_signal_strength(self):
        """获取WiFi信号强度"""
        try:
            return self.wlan.status('rssi')
        except:
            return None
    
    def scan_networks(self):
        """扫描可用的WiFi网络"""
        try:
            self.wlan.active(True)
            networks = self.wlan.scan()
            if DEBUG:
                print("Available networks:")
                for net in networks:
                    ssid = net[0].decode('utf-8')
                    bssid = ':'.join(['%02x' % b for b in net[1]])
                    channel = net[2]
                    rssi = net[3]
                    security = net[4]
                    print("  SSID: " + str(ssid) + ", BSSID: " + str(bssid) + ", Channel: " + str(channel) + ", RSSI: " + str(rssi) + ", Security: " + str(security))
            return networks
        except Exception as e:
            if DEBUG:
                print("Network scan error: " + str(e))
            return []
    
    def auto_reconnect(self):
        """自动重连WiFi"""
        if not self.check_connection():
            if DEBUG:
                print("WiFi disconnected, attempting to reconnect...")
            return self.connect()
        return True