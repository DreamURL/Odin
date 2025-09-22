import React, { useEffect, useMemo, useState } from 'react'
import Toast, { useToasts } from './Toast'

export default function OptionsPage({ api, indexInfo, setIndexInfo, setAllowedByPreset }) {
  const { basePath, allExts, aiExts, allowedExts, indexCsvPath } = indexInfo
  const [modelMsg, setModelMsg] = useState('')
  const [loading, setLoading] = useState(false)
  const [loadingText, setLoadingText] = useState('로딩 중...')
  const { ToastWrap, pushToast } = useToasts()
  const [backendReady, setBackendReady] = useState(false)

  const onBrowse = async () => {
    try {
      if (!window.odin || typeof window.odin.selectDirectory !== 'function') {
        pushToast('경로 선택 기능을 사용할 수 없습니다. 최신 앱으로 실행해주세요.', 'error');
        return;
      }
      const p = await window.odin.selectDirectory();
      if (p) {
        setIndexInfo(prev => ({ ...prev, basePath: p }))
        pushToast('경로가 설정되었습니다.', 'info')
      }
    } catch (e) { pushToast('경로 선택 실패', 'error') }
  }

  const onIndex = async () => {
    if (!basePath) { pushToast('경로를 입력하세요', 'error'); return }
  setLoadingText('파일 변경사항 확인 중…')
  setLoading(true)
    try {
      const url = api('/index')
      const payload = { base_path: basePath }
      const res = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
      const data = await res.json()
      const aiReadable = Array.isArray(data.ai_readable_exts) ? data.ai_readable_exts : []
      const allowedByDefault = aiReadable.filter(ext => ext !== '.hwp')
      setIndexInfo(prev => ({
        ...prev,
        allExts: data.extensions || [],
        aiExts: aiReadable,
        allowedExts: allowedByDefault,
        indexCsvPath: data.csv_path || ''
      }))
      pushToast(`인덱싱 완료: ${data.count} 항목 (변동사항 업데이트 완료)`, 'success')
    } catch (e) { 
      pushToast('인덱싱 실패: 백엔드가 실행 중인지 확인하세요', 'error') 
    }
    finally { setLoading(false) }
  }

  const toggleExt = (ext) => {
    setIndexInfo(prev => {
      const on = prev.allowedExts.includes(ext)
      const next = on ? prev.allowedExts.filter(x => x !== ext) : [...prev.allowedExts, ext]
      return { ...prev, allowedExts: next }
    })
  }

  async function refreshModels() {
    setModelMsg('')
    try {
      const controller = new AbortController()
      const id = setTimeout(() => controller.abort(), 8000)
      const res = await fetch(api('/ollama/models'), { signal: controller.signal })
      clearTimeout(id)
      const data = await res.json()
      setModels(data.models || [])
      if ((data.models || []).length === 0) setModelMsg(data.error || '설치된 Ollama 모델이 없습니다. ollama 설치/모델 pull 필요합니다.')
    } catch (e) { setModelMsg('모델 목록 불러오기 실패') }
  }

  const [models, setModels] = useState([])
  useEffect(() => { refreshModels() }, [])

  // 백엔드 헬스 상태 구독: 준비되면 UI 배지 업데이트
  useEffect(() => {
    if (window.odin && typeof window.odin.onBackendHealth === 'function') {
      const handler = (msg) => {
        if (msg && msg.ready) setBackendReady(true)
      }
      window.odin.onBackendHealth(handler)
    }
  }, [])

  // 초기 상태 1회 조회(이벤트 미수신 보완)
  useEffect(() => {
    (async () => {
      try {
        if (window.odin && typeof window.odin.getBackendHealth === 'function') {
          const s = await window.odin.getBackendHealth();
          if (s && s.ready) setBackendReady(true)
        }
      } catch {}
    })()
  }, [])

  const [selModel, setSelModel] = useState('')
  useEffect(() => { if (models.length && !selModel) setSelModel(models[0]) }, [models])

  const onSelectModel = async () => {
    if (!basePath) { pushToast('경로를 먼저 설정하세요', 'error'); return }
    if (!indexCsvPath) { pushToast('인덱싱을 먼저 완료하세요', 'error'); return }
    if (!selModel) { pushToast('모델을 선택하세요', 'error'); return }
  setLoadingText('모델 적용 중…')
  setLoading(true)
    const res = await fetch(api('/ollama/select'), { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ base_path: basePath, model: selModel }) })
    const data = await res.json(); setLoading(false)
    if (data.ok) setModelMsg(`모델 사용: ${selModel}`)
    else { setModelMsg(data.error || '실패'); pushToast('모델 선택 실패', 'error') }
  }

  const aiPresetOn = allowedExts.length === aiExts.length && aiExts.every(x => allowedExts.includes(x))

  return (
    <div className="options-container">
      <section>
        <h3>Ollama 모델 {" "}
          <span style={{
            marginLeft: 8,
            padding: '2px 8px',
            borderRadius: 999,
            fontSize: 12,
            background: backendReady ? '#e6ffed' : '#fff7e6',
            color: backendReady ? '#067d3c' : '#a15c00',
            border: `1px solid ${backendReady ? '#b7eb8f' : '#ffd591'}`
          }}>
            {backendReady ? '모델 사용 가능' : '모델 준비중'}
          </span>
        </h3>
        <div className="row">
          <select value={selModel} onChange={e => setSelModel(e.target.value)} style={{ minWidth: 260 }}>
            {models.map(m => <option key={m} value={m}>{m}</option>)}
          </select>
          <button onClick={onSelectModel}>이 모델 사용</button>
        </div>
        <div style={{ marginTop: 8, color: '#64748b' }}>{modelMsg}</div>
      </section>

      <section>
        <h3>경로 & 인덱싱</h3>
        <label>검색 경로</label>
        <div className="row">
          <input value={basePath} onChange={e => setIndexInfo(prev => ({ ...prev, basePath: e.target.value }))} placeholder="예) C:\\data" />
          <button onClick={onBrowse} title="폴더 선택">찾아보기</button>
          <button onClick={onIndex}>인덱싱</button>
        </div>
        {indexCsvPath && (
          <div style={{ marginTop: 8, fontSize: 13, color: '#64748b', display: 'flex', alignItems: 'center', gap: 8 }}>
            <span>인덱스 파일 위치:</span>
            <code style={{ userSelect: 'text' }}>{indexCsvPath}</code>
            <button className="small" title="인덱스 파일 위치 열기" onClick={async () => {
              try {
                const res = await window.electronAPI.openFileLocation(indexCsvPath)
                if (res && !res.success) {
                  pushToast(`파일 위치를 열 수 없습니다: ${res.error}`, 'error')
                }
              } catch (e) {
                pushToast('파일 위치를 열 수 없습니다', 'error')
              }
            }}>폴더 열기</button>
          </div>
        )}
        <div className="chips" style={{ marginTop: 8 }}>
          {(allExts || []).map(e => <span key={e} className="pill">{e}</span>)}
        </div>
      </section>

      <section>
        <h3>확장자 On/Off</h3>
        <div className="row" style={{ alignItems: 'center', gap: 12 }}>
          <label className="row" style={{ gap: 6 }}>
            <input type="checkbox" checked={aiPresetOn} onChange={e => setAllowedByPreset(e.target.checked)} /> AI가 읽을 수 있는 확장자 On 기본
          </label>
        </div>
        <div className="chips">
          {(allExts || []).map(e => (
            <label key={e} className="pill" style={{ userSelect: 'none' }}>
              <input type="checkbox" checked={allowedExts.includes(e)} onChange={() => toggleExt(e)} /> {e}
            </label>
          ))}
        </div>
      </section>

      {loading && (
        <div className="overlay">
          <div className="spinner" />
          <div>{loadingText}</div>
        </div>
      )}
      <ToastWrap />
    </div>
  )
}
