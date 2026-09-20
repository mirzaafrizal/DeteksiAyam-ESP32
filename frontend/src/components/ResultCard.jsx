/**
 * ResultCard — menampilkan hasil deteksi terakhir (label + confidence).
 */

const LABEL_STYLES = {
  'Normal': 'bg-green-100 text-green-700 border-green-200',
  'Duduk Tidak Tegak': 'bg-yellow-100 text-yellow-700 border-yellow-200',
  'Telungkup': 'bg-red-100 text-red-700 border-red-200',
}

// --- FUNGSI TAMBAHAN UNTUK MEMPERBAIKI JAM & INVALID DATE ---
const formatWaktuHasil = (timestamp) => {
  // Jika timestamp kosong/undefined, otomatis ambil jam laptop SAAT INI.
  // Jika ada isinya, paksakan tambah huruf 'Z' di akhir agar mutlak dibaca sebagai UTC.
  const date = timestamp 
    ? new Date(timestamp.endsWith('Z') ? timestamp : `${timestamp}Z`) 
    : new Date(); 

  return date.toLocaleString('id-ID', {
    timeZone: 'Asia/Jakarta',
    dateStyle: 'medium',
    timeStyle: 'medium',
    hour12: false
  });
};
// -------------------------------------------------------------

export default function ResultCard({ result }) {
  if (!result) return null

  const labelStyle = LABEL_STYLES[result.posture_label] ?? 'bg-gray-100 text-gray-700 border-gray-200'
  const pct = (result.confidence_score * 100).toFixed(1)

  return (
    <div className="bg-white rounded-2xl shadow p-6">
      <h2 className="text-lg font-semibold text-gray-700 mb-4">Hasil Deteksi</h2>

      <div className={`inline-block border rounded-xl px-4 py-2 font-semibold text-lg mb-4 ${labelStyle}`}>
        {result.posture_label}
      </div>

      <div className="space-y-2 text-sm text-gray-600">
        <div className="flex justify-between">
          <span>Confidence</span>
          <span className="font-medium">{pct}%</span>
        </div>
        {/* Confidence bar */}
        <div className="w-full bg-gray-100 rounded-full h-2">
          <div
            className="h-2 rounded-full bg-blue-500 transition-all"
            style={{ width: `${pct}%` }}
          />
        </div>
        <div className="flex justify-between pt-1">
          <span>Waktu</span>
          <span className="font-medium">
            {/* UBAH BAGIAN SINI: Panggil fungsi pemformatan waktunya */}
            {formatWaktuHasil(result.timestamp)}
          </span>
        </div>
      </div>
    </div>
  )
}