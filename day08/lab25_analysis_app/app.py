import streamlit as st
import pandas as pd  # CSV를 표로 읽고 계산하기 위해 사용
from datetime import datetime  # 현재 시각을 구하기 위해 사용


def 한글_글꼴_파일_찾기(굵게=False):
    # 이 컴퓨터에 실제로 깔린 한글 글꼴 파일을 찾는다
    # 내 컴퓨터(윈도우)는 맑은 고딕, 배포 서버(리눅스, packages.txt로 나눔고딕을 깔아둠)는 나눔고딕을 쓴다
    from matplotlib import font_manager as fm

    후보_이름들 = ["Malgun Gothic", "NanumGothic", "NanumBarunGothic"]
    굵기 = "bold" if 굵게 else "normal"
    for 이름 in 후보_이름들:
        try:
            return fm.findfont(fm.FontProperties(family=이름, weight=굵기), fallback_to_default=False)
        except Exception:
            continue
    return None  # 아무 것도 못 찾으면 None - 부르는 쪽에서 알아서 처리한다


st.set_page_config(page_title="비만 위험군 선별 프로젝트")

st.title("비만 위험군 선별 프로젝트")
st.caption("문진(설문) 응답만으로, 비만이 될 위험이 큰 사람을 검사 전에 미리 가려내는 프로젝트")

# 방금 만든 해석 문장을 리포트 탭의 기본값으로 넣어둔다 - "해석 문장 만들기"를 누르면 새로 받아온 문장으로 바뀐다
if "해석문장" not in st.session_state:
    st.session_state["해석문장"] = (
        "기준 모델 정확도 0.533 대비 내 모델은 0.943으로 크게 올랐다. "
        "지금 문턱 0.5에서 193건을 지목했고 그중 182건이 진짜였으며, 놓친 건수는 13건이었다. "
        "놓친 13건이 어떤 구간에 몰려 있었는지는 이 숫자만으로 단정할 수 없어 조심스럽게 봐야 한다."
    )

탭_데이터훑기, 탭_전처리, 탭_학습, 탭_결과, 탭_리포트 = st.tabs(
    ["데이터 훑기", "전처리", "학습", "결과", "리포트"]
)

with 탭_데이터훑기:
    올린_파일 = st.file_uploader("CSV 파일을 올려주세요", type="csv")  # 업로드 칸

    if 올린_파일 is not None:
        df = pd.read_csv(올린_파일)  # 올라온 파일을 표로 읽는다

        # 1) 행 수와 열 수를 한 줄로
        st.write(f"행 {df.shape[0]}개, 열 {df.shape[1]}개")

        # 2) 앞의 다섯 줄을 표로
        st.dataframe(df.head())

        # 3) 빈칸이 모두 몇 개인지 한 줄로
        빈칸_전체 = int(df.isna().sum().sum())
        st.write(f"빈칸 : 전체 {빈칸_전체}개")

        if 빈칸_전체 > 0:
            # 빈칸이 있으면 그 열들만 골라 열 이름 / 빈칸 개수 / 빈칸 비율 표로 이어서 보여준다
            빈칸_열 = df.isna().sum()
            빈칸_열 = 빈칸_열[빈칸_열 > 0]
            빈칸표 = pd.DataFrame({
                "열 이름": 빈칸_열.index,
                "빈칸 개수": 빈칸_열.values,
                "빈칸 비율(%)": (빈칸_열.values / len(df) * 100).round(1),
            })
            st.dataframe(빈칸표)
        else:
            # 빈칸이 0개면 제목 없이 한 줄만 보여준다
            st.write("빈칸 없음")

        # 4) 결과 열을 고르는 선택 상자 - 처음 값은 맨 마지막 열로
        st.caption("맞는 열인지 확인하세요")
        결과열 = st.selectbox("결과 열을 고르세요", df.columns, index=len(df.columns) - 1)

        건수 = df[결과열].value_counts()  # 값별 개수
        비율 = (df[결과열].value_counts(normalize=True) * 100).round(1)  # 값별 비율
        결과표 = pd.DataFrame({"건수": 건수, "비율(%)": 비율})
        st.dataframe(결과표)

        # 다른 탭(전처리 등)에서도 이 파일을 다시 올리지 않고 쓸 수 있게 저장해둔다
        st.session_state["df"] = df
        st.session_state["결과열"] = 결과열
    else:
        # 파일을 아직 안 올렸을 때
        st.write("파일을 올려주세요")

