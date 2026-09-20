/**
 * api.js — wrapper fetch untuk komunikasi ke backend FastAPI.
 * Mengarahkan request langsung ke backend FastAPI di http://localhost:8000
 */

const API_BASE_URL = 'http://localhost:8000'

/**
 * Upload gambar ke POST /upload
 * @param {File} file - file gambar (JPEG/PNG)
 * @returns {Promise<{id: string, posture_label: string, confidence_score: number, image_url: string, timestamp: string}>}
 */
export async function uploadImage(file) {
  const formData = new FormData()
  formData.append('file', file)

  const res = await fetch(`${API_BASE_URL}/upload`, {
    method: 'POST',
    body: formData,
  })

  if (!res.ok) {
    const err = await res.json().catch(() => ({ message: 'Upload gagal' }))
    throw new Error(err.message || `HTTP ${res.status}`)
  }

  return res.json()
}

/**
 * Ambil riwayat log dari GET /logs
 * @param {{ limit?: number, posture_label?: string }} params
 * @returns {Promise<Array>}
 */
export async function fetchLogs({ limit = 500, posture_label } = {}) {
  const params = new URLSearchParams()
  params.set('limit', limit)
  if (posture_label) params.set('posture_label', posture_label)

  const res = await fetch(`${API_BASE_URL}/logs?${params.toString()}`)

  if (!res.ok) {
    const err = await res.json().catch(() => ({ message: 'Gagal mengambil data' }))
    throw new Error(err.message || `HTTP ${res.status}`)
  }

  return res.json()
}

// Cek status nyala/mati ESP32
export const checkEsp32Status = async () => {
  try {
    const response = await fetch('http://localhost:8000/api/esp32/status')
    if (!response.ok) return false
    const data = await response.json()
    return data.online
  } catch (error) {
    return false // Kalau server mati, otomatis dianggap offline
  }
}