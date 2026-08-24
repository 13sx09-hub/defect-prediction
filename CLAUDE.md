# CLAUDE.md

이 파일은 Claude Code(claude.ai/code)가 이 저장소에서 작업할 때 참고할 지침을 제공합니다.

## 이 저장소는 무엇인가

SECOM 반도체 제조 데이터셋(`data/04_secom.csv`: 1567행, `measured_at`·`sensor_001`~`sensor_590`·
`result`(값은 `양품`/`불량`) 열)을 중심으로 만들어진, 한국어로 진행되는 노트북 기반 데이터 사이언스
커리큘럼입니다. 애플리케이션 코드나 패키지, 테스트 스위트는 없으며 — 각 실습(lab)의 결과물은 실제로
실행되어 셀 출력이 저장된 `.ipynb` 파일입니다. 이 폴더는 git 저장소가 아닙니다.

## 명령어

빌드·린트·테스트 도구는 없습니다. 유일한 작업 방식은 노트북을 실행하는 것입니다:

```powershell
python -m jupyter nbconvert --to notebook --execute --inplace "day0N\labNN_xxx\labNN_xxx.ipynb"
```

이 명령은 모든 셀을 처음부터 끝까지 다시 실행해서 실제 출력값을 파일에 그대로 저장합니다 — 이 저장소의
작업은 이렇게 검증·저장됩니다. 환경: 별도의 venv/conda 없이 설치된 Python 3.14이며, pandas, numpy,
matplotlib, scikit-learn, jupyter/nbconvert가 전역으로 설치되어 있습니다.

**셀의 출력값을 "이럴 것이다"라고 손으로 지어 쓰지 말 것.** 실습에서 제시하는 모든 숫자·표·그래프는
위 nbconvert 명령을 실제로 실행한 뒤 저장된 출력을 읽어서 나온 것이어야 합니다 — 이 프로젝트의 관례이자
반복적으로 명시된 사용자 지침은 "지어내지 말고 실제 실행값만"입니다.

### 노트북을 처음부터 새로 만들 때

`Write`/`Edit` 도구로는 유효한 `.ipynb`를 바로 만들 수 없습니다. 먼저 셀이 비어 있는 최소 JSON 골격
(`{"cells": [], "metadata": {...}, "nbformat": 4, "nbformat_minor": 5}`)을 **BOM 없는** UTF-8로
작성한 뒤(BOM이 있으면 노트북을 다시 읽어들이는 JSON 파서가 깨집니다), 셀을 추가하고 nbconvert로
실행합니다.

## 폴더 구조와 이름 규칙

```
dayNN/labNN_kebab-case-topic/labNN_snake_case_topic.ipynb
dayNN/labNN_kebab-case-topic/results/        # 생성된 결과물(그림, CSV) — 모든 실습에 있는 건 아님
```
각 실습은 독립적인 노트북입니다 — 공유하는 `.py` 모듈이나 패키지는 없습니다. 모든 노트북은 상대경로로
디스크의 CSV를 직접 다시 불러오며, 노트북 간에 서로 import하지 않습니다.

## 실습 간 데이터 파이프라인 (여러 파일에 걸쳐 있는 부분)

실습들은 서로의 코드가 아니라 저장된 CSV 결과물을 이어받습니다:

1. **`data/04_secom.csv`** — 원본 데이터셋. day02의 실습들이 `../../data/04_secom.csv` 경로로
   직접 불러옵니다.
2. **`day02/lab06_clean-dataset/lab06_clean_dataset.ipynb`** — 정제된 표준 데이터셋을 단계별로
   만듭니다 (`df` → `df1` → `df2` → `df3`):
   - `df1`: 빈칸 비율 50% 이상, 상수열(nunique==1), 또는 거의 안 변하는 열(std<=0.001)인 센서 열을
     제거.
   - `df2`: 상관계수 절댓값이 0.9 이상인 센서 짝마다, 빈칸이 더 많은 쪽을 제거(중복 센서 정리).
   - `df3`/`df3b`: 불량 여부와의 상관계수 절댓값 기준 상위 N개 센서만 남겨
     **`day02/lab06_clean-dataset/results/secom_clean.csv`**(상위 50개 센서 + `result`,
     `measured_at`은 제외)와 `secom_clean_b.csv`(상위 20개 버전)로 저장.
3. **`day03/lab07_train-test-split/`**와 **`day03/lab08_baseline-model/`** — 각각 독립적으로
   `secom_clean.csv`(경로: `../../day02/lab06_clean-dataset/results/secom_clean.csv`)를 다시
   불러온 뒤, 남은 센서 빈칸을 열의 중앙값으로 채우고, `result`로부터 숫자형 `불량여부` 라벨(1=불량,
   0=양품)을 만들고, `train_test_split(test_size=0.2, random_state=42, stratify=y)`를 호출합니다.
   두 실습 모두 **동일한** 분할 결과(학습용 1253행/불량 83건, 시험용 314행/불량 21건)가 나와야 하며,
   이것이 일치하는지가 일종의 정합성 확인 역할을 합니다.

`secom_clean.csv`를 쓰는 새 실습을 추가한다면, 새로운 전처리 방식을 만들지 말고 이 "디스크에서 다시
불러오기 + 중앙값 채우기 + `불량여부` + 동일한 분할 파라미터" 패턴을 그대로 따르세요.

## 노트북 내부 작성 관례

실습들은 일관된 교육용 구조를 따릅니다 — 기존 실습을 수정하거나 새 실습을 추가할 때 이 형식을
맞추세요:
- `## Step N. <제목>` 마크다운 헤더로 노트북을 단계별로 나누고, 첫 스텝 뒤에는 보통 `### 용어 풀이`
  표가 따라옵니다.
- 주요 스텝 뒤에는 빈칸 채우기 형식의 마크다운 요약 셀이 나옵니다. 형식은
  `[Step N 결과]<br>항목 : [실제값]<br>...`이며, 완성됐을 때는 대괄호 안에 (자리표시자가 아니라)
  실제로 계산된 값이 들어갑니다.
- 노트북 끝부분에는 `---` + `## 직접 해보기 (도전)` 섹션이 있어 학습자가 이어서 풀어볼 과제를
  제시합니다. 이런 과제를 완성해달라는 요청을 받으면, 거기 적힌 "상황/할 일/결과물"이 기대되는
  코드와 출력을 정의합니다.
- 이 저장소 전반에서 관찰된 관례: 특정 기존 빈 셀이나 헤딩을 채워달라고 콕 집어 말한 경우가 아니라면,
  **새 셀은 항상 노트북의 맨 마지막에 추가**하고, 관련 주제 옆에 끼워 넣지 않습니다.

## 알려진 문제: matplotlib에서 한글 깨짐

matplotlib 기본 폰트로는 한글 라벨이 `□`로 깨져 보입니다. 한글 제목·축 라벨·범례가 들어가는 그래프
셀에서는 그림을 그리기 전에 아래를 넣어야 합니다:
```python
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False
```
