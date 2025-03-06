import React from 'react';
import './StatusBar.css';

const StatusBar = ({ status, message }) => {
  const getStatusIcon = () => {
    switch (status) {
      case 'online':
        return <i className="fas fa-circle status-icon online"></i>;
      case 'offline':
        return <i className="fas fa-circle status-icon offline"></i>;
      case 'connecting':
        return <i className="fas fa-circle-notch fa-spin status-icon connecting"></i>;
      default:
        return <i className="fas fa-circle status-icon offline"></i>;
    }
  };
  
  return (
    <div className="status-bar">
      <div className="status-indicator">
        {getStatusIcon()}
        <span className="status-text">{message}</span>
      </div>
      
      <div className="app-version">
        数字人助手 v1.0.0
      </div>
    </div>
  );
};

export default StatusBar;
