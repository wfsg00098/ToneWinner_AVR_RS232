import paho.mqtt.client as mqtt
import socket
import serial  # 新增：物理串口通信库
import threading
import time
import json

# ================= 全局配置区 =================

# 1. 模式切换开关 ('TCP' 或 'SERIAL')
CONNECTION_MODE = 'SERIAL'  # <--- 在这里选择你要用的硬件方式

# 2. MQTT 服务器配置
MQTT_BROKER = "192.168.50.98"  # HA 的 IP
MQTT_PORT = 1883
MQTT_USER = "mqtt"
MQTT_PASS = "mqtt"

# 3. 网络串口配置 (当 CONNECTION_MODE = 'TCP' 时生效)
TCP_IP = "192.168.x.x"  # 串口服务器 IP
TCP_PORT = 8234  # 串口服务器端口

# 4. USB物理串口配置 (当 CONNECTION_MODE = 'SERIAL' 时生效)
SERIAL_PORT = "/dev/ttyUSB0"  # Linux 下通常是 /dev/ttyUSB0，Windows 下是 COM3 等
BAUD_RATE = 9600  # 协议文档标明的波特率
# ==============================================

# 功放的“身份证”(用于 MQTT 自动发现)
DEVICE_INFO = {
    "identifiers": ["tonewinner_amp_ad7300_hd"],
    "name": "天逸功放",
    "manufacturer": "ToneWinner",
    "model": "AD-7300HD"
}

amp_conn = None  # 全局连接对象 (可能是 socket，也可能是 serial 实例)

INPUT_SOURCES = ["HDMI 1", "HDMI 2", "HDMI 3", "HDMI 4", "HDMI 5", "HDMI 6", "HDMI ARC"]

AUDIO_MODE_DISPLAY = ['直通', '纯音', '2声道', '多声道', 'Dolby 音效', 'DTS 音效']
AUDIO_SEND_MODE = ['DIRECT', 'PURE', 'STEREO', 'ALLSTEREO', 'PLIIMOVIE', 'NEO6CINEMA']
AUDIO_RECV_MODE = ['DITECT', 'PURE', 'STEREO', 'ALLSTEREO', 'PLIIMOVIE', 'NEO6CINEMA']

