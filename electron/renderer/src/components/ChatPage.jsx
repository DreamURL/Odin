import React, { useEffect, useRef, useState } from 'react'
import Toast, { useToasts } from './Toast'

export default function ChatPage({ api, indexInfo }) {
  const { basePath, allowedExts } = indexInfo
  const [messages, setMessages] = useState([{ type: 'text', who: 'assistant', text: '키워드 기반 검색 요청을 해주세요' }])
  const [input, setInput] = useState('')
  const [items, setItems] = useState([])
  const [selectedPaths, setSelectedPaths] = useState([])
  const [qaFiles, setQaFiles] = useState([])
  const [waitingForRefine, setWaitingForRefine] = useState(false)
  const [loading, setLoading] = useState(false)
  const [loadingText, setLoadingText] = useState('로딩 중...')
  const [leftPaneWidth, setLeftPaneWidth] = useState(50) // 50% initial width
  const [isResizing, setIsResizing] = useState(false)
  const listRef = useRef(null)
  const assistantIndexRef = useRef(-1)
  const { ToastWrap, pushToast } = useToasts()

  // 파일 위치 열기 함수
  const openFileLocation = async (filePath) => {
    try {
      const result = await window.electronAPI.openFileLocation(filePath)
      if (result && !result.success) {
        pushToast(`파일 위치를 열 수 없습니다: ${result.error}`, 'error')
      }
    } catch (error) {
      pushToast('파일 위치를 열 수 없습니다', 'error')
    }
  }

  // 리사이저 핸들러
  const handleMouseDown = (e) => {
    setIsResizing(true)
    e.preventDefault()
  }

  const handleMouseMove = (e) => {
    if (!isResizing) return
    
    const container = e.currentTarget.closest('.chat-layout')
    if (!container) return
    
    const rect = container.getBoundingClientRect()
    const newWidth = ((e.clientX - rect.left) / rect.width) * 100
    
    // 최소/최대 너비 제한 (20% ~ 80%)
    if (newWidth >= 20 && newWidth <= 80) {
      setLeftPaneWidth(newWidth)
    }
  }

  const handleMouseUp = () => {
    setIsResizing(false)
  }

  // 마우스 이벤트 리스너 등록/해제
  React.useEffect(() => {
    if (isResizing) {
      document.addEventListener('mousemove', handleMouseMove)
      document.addEventListener('mouseup', handleMouseUp)
      document.body.style.userSelect = 'none'
      document.body.style.cursor = 'col-resize'
    } else {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
      document.body.style.userSelect = ''
      document.body.style.cursor = ''
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
      document.body.style.userSelect = ''
      document.body.style.cursor = ''
    }
  }, [isResizing])

  const scrollBottom = () => {
    const el = listRef.current
    if (el) {
      // Use requestAnimationFrame to ensure DOM updates are complete
      requestAnimationFrame(() => {
        el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
      })
    }
  }

  const appendMsg = (text, who) => setMessages(prev => [...prev, { type: 'text', who, text }])

  async function onReadFiles() {
    if (!basePath) { pushToast('옵션 탭에서 경로를 설정하세요', 'error'); return }
    if (selectedPaths.length === 0) { pushToast('오른쪽 목록에서 파일을 선택하세요', 'error'); return }
  setLoadingText('파일 읽는 중…')
  setLoading(true)
    try {
      const res = await fetch(api('/proceed'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ base_path: basePath, paths: selectedPaths }) })
      const data = await res.json()
      const loaded = Array.isArray(data.loaded) ? data.loaded : []
      const failures = selectedPaths.filter(p => !loaded.includes(p))

      if (loaded.length > 0) {
        // 현재 선택된 파일들로 교체 (누적하지 않음)
        setQaFiles(loaded)
        const loadedNames = loaded.map(fp => (fp.split(/[\\/]/).pop() || fp))
        const maxShow = 10
        const shown = loadedNames.slice(0, maxShow).map(n => `("${n}")`)
        let msg = `다음 파일을 읽었습니다: ${shown.join(', ')}`
        if (loadedNames.length > maxShow) {
          msg += ` 외 ${loadedNames.length - maxShow}개`
        }
        msg += '. 이제 파일 기반 Q&A가 가능합니다.'
        appendMsg(msg, 'assistant')
      }

      if (failures.length > 0) {
        // 읽을 수 없는(파싱 실패/내용 없음/미지원) 파일별 안내 메시지 추가
        failures.forEach(fp => {
          const name = fp.split(/[\\/]/).pop() || fp
          appendMsg(`"${name}"은 텍스트를 읽을 수 없습니다.`, 'assistant')
        })
      }
    } catch (e) {
      pushToast('파일 읽기 실패', 'error')
    } finally { setLoading(false) }
  }

  async function onSend() {
    if (!basePath) { pushToast('옵션 탭에서 경로를 설정하세요', 'error'); return }
    const q = input.trim(); if (!q) return
    setInput('')
    
    const hasQA = qaFiles.length > 0
    
    if (hasQA) {
      // First add user message
      appendMsg(q, 'user')
      
      // Then add assistant thinking message and remember its position
      setMessages(prev => {
        const assistantIndex = prev.length
        assistantIndexRef.current = assistantIndex
        return [...prev, { type: 'text', who: 'assistant', text: '생각 중…' }]
      })
      
      setLoadingText('생각 중…')
      setLoading(true)
      
      // Try SSE then fallback
      try {
        const resp = await fetch(api(`/qa/stream?base_path=${encodeURIComponent(basePath)}&q=${encodeURIComponent(q)}`))
        if (resp.ok && (resp.headers.get('content-type') || '').includes('text/event-stream')) {
          setLoading(false)
          const reader = resp.body.getReader()
          const decoder = new TextDecoder()
          let acc = ''
          let gotAny = false
          let done = false
          const watchdog = setTimeout(() => { try { reader.cancel() } catch {} }, 15000)
          while (true) {
            const { done: d, value } = await reader.read(); if (d) break
            const chunk = decoder.decode(value, { stream: true }); acc += chunk
            const parts = acc.split('\n\n'); acc = parts.pop() || ''
            for (const ev of parts) {
              const lines = ev.split('\n').filter(Boolean)
              if (lines.some(l => l.startsWith('event: done'))) done = true
              const dataLines = lines.filter(l => l.startsWith('data: ')).map(l => l.slice(6))
              const text = dataLines.join('\n')
              if (text) {
                gotAny = true
                const targetIndex = assistantIndexRef.current
                setMessages(prev => {
                  return prev.map((m, i) => {
                    if (i !== targetIndex) return m
                    const base = (m.text || '')
                    const nextText = base === '생각 중…' ? text : base + text
                    return { ...m, text: nextText }
                  })
                })
              }
            }
          }
          clearTimeout(watchdog)
          if (!gotAny && !done) {
            const res2 = await fetch(api('/qa'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ base_path: basePath, question: q }) })
            const data2 = await res2.json()
            const targetIndex = assistantIndexRef.current
            setMessages(prev => prev.map((m, i) => i === targetIndex ? { ...m, text: data2.answer || '(응답 없음)' } : m))
          }
          
          // QA 답변 완료 후 액션 버튼 추가
          setMessages(prev => [...prev, {
            type: 'actions',
            total: qaFiles.length,
            qaMode: true
          }])
        } else {
          // Non-SSE: QA API call
          const res = await fetch(api('/qa'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ base_path: basePath, question: q }) })
          const data = await res.json(); setLoading(false)
          const targetIndex = assistantIndexRef.current
          setMessages(prev => prev.map((m, i) => i === targetIndex ? { ...m, text: (data.answer || '(응답 없음)') } : m))
          
          // QA 답변 완료 후 액션 버튼 추가
          setMessages(prev => [...prev, {
            type: 'actions',
            total: qaFiles.length,
            qaMode: true
          }])
        }
      } catch (e) {
        setLoading(false)
        pushToast('네트워크 오류: QA 실패', 'error')
      }
    } else if (waitingForRefine) {
      // Add user message normally for search flows
      appendMsg(q, 'user')
      
      // Add "찾는 중..." message before search
      setMessages(prev => {
        const assistantIndex = prev.length
        assistantIndexRef.current = assistantIndex
        return [...prev, { type: 'text', who: 'assistant', text: '찾는 중…' }]
      })
      
      try {
        const sres = await fetch(api('/search'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ base_path: basePath, query: q, allowed_exts: allowedExts }) })
        const sk = await sres.json()
        const rres = await fetch(api('/refine'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ base_path: basePath, keywords: sk.keywords || [], current_items: items.map(i => i.path) }) })
        const data = await rres.json()
        setItems(data.items || [])
        setWaitingForRefine(false)

        // Replace "찾는 중..." message with expanded keywords info first, then actions
        const targetIndex = assistantIndexRef.current
        const expandedKeywords = sk.expanded_keywords || []

        if (expandedKeywords.length > 0) {
          const keywordsStr = expandedKeywords.join(', ')
          setMessages(prev => prev.map((m, i) => i === targetIndex ? { ...m, text: `(${keywordsStr}) 으로 상세 탐색 완료` } : m))

          // Add actions after the search completion message
          setTimeout(() => {
            setMessages(prev => [...prev, { type: 'actions', total: (data.items || []).length }])
          }, 100)
        } else {
          // No expanded keywords, use original behavior
          setMessages(prev => prev.map((m, i) => i === targetIndex ? { type: 'actions', total: (data.items || []).length } : m))
        }
      } catch (e) {
        setWaitingForRefine(false);
        pushToast('상세 검색 실패', 'error')

        // Replace "찾는 중..." message with error
        const targetIndex = assistantIndexRef.current
        setMessages(prev => prev.map((m, i) => i === targetIndex ? { ...m, text: '검색에 실패했습니다.' } : m))
      }
    } else {
      // Add user message normally for initial search
      appendMsg(q, 'user')
      
      // Add "찾는 중..." message before search
      setMessages(prev => {
        const assistantIndex = prev.length
        assistantIndexRef.current = assistantIndex
        return [...prev, { type: 'text', who: 'assistant', text: '찾는 중…' }]
      })
      
      try {
        const res = await fetch(api('/search'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ base_path: basePath, query: q, allowed_exts: allowedExts }) })
        const data = await res.json()
        setItems(data.items || [])

        // Replace "찾는 중..." message with expanded keywords info first, then actions
        const targetIndex = assistantIndexRef.current
        const expandedKeywords = data.expanded_keywords || []

        if (expandedKeywords.length > 0) {
          const keywordsStr = expandedKeywords.join(', ')
          setMessages(prev => prev.map((m, i) => i === targetIndex ? { ...m, text: `(${keywordsStr}) 으로 탐색 완료` } : m))

          // Add actions after the search completion message
          setTimeout(() => {
            setMessages(prev => [...prev, { type: 'actions', total: (data.items || []).length }])
          }, 100)
        } else {
          // No expanded keywords, use original behavior
          setMessages(prev => prev.map((m, i) => i === targetIndex ? { type: 'actions', total: (data.items || []).length } : m))
        }
      } catch (e) {
        pushToast('네트워크 오류: 검색 실패', 'error')

        // Replace "찾는 중..." message with error
        const targetIndex = assistantIndexRef.current
        setMessages(prev => prev.map((m, i) => i === targetIndex ? { ...m, text: '검색에 실패했습니다.' } : m))
      }
    }
  }

  useEffect(() => { scrollBottom() }, [messages])

  return (
    <div>
      <section className="chat-layout" onMouseMove={handleMouseMove}>
        <div className="chat-pane" style={{ width: `${leftPaneWidth}%` }}>
          <div ref={listRef} className="chat-messages">
            {messages.map((m, i) => {
              if (m.type === 'actions') {
                return (
                  <div key={i} className="msg assistant">
                    <div>{m.qaMode ? 
                      `파일 ${m.total}개에 대한 Q&A가 가능합니다.` : 
                      `총 ${m.total}개의 데이터가 확인되었습니다. 오른쪽의 파일을 선택 후 "파일 읽기"를 눌러주세요. 세부 검색이 필요하면 "상세 검색" 버튼을 눌러주세요.`
                    }</div>
                    <div className="action-buttons">
                      {!m.qaMode && (
                        <button className="small" onClick={() => { setWaitingForRefine(true); appendMsg('상세 검색 키워드를 입력해주세요.', 'assistant') }}>상세 검색</button>
                      )}
                      <button className="small" onClick={onReadFiles}>파일 읽기</button>
                      <button className="small" onClick={() => { setMessages([{ type: 'text', who: 'assistant', text: '키워드 기반 검색 요청을 해주세요' }]); setItems([]); setSelectedPaths([]); setQaFiles([]); setWaitingForRefine(false); }}>새로운 대화</button>
                    </div>
                  </div>
                )
              }
              // default text message
              return <div key={i} className={`msg ${m.who}`}>{m.text}</div>
            })}
          </div>
          <div className="chat-input">
            <textarea 
              value={input} 
              onChange={e => setInput(e.target.value)} 
              placeholder="메시지를 입력하세요..." 
              onKeyPress={e => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), onSend())}
              rows="3"
            />
            <button className="primary" onClick={onSend}>전송</button>
          </div>
        </div>
        
        <div className="resizer" onMouseDown={handleMouseDown}></div>
        
        <div className="side-pane" style={{ width: `${100 - leftPaneWidth}%` }}>
          <h4>선택된 파일</h4>
          <div className="chips">
            {selectedPaths.map((p, i) => <span key={i} className="pill">{p.split(/[\\/]/).pop()}</span>)}
          </div>
          <h4>검색 결과</h4>
          <div className="table-container">
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>폴더</th>
                    <th>파일명</th>
                    <th>확장자</th>
                    <th>크기</th>
                    <th>위치 열기</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((it, i) => {
                    const parts = it.path.split(/[/\\]/)
                    const folder = parts.slice(-2, -1)[0] || ''
                    const selected = selectedPaths.includes(it.path)
                    return (
                      <tr key={i} className={selected ? 'selected' : ''}>
                        <td onClick={() => setSelectedPaths(prev => prev.includes(it.path) ? prev.filter(x => x !== it.path) : [...prev, it.path])}>{folder}</td>
                        <td onClick={() => setSelectedPaths(prev => prev.includes(it.path) ? prev.filter(x => x !== it.path) : [...prev, it.path])}>{it.name}</td>
                        <td onClick={() => setSelectedPaths(prev => prev.includes(it.path) ? prev.filter(x => x !== it.path) : [...prev, it.path])}>{it.extension || ''}</td>
                        <td onClick={() => setSelectedPaths(prev => prev.includes(it.path) ? prev.filter(x => x !== it.path) : [...prev, it.path])}>{it.size_bytes || 0}</td>
                        <td>
                          <button 
                            className="open-location-btn" 
                            onClick={(e) => {
                              e.stopPropagation()
                              openFileLocation(it.path)
                            }}
                            title="파일 위치 열기"
                          >
                            📁
                          </button>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
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
