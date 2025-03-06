sequenceDiagram
    participant Client as 客户端
    participant Server as 服务端
    participant STT as 语音转文本API
    participant LLM as 大语言模型API
    participant TTS as 文本转语音API
    participant EM as EchoMimic引擎
    
    %% STT处理流程
    Client->>Server: 发送音频数据
    Note over Server: 音频预处理
    Server->>STT: 请求语音识别
    activate STT
    Note over STT: 音频转文本处理
    STT-->>Server: 返回文本及时间戳
    deactivate STT
    
    %% LLM处理流程
    Note over Server: 构建对话上下文
    Server->>LLM: 发送用户文本和对话历史
    activate LLM
    Note over LLM: 生成回复内容
    LLM-->>Server: 返回AI回复文本
    deactivate LLM
    
    %% TTS处理流程
    Note over Server: 准备文本内容
    Server->>TTS: 请求语音合成
    activate TTS
    Note over TTS: 文本转语音处理
    TTS-->>Server: 返回合成音频
    deactivate TTS
    
    %% EchoMimic处理流程
    Note over Server: 准备合成请求
    Server->>EM: 提交处理任务
    activate EM
    Note over EM: 生成数字人视频
    EM-->>Server: 返回视频URL
    deactivate EM
    
    %% 返回结果给客户端
    Server-->>Client: 返回数字人视频
    
    %% API调用细节
    rect rgb(240, 240, 240)
        Note right of STT: STT API调用示例<br/>POST https://api.openai.com/v1/audio/transcriptions<br/>Headers: {Authorization: Bearer API_KEY}<br/>Body: {file: audio.mp3, model: "whisper-1", response_format: "json"}
    end
    
    rect rgb(240, 240, 240)
        Note right of LLM: LLM API调用示例<br/>POST https://api.openai.com/v1/chat/completions<br/>Headers: {Authorization: Bearer API_KEY}<br/>Body: {model: "gpt-4", messages: [{role: "user", content: "..."}]}
    end
    
    rect rgb(240, 240, 240)
        Note right of TTS: TTS API调用示例<br/>POST https://api.openai.com/v1/audio/speech<br/>Headers: {Authorization: Bearer API_KEY}<br/>Body: {model: "tts-1", input: "...", voice: "alloy"}
    end
    
    %% 错误处理
    alt API调用失败
        STT--xServer: 返回错误
        Server-->>Server: 错误处理和重试逻辑
    else 超时
        LLM--xServer: 请求超时
        Server-->>Server: 超时处理和降级策略
    end