import React, { useMemo, useState, useCallback, useEffect } from 'react'
import ChatPage from './components/ChatPage'
import OptionsPage from './components/OptionsPage'
import ToastProvider from './components/Toast'
import './app.css'

function App() {
  const port = (window.odin && window.odin.backendPort()) || '8765';
  const api = useMemo(() => (p) => `http://127.0.0.1:${port}${p}`, [port]);
  const [tab, setTab] = useState('chat');
  const [theme, setTheme] = useState('light');

  const [indexInfo, setIndexInfo] = useState({
    basePath: '',
    allExts: [],
    aiExts: [],
    allowedExts: [],
    indexCsvPath: ''
  });

  const setAllowedByPreset = useCallback((aiOnly) => {
    setIndexInfo((prev) => ({
      ...prev,
      allowedExts: aiOnly ? prev.aiExts.filter(ext => ext !== '.hwp') : [...prev.allExts]
    }))
  }, [])

  // Apply theme to document
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  // Load fonts dynamically
  useEffect(() => {
    const loadFonts = async () => {
      if (window.odin && window.odin.getFontPath) {
        try {
          const fontPath = await window.odin.getFontPath();
          
          // Create dynamic font face CSS
          const fontCSS = `
            @font-face {
              font-family: 'GowunBatang';
              src: url('${fontPath}GowunBatang-Regular.ttf') format('truetype');
              font-weight: normal;
              font-style: normal;
            }
            @font-face {
              font-family: 'GowunBatang';
              src: url('${fontPath}GowunBatang-Bold.ttf') format('truetype');
              font-weight: bold;
              font-style: normal;
            }
          `;
          
          // Add the CSS to the document
          const styleElement = document.createElement('style');
          styleElement.textContent = fontCSS;
          document.head.appendChild(styleElement);
        } catch (error) {
        }
      }
    };
    
    loadFonts();
  }, []);

  const toggleTheme = () => {
    setTheme(prev => prev === 'light' ? 'dark' : 'light');
  };

  return (
    <div>
      <header>
        <h1>Odin Desktop</h1>
        <button className="text" onClick={toggleTheme}>
          {theme === 'light' ? '🌙 다크 모드' : '☀️ 라이트 모드'}
        </button>
      </header>

      <div className="tabs">
        <button className={`tab ${tab==='chat'?'active':''}`} onClick={() => setTab('chat')}>대화</button>
        <button className={`tab ${tab==='options'?'active':''}`} onClick={() => setTab('options')}>옵션</button>
      </div>

      <ToastProvider>
        {tab === 'chat' && (
          <ChatPage api={api} indexInfo={indexInfo} />
        )}
        {tab === 'options' && (
          <OptionsPage api={api} indexInfo={indexInfo} setIndexInfo={setIndexInfo} setAllowedByPreset={setAllowedByPreset} />
        )}
      </ToastProvider>
    </div>
  )
}

export default App
