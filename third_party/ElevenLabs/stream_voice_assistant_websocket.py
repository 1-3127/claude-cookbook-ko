"""WebSocket Streaming을 사용하는 낮은 latency의 음성 Assistant

최소 latency의 실시간 speech-to-text, Claude 통합 및 text-to-speech를
보여주는 production에 바로 사용할 수 있는 대화형 음성 assistant.

사용법:
    1. 환경 변수 설정:
       - .env.example을 .env로 복사
       - .env에 API key 추가:
         * ElevenLabs API key 발급: https://elevenlabs.io/app/developers/api-keys
         * Anthropic API key 발급: https://console.anthropic.com/settings/keys

    2. Dependency 설치:
       pip install -r requirements.txt

    3. Script 실행:
       python stream_voice_assistant_websocket.py

    4. 상호 작용 흐름:
       - Enter를 눌러 녹음 시작
       - Microphone에 말하기
       - Enter를 눌러 녹음 중지
       - Claude가 합성 음성으로 응답
       - 반복하거나 Ctrl+C를 눌러 종료

주요 최적화:
- Claude에서 도착한 텍스트 chunk를 즉시 TTS로 전송
- 문장 buffering 불필요 - 오디오 생성 즉시 시작
- Free tier 계정과 호환되는 MP3 오디오 형식
- Pre-buffering을 포함한 연속 오디오 streaming으로 잡음 방지
"""

import base64
import io
import json
import os
import threading
import time

import anthropic
import elevenlabs
import numpy as np
import sounddevice as sd
import websocket
from dotenv import load_dotenv
from pydub import AudioSegment
from scipy.io import wavfile

# .env 파일에서 환경 변수 로드
load_dotenv()

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

assert ELEVENLABS_API_KEY is not None, (
    "ERROR: ELEVENLABS_API_KEY not found. Please copy .env.example to .env and add your API keys."
)
assert ANTHROPIC_API_KEY is not None, (
    "ERROR: ANTHROPIC_API_KEY not found. Please copy .env.example to .env and add your API keys."
)

SAMPLE_RATE = 44100  # 녹음용 오디오 sample rate
CHANNELS = 1  # Mono 오디오

elevenlabs_client = elevenlabs.ElevenLabs(
    api_key=ELEVENLABS_API_KEY, base_url="https://api.elevenlabs.io"
)

anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# 사용 가능한 voice를 가져와 첫 번째 선택
voices = elevenlabs_client.voices.search().voices
selected_voice = voices[0]
VOICE_ID = selected_voice.voice_id
print(f"Using voice: {selected_voice.name} (ID: {VOICE_ID})")

# TTS 설정
TTS_MODEL_ID = "eleven_turbo_v2_5"  # 빠르고 latency가 낮은 모델
TTS_OUTPUT_FORMAT = "mp3_44100_128"  # MP3 형식(free tier 호환)


