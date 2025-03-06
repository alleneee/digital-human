import React, { useState, useEffect, useRef } from 'react';
import { useWebSocket } from '../../contexts/WebSocketContext';
import { useConfig } from '../../contexts/ConfigContext';
import { useNotification } from '../../contexts/NotificationContext';
import './DigitalHuman.css';

const DigitalHuman = () => {
  const videoRef = useRef(null);
  const [videoUrl, setVideoUrl] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const { messages, lastMessage } = useWebSocket();
  const { config } = useConfig();
  const { error: showError } = useNotification();
  
  // 监听WebSocket消息
  useEffect(() => {
    if (!messages || messages.length === 0) return;
    
    const lastMsg = messages[messages.length - 1];
    if (lastMsg && lastMsg.type === 'video_ready' && lastMsg.video_url) {
      console.log('收到视频URL:', lastMsg.video_url);
      setVideoUrl(lastMsg.video_url);
      setLoading(false);
      setError(null);
    } else if (lastMsg && lastMsg.type === 'error') {
      console.error('收到错误消息:', lastMsg.error);
      setError(lastMsg.error || '视频生成失败');
      setLoading(false);
      showError(lastMsg.error || '视频生成失败');
    }
  }, [messages, showError]);
  
  // 额外监听lastMessage（单独的WebSocket消息状态）
  useEffect(() => {
    if (lastMessage && lastMessage.type === 'video_ready' && lastMessage.video_url) {
      console.log('收到视频URL (lastMessage):', lastMessage.video_url);
      setVideoUrl(lastMessage.video_url);
      setLoading(false);
      setError(null);
    }
  }, [lastMessage]);
  
  // 处理视频播放错误
  const handleVideoError = () => {
    console.error('视频播放错误');
    setError('视频加载失败，请检查网络连接或重试');
    setLoading(false);
    showError('视频加载失败，请检查网络连接或重试');
  };
  
  // 处理视频加载完成
  const handleVideoLoaded = () => {
    setLoading(false);
    
    // 如果视频已加载完成，尝试播放
    try {
      if (videoRef.current) {
        videoRef.current.play().catch(err => {
          console.warn('自动播放失败:', err);
        });
      }
    } catch (err) {
      console.warn('播放视频时出错:', err);
    }
  };
  
  const retryVideo = () => {
    setLoading(true);
    setError(null);
  };
  
  return (
    <div className="digital-human-section">
      <div className="model-container">
        {loading && !error && (
          <div className="model-placeholder">
            <i className="loading-icon">⏳</i>
            <p>正在加载数字人...</p>
          </div>
        )}
        
        {error && (
          <div className="error-container">
            <p>出错了: {error}</p>
            <button onClick={retryVideo}>重试</button>
          </div>
        )}
        
        {videoUrl && !error && (
          <video
            ref={videoRef}
            className="echomimic-video"
            src={videoUrl}
            autoPlay
            loop
            muted={false}
            playsInline
            onError={handleVideoError}
            onLoadedData={handleVideoLoaded}
            style={{ display: loading ? 'none' : 'block' }}
          />
        )}
      </div>
    </div>
  );
};

export default DigitalHuman;
