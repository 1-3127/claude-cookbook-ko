# Claude Skills Cookbook 🚀

문서 생성, data 분석, 업무 자동화를 위해 Claude의 Skills 기능을 사용하는 종합 가이드입니다. 이 cookbook은 Excel, PowerPoint, PDF 생성을 위한 내장 skill을 활용하는 방법과 특화된 workflow를 위한 custom skill 구축 방법을 보여 줍니다.

> **🎯 Skills의 실제 동작 보기:** **[Claude의 파일 생성](https://www.anthropic.com/news/create-files)**에서 Skills가 Claude.ai와 desktop app 안에서 직접 문서를 생성하고 편집하는 능력을 뒷받침하는 방법을 확인하세요!

## Skills란 무엇인가요?

Skills는 특정 작업에 특화된 능력을 Claude에 제공하는 지시, 실행 코드, resource로 구성된 package입니다. Claude가 다음을 위해 동적으로 발견하고 불러올 수 있는 "전문성 package"라고 생각하세요.

- 전문적인 문서 생성(Excel, PowerPoint, PDF, Word)
- 복잡한 data 분석과 시각화 수행
- 회사별 workflow와 branding 적용
- 도메인 전문성으로 업무 과정 자동화

📖 engineering 블로그 [Skills로 agent가 실제 세계에 대응할 수 있게 하기](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)를 읽어 보세요.

## 핵심 기능

- ✨ **Progressive Disclosure Architecture** - 필요할 때만 Skills를 불러와 token 사용 최적화
- 📊 **재무 중심** - 재무와 business analytics의 실제 예제
- 🔧 **Custom Skills 개발** - 자신의 skill 구축과 배포 학습
- 🎯 **Production에 사용할 수 있는 예제** - 즉시 사용하도록 조정할 수 있는 코드

## Cookbook 구조

### 📚 [Notebook 1: Skills 소개](notebooks/01_skills_introduction.ipynb)

빠른 시작 예제로 Claude Skills 기능의 기초를 배웁니다.

- Skills architecture 이해
- beta header로 API 설정
- 첫 Excel spreadsheet 생성
- PowerPoint presentation 생성
- PDF 형식으로 export

### 💼 [Notebook 2: 재무 Application](notebooks/02_skills_financial_applications.ipynb)

실제 재무 data로 강력한 업무 사용 사례를 탐색합니다.

- chart와 pivot table이 있는 재무 dashboard 구축
- Portfolio 분석과 투자 보고
- 형식 간 workflow: CSV → Excel → PowerPoint → PDF
- Token 최적화 전략

### 🔧 [Notebook 3: Custom Skills 개발](notebooks/03_skills_custom_development.ipynb)

자신의 특화 skill을 만드는 기술을 익힙니다.

- 재무 비율 계산기 구축
- 회사 brand 지침 skill 생성
- 고급: 재무 modeling suite
- [모범 사례](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/best-practices)와 보안 고려 사항

## 빠른 시작

### 사전 요구 사항

- Python 3.8 이상
- Anthropic API key([여기서 받기](https://console.anthropic.com/))
- Jupyter Notebook 또는 JupyterLab

### 설치

1. **repository clone**

```bash
git clone https://github.com/anthropics/claude-cookbooks.git
cd claude-cookbooks/skills
```

2. **virtual environment 생성**(권장)

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. **dependency 설치**

```bash
pip install -r requirements.txt
```

4. **API key 설정**

```bash
cp .env.example .env
# .env를 편집하고 ANTHROPIC_API_KEY 추가
```

5. **Jupyter 실행**

```bash
jupyter notebook
```

6. **Notebook 1부터 시작**
   `notebooks/01_skills_introduction.ipynb`를 열고 따라 하세요!

## Sample Data

cookbook은 `sample_data/`에 현실적인 재무 dataset을 포함합니다.

- 📊 **financial_statements.csv** - 분기별 P&L, 재무상태표, 현금흐름 data
- 💰 **portfolio_holdings.json** - 성과 metric이 있는 투자 portfolio
- 📋 **budget_template.csv** - variance 분석이 있는 부서 budget
- 📈 **quarterly_metrics.json** - KPI 및 운영 metric

## 프로젝트 구조

```
skills/
├── notebooks/                    # Jupyter notebook
│   ├── 01_skills_introduction.ipynb
│   ├── 02_skills_financial_applications.ipynb
│   └── 03_skills_custom_development.ipynb
├── sample_data/                  # 재무 dataset
│   ├── financial_statements.csv
│   ├── portfolio_holdings.json
│   ├── budget_template.csv
│   └── quarterly_metrics.json
├── custom_skills/                # 자신의 custom skill
│   ├── financial_analyzer/
│   ├── brand_guidelines/
│   └── report_generator/
├── outputs/                      # 생성한 파일
├── docs/                         # 문서
├── requirements.txt             # Python dependency
├── .env.example                 # 환경 template
└── README.md                    # 이 파일
```

## API 설정

Skills에는 특정 beta header가 필요합니다. notebook이 자동으로 처리하지만 내부적으로는 다음이 이루어집니다.

```python
from anthropic import Anthropic

client = Anthropic(
    api_key="your-api-key",
    default_headers={
        "anthropic-beta": "code-execution-2025-08-25,files-api-2025-04-14,skills-2025-10-02"
    }
)
```

**필수 Beta Header:**

- `code-execution-2025-08-25` - Skills의 code execution 활성화
- `files-api-2025-04-14` - 생성 파일 다운로드에 필요
- `skills-2025-10-02` - Skills 기능 활성화

## 생성한 파일 사용

Skills가 문서(Excel, PowerPoint, PDF 등)를 만들면 응답에 `file_id` attribute를 반환합니다. 파일을 다운로드하려면 **Files API**를 사용해야 합니다.

### 작동 방식

1. code execution 중 **Skills가 파일 생성**
2. 각 생성 파일의 **file_id가 응답에 포함**
3. 실제 파일 content를 다운로드하려면 **Files API 사용**
4. **로컬 저장** 또는 필요에 따라 처리

### 예제: Excel 파일 생성과 다운로드

```python
from anthropic import Anthropic

client = Anthropic(api_key="your-api-key")

# 1단계: skill로 파일 생성
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=4096,
    container={
        "skills": [
            {"type": "anthropic", "skill_id": "xlsx", "version": "latest"}
        ]
    },
    tools=[{"type": "code_execution_20250825", "name": "code_execution"}],
    messages=[{
        "role": "user",
        "content": "Create an Excel file with a simple budget spreadsheet"
    }]
)

# 2단계: 응답에서 file_id 추출
file_id = None
for block in response.content:
    if block.type == "tool_result" and hasattr(block, 'output'):
        # tool 출력에서 file_id 찾기
        if 'file_id' in str(block.output):
            file_id = extract_file_id(block.output)  # file_id parse
            break

# 3단계: Files API로 파일 다운로드
if file_id:
    file_content = client.beta.files.download(file_id=file_id)

    # 4단계: disk에 저장
    with open("outputs/budget.xlsx", "wb") as f:
        f.write(file_content.read())

    print(f"✅ File downloaded: budget.xlsx")
```

### Files API Method

```python
# 파일 content 다운로드(binary)
content = client.beta.files.download(file_id="file_abc123...")
with open("output.xlsx", "wb") as f:
    f.write(content.read())  # .content 대신 .read() 사용

# 파일 metadata 얻기
info = client.beta.files.retrieve_metadata(file_id="file_abc123...")
print(f"Filename: {info.filename}, Size: {info.size_bytes} bytes")  # size 대신 size_bytes 사용

# 모든 파일 나열
files = client.beta.files.list()
for file in files.data:
    print(f"{file.filename} - {file.created_at}")

# 파일 삭제
client.beta.files.delete(file_id="file_abc123...")
```

**중요 참고 사항:**

- 파일은 Anthropic server에 일시 저장됨
- 다운로드한 파일은 로컬 `outputs/` directory에 저장해야 함
- Files API는 Messages API와 같은 API key 사용
- 모든 notebook에 파일 다운로드 helper 함수 포함
- **기본적으로 파일 덮어쓰기** - 셀을 다시 실행하면 기존 파일 교체(출력에 `[overwritten]` 표시)

전체 세부 사항은 [Files API 문서](https://docs.claude.com/en/api/files-content)를 참조하세요.

## 내장 Skills Reference

Claude에는 다음 사전 제작 skill이 있습니다.

| Skill      | ID     | 설명                                                                 |
| ---------- | ------ | --------------------------------------------------------------------------- |
| Excel      | `xlsx` | formula, chart, 서식이 있는 Excel workbook 생성 및 조작 |
| PowerPoint | `pptx` | slide, chart, transition이 있는 전문적인 presentation 생성 |
| PDF        | `pdf`  | 텍스트, table, 이미지가 있는 서식 지정 PDF 문서 생성 |
| Word       | `docx` | 풍부한 서식과 구조가 있는 Word 문서 생성 |

## Custom Skills 생성

Custom skill은 다음 구조를 따릅니다.

```
my_skill/
├── SKILL.md           # 필수: Claude용 지시
├── scripts/           # 선택: Python/JS 코드
│   └── processor.py
└── resources/         # 선택: template, data
    └── template.xlsx
```

[Notebook 3](notebooks/03_skills_custom_development.ipynb)에서 더 알아보세요.

## 일반적인 사용 사례

### 재무 보고

- 자동 분기 보고서
- Budget variance 분석
- 투자 성과 dashboard

### Data 분석

- 복잡한 formula를 사용하는 Excel 기반 analytics
- Pivot table 생성
- 통계 분석 및 시각화

### 문서 자동화

- brand가 적용된 presentation 생성
- 여러 source에서 보고서 취합
- 형식 간 문서 변환

## 성능 팁

1. **Progressive Disclosure 사용**: token 사용 최소화를 위해 단계별 Skills 로딩
2. **Batch 작업**: 한 대화에서 여러 파일 처리
3. **Skill 조합**: 복잡한 workflow에 여러 skill 결합
4. **Cache 재사용**: container ID로 로드된 skill 재사용

## 문제 해결

### 일반적인 문제

**API Key를 찾지 못함**

```
ValueError: ANTHROPIC_API_KEY not found
```

→ `.env.example`을 `.env`로 복사하고 key를 추가했는지 확인

**Skills Beta Header 누락**

```
Error: Skills feature requires beta header
```

→ notebook에 나온 올바른 beta header 사용 확인

**Token Limit 초과**

```
Error: Request exceeds token limit
```

→ 큰 작업을 작은 chunk로 나누거나 progressive disclosure 사용

## Resource

### 문서

- 📖 [Claude API 문서](https://docs.anthropic.com/en/api/messages)
- 🔧 [Skills 문서](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview)

### 지원 문서

- 📚 [Skills로 Claude에게 자신의 작업 방식 가르치기](https://support.claude.com/en/articles/12580051-teach-claude-your-way-of-working-using-skills) - Skills 작업 사용자 가이드
- 🛠️ [대화를 통해 Claude로 skill 만드는 방법](https://support.claude.com/en/articles/12599426-how-to-create-a-skill-with-claude-through-conversation) - Interactive skill 생성 가이드

### Community 및 Support

- 💬 [Claude Support](https://support.claude.com)
- 🐙 [GitHub Issues](https://github.com/anthropics/claude-cookbooks/issues)

## 기여

기여를 환영합니다! 지침은 [CONTRIBUTING.md](../CONTRIBUTING.md)를 참조하세요.

## License

이 cookbook은 MIT License로 제공됩니다. 자세한 내용은 [LICENSE](../LICENSE)를 참조하세요.

## 감사의 말

Skills 기능 개발과 SDK 제공에 대해 Anthropic 팀에 특별히 감사드립니다.

---

**질문이 있나요?** [FAQ](docs/FAQ.md)를 확인하거나 issue를 여세요.

**시작할 준비가 됐나요?** [Notebook 1](notebooks/01_skills_introduction.ipynb)을 열고 멋진 것을 만들어 봅시다! 🎉
