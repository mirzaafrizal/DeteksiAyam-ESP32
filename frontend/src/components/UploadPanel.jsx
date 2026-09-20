import { useRef, useState } from 'react'
import { uploadImage } from '../services/api'

/**
 * UploadPanel — area drag-and-drop + tombol upload gambar.
 * Memanggil onResult(result) setelah upload berhasil.
 * Memanggil onUploadDone() agar parent bisa refresh tabel log.
 */
export default function UploadPanel({ onResult, onUploadDone }) {
  const [preview, setPreview] = useState(null)
  const [file, setFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const inputRef = useRef(null)

  function handleFileChange(e) {
    const selected = e.target.files[0]
    if (!selected) return
    setFile(selected)
    setPreview(URL.createObjectURL(selected))
    setError(null)
  }

  function handleDrop(e) {
    e.preventDefault()
    const dropped = e.dataTransfer.files[0]
    if (!dropped) return
    setFile(dropped)
    setPreview(URL.createObjectURL(dropped))
    setError(null)
  }

  async function handleUpload() {
    if (!file) return
    setLoading(true)
    setError(null)
    try {
      const result = await uploadImage(file)
      onResult(result)
      onUploadDone()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  function handleReset() {
    setFile(null)
    setPreview(null)
    setError(null)
    if (inputRef.current) inputRef.current.value = ''
  }

  return (
    <div className="bg-white rounded-2xl shadow p-6">
      <h2 className="text-lg font-semibold text-gray-700 mb-4">Upload Gambar Ayam</h2>

      {/* Drop zone */}
      <div
        onDrop={handleDrop}
        onDragOver={(e) => e.preventDefault()}
        onClick={() => !preview && inputRef.current?.click()}
        className={`border-2 border-dashed rounded-xl flex flex-col items-center justify-center min-h-48 transition-colors cursor-pointer
          ${preview ? 'border-gray-200 cursor-default' : 'border-blue-300 hover:border-blue-400 hover:bg-blue-50'}`}
      >
        {preview ? (
          <img
            src={preview}
            alt="preview"
            className="max-h-64 rounded-lg object-contain"
          />
        ) : (
          <div className="text-center text-gray-400 px-4">
            <svg className="mx-auto mb-2 w-10 h-10" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M3 16.5V18a2.25 2.25 0 002.25 2.25h13.5A2.25 2.25 0 0021 18v-1.5M16.5 12L12 7.5m0 0L7.5 12M12 7.5V18" />
            </svg>
            <p className="text-sm">Drag & drop gambar di sini</p>
            <p className="text-xs mt-1">atau klik untuk memilih file (JPEG/PNG, maks 5MB)</p>
          </div>
        )}
      </div>

      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png"
        className="hidden"
        onChange={handleFileChange}
      />

      {error && (
        <p className="mt-3 text-sm text-red-500 bg-red-50 rounded-lg px-3 py-2">{error}</p>
      )}

      <div className="flex gap-3 mt-4">
        <button
          onClick={handleUpload}
          disabled={!file || loading}
          className="flex-1 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed
            text-white font-medium py-2 px-4 rounded-lg transition-colors"
        >
          {loading ? 'Memproses...' : 'Deteksi Postur'}
        </button>
        {preview && (
          <button
            onClick={handleReset}
            className="px-4 py-2 rounded-lg border border-gray-300 text-gray-600 hover:bg-gray-50 transition-colors"
          >
            Reset
          </button>
        )}
      </div>
    </div>
  )
}
