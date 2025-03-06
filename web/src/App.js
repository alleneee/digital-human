import React from 'react';
import './App.css';
import ChatPanel from './components/ChatPanel';
import DigitalHuman from './components/DigitalHuman';
import RecordButton from './components/RecordButton';
import SettingsPanel from './components/SettingsPanel';
import ThemeSwitcher from './components/ThemeSwitcher';
import { ConfigProvider } from './contexts/ConfigContext';
import { WebSocketProvider } from './contexts/WebSocketContext';
import { WebRTCProvider } from './contexts/WebRTCContext';
import { NotificationProvider } from './contexts/NotificationContext';
import Notification from './components/Notification';

function App() {
  return (
    <NotificationProvider>
      <ConfigProvider>
        <WebSocketProvider>
          <WebRTCProvider>
            <div className="app-container">
              <div className="left-panel">
                <DigitalHuman />
              </div>
              <div className="right-panel">
                <ChatPanel />
                <RecordButton />
                <ThemeSwitcher />
                <SettingsPanel />
              </div>
              <Notification />
            </div>
          </WebRTCProvider>
        </WebSocketProvider>
      </ConfigProvider>
    </NotificationProvider>
  );
}

export default App;
