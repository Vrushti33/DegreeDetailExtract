import { useCallback, useRef, useState } from 'react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const FIELD_LABELS = [
  ['student_name', 'Student'],
  ['university_name', 'University'],
  ['course_name', 'Course'],
  ['specialization', 'Specialization'],
  ['pass_class', 'Class / Division'],
  ['authority_name', 'Signing Authority'],
  ['issue_date', 'Date of Issue'],
]

// Matching colours for field tags (must match backend FIELD_COLORS)
const FIELD_COLORS = {
  student_name:    'rgb(52,152,219)',
  university_name: 'rgb(155,89,182)',
  course_name:     'rgb(46,204,113)',
  specialization:  'rgb(26,188,156)',
  pass_class:      'rgb(241,196,15)',
  authority_name:  'rgb(230,126,34)',
  issue_date:      'rgb(231,76,60)',
}

function SealMark({ className = '' }) {
  return (
    <svg viewBox="0 0 48 48" className={className} fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="24" cy="24" r="21" stroke="currentColor" strokeWidth="1.5" />
      <circle cx="24" cy="24" r="15" stroke="currentColor" strokeWidth="1" />
      <path d="M24 12 L26.5 19 H34 L27.7 23.3 L30 30.5 L24 26 L18 30.5 L20.3 23.3 L14 19 H21.5 Z" fill="currentColor" />
    </svg>
  )
}

function Dropzone({ onFile, disabled }) {
  const [isDragActive, setIsDragActive] = useState(false)
  const inputRef = useRef(null)

  const handleDrop = useCallback(
    (e) => {
      e.preventDefault()
      setIsDragActive(false)
      if (disabled) return
      const file = e.dataTransfer.files?.[0]
      if (file) onFile(file)
    },
    [onFile, disabled],
  )

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); if (!disabled) setIsDragActive(true) }}
      onDragLeave={() => setIsDragActive(false)}
      onDrop={handleDrop}
      onClick={() => !disabled && inputRef.current?.click()}
      className={`group relative flex flex-col items-center justify-center gap-3 rounded-sm border-2 border-dashed px-8 py-16 text-center transition-colors ${disabled ? 'cursor-not-allowed opacity-60' : 'cursor-pointer'} ${isDragActive ? 'border-brass-bright bg-brass/5' : 'border-brass/40 hover:border-brass/70'}`}
    >
      <input ref={inputRef} type="file" accept="image/jpeg,image/png,image/webp" className="hidden"
        onChange={(e) => { const file = e.target.files?.[0]; if (file) onFile(file); e.target.value = '' }} />
      <SealMark className="h-10 w-10 text-brass/70" />
      <p className="font-body text-base text-parchment">Drop a certificate image here, or click to browse</p>
      <p className="font-body text-sm text-parchment/50">JPEG, PNG, or WebP up to 15MB</p>
    </div>
  )
}

function ColorDot({ field }) {
  const color = FIELD_COLORS[field]
  return (
    <span
      className="inline-block h-3 w-3 flex-shrink-0 rounded-full border border-white/20"
      style={{ backgroundColor: color }}
    />
  )
}

function LedgerRow({ label, value, field, hasBbox }) {
  const isMissing = !value
  return (
    <div className="flex flex-col gap-1 border-b border-charcoal/15 py-3 last:border-b-0 sm:flex-row sm:items-baseline sm:gap-4">
      <div className="flex items-center gap-2 sm:w-44 sm:flex-shrink-0">
        {hasBbox && <ColorDot field={field} />}
        <dt className="font-body text-sm text-charcoal/60">{label}</dt>
      </div>
      <dd className={`font-display text-lg ${isMissing ? 'italic text-charcoal/35' : 'text-charcoal'}`}>
        {isMissing ? 'not detected' : value}
      </dd>
    </div>
  )
}