class AudioQueue:
    """최소 latency로 지속적인 오디오 재생을 관리합니다.

    Callback 기반 streaming으로 sounddevice OutputStream 사용:
    - 들어오는 오디오 chunk용 byte buffer 유지
    - Stream callback이 buffer에서 실시간으로 읽기
    - Pre-buffering으로 buffer underrun의 잡음 방지
    """

    # 오디오 buffer 설정 constant
    PRE_BUFFER_SIZE = 8192  # 재생 시작 전 최소 buffer 크기(초기 잡음 방지)
    BUFFER_CLEANUP_THRESHOLD = 100000  # 메모리 증가 방지를 위한 buffer 정리 전 byte 수
    REMAINING_BYTES_THRESHOLD = 1000  # 재생이 사실상 완료된 것으로 간주할 byte 수

    def __init__(self):
        self.buffer = bytearray()
        self.buffer_lock = threading.Lock()
        self.playing = False
        self.stream = None
        self.first_audio_played = False
        self.first_audio_time = None
        self.sample_rate = 44100
        self.channels = 2
        self.finished = False
        self.read_position = 0

    def add(self, audio_data):
        """재생 buffer에 MP3 오디오 chunk를 추가합니다.

        Args:
            audio_data: 원시 MP3 오디오 byte
        """
        try:
            # MP3를 PCM으로 decode
            audio_segment = AudioSegment.from_mp3(io.BytesIO(audio_data))

            # numpy array로 변환
            samples = np.array(audio_segment.get_array_of_samples(), dtype=np.int16)
            samples = samples.astype(np.float32) / 32768.0

            if not self.playing:
                self.sample_rate = audio_segment.frame_rate
                self.channels = audio_segment.channels

            # Channel 수에 따라 reshape
            if self.channels > 1:
                samples = samples.reshape((-1, self.channels))
            else:
                samples = samples.reshape((-1, 1))

            with self.buffer_lock:
                self.buffer.extend(samples.tobytes())

            # Pre-buffering 후 재생 시작
            if not self.playing and len(self.buffer) >= self.PRE_BUFFER_SIZE:
                self.start_playback()
        except Exception:  # noqa: S110
            # Decode에 실패한 잘못된 MP3 chunk를 조용히 건너뛰기
            # Chunk에 불완전한 frame이 포함될 수 있으므로 MP3 데이터를 실시간으로
            # streaming할 때 흔히 발생합니다. 이를 건너뛰면 console 오류를 방지하지만
            # 짧은 오디오 튀는 소리가 날 수 있습니다. 이를 없애려면 유료 ElevenLabs tier로 업그레이드하고
            # MP3 대신 pcm_44100 형식을 사용하세요.
            pass

    def start_playback(self):
        """오디오 output stream을 시작합니다."""
        self.playing = True

        def callback(outdata, frames, _time_info, _status):
            """Output buffer를 채우기 위해 sounddevice가 호출합니다."""
            if not self.first_audio_played:
                self.first_audio_time = time.time()
                self.first_audio_played = True

            bytes_needed = frames * self.channels * 4

            with self.buffer_lock:
                bytes_available = len(self.buffer) - self.read_position
                bytes_to_read = min(bytes_needed, bytes_available)

                if bytes_to_read > 0:
                    data = bytes(
                        self.buffer[self.read_position : self.read_position + bytes_to_read]
                    )
                    self.read_position += bytes_to_read

                    if self.read_position > self.BUFFER_CLEANUP_THRESHOLD:
                        self.buffer = self.buffer[self.read_position :]
                        self.read_position = 0
                else:
                    data = b""

            if len(data) > 0:
                audio_array = np.frombuffer(data, dtype=np.float32)
                audio_array = audio_array.reshape((-1, self.channels))

                samples_to_write = min(len(audio_array), frames)
                if samples_to_write > 0:
                    outdata[:samples_to_write] = audio_array[:samples_to_write]
                if samples_to_write < frames:
                    outdata[samples_to_write:] = 0
            else:
                outdata[:] = 0

        self.stream = sd.OutputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            callback=callback,
            dtype=np.float32,
            blocksize=2048,
        )
        self.stream.start()

    def wait_until_done(self):
        """Buffer에 있는 모든 오디오 재생이 끝날 때까지 block합니다."""
        while True:
            with self.buffer_lock:
                remaining = len(self.buffer) - self.read_position
            if remaining < self.REMAINING_BYTES_THRESHOLD:
                break
            time.sleep(0.1)

        time.sleep(0.5)

        if self.stream:
            self.stream.stop()
            self.stream.close()
        self.playing = False


def record_audio():
    """Enter로 시작하고 중지하여 microphone에서 오디오를 녹음합니다.

    Returns:
        io.BytesIO: WAV 형식 오디오 buffer
    """
    input("Press Enter to start recording...")
    print("Recording... Press Enter to stop.")
    recording = []

    def callback(indata, _frames, _time_info, _status):
        """녹음 목록에 오디오 chunk를 추가하는 callback."""
        recording.append(indata.copy())

    # 오디오 input stream 생성
    stream = sd.InputStream(
        samplerate=SAMPLE_RATE, channels=CHANNELS, callback=callback, dtype=np.float32
    )

    stream.start()
    input()  # Enter key 입력 대기
    stream.stop()
    stream.close()

    # 모든 오디오 chunk를 하나의 array로 결합
    audio_data = np.concatenate(recording, axis=0)

    # float32 오디오를 int16 WAV 형식으로 변환
    audio_buffer = io.BytesIO()
    audio_int16 = (audio_data * 32767).astype(np.int16)
    wavfile.write(audio_buffer, SAMPLE_RATE, audio_int16)
    audio_buffer.seek(0)

    return audio_buffer


