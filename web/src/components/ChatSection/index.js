import React, { useState, useEffect, useRef } from 'react';
import './ChatSection.css';
import { useWebSocket } from '../../contexts/WebSocketContext';
import { useNotification } from '../../contexts/NotificationContext';
import { useConfig } from '../../contexts/ConfigContext';

const ChatSection = () => {
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [isGeneratingVideo, setIsGeneratingVideo] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const { sendMessage, sendAudioData, isConnected, setLoading } = useWebSocket();
  const { error, success } = useNotification();
  const { config } = useConfig();
  
  // 媒体录制相关的状态
  const [mediaRecorder, setMediaRecorder] = useState(null);
  const [audioChunks, setAudioChunks] = useState([]);
  
  // 音频配置
  const audioConfig = {
    sampleRate: 16000,
    channels: 1
  };
  
  // 监听服务器消息
  useEffect(() => {
    const handleServerMessage = (event) => {
      const message = event.detail;
      console.log('ChatSection收到服务器消息:', message);
      
      // 处理聊天消息
      if (message.type === 'response') {
        // 添加助手回复
        if (message.text) {
          addMessage('assistant', message.text);
        }
        
        // 添加状态消息
        if (message.status && message.message) {
          addStatusMessage(message.message);
        }
        
        // 处理参考图像
        if (message.refImagePath) {
          addMessage('system', `参考图像: ${config.refImagePath}`);
        }
      }
      // 处理错误消息
      else if (message.type === 'error') {
        error(message.message || '出现错误，请重试');
        addStatusMessage('错误: ' + (message.message || '未知错误'));
      }
    };
    
    window.addEventListener('server-message', handleServerMessage);
    
    return () => {
      window.removeEventListener('server-message', handleServerMessage);
    };
  }, []);
  
  // 初始化媒体录制
  const initMediaRecorder = async () => {
    try {
      console.log('初始化媒体录制器');
      
      // 请求音频权限
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      
      // 设置音频处理
      const options = { mimeType: 'audio/webm' };
      const recorder = new MediaRecorder(stream, options);
      
      // 收集音频数据
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          setAudioChunks(prev => [...prev, event.data]);
        }
      };
      
      // 处理录制停止
      recorder.onstop = async () => {
        if (audioChunks.length === 0) {
          console.warn('没有收集到音频数据');
          return;
        }
        
        try {
          // 合并音频块
          const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
          
          // 发送音频数据到服务器
          console.log('发送音频数据, 大小:', audioBlob.size);
          const result = sendAudioData(audioBlob, {
            language: config.language,
            voiceName: config.voiceName,
            useEchoMimic: config.useEchoMimic
          });
          
          if (result) {
            // 添加用户消息 (使用"录音中..."作为占位符)
            addMessage('user', '🎤 语音输入');
            
            // 重置音频块
            setAudioChunks([]);
            
            // 设置加载状态
            setLoading(true, '处理中...');
          }
        } catch (err) {
          console.error('处理录音失败:', err);
          error('处理录音失败');
        }
      };
      
      // 保存录制器实例
      setMediaRecorder(recorder);
      success('麦克风初始化成功');
      
    } catch (err) {
      console.error('初始化媒体录制失败:', err);
      error('无法访问麦克风，请确保已授予权限');
    }
  };
  
  // 组件挂载时初始化媒体录制
  useEffect(() => {
    // 自动初始化媒体录制器
    if (!mediaRecorder) {
      initMediaRecorder();
    }
    
    // 组件卸载时清理
    return () => {
      if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
      }
    };
  }, []);
  
  // 添加消息到聊天
  const addMessage = (role, content) => {
    setMessages(prev => [
      ...prev, 
      { 
        id: Date.now(),
        role,
        content,
        timestamp: new Date().toLocaleTimeString()
      }
    ]);
  };
  
  // 添加状态消息
  const addStatusMessage = (content) => {
    setMessages(prev => [
      ...prev, 
      { 
        id: Date.now(),
        role: 'status',
        content,
        timestamp: new Date().toLocaleTimeString()
      }
    ]);
  };
  
  // 自动滚动到最新消息
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);
  
  // 处理输入变化
  const handleInputChange = (e) => {
    setInputText(e.target.value);
  };
  
  // 开始录音
  const startRecording = () => {
    if (!mediaRecorder) {
      initMediaRecorder().then(() => {
        if (mediaRecorder) {
          mediaRecorder.start();
          setIsRecording(true);
        }
      });
    } else {
      mediaRecorder.start();
      setIsRecording(true);
    }
  };
  
  // 停止录音
  const stopRecording = () => {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      mediaRecorder.stop();
    }
    setIsRecording(false);
  };
  
  // 发送文本消息
  const sendTextMessage = () => {
    if (!inputText.trim()) return;
    
    // 如果未连接，显示错误
    if (!isConnected) {
      error('未连接到服务器，请等待连接恢复');
      return;
    }
    
    // 将消息添加到聊天
    addMessage('user', inputText);
    
    // 发送消息到服务器
    const result = sendMessage({
      type: 'message',
      text: inputText,
      language: config.language,
      voiceName: config.voiceName,
      useEchoMimic: config.useEchoMimic
    });
    
    // 如果成功发送，清空输入框并设置加载状态
    if (result) {
      setInputText('');
      setLoading(true, '思考中...');
    }
  };
  
  // 监听回车键
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendTextMessage();
    }
  };
  
  // 渲染消息
  const renderMessages = () => {
    return messages.map(message => (
      <div key={message.id} className={`message ${message.role}`}>
        {message.role === 'user' && <div className="avatar user-avatar"><i className="fas fa-user"></i></div>}
        {message.role === 'assistant' && <div className="avatar assistant-avatar"><i className="fas fa-robot"></i></div>}
        
        <div className="message-content">
          <div className="message-text">{message.content}</div>
          <div className="message-time">{message.timestamp}</div>
        </div>
      </div>
    ));
  };

  return (
    <div className="chat-section">
      <div className="chat-header">
        <h3>聊天窗口</h3>
        <div className="connection-status">
          <span className={`status-dot ${isConnected ? 'connected' : 'disconnected'}`}></span>
          <span className="status-text">{isConnected ? '已连接' : '未连接'}</span>
        </div>
      </div>
      
      <div className="chat-messages">
        {messages.length === 0 ? (
          <div className="empty-chat">
            <i className="fas fa-comment-dots"></i>
            <p>与数字人助手开始对话吧！</p>
            <p className="tip">你可以输入文字，或点击麦克风按钮进行语音输入</p>
          </div>
        ) : (
          renderMessages()
        )}
        <div ref={messagesEndRef} />
      </div>
      
      <div className="chat-input">
        <textarea
          ref={inputRef}
          value={inputText}
          onChange={handleInputChange}
          onKeyPress={handleKeyPress}
          placeholder="输入消息..."
          disabled={!isConnected}
        />
        
        <div className="input-controls">
          <button 
            className={`voice-btn ${isRecording ? 'recording' : ''}`}
            onClick={isRecording ? stopRecording : startRecording}
            disabled={!isConnected}
          >
            <i className={`fas ${isRecording ? 'fa-stop' : 'fa-microphone'}`}></i>
          </button>
          
          <button 
            className="send-btn" 
            onClick={sendTextMessage}
            disabled={!inputText.trim() || !isConnected}
          >
            <i className="fas fa-paper-plane"></i>
          </button>
        </div>
      </div>
    </div>
  );
};

export default ChatSection;
