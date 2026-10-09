# Skills Cookbook - Claude Code 가이드

## 프로젝트 개요

문서 생성(Excel, PowerPoint, PDF)을 위한 Claude Skills 기능을 보여 주는 종합 Jupyter notebook cookbook입니다. application에 Skills를 통합하는 방법을 배우는 개발자를 위해 설계되었습니다.

## 빠른 시작 명령

### 환경 설정
```bash
# virtual environment 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# dependency 설치(Skills 지원을 위해 local whl 사용 필수)
pip install -r requirements.txt

# API key 설정
cp .env.example .env
# .env를 편집하고 ANTHROPIC_API_KEY 추가
```

### Notebook 실행
```bash
# Jupyter 실행
jupyter notebook

# 또는 Jupyter extension이 있는 VSCode 사용
# VSCode에서 venv kernel 선택 확인: Cmd+Shift+P → "Python: Select Interpreter"
```

### 테스트 및 검증
```bash
# 환경과 SDK 버전 확인
python -c "import anthropic; print(f'SDK Version: {anthropic.__version__}')"

# outputs directory의 생성 파일 확인
ls -lh outputs/
```

## Architecture 개요

### Directory 구조
```
skills/
├── notebooks/              # 단계적으로 진행하는 Jupyter notebook 3개
│   ├── 01_skills_introduction.ipynb
│   ├── 02_skills_financial_applications.ipynb  # WIP
│   └── 03_skills_custom_development.ipynb      # WIP
├── sample_data/           # 예제의 재무 dataset
├── custom_skills/         # custom skill 개발 영역
├── outputs/               # 생성 파일(xlsx, pptx, pdf)
├── file_utils.py          # Files API helper 함수
└── docs/                  # 구현 추적
```

### 핵심 기술 세부 사항

**Beta API 요구 사항:**
- 모든 Skills 기능은 `client.beta.*` namespace 사용
- 필수 beta header: `code-execution-2025-08-25`, `files-api-2025-04-14`, `skills-2025-10-02`
- `container` parameter와 함께 `client.beta.messages.create()` 사용 필수
- Code execution tool(`code_execution_20250825`) 필수
- `skill_id`를 참조해 사전 제작 Agent skill을 사용하거나 Skills API로 직접 생성 및 업로드

**Files API 통합:**
- Skills는 파일을 생성하고 `file_id` attribute 반환
- 파일 다운로드에 `client.beta.files.download()` 사용 필수
- 파일 정보 조회에 `client.beta.files.retrieve_metadata()` 사용 필수
- `file_utils.py`의 helper 함수가 추출과 다운로드 처리

**내장 Skills:**
- `xlsx` - formula와 chart가 있는 Excel workbook
- `pptx` - PowerPoint presentation
- `pdf` - PDF 문서
- `docx` - Word 문서

## 개발 시 주의할 점

### 1. SDK 버전
**중요**: Skills를 지원하는 Anthropic SDK 버전 0.71.0 이상인지 확인
```bash
pip install anthropic>=0.71.0
# 업그레이드라면 설치 후 Jupyter kernel 재시작!
```

### 2. Beta Namespace 필수
**문제**: `container` parameter를 인식하지 못함, files API 실패
**해결책**: `client.beta.messages.create()`와 `client.beta.files.*` 사용
```python
# ❌ 잘못됨
response = client.messages.create(container={...})
content = client.files.content(file_id)

# ✅ 올바름
response = client.beta.messages.create(container={...})
content = client.beta.files.content(file_id)
```

### 3. Beta Header 배치
**문제**: default_headers에 Skills beta를 설정하면 모든 요청에 code_execution 필요
**해결책**: 대신 요청별 `betas` parameter 사용
```python
# ❌ 잘못됨(모든 요청에 영향)
client = Anthropic(default_headers={"anthropic-beta": "skills-2025-10-02"})

# ✅ 올바름(요청별)
response = client.beta.messages.create(
    betas=["code-execution-2025-08-25", "files-api-2025-04-14", "skills-2025-10-02"],
    ...
)
```

### 4. File ID 추출
**문제**: 응답 구조가 표준 Messages API와 다름
**해결책**: File ID는 `bash_code_execution_tool_result.content.content[0].file_id`에 있음
```python
# file_utils.extract_file_ids() 사용 - beta 응답 구조 처리
from file_utils import extract_file_ids, download_all_files
file_ids = extract_file_ids(response)
```

