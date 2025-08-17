# WOL魔术包发送模块
# Wake-on-LAN magic packet sender for ESP32

import socket
from config import WOL_PORT, BROADCAST_IP, DEBUG

class WOLSender:
    def __init__(self):
        self.wol_port = WOL_PORT
        self.broadcast_ip = BROADCAST_IP
    
    def parse_mac_address(self, mac_str):
        """解析MAC地址字符串为字节数组
        支持格式: AA:BB:CC:DD:EE:FF 或 AA-BB-CC-DD-EE-FF 或 AABBCCDDEEFF
        """
        try:
            # 移除所有分隔符并转换为大写
            mac_clean = mac_str.replace(':', '').replace('-', '').replace(' ', '').upper()
            
            # 检查长度
            if len(mac_clean) != 12:
                raise ValueError("Invalid MAC address length: " + str(len(mac_clean)))
            
            # 检查是否都是十六进制字符
            for char in mac_clean:
                if char not in '0123456789ABCDEF':
                    raise ValueError("Invalid character in MAC address: " + char)
            
            # 转换为字节数组
            mac_bytes = bytes.fromhex(mac_clean)
            
            if DEBUG:
                mac_formatted = ':'.join(['%02X' % b for b in mac_bytes])
                print("Parsed MAC address: " + mac_formatted)
            
            return mac_bytes
            
        except Exception as e:
            if DEBUG:
                print("MAC address parsing error: " + str(e))
            return None
    
    def create_magic_packet(self, mac_address):
        """创建WOL魔术包
        魔术包格式: 6字节的0xFF + 16次重复的目标MAC地址 = 102字节
        """
        try:
            # 解析MAC地址
            if isinstance(mac_address, str):
                mac_bytes = self.parse_mac_address(mac_address)
                if mac_bytes is None:
                    return None
            else:
                mac_bytes = mac_address
            
            # 验证MAC地址长度
            if len(mac_bytes) != 6:
                if DEBUG:
                    print("Invalid MAC address length: " + str(len(mac_bytes)))
                return None
            
            # 构造魔术包
            # 前6字节: 0xFF
            magic_packet = b'\xFF' * 6
            
            # 后96字节: MAC地址重复16次
            for i in range(16):
                magic_packet += mac_bytes
            
            if DEBUG:
                print("Magic packet created, length: " + str(len(magic_packet)) + " bytes")
                mac_formatted = ':'.join(['%02X' % b for b in mac_bytes])
                print("Target MAC: " + mac_formatted)
            
            return magic_packet
            
        except Exception as e:
            if DEBUG:
                print("Magic packet creation error: " + str(e))
            return None
    
    def send_wol_packet(self, mac_address, broadcast_ip=None, port=None):
        """发送WOL魔术包"""
        try:
            # 使用默认值或传入的参数
            target_ip = broadcast_ip or self.broadcast_ip
            target_port = port or self.wol_port
            
            # 创建魔术包
            magic_packet = self.create_magic_packet(mac_address)
            if magic_packet is None:
                if DEBUG:
                    print("Failed to create magic packet")
                return False
            
            # 创建UDP套接字
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            try:
                # 设置广播选项
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                
                # 设置超时
                sock.settimeout(5)
                
                # 发送魔术包
                if DEBUG:
                    print("Sending WOL packet to " + target_ip + ":" + str(target_port))
                
                bytes_sent = sock.sendto(magic_packet, (target_ip, target_port))
                
                if DEBUG:
                    print("WOL packet sent successfully, " + str(bytes_sent) + " bytes")
                
                return True
                
            finally:
                sock.close()
                
        except Exception as e:
            if DEBUG:
                print("WOL packet sending error: " + str(e))
            return False
    
    def send_wol_to_subnet(self, mac_address, gateway_ip):
        """向子网广播发送WOL包
        计算子网广播地址并发送
        """
        try:
            # 简单的子网广播地址计算（假设/24网络）
            ip_parts = gateway_ip.split('.')
            if len(ip_parts) == 4:
                subnet_broadcast = ip_parts[0] + "." + ip_parts[1] + "." + ip_parts[2] + ".255"
                if DEBUG:
                    print("Calculated subnet broadcast: " + subnet_broadcast)
                return self.send_wol_packet(mac_address, subnet_broadcast)
            else:
                if DEBUG:
                    print("Invalid gateway IP format")
                return False
                
        except Exception as e:
            if DEBUG:
                print("Subnet WOL sending error: " + str(e))
            return False
    
    def send_multiple_wol(self, mac_address, attempts=3, delay=1):
        """发送多次WOL包以提高成功率"""
        success_count = 0
        
        for i in range(attempts):
            if DEBUG:
                print("WOL attempt " + str(i + 1) + "/" + str(attempts))
            
            if self.send_wol_packet(mac_address):
                success_count += 1
            
            if i < attempts - 1:  # 最后一次不需要延迟
                import time
                time.sleep(delay)
        
        if DEBUG:
            print("WOL sending completed: " + str(success_count) + "/" + str(attempts) + " successful")
        
        return success_count > 0
    
    def validate_mac_address(self, mac_address):
        """验证MAC地址格式"""
        try:
            mac_bytes = self.parse_mac_address(mac_address)
            return mac_bytes is not None
        except:
            return False
    
    def get_broadcast_addresses(self, network_config):
        """根据网络配置计算可能的广播地址"""
        broadcast_addresses = []
        
        try:
            if network_config:
                ip = network_config.get('ip', '')
                subnet = network_config.get('subnet', '')
                gateway = network_config.get('gateway', '')
                
                # 添加默认广播地址
                broadcast_addresses.append('255.255.255.255')
                
                # 添加子网广播地址
                if gateway:
                    ip_parts = gateway.split('.')
                    if len(ip_parts) == 4:
                        subnet_broadcast = ip_parts[0] + "." + ip_parts[1] + "." + ip_parts[2] + ".255"
                        broadcast_addresses.append(subnet_broadcast)
                
                # 根据子网掩码计算广播地址（简化版本）
                if ip and subnet == '255.255.255.0':
                    ip_parts = ip.split('.')
                    if len(ip_parts) == 4:
                        network_broadcast = ip_parts[0] + "." + ip_parts[1] + "." + ip_parts[2] + ".255"
                        if network_broadcast not in broadcast_addresses:
                            broadcast_addresses.append(network_broadcast)
            
            if DEBUG:
                print("Calculated broadcast addresses: " + str(broadcast_addresses))
            
            return broadcast_addresses
            
        except Exception as e:
            if DEBUG:
                print("Broadcast address calculation error: " + str(e))
            return ['255.255.255.255']