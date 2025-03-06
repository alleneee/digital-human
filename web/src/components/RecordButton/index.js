import React, { useEffect, useState } from 'react';
import { useWebRTC } from '../../contexts/WebRTCContext';
import { useWebSocket } from '../../contexts/WebSocketContext';
import './RecordButton.css';

const RecordButton = () => {
  const { isRecording, toggleRecording, isReady, audioLevel, lowVolumeWarning } = useWebRTC();
  const { isProcessing, webrtcSupported, connectionStatus, hasPendingMessages } = useWebSocket();
  const [volumeLevel, setVolumeLevel] = useState(0);
  
  // 处理音量显示动画
  useEffect(() => {
    // 平滑音量变化
    setVolumeLevel(prev => audioLevel ? Math.max(prev * 0.7, audioLevel * 0.3) : prev * 0.9);
  }, [audioLevel]);
  
  // 处理录音按钮点击
  const handleRecordClick = () => {
    toggleRecording();
  };
  
  // 根据支持的功能和状态显示不同的按钮文本
  const getButtonText = () => {
    if (!isReady) {
      return '麦克风不可用';
    }
    if (connectionStatus === 'offline') {
      return '网络已断开';
    }
    if (connectionStatus === 'reconnecting') {
      return '正在重连...';
    }
    if (hasPendingMessages) {
      return isRecording ? '停止录音 (离线)' : '开始录音 (离线)';
    }
    return isRecording ? '停止录音' : '开始录音';
  };
  
  // 是否禁用按钮
  const isButtonDisabled = () => {
    return isProcessing || !isReady || connectionStatus === 'offline';
  };
  
  // 获取音量等级条的样式
  const getVolumeBarStyle = () => {
    if (!isRecording) return {};
    
    // 计算高度百分比(0-100)
    const height = Math.min(Math.max(volumeLevel * 2, 5), 100);
    
    return {
      height: `${height}%`,
      backgroundColor: lowVolumeWarning ? '#ff9800' : '#4caf50'
    };
  };
  
  return (
    <div className="record-button-container">
      {/* 音量显示条 */}
      {isRecording && (
        <div className="volume-indicator">
          <div className="volume-bar" style={getVolumeBarStyle()}></div>
        </div>
      )}
      
      {/* 主录音按钮 */}
      <button 
        className={`record-button ${isRecording ? 'recording' : ''} 
          ${isButtonDisabled() ? 'disabled' : ''} 
          ${connectionStatus !== 'online' ? 'network-issue' : ''}
          ${lowVolumeWarning ? 'low-volume' : ''}
          ${hasPendingMessages ? 'pending-messages' : ''}`}
        onClick={handleRecordClick}
        disabled={isButtonDisabled()}
        title={
          !isReady ? '您的浏览器不支持语音功能或麦克风不可用' : 
          connectionStatus !== 'online' ? '网络连接已断开，正在尝试重连' :
          lowVolumeWarning ? '检测到音量过低，请靠近麦克风或调高音量' :
          hasPendingMessages ? '您有待发送的消息，将在网络恢复后自动发送' :
          (isRecording ? '点击停止录音' : '点击开始录音')
        }
      >
        {getButtonText()}
        
        {/* 连接状态指示器 */}
        {connectionStatus !== 'online' && (
          <span className="connection-indicator"></span>
        )}
        
        {/* 低音量警告 */}
        {isRecording && lowVolumeWarning && (
          <span className="volume-warning">音量低</span>
        )}
      </button>
      
      {/* 待发送消息指示器 */}
      {hasPendingMessages && (
        <div className="pending-message-indicator" title="有待发送的消息，网络恢复后将自动发送">
          待发送: {hasPendingMessages ? '有' : '无'}
        </div>
      )}
    </div>
  );
};

export default RecordButton;
