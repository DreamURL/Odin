import { app, BrowserWindow, ipcMain, shell, dialog, Menu } from 'electron';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { spawn } from 'node:child_process';
import fs from 'node:fs';

// __dirname is not defined in ESM; reconstruct it
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

let pyProc = null;
let mainWindow = null;

const BACKEND_PORT = process.env.BACKEND_PORT || '8765';
let healthInterval = null;
let backendReady = false;

function startPythonBackend() {
  const isDev = process.env.RENDERER_URL || !app.isPackaged;
  let command, args, cwd;

  if (isDev) {
    // 개발 모드: 가상환경의 Python 사용
    const projectRoot = path.resolve(__dirname, '..');
    const venvPath = path.join(projectRoot, '.venv_odin');
    const pythonExe = process.platform === 'win32' 
      ? path.join(venvPath, 'Scripts', 'python.exe')
      : path.join(venvPath, 'bin', 'python');
    
    const scriptPath = path.resolve(projectRoot, 'backend', 'server.py');
    
    command = pythonExe;
    args = [scriptPath];
    cwd = projectRoot;
    
    console.log(`Development mode: Using virtual environment Python`);
    console.log(`Python: ${pythonExe}`);
    console.log(`Script: ${scriptPath}`);
  } else {
    // 패키징된 모드: 포함된 실행 파일 사용
    const resourcesPath = process.resourcesPath;
    const pythonDistPath = path.join(resourcesPath, 'python-dist');
    const executableName = process.platform === 'win32' ? 'odin-backend.exe' : 'odin-backend';
    const executablePath = path.join(pythonDistPath, executableName);
    
    command = executablePath;
    args = [];
    cwd = pythonDistPath;
    
    console.log('Production mode: Using packaged executable');
    console.log(`Executable: ${executablePath}`);
  }

  console.log(`Starting Python backend: ${command} ${args.join(' ')}`);

  pyProc = spawn(command, args, {
    env: { 
      ...process.env, 
      PORT: BACKEND_PORT, 
      PYTHONIOENCODING: 'utf-8', 
      PYTHONUTF8: '1',
      PYTHONLEGACYWINDOWSSTDIO: '0',
      // Windows에서 한글 처리를 위한 추가 설정
      LANG: 'ko_KR.UTF-8',
      LC_ALL: 'ko_KR.UTF-8'
    },
    cwd: cwd,
    stdio: ['ignore', 'pipe', 'pipe']
  });
  if (pyProc.stdout) {
    pyProc.stdout.setEncoding('utf8');
    pyProc.stdout.on('data', (d) => {
      try { 
        console.log(`[backend] ${d.toString('utf8')}`.trimEnd()); 
      } catch (e) { 
        console.log('[backend] (encoding error)', d); 
      }
    });
  }
  if (pyProc.stderr) {
    pyProc.stderr.setEncoding('utf8');
    pyProc.stderr.on('data', (d) => {
      try { 
        console.error(`[backend:err] ${d.toString('utf8')}`.trimEnd()); 
      } catch (e) { 
        console.error('[backend:err] (encoding error)', d); 
      }
    });
  }
  pyProc.on('exit', (code) => {
    console.log(`[backend] exited with code ${code}`);
  });
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    title: 'Odin',
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false
    }
  });

  // 메뉴바 완전 제거
  Menu.setApplicationMenu(null);

  // 개발 모드에서 개발자 도구 자동 열기
  if (process.env.RENDERER_URL || process.env.NODE_ENV === 'development') {
    mainWindow.webContents.openDevTools();
  }

  // 개발자 도구 토글 단축키 (F12)
  mainWindow.webContents.on('before-input-event', (event, input) => {
    if (input.key === 'F12') {
      if (mainWindow.webContents.isDevToolsOpened()) {
        mainWindow.webContents.closeDevTools();
      } else {
        mainWindow.webContents.openDevTools();
      }
    }
  });

  // Prefer Vite dev server if provided, otherwise load built files, else show hint
  const devUrl = process.env.RENDERER_URL; // e.g. http://localhost:5173
  const distIndex = path.join(__dirname, 'renderer', 'dist', 'index.html');
  if (devUrl) {
    mainWindow.loadURL(devUrl).catch(() => {
      if (fs.existsSync(distIndex)) {
        mainWindow.loadFile(distIndex);
      }
    });
  } else if (fs.existsSync(distIndex)) {
    mainWindow.loadFile(distIndex);
  } else {
    const hint = encodeURIComponent(
      '<!doctype html>\n<html><head><meta charset="utf-8"><title>Odin</title></head>' +
      '<body style="font-family: system-ui; padding: 24px;">' +
      '<h2>Renderer not built</h2>' +
      '<p>Please build the renderer (React+Vite) first:</p>' +
      '<pre>cd electron\\renderer &amp;&amp; npm install &amp;&amp; npm run build</pre>' +
      '<p>Or start a dev server and set RENDERER_URL to its URL.</p>' +
      '</body></html>'
    );
    mainWindow.loadURL(`data:text/html;charset=utf-8,${hint}`);
  }
}

