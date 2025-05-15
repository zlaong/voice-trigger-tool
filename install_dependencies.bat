@echo off
echo 正在安装Python依赖...
python -m pip install --upgrade pip
python -m pip install setuptools wheel
python -m pip install -r requirements.txt

echo 需要单独安装的音频驱动...
python -m pip install https://github.com/intxcc/pyaudio_portaudio/releases/download/v0.2.14/PyAudio-0.2.14-cp310-cp310-win_amd64.whl

echo 安装完成后请以管理员身份运行主脚本！
pause