function ResultLedger({ result, onReset }) {
  const hasBbox = result.tesseract_available && result.field_boxes
  return (
    <div className="animate-reveal rounded-sm bg-parchment px-6 py-8 shadow-[0_1px_0_rgba(185,139,42,0.4)] sm:px-10 sm:py-10">
      <div className="mb-6 flex items-center gap-3 text-brass-muted">
        <SealMark className="h-7 w-7" />
        <span className="font-body text-sm tracking-wide text-charcoal/50">Extracted details</span>
      </div>

      {hasBbox && (
        <p className="mb-4 rounded-sm bg-charcoal/5 px-3 py-2 font-body text-xs text-charcoal/50">
          🔍 Coloured dots indicate fields highlighted on the certificate image.
        </p>
      )}

      <dl>
        {FIELD_LABELS.map(([key, label]) => (
          <LedgerRow
            key={key}
            field={key}
            label={label}
            value={result.fields[key]}
            hasBbox={hasBbox && result.field_boxes?.[key] !== null}
          />
        ))}
      </dl>

      {result.missing_fields.length > 0 && (
        <p className="mt-6 font-body text-sm text-charcoal/50">
          {result.missing_fields.length === 1
            ? 'One field could not be read from this image.'
            : `${result.missing_fields.length} fields could not be read from this image.`}{' '}
          A clearer or higher-resolution photo often helps.
        </p>
      )}

      {!result.tesseract_available && (
        <p className="mt-4 rounded-sm border border-yellow-800/30 bg-yellow-900/10 px-3 py-2 font-body text-xs text-yellow-600">
          ⚠ Tesseract not installed on server — bounding box highlighting unavailable.
        </p>
      )}

      <button onClick={onReset} className="mt-8 font-body text-sm text-brass-muted underline decoration-brass/40 underline-offset-4 hover:text-brass">
        Extract another certificate
      </button>
    </div>
  )
}

