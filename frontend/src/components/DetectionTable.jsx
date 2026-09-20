import { useState } from 'react';

/**
 * DetectionTable — tabel riwayat log deteksi dengan filter postur dan tanggal.
 */

const LABEL_BADGE = {
  'Normal': 'bg-green-100 text-green-700',
  'Duduk Tidak Tegak': 'bg-yellow-100 text-yellow-700',
  'Telungkup': 'bg-red-100 text-red-700',
  'Tidak Ada Ayam': 'bg-gray-200 text-gray-600', 
  // ── WARNA BADGE UNTUK CONFIDENCE RENDAH ──
  'Tidak Ada Ayam (Confidence Rendah)': 'bg-gray-200 text-gray-600', 
}

export default function DetectionTable({ logs, loading, error, filter, onFilterChange, dateFilter, onDateFilterChange }) {
  const [selectedImage, setSelectedImage] = useState(null);

  // FUNGSI FORMAT WAKTU WIB YANG SUDAH DIPERBAIKI (Sinkron dengan Database & Realtime)
  const formatWaktuWIB = (timestamp) => {
    if (!timestamp) return '-'
    // Pastikan string waktu dibaca dengan benar oleh JavaScript
    const validTimestamp = timestamp.endsWith('Z') || timestamp.includes('+') ? timestamp : `${timestamp}Z`
    const date = new Date(validTimestamp)
    
    return date.toLocaleString('id-ID', {
      timeZone: 'Asia/Jakarta',
      dateStyle: 'medium',
      timeStyle: 'medium',
      hour12: false
    })
  }

  // Menyaring data log berdasarkan tanggal yang dipilih pada input kalender
  const filteredLogs = logs.filter(log => {
    if (!dateFilter) return true; // Kalau tanggal kosong, tampilkan semua
    return log.timestamp.startsWith(dateFilter);
  });

  return (
    <div className="bg-white rounded-2xl shadow p-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
        <h2 className="text-lg font-semibold text-gray-700">Riwayat Deteksi</h2>

        {/* Bagian Filter Berjejer */}
        <div className="flex flex-col sm:flex-row gap-2">
          {/* 1. Filter Tanggal (Harian) */}
          <input 
            type="date" 
            value={dateFilter}
            onChange={(e) => onDateFilterChange(e.target.value)}
            className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-300"
            title="Filter berdasarkan hari"
          />

          {/* 2. Filter Postur */}
          <select
            value={filter}
            onChange={(e) => onFilterChange(e.target.value)}
            className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-300"
          >
            <option value="">Semua Postur</option>
            <option value="Normal">Normal</option>
            <option value="Duduk Tidak Tegak">Duduk Tidak Tegak</option>
            <option value="Telungkup">Telungkup</option>
            <option value="Tidak Ada Ayam">Tidak Ada Ayam</option>
            {/* 👇 INI TAMBAHAN OPTION-NYA KAK 👇 */}
            <option value="Tidak Ada Ayam (Confidence Rendah)">Tidak Ada Ayam (Confidence Rendah)</option>
          </select>
        </div>
      </div>

      {error && (
        <p className="text-sm text-red-500 bg-red-50 rounded-lg px-3 py-2 mb-3">{error}</p>
      )}

      {loading ? (
        <div className="text-center text-gray-400 py-12 text-sm">Memuat data...</div>
      ) : filteredLogs.length === 0 ? (
        <div className="text-center text-gray-400 py-12 text-sm">
          {dateFilter ? "Tidak ada deteksi pada tanggal tersebut." : "Belum ada data deteksi."}
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-500 border-b border-gray-100">
                <th className="pb-3 font-medium">Waktu</th>
                <th className="pb-3 font-medium">Postur</th>
                <th className="pb-3 font-medium">Confidence</th>
                <th className="pb-3 font-medium text-center">Jumlah Ayam</th>
                <th className="pb-3 font-medium hidden md:table-cell">Gambar</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {filteredLogs.map((log) => (
                <tr key={log._id} className="hover:bg-gray-50 transition-colors">
                  <td className="py-3 text-gray-600 whitespace-nowrap">
                    {formatWaktuWIB(log.timestamp)}
                  </td>
                  <td className="py-3">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${LABEL_BADGE[log.posture_label] ?? 'bg-gray-100 text-gray-600'}`}>
                      {log.posture_label}
                    </span>
                  </td>
                  <td className="py-3 text-gray-600">
                    {(log.confidence_score * 100).toFixed(1)}%
                  </td>
                  <td className="py-3 text-gray-700 font-semibold text-center">
                    {log.jumlah_ayam || 0} Ekor
                  </td>
                  <td className="py-2 hidden md:table-cell">
                    {log.image_url ? (
                      <img 
                        src={`http://localhost:8000${log.image_url}`} 
                        alt="Thumbnail" 
                        onClick={() => setSelectedImage(log.image_url)}
                        className="w-16 h-16 object-cover rounded-lg shadow-sm cursor-pointer hover:opacity-75 transition-opacity border border-gray-200"
                        title="Klik untuk memperbesar"
                      />
                    ) : (
                      <span className="text-gray-300 text-xs">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* --- MODAL POPUP --- */}
      {selectedImage && (
        <div 
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm transition-opacity"
          onClick={() => setSelectedImage(null)} 
        >
          <div 
            className="relative bg-white p-4 rounded-2xl shadow-2xl max-w-4xl max-h-[95vh] flex flex-col items-center"
            onClick={(e) => e.stopPropagation()} 
          >
            <button 
              onClick={() => setSelectedImage(null)}
              className="absolute -top-3 -right-3 bg-red-500 text-white rounded-full w-8 h-8 flex items-center justify-center font-bold shadow-lg hover:bg-red-600 focus:outline-none transition-colors"
            >
              ✕
            </button>
            
            <img 
              src={`http://localhost:8000${selectedImage}`} 
              alt="Deteksi AI Besar" 
              className="max-w-full max-h-[75vh] object-contain rounded-xl mb-4"
            />

            <a 
              href={`http://localhost:8000${selectedImage}`} 
              target="_blank" 
              rel="noreferrer"
              className="bg-blue-500 hover:bg-blue-600 text-white px-5 py-2 rounded-lg text-sm font-medium transition-colors shadow-sm flex items-center gap-2"
            >
              Buka di Tab Baru ↗
            </a>
          </div>
        </div>
      )}
    </div>
  )
}