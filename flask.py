from flask import Flask, request, jsonify
from pymongo import MongoClient
from datetime import datetime

app = Flask(__name__)

# Konfigurasi MongoDB Atlas
MONGO_URI = "mongodb+srv://SigmaBoys:yy1234567@cluster0.atarb.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client["rakan"]  # Nama database
collection = db["sic"]  # Nama collection

# Endpoint untuk menerima data dari ESP32
@app.route('/sensor-data', methods=['POST'])
def receive_sensor_data():
    try:
        # Ambil data dari request
        data = request.json
        temperature = data.get("temperature")
        humidity = data.get("humidity")
        lux = data.get("lux")

        # Validasi data
        if None in [temperature, humidity, lux]:
            return jsonify({"status": "error", "message": "Invalid data received"}), 400

        # Simpan data ke MongoDB
        sensor_reading = {
            "temperature": temperature,
            "humidity": humidity,
            "lux": lux,
            "timestamp": datetime.now()
        }
        collection.insert_one(sensor_reading)

        # Kirim respons sukses
        return jsonify({"status": "success", "message": "Data saved to MongoDB"}), 200

    except Exception as e:
        print("Error:", e)
        return jsonify({"status": "error", "message": str(e)}), 500

# Jalankan Flask app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)