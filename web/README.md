# 数字人助手 React 前端

这是基于 React 重构的数字人助手前端项目，提供了更加现代化和可维护的用户界面。

## 功能特点

- **Live2D 模型展示**：集成 Live2D 模型，实现数字人形象的展示和动画效果
- **语音交互**：支持通过麦克风与数字人进行语音对话
- **实时对话**：文本输入和语音输入支持，与 AI 进行自然对话
- **多语言支持**：支持中文、英文和日语的交互
- **主题切换**：支持浅色和深色主题
- **响应式设计**：适配桌面、平板和移动设备

## 技术栈

- React 18
- Context API 用于状态管理
- WebSocket 用于实时通信
- Web Audio API 用于音频处理
- PIXI.js 和 pixi-live2d-display 用于渲染 Live2D 模型

## 项目结构

```
frontend-react/
├── public/             # 静态资源
├── src/
│   ├── components/     # React 组件
│   │   ├── ChatSection/        # 聊天相关组件
│   │   ├── DigitalHuman/       # 数字人模型组件
│   │   ├── Header/             # 页面头部
│   │   ├── LoadingOverlay/     # 加载状态组件
│   │   ├── NotificationContainer/  # 通知组件
│   │   ├── SettingsPanel/      # 设置面板
│   │   └── StatusBar/          # 状态栏
│   ├── contexts/       # React 上下文
│   │   ├── ConfigContext.js    # 配置管理
│   │   ├── NotificationContext.js # 通知管理
│   │   └── WebSocketContext.js # WebSocket通信
│   ├── App.js          # 主应用组件
│   ├── App.css         # 主应用样式
│   ├── index.js        # 应用入口
│   └── index.css       # 全局样式
└── package.json        # 依赖配置
```

## 开发指南

### 安装依赖

```bash
npm install
```

### 启动开发服务器

```bash
npm start
```
或使用提供的脚本：
```bash
./start-dev.sh
```

默认情况下，开发服务器将在 http://localhost:3000 启动。API 请求将被代理到 http://localhost:8000。

### 构建生产版本

```bash
npm run build
```

## WebSocket 通信

前端通过 WebSocket 与后端进行实时通信，消息格式如下：

### 发送消息
```javascript
// 文本消息
{
  type: 'text_input',
  text: '用户输入的文本'
}

// 配置消息
{
  type: 'config',
  config: {
    language: 'zh-CN',
    voice: 'aura-mandarin',
    modelPath: '模型路径',
    theme: 'light'
  }
}
```

### 接收消息
```javascript
// 文本响应
{
  type: 'response',
  text: 'AI 返回的文本'
}

// 转写结果
{
  type: 'transcription',
  text: '语音识别的文本'
}

// 错误消息
{
  type: 'error',
  message: '错误信息'
}
```

音频数据以二进制形式通过 WebSocket 传输。