### 5. Files API Response 객체
**문제**: `'BinaryAPIResponse' object has no attribute 'content'`, `'FileMetadata' object has no attribute 'size'`
**해결책**: 파일 content에 `.read()`, 파일 크기에 `.size_bytes` 사용
```python
# ❌ 잘못됨
file_content = client.beta.files.download(file_id)
with open(path, 'wb') as f:
    f.write(file_content.content)  # .content attribute 없음!

# ✅ 올바름
file_content = client.beta.files.download(file_id)
with open(path, 'wb') as f:
    f.write(file_content.read())  # .read() 사용

# FileMetadata field: id, filename, size_bytes(size가 아님), mime_type, created_at, type, downloadable
metadata = client.beta.files.retrieve_metadata(file_id)
print(f"Size: {metadata.size_bytes} bytes")  # size 대신 size_bytes 사용
```

### 6. Jupyter Kernel 선택
**문제**: 잘못된 Python interpreter = 잘못된 dependency
**해결책**: VSCode/Jupyter에서 항상 venv kernel 선택
- VSCode: Cmd+Shift+P → "Python: Select Interpreter" → venv 선택
- Jupyter: Kernel → Change Kernel → venv 선택

### 7. Module Reload 필수
**문제**: `file_utils.py` 변경이 실행 중인 notebook에 반영되지 않음
**해결책**: kernel 재시작 또는 module reload
```python
import importlib
importlib.reload(file_utils)
```

### 8. 문서 생성 시간
**문제**: 파일 생성은 일반 API 호출보다 오래 걸려 사용자가 셀이 멈췄다고 생각할 수 있음
**실제 관찰 시간:**
- Excel: 약 2분
- PowerPoint: 약 1~2분(간단한 2~3 slide presentation)
- PDF: 약 1~2분

**해결책**: 파일 생성 셀 앞에 명확한 예상 시간 추가
```markdown
**⏱️ 참고**: Excel 생성은 보통 1~2분 걸립니다.
기다려 주세요 - 실행 중 셀에 [*]가 표시됩니다!
```
**중요**: 예제를 간단하고 집중적으로 유지하세요. 범위가 명확한 예제의 생성 시간은 일관되게 1~2분입니다.

## 일반적인 작업

### 새 Notebook Section 추가
1. `01_skills_introduction.ipynb`의 기존 구조 따르기
2. import와 beta header가 있는 setup cell 포함
3. API 호출, 응답 처리, 파일 다운로드 표시
4. error handling 예제 추가
5. `docs/skills_cookbook_plan.md` checklist 갱신

### Sample Data 생성
1. `sample_data/`에 현실적인 재무 data 추가
2. 표 형태는 CSV, 구조화된 것은 JSON 사용
3. header와 올바른 서식 포함
4. notebook에서 pandas로 참조
5. 적절한 파일 크기 유지(<100KB)

### 파일 다운로드 테스트
1. notebook 셀을 실행해 파일 생성
2. 응답에서 file_id 확인
3. `download_all_files()` helper 사용
4. `outputs/` directory의 파일 확인
5. native app에서 파일을 열어 검증

**참고**: 기본적으로 파일을 덮어씁니다. 파일이 이미 있으면 다운로드 요약에 `[overwritten]`이 보입니다. 방지하려면 `overwrite=False`로 설정하세요.

### API Error Debugging
1. SDK 버전 확인: `anthropic.__version__`은 `0.69.0`이어야 함
2. beta header가 요청별로 전달되는지 확인
3. code_execution 도구 포함 확인
4. `print(response)`로 응답 구조 확인
5. `response.stop_reason`에서 오류 세부 사항 찾기

## 테스트 Checklist

notebook 변경을 commit하기 전에:
- [ ] kernel 재시작 및 모든 셀 실행
- [ ] 모든 파일 다운로드 작동 확인
- [ ] outputs/의 생성 파일 확인
- [ ] native app에서 올바르게 열리는지 검증
- [ ] skills_cookbook_plan.md checklist 갱신
- [ ] 새 virtual environment에서 테스트

## Resource

- **API Reference**: https://docs.claude.com/en/api/messages
- **Files API**: https://docs.claude.com/en/api/files-content
- **Skills 문서**: https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview

## 프로젝트별 참고

- **집중 도메인**: 실제 업무 application을 사용하는 Finance 및 Analytics
- **대상 독자**: 중급 개발자와 business analyst
- **Notebook 1**: 완료 및 테스트됨(파일 다운로드 작동)
- **Notebook 2**: 재무 Application - 다음 우선순위
- **Notebook 3**: Custom Skills 개발 - Notebook 2 이후

## 환경 변수

`.env`의 필수 항목:
```bash
ANTHROPIC_API_KEY=your-api-key-here
```

선택 사항(고급 예제용):
```bash
ANTHROPIC_BASE_URL=https://api.anthropic.com  # proxy를 사용하는 경우
```
