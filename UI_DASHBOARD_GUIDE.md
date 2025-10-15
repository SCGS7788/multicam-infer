# 🎨 UI Dashboard Guide

## ตัวเลือก UI สำหรับ KVS Inference System

### 📊 ตัวเลือก 1: Web Dashboard (Built-in) ⭐ แนะนำเริ่มต้น

**คุณสมบัติ:**
- ✅ ติดตั้งง่าย (มีมาพร้อมระบบ)
- ✅ Real-time metrics
- ✅ Camera status monitoring
- ✅ Responsive design
- ✅ ไม่ต้องติดตั้งอะไรเพิ่ม

**วิธีใช้:**

1. **รันระบบ:**
```bash
./run.sh --config config/cameras.yaml
```

2. **เปิด Browser:**
```
http://localhost:8080/
```

3. **Features ที่มี:**
   - 📈 Total frames processed
   - 🎥 Active cameras count
   - ⚡ Detection events
   - ⏱️ Average latency
   - 📹 Camera status cards
   - Auto-refresh ทุก 5 วินาที

**Screenshots:**
```
┌─────────────────────────────────────────────────────────────┐
│  🎥 KVS Inference Dashboard           ● ONLINE             │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐       │
│  │  1,234  │  │    3    │  │   45    │  │ 2.5 ms  │       │
│  │ Frames  │  │ Cameras │  │ Events  │  │ Latency │       │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘       │
│                                                              │
│  Camera Status                                              │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐  │
│  │ camera_1    ● │  │ camera_2    ● │  │ camera_3    ● │  │
│  │ Frames: 450  │  │ Frames: 392  │  │ Frames: 392  │  │
│  │ Latency: 2ms │  │ Latency: 3ms │  │ Latency: 2ms │  │
│  │ FPS: ~5      │  │ FPS: ~5      │  │ FPS: ~5      │  │
│  │ ✓ Active     │  │ ✓ Active     │  │ ✓ Active     │  │
│  └───────────────┘  └───────────────┘  └───────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

### 📊 ตัวเลือก 2: Grafana Dashboard (Professional) 🚀

**คุณสมบัติ:**
- ✅ Professional monitoring
- ✅ Advanced visualizations
- ✅ Alerting system
- ✅ Historical data
- ✅ Customizable dashboards
- ✅ Multi-datasource support

**วิธีติดตั้ง:**

1. **Start with Docker Compose:**
```bash
docker-compose -f docker-compose-with-grafana.yml up -d
```

2. **เข้าถึง Services:**
```
Grafana:    http://localhost:3000
            Username: admin
            Password: admin123

Prometheus: http://localhost:9090
KVS App:    http://localhost:8080
```

3. **Import Dashboard:**
   - ไปที่ Grafana → Dashboards
   - Dashboard จะถูกโหลดอัตโนมัติ (provisioned)
   - ชื่อ: "KVS Inference Dashboard"

**Dashboard Panels:**

| Panel | Description |
|-------|-------------|
| **Frame Processing Rate** | FPS ของแต่ละกล้อง (real-time) |
| **Detection Events** | Events/sec แยกตาม type (weapon, fire, alpr) |
| **Processing Latency** | p50 และ p95 latency |
| **Active Cameras** | จำนวนกล้องที่ทำงาน |
| **Total Frames** | Total frames processed (all cameras) |
| **Worker Status** | Table แสดงสถานะ workers |
| **Publisher Failures** | Alert เมื่อ publisher ล้มเหลว |

**Screenshots:**
```
┌─────────────────────────────────────────────────────────────┐
│  Grafana - KVS Inference Dashboard                          │
├─────────────────────────────────────────────────────────────┤
│  Frame Processing Rate        │  Detection Events          │
│  ┌───────────────────────────┐│ ┌───────────────────────┐  │
│  │    📈 camera_1: 5.2 FPS   ││ │ 📊 weapon: 0.5/sec    │  │
│  │    📈 camera_2: 4.8 FPS   ││ │ 📊 fire: 0.1/sec      │  │
│  │    📈 camera_3: 5.1 FPS   ││ │ 📊 alpr: 2.3/sec      │  │
│  └───────────────────────────┘│ └───────────────────────┘  │
│                                                              │
│  Processing Latency (ms)      │  Active Cameras: 3        │
│  ┌───────────────────────────┐│ ┌───────────────────────┐  │
│  │    p95: 15.2 ms           ││ │     ████████          │  │
│  │    p50: 8.5 ms            ││ │     3 / 3 Active      │  │
│  └───────────────────────────┘│ └───────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

