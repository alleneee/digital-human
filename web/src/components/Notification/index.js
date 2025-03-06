import React, { useEffect } from 'react';
import { useNotification } from '../../contexts/NotificationContext';
import './Notification.css';

const Notification = () => {
  const { notifications, closeNotification } = useNotification();
  
  // 自动移除通知
  useEffect(() => {
    if (notifications.length > 0) {
      const timer = setTimeout(() => {
        closeNotification(notifications[0].id);
      }, 3000);
      
      return () => clearTimeout(timer);
    }
  }, [notifications, closeNotification]);
  
  if (notifications.length === 0) return null;
  
  return (
    <div className="notification-container">
      {notifications.map((notification) => (
        <div 
          key={notification.id}
          className={`notification ${notification.type}`}
        >
          <div className="notification-content">{notification.message}</div>
          <button 
            className="notification-close"
            onClick={() => closeNotification(notification.id)}
          >
            ×
          </button>
        </div>
      ))}
    </div>
  );
};

export default Notification;
