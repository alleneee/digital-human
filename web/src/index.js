import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';

// 直接渲染App组件，不使用任何上下文提供者
const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

// 添加一个控制台日志，确认index.js已加载
console.log('index.js已加载，React版本:', React.version);