def transcribe_audio(audio_buffer):
    """ElevenLabs speech-to-text로 오디오를 전사합니다.

    Args:
        audio_buffer: WAV 형식 오디오 데이터

    Returns:
        str: 전사된 텍스트
    """
    print("\nTranscribing...")

    # Speech-to-text에 ElevenLabs Scribe 모델 사용
    transcription = elevenlabs_client.speech_to_text.convert(
        file=audio_buffer, model_id="scribe_v1"
    )

    print(f"Transcription: {transcription.text}")

    return transcription.text


def stream_claude_and_synthesize_ws(messages, audio_queue):
    """Claude 응답을 ElevenLabs WebSocket으로 직접 streaming합니다.

    텍스트 chunk는 buffering 없이 즉시 TTS로 전송하여,
    첫 token부터 첫 오디오까지의 latency를 최소화합니다.

    Args:
        messages: 대화 이력(message dict 목록)
        audio_queue: AudioQueue instance

    Returns:
        str: Assistant의 전체 응답 텍스트
    """
    print("\nStreaming Claude response...\n")

    ws_url = f"wss://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}/stream-input?model_id={TTS_MODEL_ID}&output_format={TTS_OUTPUT_FORMAT}"

    ws_connected = False
    ws_finished = False

    def on_message(ws, message):
        """들어오는 WebSocket message를 처리합니다."""
        nonlocal ws_finished
        data = json.loads(message)

        if "audio" in data and data["audio"]:
            audio_bytes = base64.b64decode(data["audio"])
            audio_queue.add(audio_bytes)

        # 생성이 완료되었는지 확인
        if data.get("isFinal"):
            ws_finished = True

    def on_error(ws, error):
        print(f"\nWebSocket error: {error}")

    def on_close(ws, close_status_code, close_msg):
        """WebSocket 연결 종료를 처리합니다."""
        if close_status_code or close_msg:
            print(f"\nWebSocket closed with status {close_status_code}: {close_msg}")

    def on_open(ws):
        nonlocal ws_connected
        ws_connected = True

        initial_message = {
            "text": " ",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.8},
            "xi_api_key": ELEVENLABS_API_KEY,
        }
        ws.send(json.dumps(initial_message))

    ws = websocket.WebSocketApp(
        ws_url, on_message=on_message, on_error=on_error, on_close=on_close, on_open=on_open
    )

    ws_thread = threading.Thread(target=ws.run_forever)
    ws_thread.daemon = True
    ws_thread.start()

    while not ws_connected:
        time.sleep(0.01)

    response_text = ""

    # Claude 응답을 streaming하고 각 chunk를 WebSocket으로 전송
    with anthropic_client.messages.stream(
        model="claude-haiku-4-5",
        max_tokens=1000,
        temperature=0,
        system="""You are a helpful voice assistant. Your responses will be converted to speech using ElevenLabs.
Do not write in markdown, as it cannot be read aloud properly.""",
        messages=messages,
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
            response_text += text
            ws.send(json.dumps({"text": text, "try_trigger_generation": True}))

    ws.send(json.dumps({"text": ""}))

    # WebSocket의 완료 신호 대기
    while not ws_finished:
        time.sleep(0.1)

    ws.close()
    ws_thread.join(timeout=2)
    print()

    return response_text


def main():
    """주 실행 loop."""
    print("=== Low Latency Voice Assistant (WebSocket) ===\n")
    print("Press Ctrl+C to exit\n")

    conversation_history = []

    try:
        while True:
            audio_buffer = record_audio()
            enter_pressed_time = time.time()

            transcription = transcribe_audio(audio_buffer)
            conversation_history.append({"role": "user", "content": transcription})

            audio_queue = AudioQueue()
            response_text = stream_claude_and_synthesize_ws(conversation_history, audio_queue)
            conversation_history.append({"role": "assistant", "content": response_text})

            audio_queue.wait_until_done()

            if audio_queue.first_audio_time:
                time_to_first_audio = audio_queue.first_audio_time - enter_pressed_time
                print(f"Time to first audio: {time_to_first_audio:.2f}s\n")
    except KeyboardInterrupt:
        print("\n\nExiting...")


if __name__ == "__main__":
    main()