with 탭_전처리:
    if "df" not in st.session_state:
        # 데이터 훑기 탭에서 파일을 먼저 올려야 여기서 쓸 수 있다
        st.write("먼저 [데이터 훑기] 탭에서 파일을 올려주세요")
    else:
        df = st.session_state["df"]  # 데이터 훑기 탭에서 올린 파일을 그대로 쓴다
        결과열 = st.session_state["결과열"]  # 데이터 훑기 탭에서 고른 결과 열을 그대로 쓴다

        # 맨 위 - 빈칸이 몇 개인지 먼저 센다
        빈칸_전체 = int(df.isna().sum().sum())
        st.write(f"빈칸 : 전체 {빈칸_전체}개")

        if 빈칸_전체 == 0:
            st.write("빈칸이 없습니다. 채울 것이 없어요")
            채우기_방법 = None
        else:
            채우기_방법 = st.selectbox("빈칸을 무엇으로 채울까요", ["중앙값", "평균", "0"])

        # 글자로 된 열 목록 (결과 열은 따로 처리하므로 뺀다)
        글자열 = [c for c in df.select_dtypes(include="object").columns if c != 결과열]
        if 글자열:
            st.write("글자로 된 열 :", 글자열)
            글자열_처리 = st.selectbox("글자 열을 어떻게 할까요", ["학습에서 빼기", "숫자로 바꾸기"])
        else:
            글자열_처리 = None

        # 결과 열의 어느 값들을 1로 볼지 고르는 선택 상자 - 여러 개를 골라도 된다
        결과값들 = df[결과열].dropna().unique().tolist()
        양성값들 = st.multiselect("결과 열에서 어느 값들을 1로 볼까요 (여러 개 고를 수 있어요)", 결과값들)

        # 학습용·시험용 비율 슬라이더 - 기본 8대 2
        학습비율 = st.slider("학습용 비율(%)", min_value=50, max_value=95, value=80, step=5)
        st.write(f"학습용 {학습비율}% / 시험용 {100 - 학습비율}%")

        적용_눌림 = st.button("적용")

        if 적용_눌림 and not 양성값들:
            # 하나도 안 고르면 전부 0이 되어 나눌 수 없으니 여기서 멈춘다
            st.write("1로 볼 값을 적어도 하나는 골라주세요")
        elif 적용_눌림:
            from sklearn.model_selection import train_test_split

            X = df.drop(columns=[결과열]).copy()

            # 빈칸 채우기 - 숫자 열만 대상으로 한다
            숫자열 = X.select_dtypes(include="number").columns
            if 채우기_방법 == "중앙값":
                X[숫자열] = X[숫자열].fillna(X[숫자열].median())
            elif 채우기_방법 == "평균":
                X[숫자열] = X[숫자열].fillna(X[숫자열].mean())
            elif 채우기_방법 == "0":
                X[숫자열] = X[숫자열].fillna(0)

            # 글자 열 처리
            if 글자열_처리 == "학습에서 빼기":
                X = X.drop(columns=글자열)
                글자열_설명 = f"글자 열 {글자열} 을(를) 학습에서 뺐습니다"
            elif 글자열_처리 == "숫자로 바꾸기":
                for 열 in 글자열:
                    X[열] = X[열].astype("category").cat.codes
                글자열_설명 = f"글자 열 {글자열} 을(를) 숫자로 바꿨습니다"
            else:
                글자열_설명 = "글자로 된 열이 없었습니다"

            처리후_빈칸 = int(X.isna().sum().sum())

            # 결과 열이 고른 값들 중 하나면 1, 아니면 0으로 바꾼다
            y = df[결과열].isin(양성값들).astype(int)

            학습입력, 시험입력, 학습정답, 시험정답 = train_test_split(
                X, y, test_size=(100 - 학습비율) / 100, random_state=42, stratify=y
            )

            # 1) 빈칸이 몇 개에서 몇 개로 줄었는지
            st.write(f"빈칸 : {빈칸_전체}개 → {처리후_빈칸}개")

            # 2) 글자 열을 어떻게 처리했는지
            st.write(글자열_설명)

            # 3) 학습용·시험용 행 수
            st.write(f"학습용 {len(학습입력)}행 / 시험용 {len(시험입력)}행")

            # 4) 학습용·시험용 각각의 1 개수와 비율
            나눈결과표 = pd.DataFrame(
                {
                    "1 개수": [int(학습정답.sum()), int(시험정답.sum())],
                    "1 비율(%)": [
                        round(학습정답.mean() * 100, 1),
                        round(시험정답.mean() * 100, 1),
                    ],
                },
                index=["학습용", "시험용"],
            )
            st.dataframe(나눈결과표)

            # 학습 탭에서 다시 올리지 않고 쓸 수 있게 나눈 결과를 저장 상자에 넣어둔다
            st.session_state["학습입력"] = 학습입력
            st.session_state["시험입력"] = 시험입력
            st.session_state["학습정답"] = 학습정답
            st.session_state["시험정답"] = 시험정답

