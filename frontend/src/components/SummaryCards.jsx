/**
 * SummaryCards — menampilkan ringkasan statistik dari log deteksi.
 */
export default function SummaryCards({ logs }) {
  const total = logs.length

  const counts = logs.reduce((acc, log) => {
    acc[log.posture_label] = (acc[log.posture_label] || 0) + 1
    return acc
  }, {})

  const normal = counts['Normal'] || 0
  const duduk = counts['Duduk Tidak Tegak'] || 0
  const telungkup = counts['Telungkup'] || 0

  // ─── KODE BARU: MENGANULIR CONFIDENCE 0% DARI RATA-RATA ───
  // 1. Ambil data yang confidence-nya benar-benar ada (lebih dari 0)
  const validLogs = logs.filter(log => log.confidence_score > 0);
  
  // 2. Hitung jumlah confidence yang valid saja
  const totalValidConf = validLogs.reduce((sum, log) => sum + log.confidence_score, 0);
  
  // 3. Rata-rata dibagi jumlah data valid (bukan 'total' keseluruhan)
  const avgConf = validLogs.length > 0
    ? (totalValidConf / validLogs.length * 100).toFixed(1)
    : '0.0';
  // ────────────────────────────────────────────────────────

  const cards = [
    { label: 'Total Deteksi', value: total, color: 'bg-blue-50 text-blue-700', icon: '📊' },
    { label: 'Normal', value: normal, color: 'bg-green-50 text-green-700', icon: '✅' },
    { label: 'Duduk Tidak Tegak', value: duduk, color: 'bg-yellow-50 text-yellow-700', icon: '⚠️' },
    { label: 'Telungkup', value: telungkup, color: 'bg-red-50 text-red-700', icon: '🚨' },
    { label: 'Avg Confidence', value: total > 0 ? `${avgConf}%` : '—', color: 'bg-purple-50 text-purple-700', icon: '🎯' },
  ]

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
      {cards.map((c) => (
        <div key={c.label} className={`rounded-2xl p-4 ${c.color} shadow-sm`}>
          <div className="text-xl mb-1">{c.icon}</div>
          <div className="text-2xl font-bold">{c.value}</div>
          <div className="text-xs font-medium mt-1 opacity-80">{c.label}</div>
        </div>
      ))}
    </div>
  )
}