flowchart LR
    subgraph Client["客户端"]
        UI[用户界面]
        AudioRec[音频录制]
        VideoPlayer[视频播放器]
        
        UI --> AudioRec
        UI --> VideoPlayer
    end
    
    subgraph Server["服务端"]
        APIGateway[API网关]
        
        subgraph AudioManager["音频管理器"]
            AudioReceiver[音频接收器]
            FormatConverter[格式转换器]
            AudioProcessor[音频预处理器]
        end
        
        subgraph APIService["API服务集成"]
            STTConnector[STT API连接器]
            LLMConnector[LLM API连接器]
            TTSConnector[TTS API连接器]
            APICache[API响应缓存]
        end
        
        subgraph AIProvider["AI服务提供商"]
            OpenAIService[OpenAI服务]
            AnthropicService[Anthropic服务]
            CustomProvider[其他AI提供商]
        end
        
        subgraph DigitalHumanRenderer["数字人渲染服务"]
            EchoMimic[EchoMimic引擎]
            AudioFeature[音频特征处理]
            RefImageProcessor[参考图像处理]
            PoseDataManager[姿态数据管理]
            VideoGenerator[视频生成器]
        end
        
        TaskQueue[任务队列]
        ResultCache[结果缓存]
        DataStorage[数据存储]
    end
    
    %% 连接关系
    AudioRec -->|音频数据| APIGateway
    APIGateway --> AudioManager
    
    AudioManager --> APIService
    APIService --> AIProvider
    
    AIProvider -->|STT结果| APIService
    AIProvider -->|LLM回复| APIService
    AIProvider -->|TTS音频| APIService
    
    APIService --> DigitalHumanRenderer
    DigitalHumanRenderer -->|视频URL| APIGateway
    APIGateway -->|视频数据| VideoPlayer
    
    %% 任务流程和数据流
    APIGateway <--> TaskQueue
    TaskQueue --> AudioManager
    TaskQueue --> APIService
    TaskQueue --> DigitalHumanRenderer
    
    APIService <--> APICache
    DigitalHumanRenderer <--> ResultCache
    DataStorage <--> AudioManager
    DataStorage <--> DigitalHumanRenderer
    DataStorage <--> ResultCache
    
    %% 系统内通信
    DigitalHumanRenderer -->|反馈| TaskQueue
    AudioManager -->|状态更新| APIGateway
    
    %% 样式定义
    classDef client fill:#d5e8d4,stroke:#82b366
    classDef server fill:#dae8fc,stroke:#6c8ebf
    classDef api fill:#fff2cc,stroke:#d6b656
    classDef ai fill:#f8cecc,stroke:#b85450
    classDef storage fill:#e1d5e7,stroke:#9673a6
    
    class Client client
    class Server server
    class AudioManager,DigitalHumanRenderer server
    class APIService api
    class AIProvider ai
    class TaskQueue,ResultCache,DataStorage,APICache storage