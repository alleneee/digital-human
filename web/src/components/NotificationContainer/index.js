import React from 'react';
import './NotificationContainer.css';
import { useNotification } from '../../contexts/NotificationContext';

const NotificationContainer = () => {
  const { notifications, closeNotification } = useNotification();
  
  return (
    <div className="notifications-container">
      {notifications.map(notification => (
        <div
          key={notification.id}
          className={`notification notification-${notification.type}`}
        >
          <div className="notification-icon">
            {notification.type === 'info' && <i className="fas fa-info-circle"></i>}
            {notification.type === 'success' && <i className="fas fa-check-circle"></i>}
            {notification.type === 'error' && <i className="fas fa-exclamation-circle"></i>}
            {notification.type === 'warning' && <i className="fas fa-exclamation-triangle"></i>}
          </div>
          
          <div className="notification-message">
            {notification.message}
          </div>
          
          <button
            className="notification-close"
            onClick={() => closeNotification(notification.id)}
          >
            &times;
          </button>
        </div>
      ))}
    </div>
  );
};

export default NotificationContainer;
