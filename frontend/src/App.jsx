import { useState, useEffect, useCallback } from 'react'
import mqtt from 'mqtt' // <-- KODE BARU: Import library MQTT
import UploadPanel from './components/UploadPanel'
import ResultCard from './components/ResultCard'
import SummaryCards from './components/SummaryCards'
import DetectionTable from './components/DetectionTable'
import { fetchLogs, checkEsp32Status } from './services/api'

function App() {
  const [logs, setLogs] = useState([])
  const [initialLoading, setInitialLoading] = useState(true) 
  const [logsError, setLogsError] = useState(null)
  const [filter, setFilter] = useState('')
  
  // --- KODE BARU: State untuk Filter Tanggal ---
  const [dateFilter, setDateFilter] = useState('') 

  const [lastResult, setLastResult] = useState(null)
  const [showManualUpload, setShowManualUpload] = useState(false)
  const [isEspOnline, setIsEspOnline] = useState(false)
  
  // State indikator MQTT untuk UI
  const [isMqttConnected, setIsMqttConnected] = useState(false)

  // --- KODE BARU: State untuk gambar Livestream 1 Detik ---
  const [liveImageUrl, setLiveImageUrl] = useState("http://localhost:8000/images/latest_frame.jpg")
  
  // --- KODE BARU: STATE UNTUK JAM REAL-TIME ---
  const [currentTime, setCurrentTime] = useState(new Date())

  // Interval Jam Real-time (Update setiap 1 detik)
  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000)
    return () => clearInterval(timer)
  }, [])

  const loadLogs = useCallback(async (isSilent = false) => {
    if (!isSilent) setInitialLoading(true)
    setLogsError(null)
    try {
      const data = await fetchLogs({ limit: 500, posture_label: filter || undefined })
      setLogs(data)
    } catch (err) {
      setLogsError(err.message)
    } finally {
      if (!isSilent) setInitialLoading(false)
    }
  }, [filter])

  useEffect(() => {
    loadLogs(false) 
    const intervalId = setInterval(async () => {
      loadLogs(true) 
      const status = await checkEsp32Status()
      setIsEspOnline(status)
    }, 3000)
    return () => clearInterval(intervalId)
  }, [loadLogs])

  // --- KODE BARU: Interval 1 Detik Khusus Refresh Gambar Livestream ---
  useEffect(() => {
    const liveInterval = setInterval(() => {
      // Tambahkan Date.now() agar browser tidak nge-cache gambar lama
      const timestamp = Date.now()
      setLiveImageUrl(`http://localhost:8000/images/latest_frame.jpg?t=${timestamp}`)
    }, 1000) // 1000 milidetik = 1 detik

    return () => clearInterval(liveInterval)
  }, [])

  const latestLog = logs.length > 0 ? logs[0] : null;

  // --- KODE BARU: FILTER UNTUK SUMMARY CARDS (ATAS) ---
  const filteredLogsForSummary = logs.filter(log => {
    if (!dateFilter) return true; // Kalau tanggal kosong, tampilkan semua
    return log.timestamp.startsWith(dateFilter);
  });
  // ----------------------------------------------------

 // FUNGSI MEMBUNYIKAN BUZZER DIGITAL (Multi-Beep)
  const playAlarm = useCallback(() => {
    try {
      // Loop untuk membunyikan beep sebanyak 4 kali berturut-turut
      for (let i = 0; i < 4; i++) {
        setTimeout(() => {
          const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
          const oscillator = audioCtx.createOscillator();
          const gainNode = audioCtx.createGain();

          oscillator.connect(gainNode);
          gainNode.connect(audioCtx.destination);
          oscillator.type = 'square'; 
          oscillator.frequency.setValueAtTime(750, audioCtx.currentTime); 

          oscillator.start();
          setTimeout(() => { oscillator.stop(); }, 400); // Durasi per beep agak ringkas
        }, i * 600); // Jeda waktu antar bunyi beep (600 milidetik)
      }
    } catch (error) {
      console.log("Autoplay diblokir browser.");
    }
  }, []);

  // --- KODE BARU: JALUR KOMUNIKASI RABBITMQ (WEB MQTT) ---
  useEffect(() => {
    // Konek ke RabbitMQ lewat jalur WebSocket (Port 15675)
    const client = mqtt.connect('ws://localhost:15675/ws', {
      username: 'guest',
      password: 'guest',
      clientId: `frontend_dashboard_${Math.random().toString(16).slice(3)}`,
    });

    client.on('connect', () => {
      console.log('✅ Terhubung ke RabbitMQ Broker!');
      setIsMqttConnected(true);
      // Begitu konek, langsung pasang telinga di topik ini
      client.subscribe('kandang/buzzer');
    });

    client.on('message', (topic, message) => {
      const payload = message.toString();
      console.log(`📩 Pesan MQTT Masuk [${topic}]: ${payload}`);
      
      // Jika Backend/ESP32 teriak "ON", bunyikan alarm laptop!
      if (topic === 'kandang/buzzer' && payload === 'ON') {
        playAlarm();
      }
    });

    client.on('error', (err) => {
      console.error('❌ MQTT Error:', err);
      setIsMqttConnected(false);
    });

    return () => {
      if (client) client.end();
    };
  }, [playAlarm]);
  // --------------------------------------------------------

  const formatWaktuWIB = (timestamp) => {
    if (!timestamp) return '-'
    // Hapus format endsWith('Z') karena backend sudah murni pakai WIB
    const date = new Date(timestamp)
    return date.toLocaleString('id-ID', {
      timeZone: 'Asia/Jakarta',
      dateStyle: 'medium',
      timeStyle: 'medium',
      hour12: false
    })
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <span className="text-2xl">🐔</span>
            <div>
              <h1 className="text-lg font-bold text-gray-800 leading-tight">
                Dashboard Monitoring Postur Ayam (IoT)
              </h1>
              <div className="flex items-center gap-2 text-xs text-gray-400 mt-1">
                <span>Powered by YOLOv8 & ESP32</span>
                <span>•</span>
                {/* Indikator status MQTT */}
                <span className={`font-medium ${isMqttConnected ? 'text-blue-500' : 'text-gray-400'}`}>
                  {isMqttConnected ? '☁️ RabbitMQ Connected' : '☁️ Broker Offline'}
                </span>
              </div>
            </div>
          </div>
          
          <div className="flex flex-col items-end gap-2">
            {/* WIDGET JAM REAL-TIME */}
            <div className="bg-blue-50 text-blue-700 px-4 py-1 rounded-full text-sm font-bold border border-blue-200 shadow-sm flex items-center gap-2">
              🕒 {currentTime.toLocaleString('id-ID', { timeZone: 'Asia/Jakarta', dateStyle: 'full', timeStyle: 'medium' })} WIB
            </div>

            <div className={`px-4 py-1.5 rounded-full border text-sm font-semibold flex items-center gap-2 transition-colors ${
              isEspOnline ? 'bg-green-50 border-green-200 text-green-700' : 'bg-red-50 border-red-200 text-red-600'
            }`}>
              <span className="relative flex h-3 w-3">
                {isEspOnline && <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>}
                <span className={`relative inline-flex rounded-full h-3 w-3 ${isEspOnline ? 'bg-green-500' : 'bg-red-500'}`}></span>
              </span>
              {isEspOnline ? 'ESP32 Terhubung' : 'ESP32 Terputus'}
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-6 space-y-6">
        
        {/* KODE BARU: Kirim filteredLogsForSummary agar totalan atas ikut berubah */}
        <SummaryCards logs={filteredLogsForSummary} />

        {/* --- TAMPILAN 2 LAYAR (SIDE-BY-SIDE) --- */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 w-full">
          
          {/* LAYAR KIRI: LIVESTREAM 1 DETIK */}
          <div className="bg-white rounded-2xl shadow p-6 flex flex-col items-center">
            <div className="w-full mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-700">🔴 Live Monitor </h2>
              <span className={`flex items-center gap-2 text-sm font-medium ${isEspOnline ? 'text-green-600' : 'text-gray-400'}`}>
                {isEspOnline ? 'Live Transmitting' : 'Offline'}
              </span>
            </div>

            {latestLog || isEspOnline ? (
              <div className="relative w-full bg-gray-100 rounded-xl overflow-hidden border border-gray-200">
                <img
                  src={liveImageUrl}
                  onError={(e) => { e.target.src = "https://via.placeholder.com/640x480?text=Menunggu+Kamera..." }}
                  alt="Live Camera Detection"
                  className="w-full h-auto object-contain max-h-[350px]"
                />
                {!isEspOnline && (
                  <div className="absolute inset-0 bg-black/40 flex items-center justify-center backdrop-blur-[1px]">
                    <span className="bg-red-600 text-white px-4 py-2 rounded-full font-bold shadow-lg text-sm">
                      ⚠️ ESP32 Terputus
                    </span>
                  </div>
                )}
              </div>
            ) : (
               <div className="w-full h-[350px] bg-gray-100 rounded-xl flex flex-col items-center justify-center border-2 border-dashed border-gray-300">
                <span className="text-4xl mb-3 animate-pulse">📷</span>
                <p className="text-gray-500 font-medium text-sm">Menunggu tangkapan kamera...</p>
              </div>
            )}
          </div>

          {/* LAYAR KANAN: LOG DATABASE TERAKHIR (15 DETIK) */}
          <div className="bg-white rounded-2xl shadow p-6 flex flex-col items-center border-2 border-blue-50">
            <div className="w-full mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-blue-700">💾 Hasil Deteksi</h2>
            </div>

            {latestLog ? (
              <div className={`relative w-full bg-gray-100 rounded-xl overflow-hidden border ${
                  latestLog.posture_label === 'Telungkup' ? 'border-red-500 shadow-lg' : 'border-blue-200'
                }`}>
                
                {latestLog.posture_label === 'Telungkup' && (
                  <div className="absolute top-4 left-1/2 transform -translate-x-1/2 bg-red-600 text-white px-3 py-1.5 rounded-full font-bold shadow-lg z-10 animate-pulse text-[11px] sm:text-sm whitespace-nowrap">
                    🚨 BAHAYA TEREKAM!
                  </div>
                )}

                <img
                  src={`http://localhost:8000${latestLog.image_url}`}
                  onError={(e) => { e.target.src = "https://via.placeholder.com/640x480?text=Gambar+Kosong/Dihapus" }}
                  alt="Database Capture"
                  className="w-full h-auto object-contain max-h-[350px]"
                />
                
                <div className={`absolute bottom-0 left-0 right-0 p-3 flex justify-between items-center backdrop-blur-sm text-white ${
                  latestLog.posture_label === 'Telungkup' ? 'bg-red-900/80' : 'bg-black/70'
                }`}>
                  <div>
                    <p className="font-bold text-base">{latestLog.posture_label}</p>
                    <p className="text-xs text-gray-300">{formatWaktuWIB(latestLog.timestamp)}</p>
                  </div>
                  <div className="text-right">
                    <span className="text-base font-bold">{(latestLog.confidence_score * 100).toFixed(1)}%</span>
                  </div>
                </div>
              </div>
            ) : (
               <div className="w-full h-[350px] bg-gray-100 rounded-xl flex flex-col items-center justify-center border-2 border-dashed border-gray-300">
                <span className="text-4xl mb-3">📭</span>
                <p className="text-gray-500 font-medium text-sm">Belum ada data di database...</p>
              </div>
            )}
          </div>
        </div>
        {/* ------------------------------------------- */}

        <div className="flex justify-center">
          <button 
            onClick={() => setShowManualUpload(!showManualUpload)}
            className="text-sm px-6 py-2.5 rounded-full font-medium transition-all shadow-sm focus:outline-none 
                        bg-white text-gray-700 hover:bg-gray-100 border-2 border-gray-200 hover:border-gray-300"
          >
            {showManualUpload ? 'Tutup Uji Coba Manual ✕' : 'Tampilkan Uji Coba Manual (Simulasi) ⚙️'}
          </button>
        </div>

        {showManualUpload && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <UploadPanel
              onResult={setLastResult}
              onUploadDone={() => loadLogs(true)} 
            />
            <ResultCard result={lastResult} />
          </div>
        )}

        <DetectionTable
          logs={logs}
          loading={initialLoading} 
          error={logsError}
          filter={filter}
          onFilterChange={setFilter}
          dateFilter={dateFilter}
          onDateFilterChange={setDateFilter}
        />
      </main>
    </div>
  )
}

export default App