### 📊 ตัวเลือก 3: Prometheus UI (Raw Metrics)

**วิธีเข้าถึง:**
```
http://localhost:9090
```

**Query Examples:**
```promql
# Frame rate per camera
rate(infer_frames_total[1m])

# Total events by type
sum by (type) (infer_events_total)

# P95 latency
histogram_quantile(0.95, rate(infer_latency_ms_bucket[5m]))

# Worker health
worker_alive
```

---

## 🚀 Quick Start Guide

### Option A: Simple Web UI (Fastest)

```bash
# 1. Start application
./run.sh --config config/cameras.yaml

# 2. Open browser
open http://localhost:8080

# Done! ✅
```

### Option B: Full Grafana Stack

```bash
# 1. Start all services
docker-compose -f docker-compose-with-grafana.yml up -d

# 2. Wait for services to start (~30 seconds)
docker-compose -f docker-compose-with-grafana.yml ps

# 3. Open Grafana
open http://localhost:3000

# 4. Login (admin/admin123)

# 5. Go to Dashboards → KVS Inference Dashboard

# Done! ✅
```

---

## 📱 Mobile Access

Web UI รองรับ mobile devices:

```
📱 iPhone/iPad:  http://192.168.1.xxx:8080
🤖 Android:      http://192.168.1.xxx:8080
💻 Laptop:       http://localhost:8080
```

*(เปลี่ยน 192.168.1.xxx เป็น IP ของ server)*

---

## 🔧 Customization

### เปลี่ยนสี Theme ของ Web UI:

แก้ไข `src/kvs_infer/static/dashboard.html`:

```css
/* Line 15: Change gradient colors */
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);

/* To different theme: */
background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); /* Pink */
background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); /* Blue */
background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); /* Green */
```

### เพิ่ม Custom Grafana Dashboard:

1. สร้าง dashboard ใน Grafana UI
2. Export เป็น JSON
3. บันทึกที่ `monitoring/grafana/dashboards/`
4. Restart Grafana

---

## 🐛 Troubleshooting

### UI ไม่โหลด

```bash
# ตรวจสอบว่าระบบทำงาน
curl http://localhost:8080/healthz

# ดู logs
docker-compose -f docker-compose-with-grafana.yml logs -f
```

### Grafana ไม่เชื่อมต่อ Prometheus

1. ไปที่ Configuration → Data Sources
2. Test connection
3. ถ้าล้มเหลว check `monitoring/grafana/datasources/prometheus.yml`

### Metrics ไม่อัพเดท

```bash
# Restart Prometheus
docker-compose -f docker-compose-with-grafana.yml restart prometheus

# Check Prometheus targets
open http://localhost:9090/targets
```

---

## 📊 Comparison

| Feature | Web UI | Grafana | Prometheus |
|---------|--------|---------|------------|
| **Setup Time** | < 1 min | ~5 min | < 1 min |
| **Real-time** | ✅ 5s refresh | ✅ 5s refresh | ✅ On-demand |
| **Historical Data** | ❌ No | ✅ 30 days | ✅ 15 days |
| **Alerting** | ❌ No | ✅ Yes | ✅ Yes |
| **Customization** | ⚡ Limited | 🚀 Full | 📊 Query-based |
| **Mobile** | ✅ Yes | ✅ Yes | ⚠️ Desktop only |
| **Best For** | Quick view | Production | Debugging |

---

## 💡 Recommendations

| Use Case | Recommended UI |
|----------|---------------|
| **Development** | Web UI (Built-in) |
| **Production** | Grafana + Prometheus |
| **Demo/Testing** | Web UI |
| **24/7 Monitoring** | Grafana with Alerts |
| **Quick Check** | Web UI or `/metrics` endpoint |
| **Debugging** | Prometheus + raw queries |

---

## 🎯 Next Steps

1. **Start with Web UI** (http://localhost:8080)
2. **Try Grafana** when you need advanced features
3. **Set up Alerts** in Grafana for production
4. **Customize dashboards** based on your needs

**Need help?** Check:
- `/healthz` - System health
- `/metrics` - Raw Prometheus metrics
- Logs: `docker-compose logs -f`