def send_mqtt_discovery(client):
    """向 HA 自动广播设备的 JSON 配置"""
    print("[系统] 正在广播 MQTT 自动发现配置...")

    # 电源状态 (Sensor)
    power_sensor = {
        "name": "当前电源状态", "unique_id": "tw_amp_power_sens",
        "state_topic": "amp/power/state", "icon": "mdi:information-outline", "device": DEVICE_INFO
    }
    client.publish("homeassistant/sensor/tw_amp/power_status/config", json.dumps(power_sensor), retain=True)

    # 音量状态 (Sensor)
    volume_sensor = {
        "name": "当前主音量", "unique_id": "tw_amp_volume_sens",
        "state_topic": "amp/volume/state", "unit_of_measurement": "Vol",  # 可以加上单位
        "icon": "mdi:volume-medium", "device": DEVICE_INFO
    }
    client.publish("homeassistant/sensor/tw_amp/volume_status/config", json.dumps(volume_sensor), retain=True)

    # 输入源状态 (Sensor)
    source_sensor = {
        "name": "当前输入源", "unique_id": "tw_amp_source_sens",
        "state_topic": "amp/source/state", "icon": "mdi:import", "device": DEVICE_INFO
    }
    client.publish("homeassistant/sensor/tw_amp/source_status/config", json.dumps(source_sensor), retain=True)

    # 音效模式状态 (Sensor)
    mode_sensor = {
        "name": "当前音效模式", "unique_id": "tw_amp_mode_sens",
        "state_topic": "amp/mode/state", "icon": "mdi:surround-sound", "device": DEVICE_INFO
    }
    client.publish("homeassistant/sensor/tw_amp/sound_mode/config", json.dumps(mode_sensor), retain=True)

    # 主电源
    power_config = {
        "name": "主电源", "unique_id": "tw_amp_power_01",
        "command_topic": "amp/power/set", "state_topic": "amp/power/state",
        "payload_on": "ON", "payload_off": "OFF", "icon": "mdi:power", "device": DEVICE_INFO
    }
    client.publish("homeassistant/switch/tw_amp/power/config", json.dumps(power_config), retain=True)

    # 主音量
    volume_config = {
        "name": "主音量", "unique_id": "tw_amp_volume_01",
        "command_topic": "amp/volume/set", "state_topic": "amp/volume/state",
        "min": 0, "max": 80, "step": 0.5, "icon": "mdi:volume-high", "device": DEVICE_INFO
    }
    client.publish("homeassistant/number/tw_amp/volume/config", json.dumps(volume_config), retain=True)

    volume_box = {
        "name": "主音量设置", "unique_id": "tw_amp_volume_box",
        "command_topic": "amp/volume/set", "state_topic": "amp/volume/state",
        "min": 0, "max": 80, "step": 0.5,
        "mode": "box",  # <--- 强制显示为数字输入框
        "icon": "mdi:form-textbox", "device": DEVICE_INFO
    }
    client.publish("homeassistant/number/tw_amp/volume_box/config", json.dumps(volume_box), retain=True)


    # 静音
    mute_config = {
        "name": "静音开关", "unique_id": "tw_amp_mute_01",
        "command_topic": "amp/mute/set", "state_topic": "amp/mute/state",
        "payload_on": "ON", "payload_off": "OFF", "icon": "mdi:volume-mute", "device": DEVICE_INFO
    }
    client.publish("homeassistant/switch/tw_amp/mute/config", json.dumps(mute_config), retain=True)

    # 输入源
    source_config = {
        "name": "输入源", "unique_id": "tw_amp_source_01",
        "command_topic": "amp/source/set", "state_topic": "amp/source/state",
        "options": INPUT_SOURCES,
        "icon": "mdi:hdmi-port", "device": DEVICE_INFO
    }
    client.publish("homeassistant/select/tw_amp/source/config", json.dumps(source_config), retain=True)

    # 音频模式
    audio_mode_config = {
        "name": "音频模式", "unique_id": "tw_amp_mode_01",
        "command_topic": "amp/mode/set", "state_topic": "amp/mode/state",
        "options": AUDIO_MODE_DISPLAY,
        "icon": "mdi:surround-sound", "device": DEVICE_INFO
    }
    client.publish("homeassistant/select/tw_amp/mode/config", json.dumps(audio_mode_config), retain=True)


def send_to_amp(cmd):
    """根据所选模式，向功放发送指令"""
    global amp_conn
    if not amp_conn: return

    full_cmd = f"##{cmd}*".encode('utf-8')
    try:
        if CONNECTION_MODE == 'TCP':
            amp_conn.sendall(full_cmd)
        elif CONNECTION_MODE == 'SERIAL':
            amp_conn.write(full_cmd)
        print(f"[发往功放] {full_cmd.decode('utf-8')}")
    except Exception as e:
        print(f"[发送失败] {e}")
        amp_conn = None  # 触发重连机制


def on_message(client, userdata, msg):
    """接收 HA 指令"""
    topic = msg.topic
    payload = msg.payload.decode('utf-8')

    if topic == "amp/power/set":
        send_to_amp(f"POWER {payload}")
    elif topic == "amp/volume/set":
        try:
            vol_val = float(payload)
            stepped_vol = round(vol_val * 2) / 2.0
            send_to_amp(f"VOL {stepped_vol:.1f}")
        except ValueError:
            pass
    elif topic == "amp/source/set":
        send_to_amp(f"SI 0{INPUT_SOURCES.index(payload)}")
    elif topic == "amp/mute/set":
        send_to_amp(f"MUTE {payload}")
    elif topic == "amp/mode/set":
        send_to_amp(f"MODE {AUDIO_SEND_MODE[AUDIO_MODE_DISPLAY.index(payload)]}")