with 탭_학습:
    if "학습입력" not in st.session_state:
        # 전처리 탭에서 [적용]을 눌러 나누기까지 끝나야 학습할 수 있다
        st.write("전처리를 먼저 해주세요")
    else:
        # 전처리 탭이 저장해둔 학습용·시험용을 그대로 꺼내 쓴다
        학습입력 = st.session_state["학습입력"]
        시험입력 = st.session_state["시험입력"]
        학습정답 = st.session_state["학습정답"]
        시험정답 = st.session_state["시험정답"]

        # 모델을 고르는 선택 상자
        모델_이름 = st.selectbox("모델을 고르세요", ["로지스틱 회귀", "의사결정나무", "랜덤 포레스트"])

        # 적은 쪽(불량)에 가중치를 줄지 켜고 끄는 스위치
        가중치_켜기 = st.toggle("적은 쪽에 가중치 주기")

        if st.button("학습"):
            from sklearn.ensemble import RandomForestClassifier  # 랜덤 포레스트 모델
            from sklearn.linear_model import LogisticRegression  # 로지스틱 회귀 모델
            from sklearn.metrics import (  # 네 가지 점수를 계산하는 함수들
                accuracy_score,
                f1_score,
                precision_score,
                recall_score,
            )
            from sklearn.tree import DecisionTreeClassifier  # 의사결정나무 모델

            import numpy as np  # 기준 모델의 예측(전부 0)을 만들기 위해 사용

            # 스위치가 켜져 있으면 적은 쪽(불량)에 가중치를 준다
            가중치_설정 = "balanced" if 가중치_켜기 else None

            # 고른 이름에 맞는 모델을 만든다 - random_state는 결과 재현을 위해 고정
            if 모델_이름 == "로지스틱 회귀":
                모델 = LogisticRegression(max_iter=1000, class_weight=가중치_설정, random_state=42)
            elif 모델_이름 == "의사결정나무":
                모델 = DecisionTreeClassifier(class_weight=가중치_설정, random_state=42)
            else:
                모델 = RandomForestClassifier(class_weight=가중치_설정, random_state=42)

            모델.fit(학습입력, 학습정답)  # 학습용으로 학습시킨다
            예측값 = 모델.predict(시험입력)  # 시험용으로 채점한다
            예측확률 = 모델.predict_proba(시험입력)[:, 1]  # 다음 탭 문턱 조정에 쓸 불량 확률

            기준_예측값 = np.zeros_like(시험정답)  # 전부 정상(0)이라고만 답하는 기준 모델

            def 점수_계산(정답, 예측):
                # 정확도·정밀도·재현율·F1 네 가지를 한 번에 계산해서 돌려준다
                return {
                    "정확도": accuracy_score(정답, 예측),
                    "정밀도": precision_score(정답, 예측, zero_division=0),
                    "재현율": recall_score(정답, 예측, zero_division=0),
                    "F1": f1_score(정답, 예측, zero_division=0),
                }

            비교표 = pd.DataFrame(
                {
                    "기준 모델(전부 정상)": 점수_계산(시험정답, 기준_예측값),
                    모델_이름: 점수_계산(시험정답, 예측값),
                }
            ).T.round(3)  # 행 : 모델 이름, 열 : 점수 - 소수 셋째 자리까지
            st.dataframe(비교표)

            # 결과 탭에서 이어서 쓸 수 있게 학습 결과를 저장 상자에 담아둔다
            st.session_state["학습모델"] = 모델
            st.session_state["모델이름"] = 모델_이름
            st.session_state["가중치_사용"] = 가중치_켜기
            st.session_state["예측값"] = 예측값
            st.session_state["예측확률"] = 예측확률
            st.session_state["비교표"] = 비교표

