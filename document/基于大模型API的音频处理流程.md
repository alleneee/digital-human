flowchart TD
    A[用户语音输入] --> B[音频预处理]
    
    subgraph 音频预处理
        B1[格式转换\nWAV/MP3]
        B2[采样率校准\n16kHz]
        B3[音频分段\n长音频切分]
        
        B1 --> B2 --> B3
    end
    
    B --> C[大模型STT API]
    
    subgraph STT服务
        C1[音频文件上传]
        C2[API调用\nOpenAI Whisper API]
        C3[JSON响应解析]
        
        C1 --> C2 --> C3
    end
    
    C --> D[文本后处理]
    D --> E[文本输入LLM]
    
    subgraph LLM处理
        E1[构建提示词]
        E2[API调用\nGPT/Claude]
        E3[回复提取]
        
        E1 --> E2 --> E3
    end
    
    E --> F[大模型TTS API]
    
    subgraph TTS服务
        F1[文本准备]
        F2[API调用\nOpenAI TTS API]
        F3[音频下载]
        
        F1 --> F2 --> F3
    end
    
    F --> G[音频特征提取]
    G --> H[EchoMimic处理]
    
    subgraph EchoMimic流程
        H1[音频特征融合]
        H2[图像特征处理]
        H3[姿态数据处理]
        H4[视频生成]
        
        H1 & H2 & H3 --> H4
    end
    
    H --> I[音视频同步处理]
    I --> J[数字人视频输出]
    
    %% 数据流向和API调用
    API[大模型API服务] -.->|STT API| C
    API -.->|LLM API| E
    API -.->|TTS API| F
    
    %% 样式定义
    classDef input fill:#d1f0ff,stroke:#0066cc
    classDef process fill:#fffacd,stroke:#d6b656
    classDef output fill:#d5e8d4,stroke:#82b366
    classDef api fill:#f8cecc,stroke:#b85450
    
    class A input
    class B,D,G,I process
    class J output
    class API,STT服务,LLM处理,TTS服务 api
    class 音频预处理,EchoMimic流程 process