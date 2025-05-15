from vosk import Model, KaldiRecognizer
import pyaudio
from pynput.keyboard import Controller, Key
import os
import time
import threading
import ctypes
import sys
import json
import signal
import atexit

# 检查管理员权限
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if not is_admin():
    print("请以管理员身份重新运行此脚本！")
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, __file__, None, 1)
    sys.exit()

# 初始化键盘控制器
keyboard = Controller()

# 配置参数
# 配置参数
CONFIG = {
    # 语音触发关键词（需完整说出该词才会触发）
    "keyword": "关注",  
    # 触发后的冷却时间（秒），防止短时间内重复触发
    "cooldown": 10,  
    # 延迟触发配置
    "delay_trigger": {
        "enable": True,   # 是否启用延迟触发功能
        "delay": 5,       # 延迟触发等待时间（秒）
        "hotkey": ['ctrl', '2']  # 延迟触发的快捷键组合
    },
    # 快捷键配置
    "hotkeys": {
        "main": ['ctrl', '1'],  # 主快捷键（立即触发的组合键）
    },
    # 语音识别模型路径（需下载中文模型并解压到此路径）
    "model_path": "vosk-model-cn-0.22",   
    # 音频采样率（需与模型匹配，通常为16000或8000）
    "sample_rate": 16000,  
    # 流式处理模式开关（True实时处理语音流，False等待完整语句）
    "streaming_mode": True,  
    # 部分结果处理阈值（当实时识别的分词数量超过该值时进行处理）
    "partial_threshold": 3,  
    # 音频流缓冲区大小（数值越小延迟越低，但CPU占用越高）
    "buffer_size": 1024,  
}

def cleanup():
    if 'stream' in globals():
        stream.stop_stream()
        stream.close()
    print("资源已清理")

atexit.register(cleanup)
signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))

# 状态跟踪变量
LAST_TRIGGER_TIME = 0
LOCK = threading.Lock()

def select_microphone():
    """选择音频输入设备"""
    audio = pyaudio.PyAudio()
    print("\n检测到以下音频输入设备：")
    
    valid_devices = []
    for i in range(audio.get_device_count()):
        dev_info = audio.get_device_info_by_index(i)
        if dev_info['maxInputChannels'] > 0:
            valid_devices.append((i, dev_info['name']))
            print(f"[{i}] {dev_info['name']}")
    
    while True:
        try:
            choice = int(input("\n请输入设备前的数字编号："))
            if any(dev[0] == choice for dev in valid_devices):
                return choice
            print("× 无效的编号，请重新输入")
        except ValueError:
            print("× 请输入数字")

def trigger_hotkey(keys):
    """触发快捷键"""
    try:
        modifier = getattr(Key, keys[0])
        main_key = keys[1]
        
        with keyboard.pressed(modifier):
            keyboard.press(main_key)
            time.sleep(0.1)
            keyboard.release(main_key)
        
        print(f"✓ 已触发 {keys[0].upper()}+{main_key.upper()}")
    except Exception as e:
        print(f"! 触发失败：{str(e)}")

def check_cooldown():
    """冷却时间检查"""
    global LAST_TRIGGER_TIME
    with LOCK:
        elapsed = time.time() - LAST_TRIGGER_TIME
        if elapsed < CONFIG['cooldown']:
            remaining = CONFIG['cooldown'] - elapsed
            print(f"⏳ 冷却中（剩余{remaining:.1f}秒）")
            return False
        return True

def delayed_trigger():
    """延迟触发逻辑"""
    time.sleep(CONFIG['delay_trigger']['delay'])
    print(f"⚡ 延迟{CONFIG['delay_trigger']['delay']}秒后触发备用快捷键")
    trigger_hotkey(CONFIG['delay_trigger']['hotkey'])

def audio_listener():
    """本地语音识别线程"""
    global LAST_TRIGGER_TIME
    global stream, p  # 声明为全局变量
    
    # 加载Vosk中文模型
    if not os.path.exists(CONFIG['model_path']):
        raise FileNotFoundError(f"未找到语音模型，请下载并解压到: {CONFIG['model_path']}")
    
    model = Model(CONFIG['model_path'])
    recognizer = KaldiRecognizer(model, CONFIG['sample_rate'])
    
    p = pyaudio.PyAudio()
    stream = p.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=CONFIG['sample_rate'],
        input=True,
        frames_per_buffer=CONFIG['buffer_size'],
        input_device_index=selected_device
    )

    # 创建双缓冲队列
    partial_buffer = []

    print("监听已启动...")
    while True:
        data = stream.read(CONFIG['buffer_size'])
        
        # 流式处理核心逻辑
        if recognizer.AcceptWaveform(data):
            final_result = json.loads(recognizer.Result())
            text = final_result.get('text', '')
            print(f"最终结果：{text}")
            process_keyword(text)
        else:
            # 获取实时部分结果
            partial_result = json.loads(recognizer.PartialResult())
            partial_text = partial_result.get('partial', '')
            
            # 智能分段处理
            if len(partial_text.split()) > CONFIG['partial_threshold']:
                print(f"部分结果：{partial_text}")
                partial_buffer.append(partial_text)
                
                # 合并缓冲区并检查关键词
                merged_text = ' '.join(partial_buffer)
                if CONFIG['keyword'] in merged_text:
                    process_keyword(merged_text)
                    partial_buffer.clear()

def process_keyword(text):
    """优化后的关键词处理"""
    global LAST_TRIGGER_TIME
    
    if CONFIG['keyword'] in text:
        if check_cooldown():
            with LOCK:
                LAST_TRIGGER_TIME = time.time()
            trigger_hotkey(CONFIG['hotkeys']['main'])
            
            # 延迟触发使用独立计时器
            if CONFIG['delay_trigger']['enable']:
                threading.Timer(
                    CONFIG['delay_trigger']['delay'],
                    trigger_hotkey,
                    args=[CONFIG['delay_trigger']['hotkey']]
                ).start()

if __name__ == "__main__":
    if not is_admin():
        print("请右键点击脚本，选择'以管理员身份运行'")
        sys.exit(1)
        
    try:
        # 选择音频输入设备
        selected_device = select_microphone()
        
        # 启动监听线程
        listener_thread = threading.Thread(target=audio_listener)
        listener_thread.daemon = True
        listener_thread.start()
        
        print(f"监听已启动 | 冷却时间：{CONFIG['cooldown']}秒 | 按Ctrl+C退出")
        while True:
            time.sleep(1)
    
        
            
    except KeyboardInterrupt:
        print("\n正在释放资源...")
        if 'stream' in globals() and stream.is_active():
            stream.stop_stream()
            stream.close()
        if 'p' in globals():
            p.terminate()  # 必须调用才能释放ASIO驱动
        sys.exit(0)
    except Exception as e:
        print(f"! 发生错误：{str(e)}")