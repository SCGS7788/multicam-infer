# 🎨 Quick Start - UI Dashboard

## เริ่มใช้งาน Web UI ใน 3 ขั้นตอน

### 1️⃣ รันระบบ
```bash
./run.sh --config config/cameras.yaml
```

### 2️⃣ เปิด Browser
```
http://localhost:8080
```

### 3️⃣ เสร็จแล้ว! ✅

---

## 📸 ตัวอย่างหน้าจอ

### หน้าหลัก (Dashboard)
- แสดงสถิติรวม: Frames, Cameras, Events, Latency
- แสดงสถานะกล้องทุกตัว real-time
- Auto-refresh ทุก 5 วินาที

### API Endpoints
```bash
# Health Check
curl http://localhost:8080/healthz

# Prometheus Metrics
curl http://localhost:8080/metrics

# Web Dashboard
open http://localhost:8080
```

---

## 🎯 สิ่งที่เห็นใน UI

### 📊 Overview Stats
- **Total Frames**: จำนวน frame ที่ประมวลผลทั้งหมด
- **Active Cameras**: จำนวนกล้องที่ทำงานอยู่
- **Detection Events**: จำนวน events ที่ตรวจพบ
- **Avg Latency**: เวลาประมวลผลเฉลี่ย (ms)

### 🎥 Camera Cards
แต่ละกล้องแสดง:
- **Status**: ● สีเขียว = Active, สีแดง = Offline
- **Frames**: จำนวน frames ที่ประมวลผล
- **Latency**: เวลาประมวลผลเฉลี่ย
- **FPS**: Frames per second

### 📱 ใช้งานบน Mobile
- Responsive design
- ใช้งานได้ทั้ง iPhone, Android, iPad
- เปิดผ่าน browser ธรรมดา

---

## 🚀 Advanced: Grafana Dashboard

ถ้าต้องการ professional monitoring:

```bash
# Start Grafana + Prometheus
docker-compose -f docker-compose-with-grafana.yml up -d

# Open Grafana
open http://localhost:3000
# Login: admin / admin123
```

**Grafana Features:**
- 📈 Advanced charts & graphs
- ⏱️ Historical data (30 days)
- 🔔 Alerting system
- 📊 Custom dashboards
- 📤 Export reports

---

## 🔧 Customization

### เปลี่ยนสี Theme
แก้ไข `src/kvs_infer/static/dashboard.html`:

```css
/* Line 15: gradient background */
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
```

**Theme Presets:**
- Pink: `#f093fb 0%, #f5576c 100%`
- Blue: `#4facfe 0%, #00f2fe 100%`
- Green: `#43e97b 0%, #38f9d7 100%`

### เปลี่ยน Port
แก้ไข `run.sh` หรือ environment variable:
```bash
export HTTP_PORT=3000
./run.sh --config config/cameras.yaml
```

---

## 📖 เพิ่มเติม

- [คู่มือ UI แบบเต็ม](UI_DASHBOARD_GUIDE.md)
- [ภาพตัวอย่าง UI](UI_SCREENSHOTS.md)
- [README หลัก](README.md)

---

## 💡 Tips

✅ **Refresh Rate**: UI จะ refresh ทุก 5 วินาทีอัตโนมัติ
✅ **Mobile**: เข้าผ่าน IP ของ server (เช่น http://192.168.1.10:8080)
✅ **Dark Mode**: Coming soon! (หรือแก้ CSS เองได้)
✅ **Custom Metrics**: ดูที่ `/metrics` endpoint

---

**สนุกกับการใช้งาน! 🎉**
