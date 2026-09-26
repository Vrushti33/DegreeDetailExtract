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

function SealMark({ className = '' }) {
  return (
    <svg viewBox="0 0 48 48" className={className} fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="24" cy="24" r="21" stroke="currentColor" strokeWidth="1.5" />
      <circle cx="24" cy="24" r="15" stroke="currentColor" strokeWidth="1" />
      <path
        d="M24 12 L26.5 19 H34 L27.7 23.3 L30 30.5 L24 26 L18 30.5 L20.3 23.3 L14 19 H21.5 Z"
        fill="currentColor"
      />
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
      onDragOver={(e) => {
        e.preventDefault()
        if (!disabled) setIsDragActive(true)
      }}
      onDragLeave={() => setIsDragActive(false)}
      onDrop={handleDrop}
      onClick={() => !disabled && inputRef.current?.click()}
      className={`
        group relative flex flex-col items-center justify-center gap-3
        rounded-sm border-2 border-dashed px-8 py-16 text-center transition-colors
        ${disabled ? 'cursor-not-allowed opacity-60' : 'cursor-pointer'}
        ${isDragActive ? 'border-brass-bright bg-brass/5' : 'border-brass/40 hover:border-brass/70'}
      `}
    >
      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0]
          if (file) onFile(file)
          e.target.value = ''
        }}
      />
      <SealMark className="h-10 w-10 text-brass/70" />
      <p className="font-body text-base text-parchment">
        Drop a certificate image here, or click to browse
      </p>
      <p className="font-body text-sm text-parchment/50">JPEG, PNG, or WebP — up to 15MB</p>
    </div>
  )
}

function LedgerRow({ label, value }) {
  const isMissing = !value
  return (
    <div className="flex flex-col gap-1 border-b border-charcoal/15 py-3 last:border-b-0 sm:flex-row sm:items-baseline sm:gap-6">
      <dt className="font-body text-sm text-charcoal/60 sm:w-40 sm:flex-shrink-0">{label}</dt>
      <dd
        className={`font-display text-lg ${
          isMissing ? 'italic text-charcoal/35' : 'text-charcoal'
        }`}
      >
        {isMissing ? 'not detected' : value}
      </dd>
    </div>
  )
}

function ResultLedger({ result, onReset }) {
  return (
    <div className="animate-reveal rounded-sm bg-parchment px-6 py-8 shadow-[0_1px_0_rgba(185,139,42,0.4)] sm:px-10 sm:py-10">
      <div className="mb-6 flex items-center gap-3 text-brass-muted">
        <SealMark className="h-7 w-7" />
        <span className="font-body text-sm tracking-wide text-charcoal/50">
          Extracted details
        </span>
      </div>

      <dl>
        {FIELD_LABELS.map(([key, label]) => (
          <LedgerRow key={key} label={label} value={result.fields[key]} />
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

      <button
        onClick={onReset}
        className="mt-8 font-body text-sm text-brass-muted underline decoration-brass/40 underline-offset-4 hover:text-brass"
      >
        Extract another certificate
      </button>
    </div>
  )
}

export default function App() {
  const [status, setStatus] = useState('idle') // idle | loading | done | error
  const [preview, setPreview] = useState(null)
  const [result, setResult] = useState(null)
  const [errorMessage, setErrorMessage] = useState('')

  const handleFile = useCallback(async (file) => {
    setPreview(URL.createObjectURL(file))
    setStatus('loading')
    setErrorMessage('')

    const formData = new FormData()
    formData.append('file', file)

    try {
      const res = await fetch(`${API_URL}/extract`, {
        method: 'POST',
        body: formData,
      })
      const data = await res.json()

      if (!res.ok) {
        throw new Error(data.detail || 'Something went wrong while reading this certificate.')
      }

      setResult(data)
      setStatus('done')
    } catch (err) {
      setErrorMessage(
        err.message === 'Failed to fetch'
          ? 'Could not reach the extraction service. Check your connection and try again.'
          : err.message,
      )
      setStatus('error')
    }
  }, [])

  const handleReset = useCallback(() => {
    setStatus('idle')
    setResult(null)
    setPreview(null)
    setErrorMessage('')
  }, [])

  return (
    <div className="min-h-screen bg-charcoal">
      <div className="mx-auto flex min-h-screen max-w-5xl flex-col gap-12 px-6 py-16 sm:px-10">
        <header className="flex items-center gap-3 text-brass">
          <SealMark className="h-6 w-6" />
          <span className="font-body text-sm tracking-wide text-parchment/60">
            DegreeDetailExtract
          </span>
        </header>

        <main className="grid flex-1 gap-12 lg:grid-cols-2 lg:items-start">
          <div className="flex flex-col gap-8">
            <div>
              <h1 className="font-display text-4xl font-medium leading-tight text-parchment sm:text-5xl">
                Read any degree certificate.
              </h1>
              <p className="mt-4 max-w-md font-body text-base text-parchment/60">
                Upload a photo or scan of a degree certificate, and get the student, university,
                course, and every other printed detail back as structured data — no manual typing.
              </p>
            </div>

            <Dropzone onFile={handleFile} disabled={status === 'loading'} />

            {preview && (
              <div className="flex items-center gap-4">
                <img
                  src={preview}
                  alt="Uploaded certificate preview"
                  className="h-20 w-20 rounded-sm border border-parchment/15 object-cover"
                />
                <div className="font-body text-sm">
                  {status === 'loading' && (
                    <span className="text-parchment/60">Reading certificate…</span>
                  )}
                  {status === 'error' && <span className="text-maroon">{errorMessage}</span>}
                  {status === 'done' && <span className="text-sage">Done.</span>}
                </div>
              </div>
            )}
          </div>

          <div>
            {status === 'done' && result ? (
              <ResultLedger result={result} onReset={handleReset} />
            ) : (
              <div className="flex h-full min-h-[280px] items-center justify-center rounded-sm border border-parchment/10 px-8 py-16 text-center">
                <p className="font-body text-sm text-parchment/35">
                  Extracted fields will appear here once you upload a certificate.
                </p>
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  )
}
