import { execSync } from 'child_process';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

console.log('Building Python distribution...');

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, '..', '..');
const electronDir = path.resolve(__dirname, '..');
const pythonDistDir = path.join(electronDir, 'python-dist');

// 가상환경 경로 설정
const venvPath = path.join(projectRoot, '.venv_odin');
const isWindows = process.platform === 'win32';
const pythonExe = isWindows 
  ? path.join(venvPath, 'Scripts', 'python.exe')
  : path.join(venvPath, 'bin', 'python');
const pipExe = isWindows 
  ? path.join(venvPath, 'Scripts', 'pip.exe')
  : path.join(venvPath, 'bin', 'pip');

try {
  // 가상환경 존재 확인
  if (!fs.existsSync(pythonExe)) {
    console.error('가상환경을 찾을 수 없습니다:', venvPath);
    console.log('다음 명령으로 가상환경을 생성하세요:');
    console.log('python -m venv .venv_odin');
    console.log('.venv_odin\\Scripts\\activate');
    console.log('pip install -r backend/requirements.txt');
    process.exit(1);
  }

  // Python 분배 디렉토리 생성
  if (fs.existsSync(pythonDistDir)) {
    fs.rmSync(pythonDistDir, { recursive: true, force: true });
  }
  fs.mkdirSync(pythonDistDir, { recursive: true });

  console.log('Copying Python source files...');
  
  // Python 소스 파일들 복사
  const copyDirs = ['backend', 'Langchain', 'parsers'];
  
  copyDirs.forEach(dir => {
    const srcDir = path.join(projectRoot, dir);
    const destDir = path.join(pythonDistDir, dir);
    
    if (fs.existsSync(srcDir)) {
      console.log(`Copying ${dir}...`);
      fs.cpSync(srcDir, destDir, { recursive: true });
    }
  });

  // requirements.txt 복사
  const reqSrc = path.join(projectRoot, 'backend', 'requirements.txt');
  const reqDest = path.join(pythonDistDir, 'requirements.txt');
  if (fs.existsSync(reqSrc)) {
    fs.copyFileSync(reqSrc, reqDest);
  }

  console.log('Installing PyInstaller...');
  try {
    execSync(`"${pipExe}" install pyinstaller`, { 
      stdio: 'inherit',
      cwd: projectRoot 
    });
  } catch (error) {
    console.log('PyInstaller 설치 실패, 이미 설치되어 있을 수 있습니다.');
  }

  console.log('Building standalone executable with PyInstaller...');
  
  // PyInstaller로 실행 파일 생성
  const pyinstallerArgs = [
    '--onefile',                    // 단일 실행 파일
    '--noconsole',                  // 콘솔 창 숨기기
    '--name=odin-backend',          // 실행 파일 이름
    '--distpath=' + pythonDistDir,  // 출력 디렉토리
    '--workpath=' + path.join(pythonDistDir, 'build'), // 임시 파일 디렉토리
    '--specpath=' + pythonDistDir,  // spec 파일 위치
    '--add-data=' + path.join(projectRoot, 'Langchain') + (isWindows ? ';' : ':') + 'Langchain',
    '--add-data=' + path.join(projectRoot, 'parsers') + (isWindows ? ';' : ':') + 'parsers',
    '--hidden-import=langchain',
    '--hidden-import=langchain_community',
    '--hidden-import=fastapi',
    '--hidden-import=uvicorn',
    '--hidden-import=pydantic',
    path.join(projectRoot, 'backend', 'server.py')
  ];

  const pyinstallerCmd = `"${pythonExe}" -m PyInstaller ${pyinstallerArgs.join(' ')}`;
  console.log('Running:', pyinstallerCmd);
  
  execSync(pyinstallerCmd, { 
    stdio: 'inherit',
    cwd: projectRoot 
  });

  // 빌드 임시 파일 정리
  const buildDir = path.join(pythonDistDir, 'build');
  if (fs.existsSync(buildDir)) {
    fs.rmSync(buildDir, { recursive: true, force: true });
  }

  // spec 파일 정리
  const specFile = path.join(pythonDistDir, 'odin-backend.spec');
  if (fs.existsSync(specFile)) {
    fs.unlinkSync(specFile);
  }

  console.log('Python distribution built successfully!');
  console.log(`Distribution location: ${pythonDistDir}`);
  console.log(`Executable: ${path.join(pythonDistDir, 'odin-backend.exe')}`);

} catch (error) {
  console.error('Error building Python distribution:', error);
  process.exit(1);
}