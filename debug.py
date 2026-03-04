import serial
import threading
import time
import sys

# ================= 配置区 =================
SERIAL_PORT = '/dev/tty.usbserial-A9DNSQHP'  # Windows 填 'COM3', 'COM4' 等；Linux 填 '/dev/ttyUSB0'
BAUD_RATE = 9600  # 协议默认 9600


# ==========================================

def read_from_port(ser):
    """后台接收线程：时刻监听功放发来的数据"""
    buffer = ""
    while True:
        try:
            if ser.in_waiting > 0:
                # 读取所有缓冲区数据并解码
                data = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                buffer += data

                # 按照协议的结束符 '*' 进行分句解析
                while '*' in buffer:
                    msg, buffer = buffer.split('*', 1)
                    # 打印功放返回的内容 (加上高亮颜色方便区分)
                    print(f"\n\033[92m[功放返回] {msg}*\033[0m")
                    print("请输入指令 (如 POWER ?): ", end="", flush=True)
            time.sleep(0.05)
        except Exception as e:
            print(f"\n[读取错误] {e}")
            break


def main():
    try:
        # 打开串口
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        print(f"✅ 成功打开串口: {SERIAL_PORT}, 波特率: {BAUD_RATE}")
    except Exception as e:
        print(f"❌ 打开串口失败，请检查端口号是否正确或是否被占用。\n错误信息: {e}")
        sys.exit(1)

    # 启动后台监听线程
    read_thread = threading.Thread(target=read_from_port, args=(ser,), daemon=True)
    read_thread.start()

    print("=" * 50)
    print(" 🛠️  天逸功放 RS232 极简调试助手")
    print("=" * 50)
    print("💡 提示：你不需要输入前缀 ## 和后缀 *。")
    print("例如：")
    print("  输入 POWER ?   (查询电源状态)")
    print("  输入 VOL +465  (设置音量)")
    print("  输入 SI ?      (查询当前输入源)")
    print("输入 exit 退出程序。")
    print("=" * 50)

    while True:
        try:
            cmd = input("\n请输入指令 (如 POWER ?): ").strip()

            if cmd.lower() in ['exit', 'quit']:
                print("退出调试...")
                break
            if not cmd:
                continue

            # 智能补全协议的 ## 和 *
            if not cmd.startswith('#'):
                full_cmd = f"##{cmd}*"
            else:
                full_cmd = cmd  # 如果你自己输入了 ##，就不补全了

            print(f"\033[94m[发送] {full_cmd}\033[0m")
            ser.write(full_cmd.encode('utf-8'))

            # 稍微等一等，让后台线程有时间打印返回值
            time.sleep(0.3)

        except KeyboardInterrupt:
            print("\n退出调试...")
            break

    ser.close()


if __name__ == '__main__':
    main()
