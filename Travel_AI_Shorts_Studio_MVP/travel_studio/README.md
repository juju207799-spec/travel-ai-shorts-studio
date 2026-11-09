# Travel AI Shorts Studio — 실행 가능한 MVP 1

## 구현된 기능
- 호텔 콘텐츠 / 최근 7일 / 30초 / 여성 TTS 기본 설정
- Google/YouTube 검색 바로가기 (자동 수집 아님)
- 팩트체크 체크리스트, 편집 가능한 6컷 대본
- 브라우저 TTS 내레이션 **미리듣기** (MP4에 삽입되지 않음)
- 사용 권한을 확보한 사진 업로드
- **실제 9:16 무음 자막형 MP4 생성 및 다운로드**
- 프로젝트 JSON 저장

## 아직 구현되지 않은 기능
- 자동 검색·팩트체크, AI 대본 생성, 영상 소스 자동 수급, MP4 음성 삽입, SNS 자동 게시, 제휴 실적 추적
- 웹 공개 배포 (코드는 Streamlit Community Cloud 등에 배포 가능)

## 실행 방법
Python 3.10 이상 설치 후 터미널에서:

```bash
pip install -r requirements.txt
streamlit run app.py
```

실행하면 브라우저에서 로컬 웹앱이 열립니다. Windows 10에서 사용 가능합니다.

### 설치 없이 웹으로 사용하고 싶다면
이 폴더를 GitHub 저장소에 올리고 Streamlit Community Cloud에서 `app.py`를 배포하면 됩니다. 배포에는 GitHub 및 Streamlit 계정이 필요합니다. 실제 외부 공개 URL은 이 파일만으로 자동 생성되지 않습니다.

## 사용 시 주의
호텔의 실제 모습과 AI 콘셉트 장면을 혼동시키지 마세요. 호텔 이미지의 상업적 사용 허가, 사실 검증, 제휴 광고 표시를 확인하세요.
