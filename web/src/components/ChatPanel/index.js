import React, { useState, useEffect, useRef } from 'react';
import { useWebSocket } from '../../contexts/WebSocketContext';
import './ChatPanel.css';

const ChatPanel = () => {
  const { messages = [], sendMessage, isProcessing } = useWebSocket();
  const [inputText, setInputText] = useState('');
  const messagesEndRef = useRef(null);
  
  // 自动滚动到底部
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };
  
  useEffect(() => {
    scrollToBottom();
  }, [messages]);
  
  // 处理消息发送
  const handleSendMessage = (e) => {
    e.preventDefault();
    if (inputText.trim() && !isProcessing) {
      sendMessage(inputText);
      setInputText('');
    }
  };
  
  return (
    <div className="chat-panel">
      <div className="messages-container">
        {Array.isArray(messages) && messages.map((msg, index) => (
          <div 
            key={index} 
            className={`message ${msg.role === 'user' ? 'user-message' : 'assistant-message'}`}
          >
            <div className="message-content">{msg.content}</div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>
      
      <form className="message-input-form" onSubmit={handleSendMessage}>
        <input
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          placeholder="输入消息..."
          disabled={isProcessing}
        />
        <button 
          type="submit"
          disabled={!inputText.trim() || isProcessing}
        >
          发送
        </button>
      </form>
    </div>
  );
};

export default ChatPanel;