async function checkBackendHealthOnce() {
  const url = `http://127.0.0.1:${BACKEND_PORT}/health`;
  try {
    const res = await fetch(url, { method: 'GET' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    const isReady = !!(data && data.ok);
    if (isReady && !backendReady) {
      backendReady = true;
      if (mainWindow) {
        mainWindow.webContents.send('backend-health', { ready: true, details: data });
      }
      // 준비 완료되면 폴링 중단
      if (healthInterval) { clearInterval(healthInterval); healthInterval = null; }
    }
    return isReady;
  } catch (e) {
    return false;
  }
}

function startHealthPolling() {
  backendReady = false;
  if (healthInterval) { clearInterval(healthInterval); healthInterval = null; }
  // 초기에 한번 시도 후, 1초 간격 폴링
  checkBackendHealthOnce();
  healthInterval = setInterval(checkBackendHealthOnce, 1000);
}

app.on('ready', () => {
  startPythonBackend();
  createWindow();
  startHealthPolling();
  ipcMain.handle('select-directory', async () => {
    const res = await dialog.showOpenDialog(mainWindow ?? undefined, { properties: ['openDirectory'] });
    if (res.canceled || res.filePaths.length === 0) return null;
    return res.filePaths[0];
  });
  ipcMain.handle('get-backend-health', async () => {
    // 최근 상태 반환(간단히 캐시된 값 사용). 세부 데이터는 필요시 확장 가능
    return { ready: backendReady };
  });
  
  ipcMain.handle('open-file-location', async (event, filePath) => {
    try {
      console.log('Received file path:', filePath);
      console.log('File path type:', typeof filePath);
      
      // 파일 존재 여부 확인 (fs는 이미 import됨)
      const fileExists = fs.existsSync(filePath);
      console.log('File exists check:', fileExists);
      
      if (!fileExists) {
        return { success: false, error: `파일이 존재하지 않습니다: ${filePath}` };
      }
      
      // Windows에서 한글 경로 처리를 위해 정규화
      let normalizedPath = filePath;
      if (process.platform === 'win32') {
        // Windows에서 경로 정규화 (path는 이미 import됨)
        normalizedPath = path.normalize(filePath);
        console.log('Normalized path:', normalizedPath);
      }
      
      // Show the file in the file manager
      shell.showItemInFolder(normalizedPath);
      console.log('showItemInFolder called successfully');
      return { success: true };
    } catch (error) {
      console.error('Error opening file location:', error);
      return { success: false, error: error.message };
    }
  });
  
  ipcMain.handle('get-font-path', async () => {
    const isDev = process.env.RENDERER_URL || !app.isPackaged;
    if (isDev) {
      // 개발 모드: Vite의 public 폴더가 루트에 매핑되므로 절대 경로 형태로 반환
      return '/fonts/';
    } else {
      // 배포 모드: 파일 경로를 CSS에서 사용할 수 있도록 file:// URL로 변환
      const fontDir = path.join(process.resourcesPath, 'fonts');
      let url = pathToFileURL(fontDir).toString();
      if (!url.endsWith('/')) url += '/';
      return url;
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('before-quit', () => {
  if (pyProc) {
    try { pyProc.kill(); } catch {}
  }
  if (healthInterval) { try { clearInterval(healthInterval); } catch {} }
});
