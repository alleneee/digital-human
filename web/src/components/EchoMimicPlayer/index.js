import React, { useEffect, useRef, useState } from 'react';
import './EchoMimicPlayer.css';

/**
 * EchoMimic视频播放组件
 * 负责显示和控制EchoMimic生成的视频
 */
const EchoMimicPlayer = ({ 
  videoSrc, 
  onEnded, 
  onClose,
  autoPlay = true,
  width = 512,
  height = 512,
  className = ''
}) => {
  const videoRef = useRef(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoaded, setIsLoaded] = useState(false);
  const [error, setError] = useState(null);

  // 当视频源变化时，重置状态
  useEffect(() => {
    if (videoSrc) {
      setIsLoaded(false);
      setError(null);
    }
  }, [videoSrc]);

  // 处理视频加载完成事件
  const handleVideoLoaded = () => {
    setIsLoaded(true);
    if (autoPlay) {
      playVideo();
    }
  };

  // 处理视频播放结束事件
  const handleVideoEnded = () => {
    setIsPlaying(false);
    if (onEnded && typeof onEnded === 'function') {
      onEnded();
    }
  };

  // 处理播放错误
  const handleError = (e) => {
    console.error('视频播放错误:', e);
    setError('视频加载失败');
  };

  // 播放视频
  const playVideo = () => {
    if (videoRef.current) {
      videoRef.current.play()
        .then(() => {
          setIsPlaying(true);
        })
        .catch(err => {
          console.error('播放失败:', err);
          setError('视频播放失败');
        });
    }
  };

  // 暂停视频
  const pauseVideo = () => {
    if (videoRef.current) {
      videoRef.current.pause();
      setIsPlaying(false);
    }
  };

  // 重新播放
  const replayVideo = () => {
    if (videoRef.current) {
      videoRef.current.currentTime = 0;
      playVideo();
    }
  };

  return (
    <div className={`echomimic-player ${className}`} style={{ width, height }}>
      {onClose && (
        <button className="close-video-btn" onClick={onClose}>
          &times;
        </button>
      )}
      
      {videoSrc ? (
        <>
          <video
            ref={videoRef}
            className="echomimic-video"
            src={videoSrc}
            width={width}
            height={height}
            onLoadedData={handleVideoLoaded}
            onEnded={handleVideoEnded}
            onError={handleError}
            playsInline
          />
          
          {!isLoaded && !error && (
            <div className="loading-overlay">
              <div className="loading-spinner"></div>
              <div className="loading-text">加载视频中...</div>
            </div>
          )}
          
          {error && (
            <div className="error-overlay">
              <div className="error-message">{error}</div>
              <button 
                className="retry-button"
                onClick={() => {
                  setError(null);
                  if (videoRef.current) {
                    videoRef.current.load();
                  }
                }}
              >
                重试
              </button>
            </div>
          )}
          
          {isLoaded && !isPlaying && !error && (
            <div className="controls-overlay">
              <button className="play-button" onClick={replayVideo}>
                <span className="play-icon">▶</span>
              </button>
            </div>
          )}
        </>
      ) : (
        <div className="placeholder">
          <div className="placeholder-text">视频未加载</div>
        </div>
      )}
    </div>
  );
};

export default EchoMimicPlayer;
