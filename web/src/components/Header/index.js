import React from 'react';
import './Header.css';

const Header = ({ toggleSettings }) => {
  return (
    <header className="header">
      <div className="header-content">
        <h1>小智 - 数字人助手</h1>
        <p className="subtitle">由 EchoMimic + Deepgram + Gemini + LangChain 驱动</p>
      </div>
      <button className="settings-button" onClick={toggleSettings}>
        <i className="fas fa-cog"></i>
      </button>
    </header>
  );
};

export default Header;
