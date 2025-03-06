import React, { createContext, useState, useContext, useEffect, useCallback, useRef } from 'react';
import { useWebSocket } from './WebSocketContext';
import { useConfig } from './ConfigContext';
import { useNotification } from './NotificationContext';
import { createClient } from '@deepgram/sdk';

// 创建上下文
const WebRTCContext = createContext();

// WebRTC提供者组件
export const WebRTCProvider = ({ children }) => {
  const { socket, isConnected, sendMessage } = useWebSocket();
  const { config } = useConfig();
  const { success, error } = useNotification();
  
  // WebRTC状态
  const [isReady, setIsReady] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [transcription, setTranscription] = useState('');
  const [interimTranscription, setInterimTranscription] = useState('');
  const [audioLevel, setAudioLevel] = useState(0);
  const [lowVolumeWarning, setLowVolumeWarning] = useState(false);
  const [processorLoaded, setProcessorLoaded] = useState(false);
  
  // 引用存储
  const mediaStreamRef = useRef(null);
  const audioContextRef = useRef(null);
  const processorRef = useRef(null);
  const sourceNodeRef = useRef(null);
  const deepgramConnectionRef = useRef(null);
  const analyzerRef = useRef(null);
  const audioDataBufferRef = useRef([]);
  const animationFrameRef = useRef(null);
  
  // 初始化Deepgram客户端
  const initDeepgram = useCallback(async () => {
    try {
      // 使用环境变量中的API密钥
      const apiKey = process.env.REACT_APP_DEEPGRAM_API_KEY;
      if (!apiKey) {
        throw new Error('未找到Deepgram API密钥');
      }
      
      console.log('正在初始化Deepgram...');
      return createClient(apiKey);
    } catch (err) {
      console.error('初始化Deepgram失败:', err);
      error('无法连接到语音服务');
      return null;
    }
  }, [error]);
  
  // 开始录音并实时转写
  const startRecording = useCallback(async () => {
    if (isRecording) return;
    
    try {
      console.log('正在请求麦克风权限...');
      
      // 请求麦克风访问权限
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }, 
        video: false 
      });
      
      mediaStreamRef.current = stream;
      
      // 创建音频处理上下文
      const audioContext = new (window.AudioContext || window.webkitAudioContext)();
      audioContextRef.current = audioContext;
      
      // 创建媒体源节点
      const sourceNode = audioContext.createMediaStreamSource(stream);
      sourceNodeRef.current = sourceNode;
      
      // 创建音频分析器节点用于音量监测
      const analyzer = audioContext.createAnalyser();
      analyzer.fftSize = 256;
      analyzer.smoothingTimeConstant = 0.8;
      analyzerRef.current = analyzer;
      
      // 加载并创建AudioWorklet处理器
      try {
        // 检查是否已加载处理器代码
        if (!processorLoaded) {
          console.log('正在加载音频处理器模块...');
          await audioContext.audioWorklet.addModule('/audio-processor.js');
          setProcessorLoaded(true);
        }
        
        // 创建工作节点
        const processor = new AudioWorkletNode(audioContext, 'audio-processor');
        processorRef.current = processor;
        
        // 配置处理器
        processor.port.postMessage({
          command: 'configure',
          config: {
            sampleRate: audioContext.sampleRate,
            targetSampleRate: 16000  // Deepgram推荐采样率
          }
        });
        
        // 处理来自处理器的音频数据
        processor.port.onmessage = (event) => {
          if (!deepgramConnectionRef.current) return;
          
          if (event.data.type === 'audio-data') {
            // 向Deepgram发送处理好的音频数据
            deepgramConnectionRef.current.send(event.data.buffer);
          }
        };
      } catch (err) {
        console.error('创建AudioWorklet处理器失败:', err);
        error('高级音频处理不可用，将使用备用方法');
        
        // 备用方案：创建旧版处理器节点
        const backupProcessor = audioContext.createScriptProcessor(4096, 1, 1);
        processorRef.current = backupProcessor;
        
        // 处理音频数据并发送到Deepgram
        backupProcessor.onaudioprocess = (e) => {
          if (!deepgramConnectionRef.current) return;
          
          // 获取音频数据
          const inputData = e.inputBuffer.getChannelData(0);
          
          // 转换为16位PCM格式
          const pcmData = new Int16Array(inputData.length);
          for (let i = 0; i < inputData.length; i++) {
            pcmData[i] = Math.min(1, Math.max(-1, inputData[i])) * 0x7FFF;
          }
          
          // 发送到Deepgram
          deepgramConnectionRef.current.send(pcmData.buffer);
        };
      }
      
      // 初始化Deepgram客户端
      const deepgram = await initDeepgram();
      if (!deepgram) {
        throw new Error('无法初始化Deepgram');
      }
      
      // 创建Deepgram实时连接
      const deepgramConnection = deepgram.listen.live({
        language: config.language || 'zh-CN',
        model: 'nova',
        smart_format: true,
        interim_results: true,
        punctuate: true
      });
      
      // 保存连接引用
      deepgramConnectionRef.current = deepgramConnection;
      
      // 处理转写结果
      deepgramConnection.on('transcriptReceived', (transcript) => {
        // 解析转写结果
        const result = transcript.channel.alternatives[0];
        
        if (transcript.is_final) {
          // 最终结果
          if (result.transcript) {
            console.log('最终转写结果:', result.transcript);
            setTranscription(prev => prev + result.transcript + ' ');
            
            // 清除临时结果
            setInterimTranscription('');
            
            // 可选：发送到服务器
            sendMessage({
              type: 'transcription',
              text: result.transcript,
              final: true
            });
          }
        } else {
          // 临时结果
          if (result.transcript) {
            console.log('临时转写结果:', result.transcript);
            setInterimTranscription(result.transcript);
          }
        }
      });
      
      // 错误处理
      deepgramConnection.on('error', (err) => {
        console.error('Deepgram转写错误:', err);
        error('语音转写服务出错');
      });
      
      // 启动音频音量监测
      const monitorAudioLevel = () => {
        if (!analyzerRef.current || !isRecording) return;
        
        // 获取频率数据
        const dataArray = new Uint8Array(analyzerRef.current.frequencyBinCount);
        analyzerRef.current.getByteFrequencyData(dataArray);
        
        // 计算平均音量
        let sum = 0;
        for (let i = 0; i < dataArray.length; i++) {
          sum += dataArray[i];
        }
        const average = sum / dataArray.length;
        
        // 更新音量状态
        setAudioLevel(average);
        
        // 如果音量太低，显示警告
        if (isRecording && average < 10 && Date.now() - recordingStartTime > 1000) {
          setLowVolumeWarning(true);
        } else {
          setLowVolumeWarning(false);
        }
        
        // 继续监测
        animationFrameRef.current = requestAnimationFrame(monitorAudioLevel);
      };
      
      // 记录录音开始时间
      const recordingStartTime = Date.now();
      
      // 开始音量监测
      animationFrameRef.current = requestAnimationFrame(monitorAudioLevel);
      
      // 连接音频节点
      sourceNode.connect(analyzer);
      
      // 获取处理器引用
      const processor = processorRef.current;
      
      // 判断处理器类型
      const isScriptProcessor = processor instanceof ScriptProcessorNode;
      
      // 连接到音频处理器
      if (processor) {
        analyzer.connect(processor);
        // 只有ScriptProcessor需要连接到目标
        if (isScriptProcessor) {
          processor.connect(audioContext.destination);
        }
      }
      
      // 更新状态
      setIsRecording(true);
      success('已开始录音');
      
      // 通知服务器开始录音
      sendMessage({
        type: 'recording_started',
        timestamp: new Date().toISOString()
      });
      
    } catch (err) {
      console.error('启动录音失败:', err);
      error(err.message || '无法访问麦克风');
      stopRecording();
    }
  }, [isRecording, config, initDeepgram, sendMessage, success, error]);
  
  // 停止录音
  const stopRecording = useCallback(() => {
    // 停止所有媒体轨道
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach(track => track.stop());
      mediaStreamRef.current = null;
    }
    
    // 关闭Deepgram连接
    if (deepgramConnectionRef.current) {
      try {
        deepgramConnectionRef.current.finish();
        deepgramConnectionRef.current = null;
      } catch (err) {
        console.error('关闭Deepgram连接出错:', err);
      }
    }
    
    // 停止音量监测
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
      animationFrameRef.current = null;
    }
    
    // 断开音频处理节点
    try {
      if (analyzerRef.current) {
        analyzerRef.current.disconnect();
      }
      
      if (sourceNodeRef.current) {
        sourceNodeRef.current.disconnect();
      }
      
      if (processorRef.current) {
        processorRef.current.disconnect();
      }
    } catch (err) {
      console.error('断开音频节点出错:', err);
    }
    
    // 关闭音频上下文
    if (audioContextRef.current) {
      try {
        audioContextRef.current.close();
        audioContextRef.current = null;
      } catch (err) {
        console.error('关闭音频上下文出错:', err);
      }
    }
    
    // 更新状态
    setIsRecording(false);
    
    // 如果有最终的转写结果，发送到服务器
    if (transcription.trim()) {
      sendMessage({
        type: 'transcription_complete',
        text: transcription.trim(),
        timestamp: new Date().toISOString()
      });
    }
    
    // 通知服务器录音已停止
    sendMessage({
      type: 'recording_stopped',
      timestamp: new Date().toISOString()
    });
  }, [transcription, sendMessage]);
  
  // 切换录音状态
  const toggleRecording = useCallback(() => {
    if (isRecording) {
      stopRecording();
    } else {
      // 如果开始新的录音，清除之前的转写结果
      setTranscription('');
      setInterimTranscription('');
      startRecording();
    }
  }, [isRecording, startRecording, stopRecording]);
  
  // 向服务器发送完整的转写文本
  const sendTranscription = useCallback(() => {
    if (!transcription.trim()) {
      error('没有可发送的文本');
      return;
    }
    
    sendMessage({
      type: 'text_input',
      text: transcription.trim(),
      audio_quality: {
        averageLevel: audioLevel,
        hadLowVolumeWarning: lowVolumeWarning
      }
    });
    
    // 清除本地转写缓存
    setTranscription('');
    setInterimTranscription('');
    setLowVolumeWarning(false);
    
    success('消息已发送');
  }, [transcription, audioLevel, lowVolumeWarning, sendMessage, success, error]);
  
  // 初始化检查WebRTC支持
  useEffect(() => {
    // 检查浏览器支持
    const checkSupport = () => {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        console.error('浏览器不支持WebRTC');
        error('您的浏览器不支持语音功能');
        return false;
      }
      
      if (!window.AudioContext && !window.webkitAudioContext) {
        console.error('浏览器不支持AudioContext');
        error('您的浏览器不支持音频处理功能');
        return false;
      }
      
      return true;
    };
    
    const isSupported = checkSupport();
    setIsReady(isSupported);
    
    if (isSupported) {
      console.log('WebRTC和音频处理功能已就绪');
    }
    
    // 组件卸载时停止录音
    return () => {
      if (isRecording) {
        stopRecording();
      }
    };
  }, [isRecording, stopRecording, error]);
  
  // 提供上下文值
  const contextValue = {
    isReady,
    isRecording,
    transcription,
    interimTranscription,
    audioLevel,
    lowVolumeWarning,
    startRecording,
    stopRecording,
    toggleRecording,
    sendTranscription,
    clearTranscription: () => {
      setTranscription('');
      setInterimTranscription('');
      setLowVolumeWarning(false);
    }
  };
  
  return (
    <WebRTCContext.Provider value={contextValue}>
      {children}
    </WebRTCContext.Provider>
  );
};

// 自定义Hook，用于在组件中访问WebRTC功能
export const useWebRTC = () => {
  const context = useContext(WebRTCContext);
  if (!context) {
    throw new Error('useWebRTC必须在WebRTCProvider内部使用');
  }
  return context;
};
