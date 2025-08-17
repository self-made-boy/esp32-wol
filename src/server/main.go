package main

import (
	"bytes"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"strings"
	"sync"
	"time"
)

// 设备信息
type Device struct {
	ID          string    `json:"id"`
	Name        string    `json:"name"`
	MacAddress  string    `json:"mac_address"`
	Description string    `json:"description"`
	Version     string    `json:"version"`
	LastSeen    time.Time `json:"last_seen"`
}

// WOL消息
type WOLMessage struct {
	ID        string    `json:"id"`
	TargetMAC string    `json:"target_mac"`
	CreatedAt time.Time `json:"created_at"`
}

// 设备注册请求
type DeviceRegistrationRequest struct {
	Name        string `json:"name"`
	MacAddress  string `json:"mac_address"`
	Description string `json:"description"`
	Version     string `json:"version"`
}

// 发送WOL消息请求
type SendWOLRequest struct {
	DeviceID  string `json:"device_id"`  // ESP32设备ID
	TargetMAC string `json:"target_mac"` // WOL目标MAC地址
}

// 轮询响应
type PollResponse struct {
	Messages []WOLMessage `json:"messages"`
	Total    int          `json:"total"`
}

// 简单的内存存储
type SimpleStorage struct {
	mu       sync.RWMutex
	devices  map[string]*Device
	messages map[string]*WOLMessage
	pending  map[string][]*WOLMessage // device_id -> messages
}

func NewSimpleStorage() *SimpleStorage {
	return &SimpleStorage{
		devices:  make(map[string]*Device),
		messages: make(map[string]*WOLMessage),
		pending:  make(map[string][]*WOLMessage),
	}
}

// 全局存储
var storage = NewSimpleStorage()

// 全局API密钥变量
var API_KEY string

// 响应写入器包装器，用于捕获响应内容
type responseWriter struct {
	http.ResponseWriter
	body       *bytes.Buffer
	statusCode int
}

func newResponseWriter(w http.ResponseWriter) *responseWriter {
	return &responseWriter{
		ResponseWriter: w,
		body:           &bytes.Buffer{},
		statusCode:     http.StatusOK,
	}
}

func (rw *responseWriter) Write(b []byte) (int, error) {
	rw.body.Write(b)
	return rw.ResponseWriter.Write(b)
}

func (rw *responseWriter) WriteHeader(statusCode int) {
	rw.statusCode = statusCode
	rw.ResponseWriter.WriteHeader(statusCode)
}

// 身份验证中间件
func authMiddleware(handler http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		// 从Header或Query参数获取API密钥
		apiKey := r.Header.Get("X-API-Key")
		if apiKey == "" {
			apiKey = r.URL.Query().Get("api_key")
		}
		
		// 验证API密钥
		if apiKey != API_KEY {
			log.Printf("[认证失败] %s %s - 无效的API密钥: %s", r.Method, r.URL.Path, apiKey)
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusUnauthorized)
			json.NewEncoder(w).Encode(map[string]string{
				"error": "Unauthorized: Invalid API key",
			})
			return
		}
		
		// 认证通过，继续处理请求
		handler(w, r)
	}
}

// 日志中间件
func loggingMiddleware(handler http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		
		// 读取请求体
		body, _ := io.ReadAll(r.Body)
		r.Body = io.NopCloser(bytes.NewBuffer(body))
		
		// 记录请求
		log.Printf("[请求] %s %s", r.Method, r.URL.Path)
		if len(body) > 0 {
			log.Printf("[请求体] %s", string(body))
		}
		
		// 包装响应写入器
		rw := newResponseWriter(w)
		
		// 调用处理函数
		handler(rw, r)
		
		// 记录响应
		duration := time.Since(start)
		log.Printf("[响应] %d - %s (%v)", rw.statusCode, strings.TrimSpace(rw.body.String()), duration)
	}
}

func main() {
	// 解析命令行参数
	apiKey := flag.String("api-key", "", "API密钥，用于身份验证")
	port := flag.String("port", "8080", "服务器监听端口")
	flag.Parse()

	// 检查API密钥
	if *apiKey == "" {
		// 尝试从环境变量获取
		if envKey := os.Getenv("ESP32_API_KEY"); envKey != "" {
			API_KEY = envKey
			log.Println("使用环境变量中的API密钥")
		} else {
			log.Fatal("错误: 必须通过 -api-key 参数或 ESP32_API_KEY 环境变量指定API密钥")
		}
	} else {
		API_KEY = *apiKey
		log.Println("使用命令行参数中的API密钥")
	}

	log.Println("启动简化版ESP32 WOL服务器...")
	log.Printf("API密钥: %s", maskAPIKey(API_KEY))

	// 路由（使用日志中间件和认证中间件）
	http.HandleFunc("/health", loggingMiddleware(healthHandler))
	http.HandleFunc("/api/devices/register", loggingMiddleware(authMiddleware(registerDeviceHandler)))
	http.HandleFunc("/api/wol/send", loggingMiddleware(authMiddleware(sendWOLHandler)))
	http.HandleFunc("/api/wol/poll", loggingMiddleware(authMiddleware(pollWOLHandler)))

	// 启动服务器
	serverPort := ":" + *port
	log.Printf("服务器启动在端口 %s", serverPort)
	log.Fatal(http.ListenAndServe(serverPort, nil))
}

