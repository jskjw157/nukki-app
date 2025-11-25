# 누끼 메이커 ✨

AI 기반 제품 이미지 배경 제거 데스크톱 앱입니다.

**rembg**로 고품질 배경 제거를 수행하고, **Google Gemini API**로 이미지를 분석 및 후처리합니다.

## 주요 기능

- 🖼️ **다중 이미지 처리** - 여러 이미지를 한 번에 선택하여 일괄 처리
- 🎯 **고품질 배경 제거** - rembg 기반 정밀한 누끼
- 🤖 **AI 후처리** - Gemini API 분석 기반 가장자리 개선 (선택적)
- 👁️ **실시간 미리보기** - 처리 전후 이미지 비교
- 💾 **일괄 저장** - PNG 형식으로 투명 배경 유지

## 스크린샷

```
┌─────────────────────────────────────────────────────────────┐
│  ✨ 누끼 메이커          AI 기반 제품 이미지 배경 제거     ⚙️  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐      │
│   │ 이미지1  │  │ 이미지2  │  │ 이미지3  │  │ 이미지4  │      │
│   │  [🖼️]   │  │  [🖼️]   │  │  [🖼️]   │  │  [🖼️]   │      │
│   │ 완료 ✓  │  │ 완료 ✓  │  │ 처리중..│  │  대기중  │      │
│   └─────────┘  └─────────┘  └─────────┘  └─────────┘      │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│ ☑️ Gemini AI 후처리 사용     🗑️ 초기화  💾 모두 저장  🚀 누끼 따기 │
└─────────────────────────────────────────────────────────────┘
```

## 설치 방법

### 1. 요구 사항

- Python 3.10 이상
- macOS / Windows / Linux

### 2. 의존성 설치

```bash
cd nukki-app
pip install -r requirements.txt
```

### 3. 실행

```bash
python main.py
```

## Google Gemini API 키 발급

Gemini AI 후처리 기능을 사용하려면 API 키가 필요합니다.

### 발급 방법

1. [Google AI Studio](https://aistudio.google.com/) 접속
2. Google 계정으로 로그인
3. 좌측 메뉴에서 **"Get API Key"** 클릭
4. **"Create API Key"** 버튼 클릭
5. 프로젝트 선택 또는 새 프로젝트 생성
6. 생성된 API 키 복사

### 앱에서 API 키 설정

1. 앱 실행 후 우측 상단 **"⚙️ API 설정"** 버튼 클릭
2. 복사한 API 키 붙여넣기
3. 확인 버튼 클릭

> **참고**: API 키는 앱 종료 시 초기화됩니다. 매번 실행 시 다시 입력해야 합니다.

## 사용 방법

### 1. 이미지 추가

- **파일 선택**: "📂 이미지 선택" 버튼 클릭 후 이미지 파일 선택 (다중 선택 가능)
- 지원 형식: PNG, JPG, JPEG, WEBP, BMP

### 2. 옵션 설정

- **Gemini AI 후처리**: 체크하면 배경 제거 후 Gemini가 이미지를 분석하고 PIL 기반으로 가장자리를 자동 개선합니다
  - ⚠️ API 키 필요 ([Google AI Studio](https://aistudio.google.com/app/api-keys)에서 발급)
  - 처리 시간이 더 소요됩니다

### 3. 처리 시작

- **"🚀 누끼 따기"** 버튼 클릭
- 각 이미지 카드에서 실시간으로 처리 상태 확인 가능

### 4. 결과 저장

- **"💾 모두 저장"** 버튼 클릭
- 저장 폴더 선택
- 파일명: `원본파일명_nukki.png` 형식으로 저장

## 기술 스택

| 구성 요소 | 기술 |
|----------|------|
| GUI | CustomTkinter |
| 배경 제거 | rembg (U²-Net 기반) |
| AI 후처리 | Google Gemini API |
| 이미지 처리 | Pillow |

## 폴더 구조

```
nukki-app/
├── main.py                    # 앱 진입점
├── requirements.txt           # 의존성 목록
├── README.md                  # 이 문서
├── core/
│   ├── __init__.py
│   ├── background_remover.py  # rembg 배경 제거 모듈
│   └── gemini_processor.py    # Gemini API 연동 모듈
└── ui/
    ├── __init__.py
    └── app_window.py          # GUI 컴포넌트
```

## 문제 해결

### rembg 설치 오류

```bash
# onnxruntime 먼저 설치
pip install onnxruntime

# 그 다음 rembg 설치
pip install rembg
```

### Gemini API 오류

- API 키가 올바른지 확인하세요
- 무료 티어는 분당 요청 제한이 있습니다 (15 RPM)
- 네트워크 연결을 확인하세요

### GUI가 표시되지 않음

```bash
# Tkinter 설치 확인 (macOS)
brew install python-tk

# Linux (Ubuntu/Debian)
sudo apt-get install python3-tk
```

## 라이선스

MIT License

---

Made with ❤️ by AI Assistant

