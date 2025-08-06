# 📊 다목적 예산 집행·정산 시스템

행사, 워크숍, 여행, 학회 등 다양한 목적의 예산 집행과 정산을 효율적으로 관리할 수 있는 Streamlit 기반 웹 애플리케이션입니다.

## 🚀 주요 기능

| 기능 | 설명 |
|------|------|
| ✅ 예산/분류 설정 | 프로젝트별 예산 및 항목별 예산 등록 가능 |
| ✅ 경비 등록 | OCR 기반 영수증 인식, 수기 입력, CSV 업로드 모두 지원 |
| ✅ 경비 현황 분석 | 분류별 집행 통계, 일자별 집행 추이 그래프 |
| ✅ 정산 기능 | 참여자별 더치페이 자동 계산 |
| ✅ PDF 보고서 | 전문 형식의 집행내역서 생성 및 다운로드 |
| ✅ 데이터 입출력 | CSV 저장 및 불러오기 기능 |
| ✅ 프로젝트 관리 | 프로젝트 추가 및 삭제 기능 (관리자 전용) |
| ✅ 관리자 인증 | 비밀번호 기반 고급 기능 제한 |
| ✅ 한글 시각화 지원 | 한글 폰트 설정을 통한 시각화 호환성 확보 |

## 🖥️ 실행 방법

1. 저장소 클론 및 패키지 설치
    ```bash
    git clone https://github.com/your-username/your-repo-name.git
    cd your-repo-name
    pip install -r requirements.txt
    ```

2. 앱 실행
    ```bash
    streamlit run Event\ Execution\ Statement.py
    ```

3. 사이드바에서 기능 선택 및 예산 입력, 경비 등록 등 진행

## 🔧 기술 스택

- **Frontend**: Streamlit
- **Backend/Logic**: Python, Pandas, datetime, base64, FPDF
- **OCR**: pytesseract
- **시각화**: Matplotlib
- **한글 폰트**: 나눔고딕 (`NanumGothic.ttf`)

## 📁 디렉토리 구조

```
📦 your-repo/
┣ 📄 Event Execution Statement.py  # 전체 Streamlit 앱 코드
┣ 📄 README.md                      # 프로젝트 설명 파일
┣ 📄 requirements.txt               # 설치 패키지 목록 (생성 필요)
```

## 📌 활용 예시

- 교내외 행사 회계 관리
- 동아리/소모임 회비 집행
- 기업 출장비 관리
- 가족/지인 여행 경비 정산

## 🔒 관리자 기능

- 프로젝트 삭제
- 예산 항목 등록 및 수정
- 고급 통계 확인

> 기본 관리자 비밀번호: `admin123` (코드 상에서 수정 가능)

---
