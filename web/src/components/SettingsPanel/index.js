import React, { useState, useEffect } from 'react';
import { useConfig } from '../../contexts/ConfigContext';
import { useNotification } from '../../contexts/NotificationContext';
import './SettingsPanel.css';

const SettingsPanel = () => {
  const { config, updateConfig } = useConfig();
  const { success, error } = useNotification();
  const [isOpen, setIsOpen] = useState(false);
  const [presetImages, setPresetImages] = useState([]);
  const [selectedGender, setSelectedGender] = useState('woman');
  const [selectedImage, setSelectedImage] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  // 处理设置面板的开关
  const togglePanel = () => {
    setIsOpen(!isOpen);
  };

  // 切换EchoMimic功能
  const handleEchoMimicToggle = (e) => {
    updateConfig({ useEchoMimic: e.target.checked });
  };

  // 更新语言设置
  const handleLanguageChange = (e) => {
    updateConfig({ language: e.target.value });
  };

  // 获取预设图像列表
  const fetchPresetImages = async () => {
    try {
      setIsLoading(true);
      const gender = selectedGender; // 'man' 或 'woman'
      const response = await fetch(`http://localhost:8000/api/preset_images?gender=${gender}`);
      if (!response.ok) {
        throw new Error(`服务器返回错误: ${response.status}`);
      }
      const data = await response.json();
      console.log('获取到预设图像数据:', data);
      setPresetImages(data.images || []);
    } catch (err) {
      console.error('获取预设图像错误:', err);
      error('获取预设图像失败: ' + err.message);
    } finally {
      setIsLoading(false);
    }
  };

  // 当性别选择变化时，重新获取图像
  useEffect(() => {
    if (isOpen) {
      fetchPresetImages();
    }
  }, [selectedGender, isOpen]);

  // 选择预设图像
  const handleSelectImage = async (imagePath) => {
    setSelectedImage(imagePath);
    console.log('选择图像路径:', imagePath);
    
    try {
      const response = await fetch('http://localhost:8000/api/use_preset_image', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ image_path: imagePath })
      });
      
      if (!response.ok) {
        throw new Error(`服务器返回错误: ${response.status}`);
      }
      
      const data = await response.json();
      console.log('服务器响应:', data);
      
      if (data.success) {
        updateConfig({ refImagePath: imagePath });
        success('参考图像已更新');
      } else {
        throw new Error(data.error || '更新参考图像失败');
      }
    } catch (err) {
      console.error('设置参考图像失败:', err);
      error('设置参考图像失败: ' + err.message);
    }
  };

  return (
    <>
      <button className="settings-toggle" onClick={togglePanel}>
        设置
      </button>
      
      <div className={`settings-panel ${isOpen ? 'open' : ''}`}>
        <div className="settings-header">
          <h2>设置</h2>
          <button className="settings-close" onClick={togglePanel}>×</button>
        </div>
        
        <div className="settings-content">
          <div className="settings-section">
            <h3>基本设置</h3>
            
            <div className="settings-option">
              <label>启用EchoMimic</label>
              <label className="toggle-switch">
                <input 
                  type="checkbox" 
                  checked={config.useEchoMimic} 
                  onChange={handleEchoMimicToggle}
                />
                <span className="toggle-slider"></span>
              </label>
            </div>
            
            <div className="settings-option">
              <label>语言</label>
              <select value={config.language} onChange={handleLanguageChange}>
                <option value="zh">中文</option>
                <option value="en">英语</option>
              </select>
            </div>
          </div>
          
          {config.useEchoMimic && (
            <div className="settings-section">
              <h3>EchoMimic设置</h3>
              
              <div className="settings-option">
                <label>选择性别</label>
                <select 
                  value={selectedGender}
                  onChange={(e) => setSelectedGender(e.target.value)}
                >
                  <option value="woman">女性</option>
                  <option value="man">男性</option>
                </select>
              </div>
              
              <div className="settings-option">
                <label>预设参考图像</label>
                {isLoading ? (
                  <div className="loading-spinner"></div>
                ) : (
                  <div className="preset-images-grid">
                    {presetImages.map((image, index) => (
                      <div 
                        key={index}
                        className={`preset-image-item ${selectedImage === image.path ? 'selected' : ''}`}
                        onClick={() => handleSelectImage(image.path)}
                      >
                        <img src={image.thumbnail ? `http://localhost:8000${image.thumbnail}` : `http://localhost:8000/static/preset_images/${selectedGender}/${index + 1}.png`} alt={`参考图像 ${index + 1}`} />
                        <div className="preset-image-overlay">
                          <span>选择</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
};

export default SettingsPanel;
