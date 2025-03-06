/**
 * 音频处理器工作线程
 * 用于音频数据的处理和转换
 */
class AudioProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    // 创建音频缓冲区
    this._buffer = new Float32Array(4096);
    this._bufferIndex = 0;
    
    // 处理来自主线程的消息
    this.port.onmessage = (event) => {
      if (event.data.command === 'configure') {
        console.log('配置音频处理器:', event.data.config);
      }
    };
  }

  /**
   * 处理音频输入并转换为适合传输的格式
   * @param {Array} inputs - 输入通道
   * @param {Array} outputs - 输出通道
   * @param {Object} parameters - 处理参数
   * @returns {boolean} - 返回true以继续处理
   */
  process(inputs, outputs, parameters) {
    const input = inputs[0][0];
    if (!input) return true;
    
    // 将输入数据添加到缓冲区
    for (let i = 0; i < input.length; i++) {
      this._buffer[this._bufferIndex++] = input[i];
      
      // 当缓冲区已满时，发送数据并重置
      if (this._bufferIndex === this._buffer.length) {
        // 转换为Int16格式 (16位PCM)
        const pcmData = new Int16Array(this._buffer.length);
        for (let j = 0; j < this._buffer.length; j++) {
          pcmData[j] = Math.min(1, Math.max(-1, this._buffer[j])) * 0x7FFF;
        }
        
        // 发送到主线程
        this.port.postMessage({
          type: 'audio-data',
          buffer: pcmData.buffer
        }, [pcmData.buffer]);
        
        // 创建新缓冲区
        this._buffer = new Float32Array(4096);
        this._bufferIndex = 0;
      }
    }
    
    return true;
  }
}

// 注册处理器
registerProcessor('audio-processor', AudioProcessor);
