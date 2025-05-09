import machine
import time
import ssd1306
import dht
import network
import ujson
import urequests  # pastikan file ini ada di ESP32
import gc  # optional: untuk bersihin memori

# === KONFIGURASI WiFi ===
SSID = "moonstar"
PASSWORD = "17072005"

# === KONFIGURASI UBIDOTS ===
UBIDOTS_TOKEN = "BBUS-4dkNId6LDOVysK48pdwW8cUGBfAQTK"
UBIDOTS_DEVICE_LABEL = "hsc345"
UBIDOTS_URL = "http://industrial.api.ubidots.com/api/v1.6/devices/{}".format(UBIDOTS_DEVICE_LABEL)

headers = {
    "X-Auth-Token": UBIDOTS_TOKEN,
    "Content-Type": "application/json"
}

# === KONFIGURASI PIN ===
DHT_PIN = 13
LDR_PIN = 34
I2C_SDA = 21
I2C_SCL = 22
RED_LED_PIN = 14
YELLOW_LED_PIN = 15
GREEN_LED_PIN = 4
MQ2_PIN = 35

# SETUP SERVO DI PIN 26
servo_pin = machine.Pin(26)
servo = machine.PWM(servo_pin, freq=50)
servo.duty(0)  # Initialize with 0 duty

def safe_set_servo(angle):
    global last_angle
    if angle != last_angle and 0 <= angle <= 180:
        try:
            duty = int((angle / 180) * 102 + 26)
            servo.duty(duty)
            last_angle = angle
            time.sleep(0.5)  # Beri waktu untuk servo bergerak
        except Exception as e:
            print("Servo movement failed:", e)
            # Coba reset PWM
            servo.deinit()
            time.sleep(0.1)
            servo.init(freq=50)

last_angle = -1  # untuk deteksi perubahan

# Ganti implementasi servo dengan ini:
def set_servo(angle):
    global last_angle
    if angle != last_angle:
        try:
            duty = int((angle / 180) * 102 + 26)
            servo.duty(duty)
            last_angle = angle
            time.sleep(0.3)  # Beri jeda setelah gerakan
        except Exception as e:
            print("Servo error:", e)
            machine.reset()  # Soft reset jika error kritis
            
# === INISIALISASI I2C & OLED ===
try:
    i2c = machine.I2C(0, scl=machine.Pin(I2C_SCL), sda=machine.Pin(I2C_SDA))
    oled = ssd1306.SSD1306_I2C(128, 64, i2c)
except Exception as e:
    print("OLED gagal diinisialisasi:", e)
    oled = None

# === INISIALISASI PIN OUTPUT ===
red_led = machine.Pin(RED_LED_PIN, machine.Pin.OUT)
yellow_led = machine.Pin(YELLOW_LED_PIN, machine.Pin.OUT)
green_led = machine.Pin(GREEN_LED_PIN, machine.Pin.OUT)

# === INISIALISASI SENSOR ===
sensor = dht.DHT11(machine.Pin(DHT_PIN))

ldr_sensor = machine.ADC(machine.Pin(LDR_PIN))
ldr_sensor.width(machine.ADC.WIDTH_12BIT)
ldr_sensor.atten(machine.ADC.ATTN_11DB)

mq2_sensor = machine.ADC(machine.Pin(MQ2_PIN))
mq2_sensor.width(machine.ADC.WIDTH_12BIT)
mq2_sensor.atten(machine.ADC.ATTN_11DB)

# === KONEKSI KE WiFi ===
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Mencoba konek ke WiFi...")
        wlan.connect(SSID, PASSWORD)
        max_wait = 10
        while not wlan.isconnected() and max_wait > 0:
            time.sleep(1)
            max_wait -= 1
            print("Menunggu koneksi...")
    if wlan.isconnected():
        print("Terhubung ke WiFi. IP:", wlan.ifconfig()[0])
    else:
        print("Gagal konek ke WiFi")

# === BACA SENSOR ===
def read_dht11():
    try:
        sensor.measure()
        return sensor.humidity(), sensor.temperature()
    except OSError:
        print("Gagal baca DHT11")
        return None, None

def read_ldr():
    return ldr_sensor.read()

def read_mq2():
    return mq2_sensor.read()

# === KIRIM KE UBIDOTS ===
def send_to_ubidots(temperature, humidity, lux, mq2_value):
    try:
        payload = ujson.dumps({
            "temperature": temperature,
            "humidity": humidity,
            "lux": lux,
            "mq2": mq2_value
        })
        response = urequests.post(UBIDOTS_URL, headers=headers, data=payload)
        print("Data terkirim ke Ubidots:", response.text)
        response.close()
    except Exception as e:
        print("Gagal kirim ke Ubidots:", e)

# === KONTROL LED ===
def control_alerts(temperature, mq2_value):
    if mq2_value > 800:
        red_led.on()
        yellow_led.off()
        green_led.off()
    elif temperature < 29:
        green_led.on()
        yellow_led.off()
        red_led.off()
    elif 29 <= temperature <= 30:
        green_led.off()
        yellow_led.on()
        red_led.off()
    else:
        green_led.off()
        yellow_led.off()
        red_led.on()

# === TAMPILKAN DI OLED ===
def show_main_data(humidity, temperature, lux, mq2_value):
    if oled:
        try:
            oled.fill(0)
            if humidity is not None and temperature is not None:
                oled.text('Suhu: {:.1f} C'.format(temperature), 0, 0)
                oled.text('Lembab: {:.1f} %'.format(humidity), 0, 10)
                oled.text('Lux: {}'.format(lux), 0, 20)
                oled.text('MQ2: {}'.format(mq2_value), 0, 30)
            else:
                oled.text('Sensor error!', 0, 0)
            oled.show()
        except Exception as e:
            print("Gagal update OLED:", e)

# === MAIN LOOP ===
connect_wifi()

last_sensor_time = 0
last_servo_time = 0
SENSOR_INTERVAL = 5
SERVO_INTERVAL = 5

while True:
    current_time = time.time()

    # --- Baca sensor dan kirim ke Ubidots ---
    if current_time - last_sensor_time >= SENSOR_INTERVAL:
        humidity, temperature = read_dht11()
        lux = read_ldr()
        mq2_value = read_mq2()

        if temperature is not None:
            control_alerts(temperature, mq2_value)
            send_to_ubidots(temperature, humidity, lux, mq2_value)

        show_main_data(humidity, temperature, lux, mq2_value)
        gc.collect()
        last_sensor_time = current_time

    # --- Ambil data dari Firebase untuk servo ---
    if current_time - last_servo_time >= SERVO_INTERVAL:
        try:
            res = urequests.get(
                "https://servo-control-f3c90-default-rtdb.asia-southeast1.firebasedatabase.app/servo.json",
                timeout=5
            )
            if res.status_code == 200:
                angle = res.json()
                print("Set angle to:", angle)
                set_servo(angle)
            else:
                print("Gagal mendapatkan data, status code:", res.status_code)
            res.close()

        except OSError as e:
            print("Network Error:", e)
        except ValueError as e:
            print("JSON Parse Error:", e)
        except Exception as e:
            print("Unexpected Error:", e)

        last_servo_time = current_time

    time.sleep(0.1)