# ElevenLabs <> Claude Cookbooks

[ElevenLabs](https://elevenlabs.io/)는 voice cloning 및 streaming synthesis 같은 고급 기능을 갖춘 자연스러운 음성 애플리케이션을 만들기 위한 AI 기반 speech-to-text 및 text-to-speech API를 제공합니다.

이 cookbook은 ElevenLabs의 음성 처리와 Claude의 지능적인 응답을 결합하여 낮은 latency의 음성 assistant를 구축하고 실시간 성능을 위해 단계적으로 최적화하는 방법을 보여줍니다.

## 포함된 내용

* **[낮은 latency의 음성 Assistant Notebook](./low_latency_stt_claude_tts.ipynb)** - 음성 assistant 구축을 단계별로 안내하며 streaming을 통해 latency를 최소화하는 다양한 최적화 기법을 보여주는 대화형 tutorial입니다.

* **[WebSocket Streaming Script](./stream_voice_assistant_websocket.py)** - 지속적인 microphone input, 끊김 없는 오디오 재생, WebSocket streaming을 통한 가능한 가장 낮은 latency를 갖춘 production에 바로 사용할 수 있는 대화형 음성 assistant입니다.

## 이 Cookbook 사용 방법

이 cookbook을 최대한 활용하려면 다음 순서로 진행하는 것을 권장합니다:

### 1단계: 환경 설정

1. **Virtual environment 생성:**
   ```bash
   # ElevenLabs 디렉터리로 이동
   cd /path/to/claude-cookbooks/third_party/ElevenLabs

   # Virtual environment 생성
   python -m venv venv

   # 활성화
   source venv/bin/activate  # macOS/Linux에서
   # 또는
   venv\Scripts\activate     # Windows에서
   ```

2. **API key 발급:**
   - **ElevenLabs API key:** [elevenlabs.io/app/developers/api-keys](https://elevenlabs.io/app/developers/api-keys)

     API key 생성 시 다음 최소 권한이 있는지 확인하세요:
     - Text to speech
     - Speech to text
     - Voice 읽기 접근
     - 모델 읽기 접근

   - **Anthropic API key:** [console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys)

3. **환경 구성:**
   ```bash
   cp .env.example .env
   ```

   `.env`를 편집하여 API key를 추가하세요:
   ```
   ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
   ANTHROPIC_API_KEY=sk-ant-api03-...
   ```

4. **Dependency 설치:**
   ```bash
   # venv를 활성화한 상태에서
   pip install -r requirements.txt
   ```

### 2단계: Notebook 따라 하기

**[낮은 latency의 음성 Assistant Notebook](./low_latency_stt_claude_tts.ipynb)**부터 시작하세요. 이 대화형 가이드는 다음을 알려줍니다:

- ElevenLabs로 speech-to-text 전사하는 방법
- Claude 응답을 생성하고 latency를 측정하는 방법
- Streaming이 time-to-first-token을 줄이는 방식
- 더 빠른 오디오 재생을 위해 text-to-speech를 streaming하는 방법
- 서로 다른 streaming 방식 간 trade-off
- WebSocket streaming이 latency와 품질의 최적 균형을 제공하는 이유

Notebook에는 각 단계의 성능 지표와 비교가 포함되어 있어 각 최적화의 영향을 이해하는 데 도움이 됩니다.

### 3단계: Production Script 사용하기

Notebook의 개념을 이해한 뒤 **[WebSocket Streaming Script](./stream_voice_assistant_websocket.py)**를 실행하여 모든 기능을 갖춘 음성 assistant를 경험하세요:

```bash
python stream_voice_assistant_websocket.py
```

**작동 방식:**
1. Enter를 눌러 녹음 시작
2. Microphone에 질문 말하기
3. Enter를 눌러 녹음 중지
4. Assistant가 자연스러운 음성으로 응답
5. 반복하거나 Ctrl+C를 눌러 종료

Script는 다음의 production에 바로 사용할 수 있는 구현을 보여줍니다:
- sounddevice로 실시간 microphone 녹음
- Context를 유지하는 지속적인 대화
- 최소 latency를 위한 WebSocket 기반 streaming
- 매끄러운 재생을 위한 custom 오디오 queue

## 문제 해결

### 오디오의 튀는 소리나 잡음

**증상:** 재생 중 짧은 튀는 소리, 딸깍 소리 또는 오디오 끊김이 가끔 들릴 수 있습니다.

**설명:**

ElevenLabs free tier에 필요한 MP3 형식의 오디오를 script가 사용하기 때문에 발생합니다. MP3 데이터를 실시간 chunk로 streaming하면 FFmpeg가 때때로 decode할 수 없는 불완전한 frame을 받습니다. 일반적으로 다음 상황에서 발생합니다:
- Streaming 시작 시(첫 chunk가 너무 작을 수 있음)
- 짧은 네트워크 지연 중
- 오디오 생성 종료 시(마지막 chunk가 불완전할 수 있음)

Script는 오디오 decoding logic의 try-except 패턴으로 이러한 실패한 chunk를 건너뛰어 자동 처리합니다. 따라서 console에 오류가 나타나지 않지만 짧은 오디오 공백이 생겨 튀는 소리나 딸깍 소리로 나타날 수 있습니다.

**영향:**
- 오디오 재생은 정상적으로 계속됨
- 짧은 튀는 소리나 딸깍 소리는 보통 알아채기 어렵거나 미미함
- WebSocket 연결은 안정적으로 유지됨
- 기능 손실 없음

**해결 방법:**

Free tier에서 MP3 형식을 사용할 때 예상되는 동작입니다. 오디오의 튀는 소리를 완전히 없애려면:
1. 유료 ElevenLabs tier로 업그레이드
2. MP3 대신 `pcm_44100` 형식을 사용하도록 script 수정
3. PCM 형식은 decoding 문제 없이 더 깨끗한 streaming 제공

### API Key 문제

**증상:** `AssertionError: ELEVENLABS_API_KEY is not set` 또는 `AssertionError: ANTHROPIC_API_KEY is not set`

**해결 방법:**
1. `.env.example`을 `.env`로 복사했는지 확인: `cp .env.example .env`
2. `.env`를 편집하여 두 API key가 올바르게 설정되어 있는지 확인
3. API key에 오타나 불필요한 공백이 있는지 확인
4. ElevenLabs key에 필요한 권한이 있는지 확인(1단계 참조)

### Dependency 문제

**증상:** `ImportError: PortAudio library not found` 같은 오류 또는 오디오 재생 실패

**해결 방법:**

**macOS:**
```bash
brew install portaudio ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt-get install portaudio19-dev ffmpeg
```

**Windows:**
- [ffmpeg.org](https://ffmpeg.org/download.html)에서 FFmpeg 설치
- 시스템 PATH에 FFmpeg 추가
- Windows에서 PortAudio는 일반적으로 sounddevice와 함께 자동 설치됨

그런 다음 Python dependency를 다시 설치하세요:
```bash
pip install -r requirements.txt
```

### Microphone 권한

**증상:** `OSError: [Errno -9999] Unanticipated host error` 또는 microphone 접근 불가

**해결 방법:**
- **macOS:** System Preferences → Security & Privacy → Privacy → Microphone에서 Terminal(또는 Python IDE) 활성화
- **Windows:** Settings → Privacy → Microphone에서 Python/Terminal의 microphone 접근 활성화
- **Linux:** 사용자가 `audio` 그룹에 있는지 확인: `sudo usermod -a -G audio $USER`(그런 다음 로그아웃 후 다시 로그인)

Microphone 설정을 테스트하세요:
```bash
python -c "import sounddevice as sd; print(sd.query_devices())"
```

### WebSocket 연결 실패

**증상:** 연결 오류, timeout 또는 stream 중단

**해결 방법:**
1. 인터넷 연결이 안정적인지 확인
2. Firewall이 WebSocket 연결(port 443)을 차단하지 않는지 확인
3. VPN 또는 proxy를 잠시 비활성화해 보기
4. API rate limit을 초과하지 않는지 확인(사용량은 ElevenLabs dashboard 참조)

문제가 계속되면 [ElevenLabs Status](https://status.elevenlabs.io/)에서 서비스 업데이트를 확인하세요.

## 프로젝트 아이디어

음성 assistant에 익숙해졌다면 다음과 같은 흥미로운 프로젝트를 만들 수 있습니다:

- **회의 기록 도구** - 회의를 실시간으로 녹음하고 전사한 뒤 Claude로 대화의 요약, 실행 항목 및 핵심 내용을 생성합니다.

- **언어 학습 Tutor** - 실시간 feedback과 함께 어떤 언어로든 대화를 연습합니다. Claude는 발음을 교정하고 더 나은 표현을 제안하며 실력에 맞게 난이도를 조정할 수 있습니다.

- **대화형 이야기꾼** - Claude가 이야기를 들려주고 말로 한 선택에 응답하는 choose-your-own-adventure 게임을 만들며, 각 역할에 다른 voice character를 사용합니다.

- **Hands-Free Coding Assistant** - 손은 keyboard에 둔 채 코드 변경, bug 또는 기능을 말로 설명합니다. Rubber duck debugging이나 혼자 하는 pair programming에 적합합니다.

- **음성으로 작동하는 Smart Home** - 가정의 기기를 제어하는 자연스러운 대화 interface를 구축합니다. 단순한 on/off 명령 대신 "히터를 켜야 할 만큼 추운가요?" 같은 복잡한 질문을 합니다.

- **개인 음성 일기** - 생각을 말로 남기며 매일 일기를 씁니다. Claude는 항목을 주제별로 정리하고 시간에 따른 기분을 추적하며 필요할 때 관련 과거 항목을 찾아줄 수 있습니다.

## ElevenLabs 더 알아보기

이해를 깊게 하는 데 도움이 되는 자료는 다음과 같습니다:

- [ElevenLabs Platform](https://elevenlabs.io/) - 공식 웹사이트
- [API 문서](https://elevenlabs.io/docs/overview) - 전체 API reference
- [Voice Library](https://elevenlabs.io/voice-library) - 사용 가능한 voice 살펴보기
- [API Playground](https://elevenlabs.io/app/speech-synthesis/text-to-speech) - 대화형으로 voice 테스트
- [Python SDK](https://github.com/elevenlabs/elevenlabs-python) - 공식 Python SDK