def on_connect(client, userdata, flags, rc):
    print(f"[系统] 已连接到 MQTT 代理，状态码: {rc}")
    send_mqtt_discovery(client)
    client.subscribe("amp/power/set")
    client.subscribe("amp/volume/set")
    client.subscribe("amp/source/set")
    client.subscribe("amp/mute/set")
    client.subscribe("amp/mode/set")


def listen_to_amp(mqtt_client):
    """维持连接并读取数据流"""
    global amp_conn
    buffer = ""
    while True:
        try:
            # === 1. 建立连接 ===
            if CONNECTION_MODE == 'TCP':
                amp_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                amp_conn.connect((TCP_IP, TCP_PORT))
                print(f"[系统] 成功连接 TCP 串口服务器 {TCP_IP}:{TCP_PORT}")
            elif CONNECTION_MODE == 'SERIAL':
                # timeout=1 防止物理串口阻塞死锁
                amp_conn = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
                print(f"[系统] 成功打开 USB 物理串口 {SERIAL_PORT}")

            # 刚连上时主动拉取状态
            send_to_amp("POWER ?")
            send_to_amp("VOL ?")
            send_to_amp("SI ?")
            send_to_amp("MUTE ?")
            send_to_amp("MODE ?")

            # === 2. 持续读取数据 ===
            while True:
                if CONNECTION_MODE == 'TCP':
                    data = amp_conn.recv(1024).decode('utf-8')
                    if not data: raise Exception("TCP 远程端断开了连接")
                elif CONNECTION_MODE == 'SERIAL':
                    # 读取串口缓冲区所有数据，如果没有则等待 timeout 后返回空
                    raw_data = amp_conn.read(amp_conn.in_waiting or 1)
                    if not raw_data: continue  # 只是超时，串口没断，继续循环
                    data = raw_data.decode('utf-8', errors='ignore')

                buffer += data
                # 解析粘包，以 '*' 分割
                while '*' in buffer:
                    msg, buffer = buffer.split('*', 1)
                    if msg.startswith('#'):
                        parse_amp_status(msg.lstrip('#'), mqtt_client)

        except Exception as e:
            print(f"[系统] 功放连接断开，5秒后重试... ({e})")
            if amp_conn:
                try:
                    amp_conn.close()
                except:
                    pass
                amp_conn = None
            time.sleep(5)


def parse_amp_status(msg, mqtt_client):
    """解析功放状态协议"""
    print(f'[功放返回] {msg}')
    parts = msg.strip().split(' ', 1)
    if len(parts) < 2: return
    cmd, param = parts[0], parts[1]

    if cmd == "POWER":
        mqtt_client.publish("amp/power/state", param, retain=True)
    elif cmd == "VOL":
        try:
            vol_float = float(param.replace('+', ''))
            mqtt_client.publish("amp/volume/state", str(vol_float), retain=True)
        except ValueError:
            pass
    elif cmd == "SI":
        current_source = "UNKNOWN"
        try:
            current_source = INPUT_SOURCES[int(param[:2])]
        except:
            pass
        if current_source != "UNKNOWN":
            mqtt_client.publish("amp/source/state", current_source, retain=True)
    elif cmd == "MUTE":
        mqtt_client.publish("amp/mute/state", param, retain=True)
    elif cmd == "MODE":
        current_mode = 'UNKNOWN'
        try:
            current_mode = AUDIO_MODE_DISPLAY[AUDIO_RECV_MODE.index(param)]
        except:
            pass
        if current_mode != "UNKNOWN":
            mqtt_client.publish("amp/mode/state", current_mode, retain=True)

if __name__ == "__main__":
    client = mqtt.Client()
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.on_connect = on_connect
    client.on_message = on_message

    threading.Thread(target=listen_to_amp, args=(client,), daemon=True).start()

    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_forever()