export default function App() {
  const [status, setStatus] = useState('idle')
  const [preview, setPreview] = useState(null)          // original image blob URL
  const [annotated, setAnnotated] = useState(null)      // base64 annotated image
  const [showAnnotated, setShowAnnotated] = useState(true)
  const [result, setResult] = useState(null)
  const [errorMessage, setErrorMessage] = useState('')

  const handleFile = useCallback(async (file) => {
    const url = URL.createObjectURL(file)
    setPreview(url)
    setAnnotated(null)
    setShowAnnotated(true)
    setStatus('loading')
    setErrorMessage('')
    const formData = new FormData()
    formData.append('file', file)
    try {
      const res = await fetch(`${API_URL}/extract`, { method: 'POST', body: formData })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Something went wrong while reading this certificate.')
      setResult(data)
      if (data.annotated_image) {
        setAnnotated(`data:image/png;base64,${data.annotated_image}`)
        setShowAnnotated(true)
      }
      setStatus('done')
    } catch (err) {
      setErrorMessage(err.message === 'Failed to fetch'
        ? 'Could not reach the extraction service. Check your connection and try again.'
        : err.message)
      setStatus('error')
    }
  }, [])

  const handleReset = useCallback(() => {
    setStatus('idle')
    setResult(null)
    setPreview(null)
    setAnnotated(null)
    setShowAnnotated(true)
    setErrorMessage('')
  }, [])

  if (status === 'idle') {
    return (
      <div className="min-h-screen bg-charcoal">
        <div className="mx-auto flex min-h-screen max-w-5xl flex-col gap-12 px-6 py-16 sm:px-10">
          <header className="flex items-center gap-3 text-brass">
            <SealMark className="h-6 w-6" />
            <span className="font-body text-sm tracking-wide text-parchment/60">DegreeDetailExtract</span>
          </header>
          <main className="grid flex-1 gap-12 lg:grid-cols-2 lg:items-start">
            <div className="flex flex-col gap-8">
              <div>
                <h1 className="font-display text-4xl font-medium leading-tight text-parchment sm:text-5xl">Read any degree certificate.</h1>
                <p className="mt-4 max-w-md font-body text-base text-parchment/60">
                  Upload a photo or scan. Fields are extracted automatically, and highlighted on the certificate so you can verify each one.
                </p>
              </div>
              <Dropzone onFile={handleFile} disabled={false} />
            </div>
            <div>
              <div className="flex h-full min-h-[280px] items-center justify-center rounded-sm border border-parchment/10 px-8 py-16 text-center">
                <p className="font-body text-sm text-parchment/35">Extracted fields will appear here once you upload a certificate.</p>
              </div>
            </div>
          </main>
        </div>
      </div>
    )
  }

  // Determine which image to show
  const displayImage = showAnnotated && annotated ? annotated : preview

  return (
    <div className="min-h-screen bg-charcoal">
      <div className="mx-auto flex min-h-screen max-w-7xl flex-col gap-8 px-6 py-12 sm:px-10">
        <header className="flex items-center gap-3 text-brass">
          <SealMark className="h-6 w-6" />
          <span className="font-body text-sm tracking-wide text-parchment/60">DegreeDetailExtract</span>
        </header>

        <main className="grid flex-1 gap-8 lg:grid-cols-2 lg:items-start">

          {/* Left: Certificate Image */}
          <div className="flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <p className="font-body text-xs uppercase tracking-widest text-parchment/40">Uploaded Certificate</p>

              {/* Toggle between annotated and original */}
              {annotated && status === 'done' && (
                <div className="flex items-center gap-1 rounded-full border border-parchment/15 p-0.5">
                  <button
                    onClick={() => setShowAnnotated(true)}
                    className={`rounded-full px-3 py-1 font-body text-xs transition-colors ${showAnnotated ? 'bg-brass text-charcoal' : 'text-parchment/50 hover:text-parchment'}`}
                  >
                    Highlighted
                  </button>
                  <button
                    onClick={() => setShowAnnotated(false)}
                    className={`rounded-full px-3 py-1 font-body text-xs transition-colors ${!showAnnotated ? 'bg-brass text-charcoal' : 'text-parchment/50 hover:text-parchment'}`}
                  >
                    Original
                  </button>
                </div>
              )}
            </div>

            <div className="relative overflow-hidden rounded-sm border border-parchment/15 bg-charcoal/60">
              {displayImage && (
                <img
                  src={displayImage}
                  alt={showAnnotated && annotated ? 'Certificate with highlighted fields' : 'Uploaded certificate'}
                  className="w-full object-contain"
                  style={{ maxHeight: '80vh' }}
                />
              )}

              {/* Loading spinner overlay */}
              {status === 'loading' && (
                <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-charcoal/70 backdrop-blur-sm">
                  <svg className="h-10 w-10 animate-spin text-brass/70" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <circle cx="24" cy="24" r="20" stroke="currentColor" strokeWidth="3" strokeDasharray="90 30" />
                  </svg>
                  <p className="font-body text-sm text-parchment/70">Reading certificate...</p>
                </div>
              )}
            </div>

            {/* Error message */}
            {status === 'error' && (
              <p className="rounded-sm border border-red-900/40 bg-red-900/10 px-4 py-3 font-body text-sm text-red-400">{errorMessage}</p>
            )}

            {/* Upload another / reset */}
            {(status === 'done' || status === 'error') && (
              <button onClick={handleReset} className="self-start font-body text-sm text-brass-muted underline decoration-brass/40 underline-offset-4 hover:text-brass">
                Upload a different certificate
              </button>
            )}
          </div>

          {/* Right: Results ledger */}
          <div className="sticky top-8">
            {status === 'loading' && (
              <div className="flex min-h-[280px] items-center justify-center rounded-sm border border-parchment/10 px-8 py-16 text-center">
                <p className="font-body text-sm text-parchment/35">Extracting fields...</p>
              </div>
            )}
            {status === 'done' && result && <ResultLedger result={result} onReset={handleReset} />}
            {status === 'error' && (
              <div className="flex min-h-[280px] items-center justify-center rounded-sm border border-parchment/10 px-8 py-16 text-center">
                <p className="font-body text-sm text-parchment/35">Could not extract fields. Try again with a clearer image.</p>
              </div>
            )}
          </div>

        </main>
      </div>
    </div>
  )
}