// 掩码API密钥用于日志显示
func maskAPIKey(key string) string {
	if len(key) <= 8 {
		return "****"
	}
	return key[:4] + "****" + key[len(key)-4:]
}

// 健康检查
func healthHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{
		"status": "ok",
		"time":   time.Now().Format(time.RFC3339),
	})
}

// 设备注册
func registerDeviceHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req DeviceRegistrationRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid JSON", http.StatusBadRequest)
		return
	}

	if req.Name == "" || req.MacAddress == "" {
		http.Error(w, "Name and mac_address are required", http.StatusBadRequest)
		return
	}

	// 使用MAC地址作为设备ID
	deviceID := req.MacAddress

	storage.mu.Lock()
	device := &Device{
		ID:          deviceID,
		Name:        req.Name,
		MacAddress:  req.MacAddress,
		Description: req.Description,
		Version:     req.Version,
		LastSeen:    time.Now(),
	}
	storage.devices[deviceID] = device
	storage.mu.Unlock()

	log.Printf("设备注册成功: %s (%s)", req.Name, req.MacAddress)

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success":   true,
		"device_id": deviceID,
		"message":   "Device registered successfully",
	})
}

// 发送WOL消息（控制端调用）
func sendWOLHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req SendWOLRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid JSON", http.StatusBadRequest)
		return
	}

	if req.DeviceID == "" {
		http.Error(w, "device_id is required", http.StatusBadRequest)
		return
	}

	if req.TargetMAC == "" {
		http.Error(w, "target_mac is required", http.StatusBadRequest)
		return
	}

	// 创建WOL消息
	messageID := fmt.Sprintf("msg_%d", time.Now().UnixNano())
	message := &WOLMessage{
		ID:        messageID,
		TargetMAC: req.TargetMAC,
		CreatedAt: time.Now(),
	}

	storage.mu.Lock()
	storage.messages[messageID] = message

	// 找到目标设备并添加到待处理队列
	if _, exists := storage.devices[req.DeviceID]; exists {
		storage.pending[req.DeviceID] = append(storage.pending[req.DeviceID], message)
		log.Printf("WOL消息已添加到设备 %s 的队列: %s (目标MAC: %s)", req.DeviceID, messageID, req.TargetMAC)
	} else {
		log.Printf("警告: 设备 %s 未注册，但消息已创建: %s (目标MAC: %s)", req.DeviceID, messageID, req.TargetMAC)
	}
	storage.mu.Unlock()

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success":    true,
		"message_id": messageID,
		"message":    "WOL message sent successfully",
	})
}

// 设备轮询WOL消息（ESP32调用）
func pollWOLHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	deviceID := r.URL.Query().Get("device_id")
	if deviceID == "" {
		http.Error(w, "device_id parameter is required", http.StatusBadRequest)
		return
	}

	// 更新设备最后见到时间
	storage.mu.Lock()
	if device, exists := storage.devices[deviceID]; exists {
		device.LastSeen = time.Now()
	}

	// 获取待处理消息
	messages := storage.pending[deviceID]
	if len(messages) > 0 {
		// 返回消息并清空队列
		response := PollResponse{
			Messages: make([]WOLMessage, len(messages)),
			Total:    len(messages),
		}
		for i, msg := range messages {
			response.Messages[i] = *msg
		}
		// 清空队列
		storage.pending[deviceID] = nil
		storage.mu.Unlock()

		log.Printf("设备 %s 轮询到 %d 条消息", deviceID, len(messages))

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(response)
		return
	}
	storage.mu.Unlock()

	// 长轮询：等待新消息
	timeout := time.After(120 * time.Second) // 30秒超时
	ticker := time.NewTicker(1 * time.Second) // 每秒检查一次
	defer ticker.Stop()

	for {
		select {
		case <-timeout:
			// 超时，返回空结果
			w.Header().Set("Content-Type", "application/json")
			json.NewEncoder(w).Encode(PollResponse{
				Messages: []WOLMessage{},
				Total:    0,
			})
			return

		case <-ticker.C:
			// 检查是否有新消息
			storage.mu.RLock()
			messages := storage.pending[deviceID]
			if len(messages) > 0 {
				// 有新消息，返回并清空队列
				response := PollResponse{
					Messages: make([]WOLMessage, len(messages)),
					Total:    len(messages),
				}
				for i, msg := range messages {
					response.Messages[i] = *msg
				}
				storage.mu.RUnlock()

				// 清空队列
				storage.mu.Lock()
				storage.pending[deviceID] = nil
				storage.mu.Unlock()

				log.Printf("设备 %s 长轮询到 %d 条消息", deviceID, len(messages))

				w.Header().Set("Content-Type", "application/json")
				json.NewEncoder(w).Encode(response)
				return
			}
			storage.mu.RUnlock()
		}
	}
}