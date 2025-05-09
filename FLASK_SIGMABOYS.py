from flask import Flask, request, jsonify
from pymongo import MongoClient

app = Flask(__name__)

MONGO_URI = "mongodb+srv://SigmaBoys:yy1234567@cluster0.atarb.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
DB_NAME = "rakan"
COLLECTION = "sic"

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION]


@app.route("/save",methods=["POST"])
def save_data():
    data = request.get_json()
    temperature = data.get("temperature")
    humidity = data.get("humidity")
    lux = data.get("lux")
    
    data = {"temperature":temperature,"humidity":humidity,"lux":lux}
    collection.insert_one(data)
    return jsonify({"message":"success"})

if __name__=="__main__":
    app.run(debug=True,host="0.0.0.0", port=81)
