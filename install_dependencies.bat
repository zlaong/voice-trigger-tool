@echo off
echo ���ڰ�װPython����...
python -m pip install --upgrade pip
python -m pip install setuptools wheel
python -m pip install -r requirements.txt

echo ��Ҫ������װ����Ƶ����...
python -m pip install https://github.com/intxcc/pyaudio_portaudio/releases/download/v0.2.14/PyAudio-0.2.14-cp310-cp310-win_amd64.whl

echo ��װ��ɺ����Թ���Ա����������ű���
pause