with 탭_결과:
    if "예측값" not in st.session_state:
        # 학습 탭에서 [학습] 버튼을 눌러야 결과를 볼 수 있다
        st.write("학습을 먼저 해주세요")
    else:
        import numpy as np  # 기준 모델 예측과 문턱 계산에 쓴다
        from sklearn.metrics import (  # 점수·혼동행렬을 계산하는 함수들
            accuracy_score,
            confusion_matrix,
            f1_score,
            precision_score,
            recall_score,
        )

        시험정답 = st.session_state["시험정답"]  # 학습 탭이 채점에 쓴 시험용 정답
        예측확률 = st.session_state["예측확률"]  # 학습 탭이 만들어둔 불량 확률 - 다시 학습하지 않고 이것만 잘라 쓴다
        학습모델 = st.session_state["학습모델"]  # 중요 변수를 뽑기 위해 학습된 모델 자체도 가져온다
        모델이름 = st.session_state["모델이름"]  # 표·그림 범례에 쓸 모델 이름
        학습입력 = st.session_state["학습입력"]  # 항목 이름(열 이름)을 얻기 위해 가져온다

        # 문턱 슬라이더 - 옮길 때마다 모델을 다시 학습하지 않고 아래 전부를 다시 계산한다
        문턱 = st.slider("문턱(임계값)", min_value=0.05, max_value=0.95, value=0.50, step=0.05)
        st.write(f"지금 문턱 : {문턱}")

        예측값 = (예측확률 >= 문턱).astype(int)  # 이미 나온 확률을 문턱 기준으로 다시 자른다

        기준_예측값 = np.zeros_like(시험정답)  # 전부 정상(0)이라고만 답하는 기준 모델

        def 점수_계산(정답, 예측):
            # 정확도·정밀도·재현율·F1 네 가지를 한 번에 계산해서 돌려준다
            return {
                "정확도": accuracy_score(정답, 예측),
                "정밀도": precision_score(정답, 예측, zero_division=0),
                "재현율": recall_score(정답, 예측, zero_division=0),
                "F1": f1_score(정답, 예측, zero_division=0),
            }

        비교표 = pd.DataFrame(
            {
                "기준 모델(전부 정상)": 점수_계산(시험정답, 기준_예측값),
                모델이름: 점수_계산(시험정답, 예측값),
            }
        ).T.round(3)  # 문턱이 바뀔 때마다 다시 계산되는 점수표

        # 맨 위 - 기준 모델과 내 모델을 나란히 놓은 표
        st.write("기준 모델과 내 모델 비교")
        st.dataframe(비교표)

        # 혼동행렬 - labels=[0, 1]로 순서를 고정해서 정상(0)·불량(1) 자리를 맞춘다
        정상정상, 헛경보, 놓친것, 잡은것 = confusion_matrix(시험정답, 예측값, labels=[0, 1]).ravel()

        지목_건수 = int(잡은것 + 헛경보)  # 불량이라고 지목한 전체 건수
        진짜_건수 = int(잡은것)  # 지목한 것 중 실제로 불량인 건수
        놓친_건수 = int(놓친것)  # 불량인데 못 잡고 놓친 건수
        st.write(f"지목한 건수 : {지목_건수}건 (그중 진짜 불량 : {진짜_건수}건) / 놓친 건수 : {놓친_건수}건")

        # 네 칸 표 - 칸 이름 옆에 무슨 뜻인지 한국어로 짧게 적는다
        st.write("혼동행렬 (시험용 기준)")
        혼동표 = pd.DataFrame(
            {
                "칸": ["잡은 것", "놓친 것", "헛경보", "정상을 정상이라 한 것"],
                "건수": [잡은것, 놓친것, 헛경보, 정상정상],
                "뜻": [
                    "불량인데 불량이라고 맞힌 것",
                    "불량인데 정상이라고 놓친 것",
                    "정상인데 불량이라고 잘못 잡은 것",
                    "정상인데 정상이라고 맞힌 것",
                ],
            }
        )
        st.dataframe(혼동표)

        # 문턱별 비교 표 - 슬라이더와 별개로 0.1부터 0.9까지 아홉 줄을 항상 다 계산해서 보여준다
        문턱_목록 = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
        문턱별_행 = []
        for t in 문턱_목록:
            t예측값 = (예측확률 >= t).astype(int)  # 이 문턱에서는 확률을 이렇게 자른다
            t정상정상, t헛경보, t놓친것, t잡은것 = confusion_matrix(시험정답, t예측값, labels=[0, 1]).ravel()
            문턱별_행.append(
                {
                    "문턱": t,
                    "지목 건수": int(t잡은것 + t헛경보),
                    "그중 진짜": int(t잡은것),
                    "놓친 건수": int(t놓친것),
                    "정밀도": round(precision_score(시험정답, t예측값, zero_division=0), 3),
                    "재현율": round(recall_score(시험정답, t예측값, zero_division=0), 3),
                    "F1": round(f1_score(시험정답, t예측값, zero_division=0), 3),
                }
            )
        문턱표 = pd.DataFrame(문턱별_행)

        최고_위치 = 문턱표["F1"].idxmax()  # F1이 가장 높은 줄의 위치를 찾는다
        문턱표["표시"] = ""
        문턱표.loc[최고_위치, "표시"] = "★ 최고 F1"

        st.write("문턱별 비교 (0.1 ~ 0.9)")
        st.dataframe(문턱표)

        최고_문턱 = 문턱표.loc[최고_위치, "문턱"]
        st.write(f"F1이 가장 높은 문턱 : {최고_문턱}")

        # 리포트 탭에서 이어서 쓸 수 있게 지금 문턱과 세 건수, 그리고 이 문턱으로 다시 계산한 비교표를 저장 상자에 담아둔다
        st.session_state["지금_문턱"] = 문턱
        st.session_state["지목_건수"] = 지목_건수
        st.session_state["진짜_건수"] = 진짜_건수
        st.session_state["놓친_건수"] = 놓친_건수
        st.session_state["비교표"] = 비교표

        # 그림 세 장을 그리기 전에 필요한 도구를 불러온다
        import os  # 그림을 저장할 폴더를 만들기 위해 사용
        import matplotlib.pyplot as plt  # 그림 세 장을 그리기 위해 사용

        # 그래프 안 한글이 네모로 깨지지 않게 한다 - 목록 중 이 컴퓨터에 깔린 첫 번째 글꼴을 자동으로 쓴다
        # (내 컴퓨터는 맑은 고딕, 배포 서버는 packages.txt로 깐 나눔고딕)
        plt.rcParams["font.family"] = "sans-serif"
        plt.rcParams["font.sans-serif"] = ["Malgun Gothic", "NanumGothic", "NanumBarunGothic", "DejaVu Sans"]
        plt.rcParams["axes.unicode_minus"] = False  # 마이너스 기호도 깨지지 않게 한다

        그림_폴더 = os.path.join(os.path.dirname(__file__), "figures")  # 그림을 모아둘 폴더 경로
        os.makedirs(그림_폴더, exist_ok=True)  # 폴더가 없으면 만든다

        # 그림 1 - 중요 변수 : 나무 계열 모델은 feature_importances_, 로지스틱 회귀는 계수의 절댓값을 쓴다
        if hasattr(학습모델, "feature_importances_"):
            중요도 = pd.Series(학습모델.feature_importances_, index=학습입력.columns)
        else:
            중요도 = pd.Series(abs(학습모델.coef_[0]), index=학습입력.columns)
        상위10 = 중요도.sort_values(ascending=False).head(10)  # 많이 쓰인 순서로 상위 10개만 본다

        fig1, ax1 = plt.subplots(figsize=(6, 4))
        ax1.barh(상위10.index[::-1], 상위10.values[::-1])  # 값이 큰 항목이 위로 오도록 뒤집는다
        ax1.set_title("중요 변수")
        for i, v in enumerate(상위10.values[::-1]):
            ax1.text(v, i, f" {v:.3f}", va="center")
        plt.tight_layout()
        fig1.savefig(os.path.join(그림_폴더, "fig1_importance.png"), dpi=150)  # figures 폴더에 저장
        st.pyplot(fig1)  # 화면에도 띄운다
        plt.close(fig1)
        st.caption("판단에 많이 쓰인 항목 상위 10개를 큰 순서대로 보여준다")

        # 그림 2 - 혼동행렬 : 위에서 만든 네 칸 숫자를 그대로 2x2 칸에 옮겨 그린다
        행렬 = np.array([[정상정상, 헛경보], [놓친것, 잡은것]])
        칸이름 = [["정상을 정상이라 한 것", "헛경보"], ["놓친 것", "잡은 것"]]

        fig2, ax2 = plt.subplots(figsize=(5.5, 5))
        ax2.imshow(행렬, cmap="Blues")
        ax2.set_title("혼동행렬")
        ax2.set_xticks([0, 1])
        ax2.set_xticklabels(["예측: 정상", "예측: 불량"])
        ax2.set_yticks([0, 1])
        ax2.set_yticklabels(["실제: 정상", "실제: 불량"])
        for i in range(2):
            for j in range(2):
                ax2.text(j, i, f"{칸이름[i][j]}\n{행렬[i, j]}건", ha="center", va="center", fontsize=11)
        plt.tight_layout()
        fig2.savefig(os.path.join(그림_폴더, "fig2_confusion.png"), dpi=150)
        st.pyplot(fig2)
        plt.close(fig2)
        st.caption("시험용 데이터가 네 칸 중 어디에 몇 건씩 들어갔는지 보여준다")

        # 그림 3 - 기준 모델과 내 모델의 점수(정확도·정밀도·재현율·F1)를 나란히 놓은 막대그림
        지표들 = 비교표.columns.tolist()
        기준값 = 비교표.loc["기준 모델(전부 정상)"].values
        내값 = 비교표.loc[모델이름].values
        x = np.arange(len(지표들))
        너비 = 0.35

        fig3, ax3 = plt.subplots(figsize=(7, 5))
        막대1 = ax3.bar(x - 너비 / 2, 기준값, 너비, label="기준 모델")
        막대2 = ax3.bar(x + 너비 / 2, 내값, 너비, label=모델이름)
        ax3.set_title("기준 모델과 내 모델 점수 비교")
        ax3.set_xticks(x)
        ax3.set_xticklabels(지표들)
        ax3.set_ylim(0, 1.0)
        ax3.legend()
        for 막대들 in [막대1, 막대2]:
            for 막대 in 막대들:
                높이 = 막대.get_height()
                ax3.text(막대.get_x() + 막대.get_width() / 2, 높이 + 0.02, f"{높이:.3f}", ha="center", fontsize=9)
        plt.tight_layout()
        fig3.savefig(os.path.join(그림_폴더, "fig3_compare.png"), dpi=150)
        st.pyplot(fig3)
        plt.close(fig3)
        st.caption("기준 모델과 내 모델의 정확도·정밀도·재현율·F1을 나란히 비교해서 보여준다")

