import React, { createContext, useState, useContext, useEffect, useCallback, useRef } from 'react';
import { useConfig } from './ConfigContext';
import { useNotification } from './NotificationContext';

// 创建上下文
const WebSocketContext = createContext();

// WebSocket提供者组件
export const WebSocketProvider = ({ children }) => {
  const { config } = useConfig();
  const { success, error } = useNotification();
  
  const [socket, setSocket] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState('offline');
  const [statusMessage, setStatusMessage] = useState('等待连接...');
  const [isLoading, setIsLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState('');
  const [lastMessage, setLastMessage] = useState(null);
  const [messages, setMessages] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [webrtcSupported, setWebrtcSupported] = useState(null);
  const [pendingMessages, setPendingMessages] = useState([]);
  const [connectionStats, setConnectionStats] = useState({
    pingTime: null,
    avgLatency: 0,
    lastPingAt: null,
    reconnectCount: 0
  });
  
  // 使用refs存储一些不需要触发重渲染的值
  const socketRef = useRef(null);
  const pingIntervalRef = useRef(null);
  const lastPingSentRef = useRef(null);

  // 初始化WebSocket连接
  const initWebSocket = useCallback(() => {
    // 修改WebSocket URL，确保连接到正确的后端地址
    const wsUrl = 'ws://localhost:8000/ws';
    
    let reconnectAttempts = 0;
    const maxReconnectAttempts = 20; // 增加最大重连次数
    const baseReconnectDelay = 1000; // 1秒
    const reconnectBackoffFactor = 1.5; // 指数退避因子
    
    const connect = () => {
      updateStatus('connecting', `连接中... ${reconnectAttempts > 0 ? `(尝试 ${reconnectAttempts}/${maxReconnectAttempts})` : ''}`);
      
      console.log(`尝试连接到WebSocket: ${wsUrl}`);
      
      // 创建WebSocket连接
      const newSocket = new WebSocket(wsUrl);
      socketRef.current = newSocket;
      
      // 连接打开
      newSocket.onopen = () => {
        console.log('WebSocket连接已建立');
        setIsConnected(true);
        updateStatus('online', '已连接');
        reconnectAttempts = 0; // 重置重连计数
        
        // 更新连接统计
        setConnectionStats(prev => ({
          ...prev,
          reconnectCount: prev.reconnectCount + 1,
          lastConnectedAt: Date.now()
        }));
        
        // 发送配置
        newSocket.send(JSON.stringify({
          type: 'config',
          config: config
        }));
        
        // 开始ping测试
        clearInterval(pingIntervalRef.current);
        pingIntervalRef.current = setInterval(() => {
          if (newSocket.readyState === WebSocket.OPEN) {
            const pingTime = Date.now();
            lastPingSentRef.current = pingTime;
            try {
              newSocket.send(JSON.stringify({
                type: 'ping',
                timestamp: pingTime
              }));
            } catch (err) {
              console.error('发送ping失败:', err);
            }
          }
        }, 10000); // 10秒一次
        
        // 处理之前缓存的消息
        if (pendingMessages.length > 0) {
          console.log(`发送${pendingMessages.length}条缓存消息`);
          pendingMessages.forEach(msg => {
            try {
              newSocket.send(JSON.stringify(msg));
            } catch (err) {
              console.error('发送缓存消息失败:', err);
            }
          });
          
          // 清空缓存
          setPendingMessages([]);
          success(`已恢复连接并发送${pendingMessages.length}条缓存消息`);
        } else {
          // 显示成功通知
          if (reconnectAttempts > 0) {
            success('连接已恢复');
          }
        }
      };
      
      // 连接关闭
      newSocket.onclose = (event) => {
        console.log('WebSocket连接已关闭:', event);
        setIsConnected(false);
        
        // 清除ping间隔
        clearInterval(pingIntervalRef.current);
        
        if (reconnectAttempts < maxReconnectAttempts) {
          // 改进的指数退避重连
          const delay = Math.min(baseReconnectDelay * Math.pow(reconnectBackoffFactor, reconnectAttempts), 60000);
          reconnectAttempts++;
          
          updateStatus('reconnecting', `连接已断开，${Math.round(delay / 1000)}秒后重连... (${reconnectAttempts}/${maxReconnectAttempts})`);
          
          // 显示重连通知
          if (reconnectAttempts === 1) {
            error('连接已断开，正在尝试重连...');
          } else if (reconnectAttempts % 5 === 0) {
            // 每5次重试显示一次通知
            error(`连接尝试 ${reconnectAttempts}/${maxReconnectAttempts}, ${Math.round(delay / 1000)}秒后重试`);
          }
          
          setTimeout(connect, delay);
        } else {
          updateStatus('offline', '连接失败，请检查网络并刷新页面');
          error('连接失败，请检查网络并刷新页面。您可以尝试重新加载页面恢复连接。');
          
          // 在状态中记录连接失败，由UI组件自行处理重连提示
          setConnectionStats(prev => ({
            ...prev,
            reconnectFailed: true,
            lastReconnectAttempt: Date.now()
          }));
          
          // 触发重连失败事件，让上层组件决定如何处理
          const reconnectFailedEvent = new CustomEvent('websocketReconnectFailed', {
            detail: { timestamp: Date.now() }
          });
          window.dispatchEvent(reconnectFailedEvent);
        }
      };
      
      // 连接错误
      newSocket.onerror = (err) => {
        console.error('WebSocket连接错误:', err);
        error('连接发生错误，正在尝试重连...');
      };
      
      // 收到消息
      newSocket.onmessage = (event) => {
        try {
          // 检查是否为二进制数据（音频）
          if (event.data instanceof Blob) {
            console.log('收到二进制数据:', event.data.size, event.data.type);
            handleBinaryMessage(event.data);
            return;
          }
          
          // 尝试解析JSON消息
          const data = JSON.parse(event.data);
          console.log('收到JSON消息:', data);
          
          // 处理ping响应
          if (data.type === 'pong' && lastPingSentRef.current) {
            const latency = Date.now() - data.original_timestamp;
            console.log(`网络延迟: ${latency}ms`);
            
            setConnectionStats(prev => {
              // 计算移动平均延迟
              const newAvgLatency = prev.avgLatency ? 
                (prev.avgLatency * 0.8 + latency * 0.2) : latency;
                
              return {
                ...prev,
                pingTime: latency,
                avgLatency: newAvgLatency,
                lastPingAt: Date.now()
              };
            });
          }
          
          // 更新最近消息状态
          setLastMessage(data);
          
          // 根据消息类型处理
          switch (data.type) {
            case 'thinking':
              setLoading(true, data.message || '思考中...');
              break;
              
            case 'bot_reply':
              // 添加消息到历史
              addMessage({
                role: 'assistant',
                content: data.text || data.message,
                timestamp: new Date().toISOString()
              });
              setLoading(false);
              break;
              
            case 'transcription':
              // 处理语音转写结果
              if (data.final) {
                addMessage({
                  role: 'user',
                  content: data.text,
                  timestamp: new Date().toISOString()
                });
              }
              break;
              
            case 'generating_video':
              setLoading(true, data.message || '生成视频中...');
              break;
              
            case 'video_ready':
              setLoading(false);
              if (data.success && data.video_url) {
                console.log('视频已就绪:', data.video_url);
                
                // 添加视频消息
                addMessage({
                  role: 'assistant',
                  content: data.message || '视频已准备就绪',
                  video_url: data.video_url,
                  timestamp: new Date().toISOString()
                });
              }
              break;
              
            case 'webrtc_support':
              // 更新WebRTC支持状态
              setWebrtcSupported(data.supported);
              console.log('服务器WebRTC支持状态:', data.supported);
              if (data.supported) {
                success('语音转写功能已就绪');
              } else {
                console.warn('服务器不支持WebRTC或Deepgram集成，将使用备用方法');
              }
              break;
              
            case 'error':
              setLoading(false);
              error(data.message || '发生错误');
              
              // 添加错误消息
              addMessage({
                role: 'system',
                content: data.message || '发生错误',
                error: true,
                timestamp: new Date().toISOString()
              });
              break;
              
            default:
              break;
          }
        } catch (err) {
          console.error('处理WebSocket消息错误:', err);
        }
      };
      
      setSocket(newSocket);
    };
    
    connect();
    
    // 组件卸载时清理WebSocket连接和定时器
    return () => {
      clearInterval(pingIntervalRef.current);
      if (socketRef.current) {
        socketRef.current.close();
      }
      if (socket) {
        socket.close();
      }
    };
  }, [config, success, error]);

  // 组件挂载时初始化WebSocket
  useEffect(() => {
    initWebSocket();
    
    // 清理函数
    return () => {
      if (socket) {
        socket.close();
      }
    };
  }, [initWebSocket]);

  // 更新状态
  const updateStatus = (status, message) => {
    setConnectionStatus(status);
    setStatusMessage(message);
  };

  // 设置加载状态
  const setLoading = (isLoading, message = '') => {
    setIsLoading(isLoading);
    setLoadingMessage(message);
  };

  // 添加消息到历史记录
  const addMessage = (message) => {
    setMessages(prevMessages => [...prevMessages, message]);
    
    // 触发消息事件，方便其他组件监听
    const event = new CustomEvent('new-message', { detail: message });
    window.dispatchEvent(event);
  };

  // 发送文本消息
  const sendMessage = useCallback((message) => {
    // 如果传入的是字符串，转换为标准消息格式
    const messageToSend = typeof message === 'string' 
      ? { type: 'text_input', text: message }
      : message;
    
    // 添加网络状态和时间戳
    const enhancedMessage = {
      ...messageToSend,
      client_timestamp: Date.now(),
      client_connection_stats: connectionStats
    };
    
    // 检查websocket连接状态
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      console.warn('WebSocket连接未建立，消息将被缓存');
      
      // 缓存消息，等待重连后发送
      if (messageToSend.type !== 'ping') { // 不缓存ping消息
        setPendingMessages(prev => [...prev, enhancedMessage]);
        
        // 只有在特定消息类型时才显示通知
        if (['text_input', 'transcription', 'transcription_complete'].includes(messageToSend.type)) {
          error('网络连接中断，消息将在重连后发送');
        }
      }
      
      return false;
    }
    
    try {      
      // 记录用户消息（对于文本输入类型）
      if (messageToSend.type === 'text_input' && messageToSend.text) {
        addMessage({
          role: 'user',
          content: messageToSend.text,
          timestamp: new Date().toISOString(),
          pending: pendingMessages.length > 0, // 标记是否有待发送消息
        });
        
        // 设置处理状态
        setIsProcessing(true);
      }
      
      console.log('发送WebSocket消息:', enhancedMessage);
      socket.send(JSON.stringify(enhancedMessage));
      return true;
    } catch (err) {
      console.error(`发送消息失败: ${err.message}`);
      
      // 发送失败，缓存消息（除了ping）
      if (messageToSend.type !== 'ping') {
        setPendingMessages(prev => [...prev, enhancedMessage]);
        error(`发送消息失败: ${err.message}，将在连接恢复后重试`);
      }
      
      setIsProcessing(false);
      return false;
    }
  }, [socket, error]);

  // 处理二进制消息(用于音频播放)
  const handleBinaryMessage = (binaryData) => {
    // 处理接收到的二进制数据(通常是音频)
    try {
      // 创建音频URL
      const audioUrl = URL.createObjectURL(binaryData);
      
      // 创建音频元素并播放
      const audio = new Audio(audioUrl);
      
      // 播放完成后释放URL
      audio.onended = () => {
        URL.revokeObjectURL(audioUrl);
      };
      
      audio.onerror = (err) => {
        console.error('音频播放错误:', err);
        URL.revokeObjectURL(audioUrl);
      };
      
      // 播放音频
      audio.play().catch(err => {
        console.error('无法自动播放音频:', err);
        error('请点击页面以启用音频播放');
      });
    } catch (err) {
      console.error('处理二进制数据错误:', err);
    }
  };

  // 提供上下文值
  const contextValue = {
    socket,
    isConnected,
    connectionStatus,
    statusMessage,
    isLoading,
    loadingMessage,
    lastMessage,
    messages,
    isProcessing,
    webrtcSupported,
    connectionStats,
    pendingMessages,
    sendMessage,
    addMessage,
    setLoading,
    clearMessages: () => setMessages([]),
    clearPendingMessages: () => setPendingMessages([]),
    hasPendingMessages: pendingMessages.length > 0
  };

  return (
    <WebSocketContext.Provider value={contextValue}>
      {children}
    </WebSocketContext.Provider>
  );
};

// 自定义Hook，用于在组件中访问WebSocket功能
export const useWebSocket = () => {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocket 必须在 WebSocketProvider 内部使用');
  }
  return context;
};
