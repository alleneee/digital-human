import React, { createContext, useState, useContext, useEffect } from 'react';

// 默认配置
const defaultConfig = {
  language: 'zh-CN',
  voice: 'aura-mandarin',
  theme: 'light',
  // EchoMimic相关配置
  useEchoMimic: true, // 保留这个字段用于与后端通信
  refImagePath: null
};

// 创建上下文
const ConfigContext = createContext();

// 配置提供者组件
export const ConfigProvider = ({ children }) => {
  const [config, setConfig] = useState(() => {
    // 从本地存储加载配置
    const savedConfig = localStorage.getItem('digital-human-config');
    return savedConfig ? JSON.parse(savedConfig) : defaultConfig;
  });

  // 当配置变化时保存到本地存储并发送到服务器
  useEffect(() => {
    localStorage.setItem('digital-human-config', JSON.stringify(config));
    
    // 将配置同步到服务器
    fetch('http://localhost:8000/api/update_config', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        useEchoMimic: config.useEchoMimic,
        refImagePath: config.refImagePath,
        language: config.language
      })
    }).catch(err => {
      console.error('同步配置到服务器失败:', err);
    });
  }, [config]);

  // 更新配置
  const updateConfig = (newConfig) => {
    setConfig(prev => ({ ...prev, ...newConfig }));
  };

  // 应用主题
  useEffect(() => {
    if (config.theme === 'dark') {
      document.body.classList.add('dark-theme');
    } else {
      document.body.classList.remove('dark-theme');
    }
  }, [config.theme]);

  return (
    <ConfigContext.Provider value={{ config, updateConfig }}>
      {children}
    </ConfigContext.Provider>
  );
};

// 自定义Hook，用于在组件中访问配置
export const useConfig = () => {
  const context = useContext(ConfigContext);
  if (!context) {
    throw new Error('useConfig must be used within a ConfigProvider');
  }
  return context;
};
