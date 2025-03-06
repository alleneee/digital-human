import React from 'react';
import { useConfig } from '../../contexts/ConfigContext';
import './ThemeSwitcher.css';

export const ThemeSwitcher = () => {
  const { config, updateConfig } = useConfig();
  
  const toggleTheme = () => {
    const newTheme = config.theme === 'light' ? 'dark' : 'light';
    updateConfig({ theme: newTheme });
  };
  
  return (
    <button 
      className="theme-switcher"
      onClick={toggleTheme}
      aria-label={`切换至${config.theme === 'light' ? '深色' : '浅色'}主题`}
    >
      {config.theme === 'light' ? '🌙' : '☀️'}
    </button>
  );
};

export default ThemeSwitcher;
