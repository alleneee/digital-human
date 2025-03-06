import React, { createContext, useState, useContext, useCallback } from 'react';

// 创建上下文
const NotificationContext = createContext();

// 通知提供者组件
export const NotificationProvider = ({ children }) => {
  const [notifications, setNotifications] = useState([]);

  // 关闭通知
  const closeNotification = useCallback((id) => {
    setNotifications(prev => prev.filter(notification => notification.id !== id));
  }, []);

  // 显示通知
  const showNotification = useCallback((message, type = 'info', duration = 5000) => {
    const id = Date.now() + Math.random().toString(36).substr(2, 5);
    const notification = { id, message, type, duration };
    
    setNotifications(prev => [...prev, notification]);
    
    // 设置自动关闭
    if (duration > 0) {
      setTimeout(() => {
        closeNotification(id);
      }, duration);
    }
    
    return id;
  }, [closeNotification]);

  // 便捷方法
  const info = useCallback((message, duration = 5000) => {
    return showNotification(message, 'info', duration);
  }, [showNotification]);

  const success = useCallback((message, duration = 5000) => {
    return showNotification(message, 'success', duration);
  }, [showNotification]);

  const error = useCallback((message, duration = 7000) => {
    return showNotification(message, 'error', duration);
  }, [showNotification]);

  const warning = useCallback((message, duration = 6000) => {
    return showNotification(message, 'warning', duration);
  }, [showNotification]);

  // 添加一个简单的方法，用于测试
  const addNotification = useCallback((message, type = 'info') => {
    return showNotification(message, type);
  }, [showNotification]);

  return (
    <NotificationContext.Provider 
      value={{ 
        notifications, 
        showNotification, 
        closeNotification,
        info,
        success,
        error,
        warning,
        addNotification
      }}
    >
      {children}
    </NotificationContext.Provider>
  );
};

// 自定义Hook，用于在组件中访问通知功能
export const useNotification = () => {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error('useNotification must be used within a NotificationProvider');
  }
  return context;
};