with 탭_리포트:
    # 맨 위 - 프로젝트 요약 다섯 줄 (notes.md에 적어둔 내용을 그대로 옮겨온다)
    # 목록으로 만들어서, 화면에 보여줄 때와 PDF에 넣을 때 같은 문장을 그대로 같이 쓴다
    요약_다섯줄 = [
        "1. 무엇을 판단하려 했나 : 문진 응답만으로 비만 위험군을 미리 가려내려 했다. "
        "생활습관 여섯 조건으로 비만 여부를 판별하는 방식이다.",
        "2. 데이터를 어떻게 손봤나 : 숫자 열 6개만 입력으로 쓰고 키·몸무게는 결과 열의 사본이라 뺐다. "
        "빈칸은 중앙값으로 채우기로 했으나 실제로는 빈칸이 없었고, 학습용·시험용은 8대 2로 나눴다.",
        "3. 어떤 모델을 왜 골랐나 : 실습 17 계획표에서 다른 모델과 견주지 않고 처음부터 로지스틱 "
        "회귀 하나만 정했고, 표준화(StandardScaler)까지 파이프라인에 넣은 것을 보면 시작부터 "
        "로지스틱 회귀만 염두에 두고 짠 것이다.",
        "4. 결과가 어땠나 : 기준 모델과 견주었을 때 정확도는 0.533으로 별 차이가 없었고, "
        "재현율은 0.000으로 위험군을 하나도 잡아내지 못해 놓친 부분이 컸다.",
        "5. 문턱을 옮기면 무엇이 맞바뀌나 : 문턱을 0.5에서 0.3으로 낮추면 재현율이 0.569에서 "
        "0.944로 오르고 놓친 건수가 84건에서 11건으로 줄지만, 정밀도는 0.649에서 0.520으로 떨어지고 "
        "헛지목이 60건에서 170건으로 는다. 0.05까지 더 낮추면 놓침은 0건이 되지만 헛경보가 223건까지 "
        "늘어, 상담 인력 여유에 맞춰 문턱을 다시 찾아봐야 한다.",
    ]
    st.write("### 프로젝트 요약")
    for 줄 in 요약_다섯줄:
        st.write(줄)

    st.write("---")

    if "비교표" not in st.session_state:
        # 결과 탭에서 문턱까지 확인해야 표와 건수를 보여줄 수 있다
        st.write("결과를 먼저 만들어 주세요")
    else:
        # 결과 표 - 결과 탭이 지금 문턱으로 다시 계산해둔 비교표를 그대로 가져온다
        st.write("### 결과 표 (기준 모델과 내 모델)")
        st.dataframe(st.session_state["비교표"])

        # 지금 문턱에서의 지목·진짜·놓친 건수 - 결과 탭의 슬라이더 값을 그대로 따라온다
        st.write("### 지금 문턱에서")
        st.write(f"지금 문턱 : {st.session_state['지금_문턱']}")
        st.write(f"지목 건수 : {st.session_state['지목_건수']}건")
        st.write(f"진짜 건수 : {st.session_state['진짜_건수']}건")
        st.write(f"놓친 건수 : {st.session_state['놓친_건수']}건")

    st.write("---")

    # 맨 아래 - 해석 문장을 자동으로 만드는 자리
    st.write("### 해석 문장")

    if "비교표" not in st.session_state:
        # 넘길 여섯 숫자가 아직 없으면 문장을 만들 수 없다
        st.write("결과를 먼저 만들어야 해석 문장을 만들 수 있습니다")
    else:
        # 화면에 이미 나와 있는 값만 그대로 쓴다 - 여기서 새로 계산하지 않는다
        비교표 = st.session_state["비교표"]
        기준모델_점수 = 비교표.loc["기준 모델(전부 정상)", "정확도"]
        내모델_점수 = 비교표.loc[st.session_state["모델이름"], "정확도"]
        지금_문턱 = st.session_state["지금_문턱"]
        지목_건수 = st.session_state["지목_건수"]
        진짜_건수 = st.session_state["진짜_건수"]
        놓친_건수 = st.session_state["놓친_건수"]

        # 지금 화면의 여섯 숫자를 하나로 묶어둔다 - 이 숫자가 그대로면 다시 부르지 않는다
        지금_숫자 = (기준모델_점수, 내모델_점수, 지금_문턱, 지목_건수, 진짜_건수, 놓친_건수)

        # 단추를 눌렀을 때만 부른다 - 슬라이더처럼 화면이 다시 그려질 때마다 부르지 않는다
        if st.button("해석 문장 만들기"):
            if st.session_state.get("해석문장_숫자") == 지금_숫자 and "해석문장" in st.session_state:
                # 같은 숫자로 이미 만든 문장이 있으면 다시 부르지 않고 그걸 그대로 쓴다
                st.caption("숫자가 그대로라 전에 만든 문장을 다시 보여드립니다")
            else:
                import os  # .env 파일과 환경변수를 읽기 위해 사용
                import requests  # Gemini API를 호출하기 위해 사용

                # 열쇠를 두 군데에서 찾는다 - 코드 안에는 값을 적지 않는다
                # 1) 내 컴퓨터 - 환경변수, 그다음 프로젝트 맨 위 .env 파일 (파일 내용은 고치지 않는다)
                열쇠 = os.environ.get("GOOGLE_API_KEY")
                if not 열쇠:
                    env_경로 = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
                    if os.path.exists(env_경로):
                        with open(env_경로, encoding="utf-8") as f:
                            for 줄 in f:
                                if 줄.strip().startswith("GOOGLE_API_KEY="):
                                    열쇠 = 줄.strip().split("=", 1)[1].strip().strip('"').strip("'")
                                    break

                if not 열쇠:
                    # 2) 배포한 자리 - 배포 서비스의 비밀 값(secrets)에서 같은 이름으로 찾는다
                    # 비밀 값 설정이 아예 없는 컴퓨터에서는 st.secrets 접근 자체가 오류를 낼 수 있어 감싼다
                    try:
                        열쇠 = st.secrets.get("GOOGLE_API_KEY")
                    except Exception:
                        열쇠 = None

                if not 열쇠:
                    # 열쇠 자체는 화면에 보여주지 않고, 없다는 사실만 한 줄로 알려준다
                    st.write("열쇠가 없습니다")
                else:
                    # 화면의 여섯 숫자만 그대로 프롬프트에 담는다 - 새 숫자를 여기서 만들지 않는다
                    프롬프트 = (
                        "너는 비만 위험군 선별 결과를 한국어로 설명하는 조수다.\n"
                        "아래 여섯 개 숫자만 사용해서 문장을 만들어라. 이 숫자 말고 새로운 숫자를 만들어내지 마라.\n"
                        "무엇이 원인이라고 단정하지 말고, '~한 구간에 몰려 있었다' 정도로 조심스럽게 써라.\n"
                        "문장은 세 문장을 넘기지 마라. 한국어로 써라.\n"
                        f"기준 모델 점수 : {기준모델_점수}\n"
                        f"내 모델 점수 : {내모델_점수}\n"
                        f"지금 문턱 : {지금_문턱}\n"
                        f"지목 건수 : {지목_건수}\n"
                        f"진짜 건수 : {진짜_건수}\n"
                        f"놓친 건수 : {놓친_건수}\n"
                    )

                    # Gemini API 주소 - gemini-flash-latest는 항상 최신 flash 모델을 가리키는 이름
                    주소 = (
                        "https://generativelanguage.googleapis.com/v1beta/models/"
                        f"gemini-flash-latest:generateContent?key={열쇠}"
                    )
                    요청_본문 = {"contents": [{"parts": [{"text": 프롬프트}]}]}

                    # 인터넷이 안 되거나 응답 모양이 이상해도 빨간 오류 화면 대신 한국어 한 줄만 보여준다
                    try:
                        with st.spinner("해석 문장을 받아오는 중..."):
                            응답 = requests.post(주소, json=요청_본문, timeout=30)

                        if 응답.status_code == 200:
                            해석문장 = 응답.json()["candidates"][0]["content"]["parts"][0]["text"]
                            # 저장 상자에 담아둬야 다른 단추(PDF 등)를 눌러 화면이 다시 그려져도 안 사라진다
                            st.session_state["해석문장"] = 해석문장
                            st.session_state["해석문장_숫자"] = 지금_숫자
                        elif 응답.status_code in (400, 401, 403):
                            # 열쇠가 없을 때와 다른 문구 - 열쇠는 있지만 값이 잘못됐을 때 나오는 상태 코드
                            st.write("열쇠가 잘못된 것 같습니다. .env 파일의 GOOGLE_API_KEY 를 다시 확인해 주세요.")
                        else:
                            st.write("지금은 문장을 만들 수 없습니다. 다시 눌러주세요.")
                    except Exception:
                        st.write("지금은 문장을 만들 수 없습니다. 다시 눌러주세요.")

        # 방금 만들었든 이전에 만들어져 있든, 저장 상자에 있는 해석 문장을 화면에 보여준다
        if "해석문장" in st.session_state:
            st.write(st.session_state["해석문장"])

    st.write("---")

    def 리포트_pdf_만들기():
        # 지금 화면에 뜬 값만 그대로 PDF에 옮겨 담는다 - 서버 디스크에는 저장하지 않는다
        from fpdf import FPDF  # 한글이 든 PDF를 만들기 위해 사용

        # 이 컴퓨터에 깔린 한글 글꼴 파일을 찾는다 (윈도우: 맑은 고딕 / 배포 서버: 나눔고딕)
        글꼴_보통 = 한글_글꼴_파일_찾기(굵게=False)
        글꼴_굵게 = 한글_글꼴_파일_찾기(굵게=True) or 글꼴_보통  # 굵은 글꼴을 못 찾으면 보통 글꼴로 대신한다

        if not 글꼴_보통:
            # 한글 글꼴을 하나도 못 찾으면 지어내지 않고 사실만 알린다
            st.write("한글 글꼴을 찾지 못해 PDF를 만들 수 없습니다.")
            return b""

        pdf = FPDF(format="A4")
        pdf.add_font("Korean", "", 글꼴_보통)  # 한글이 네모로 깨지지 않게 글꼴을 PDF 안에 넣는다
        pdf.add_font("Korean", "B", 글꼴_굵게)
        pdf.set_auto_page_break(auto=True, margin=20)
        pdf.add_page()
        pdf.set_margins(20, 20, 20)

        # 맨 위 - 제목 한 줄과 오늘 날짜
        pdf.set_font("Korean", "B", 18)
        pdf.multi_cell(0, 10, "SECOM 프로젝트 리포트", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Korean", "", 11)
        pdf.set_text_color(110, 110, 110)
        pdf.cell(0, 8, datetime.now().strftime("%Y-%m-%d"), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)
        pdf.set_text_color(20, 20, 20)

        # 지금 화면에 뜬 요약 다섯 줄
        pdf.set_font("Korean", "B", 13)
        pdf.cell(0, 9, "프로젝트 요약", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Korean", "", 10.5)
        for 줄 in 요약_다섯줄:
            pdf.multi_cell(0, 6, 줄, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1)
        pdf.ln(3)

        # 점수 표와 지금 손잡이(문턱) 값에서 나온 건수 - 화면에 떠 있는 것만 넣는다
        if "비교표" not in st.session_state:
            pdf.set_font("Korean", "", 10.5)
            pdf.multi_cell(0, 6.5, "결과 표 : 아직 결과를 만들지 않았습니다", new_x="LMARGIN", new_y="NEXT")
        else:
            pdf.set_font("Korean", "B", 13)
            pdf.cell(0, 9, "결과 표 (기준 모델과 내 모델)", new_x="LMARGIN", new_y="NEXT")

            표 = st.session_state["비교표"]
            이름칸_너비 = 55
            숫자칸_너비 = (170 - 이름칸_너비) / len(표.columns)

            pdf.set_font("Korean", "B", 9.5)
            pdf.cell(이름칸_너비, 8, "", border=1, align="C")
            for 열이름 in 표.columns:
                pdf.cell(숫자칸_너비, 8, str(열이름), border=1, align="C")
            pdf.ln(8)

            pdf.set_font("Korean", "", 9.5)
            for 행이름, 행 in 표.iterrows():
                pdf.cell(이름칸_너비, 8, str(행이름), border=1, align="C")
                for 값 in 행:
                    pdf.cell(숫자칸_너비, 8, f"{값:.3f}", border=1, align="C")
                pdf.ln(8)
            pdf.ln(4)

            pdf.set_font("Korean", "B", 13)
            pdf.cell(0, 9, "지금 문턱에서", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Korean", "", 10.5)
            pdf.multi_cell(0, 6.5, f"지금 문턱 : {st.session_state['지금_문턱']}", new_x="LMARGIN", new_y="NEXT")
            pdf.multi_cell(0, 6.5, f"지목 건수 : {st.session_state['지목_건수']}건", new_x="LMARGIN", new_y="NEXT")
            pdf.multi_cell(0, 6.5, f"진짜 건수 : {st.session_state['진짜_건수']}건", new_x="LMARGIN", new_y="NEXT")
            pdf.multi_cell(0, 6.5, f"놓친 건수 : {st.session_state['놓친_건수']}건", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)

        # 맨 아래 - 방금 나온 해석 문장 (없으면 지어내지 않고 없다고 그대로 적는다)
        pdf.set_font("Korean", "B", 13)
        pdf.cell(0, 9, "해석 문장", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Korean", "", 10.5)
        해석문장_내용 = st.session_state.get("해석문장", "(아직 해석 문장을 만들지 않았습니다)")
        pdf.multi_cell(0, 6.5, 해석문장_내용, new_x="LMARGIN", new_y="NEXT")

        return bytes(pdf.output())  # 서버 파일로 저장하지 않고 메모리에서 바로 내려준다

    # 오늘 날짜를 파일 이름 뒤에 붙인다 - 손잡이를 옮기고 다시 누르면 매번 새 값으로 다시 만들어진다
    오늘_문자열 = datetime.now().strftime("%Y%m%d")
    st.download_button(
        "PDF로 내려받기",
        data=리포트_pdf_만들기(),
        file_name=f"secom_report_{오늘_문자열}.pdf",
        mime="application/pdf",
    )

st.caption(f"현재 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")  # 화면 맨 아래에 현재 시각 표시
