import streamlit as st
import pandas as pd
import datetime
from fpdf import FPDF
from PIL import Image
import io
import pytesseract
import base64
import matplotlib.pyplot as plt
import matplotlib
from matplotlib.font_manager import FontProperties

# --- 한글 폰트 설정 (Colab 환경) ---
NANUM_FONT_PATH = "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
NANUM_BOLD_PATH = "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"
pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"
matplotlib.rcParams['axes.unicode_minus'] = False

def set_korean_font(ax):
    font_prop = FontProperties(fname=NANUM_FONT_PATH)
    for label in (ax.get_xticklabels() + ax.get_yticklabels()):
        label.set_fontproperties(font_prop)
        label.set_fontsize(12)
    if hasattr(ax.title, 'set_fontproperties'):
        ax.title.set_fontproperties(font_prop)
        ax.title.set_fontsize(13)
    if hasattr(ax.xaxis.label, 'set_fontproperties'):
        ax.xaxis.label.set_fontproperties(font_prop)
    if hasattr(ax.yaxis.label, 'set_fontproperties'):
        ax.yaxis.label.set_fontproperties(font_prop)

# --- 세션 상태 초기화 및 프로젝트 리스트 ---
if "expense_db" not in st.session_state:
    st.session_state.expense_db = pd.DataFrame(columns=[
        "ID", "프로젝트", "분류", "날짜", "금액", "설명", "여행자", "이미지", "수량", "비고"
    ])
if "travelers" not in st.session_state: st.session_state.travelers = []
if "budget" not in st.session_state: st.session_state.budget = {}
if "categories" not in st.session_state: st.session_state.categories = ["교통", "숙박", "식비", "관광", "쇼핑", "기타"]
if "projects" not in st.session_state:
    st.session_state.projects = ["전체 프로젝트"]  # 기본 프로젝트 이름


ADMIN_PASSWORD = "admin123"

# --- PDF 보고서 클래스 ---
class ExpenseReportPDF(FPDF):
    def __init__(self, title="예산 집행내역서", project="", period=""):
        super().__init__(orientation='L', unit='mm', format='A4')
        self.report_title = title
        self.project = project
        self.period = period
        self.add_font("NanumGothic", "", NANUM_FONT_PATH, uni=True)
        self.add_font("NanumGothic", "B", NANUM_BOLD_PATH, uni=True)
        self.add_font("NanumGothic", "I", NANUM_FONT_PATH, uni=True)
        self.set_auto_page_break(auto=True, margin=15)

    def header(self):
        self.set_font("NanumGothic", "B", 15)
        self.cell(0, 12, self.report_title, 0, 1, "C")
        self.set_font("NanumGothic", "", 11)
        if self.project:
            self.cell(0, 7, f"프로젝트/행사명 : {self.project}", 0, 1)
        if self.period:
            self.cell(0, 7, f"활동 기간 : {self.period}", 0, 1)
        self.ln(3)

    def footer(self):
        self.set_y(-13)
        self.set_font("NanumGothic", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}", 0, 0, "C")

    def add_table_header(self):
        self.set_fill_color(230, 240, 250)
        self.set_font("NanumGothic", "B", 10)
        headers = ["ID", "일자", "분류", "내역/설명", "단가", "수량", "금액", "참여자", "비고"]
        self.col_widths = [20, 27, 20, 90, 18, 12, 22, 21, 27]
        for i, header in enumerate(headers):
            self.cell(self.col_widths[i], 8, header, 1, 0, "C", 1)
        self.ln()

    def add_expense_row(self, idx, row):
        self.set_font("NanumGothic", "", 9)
        get = lambda k: str(row.get(k, "") if pd.notnull(row.get(k, "")) else "")
        self.cell(self.col_widths[0], 7, get("ID"), 1)
        self.cell(self.col_widths[1], 7, get("날짜"), 1)
        self.cell(self.col_widths[2], 7, get("분류"), 1)
        self.cell(self.col_widths[3], 7, get("설명")[:35], 1)  # 설명 길이 제한
        self.cell(self.col_widths[4], 7, "{:,}".format(int(float(row.get("금액", 0) or 0))), 1, 0, "R")
        qty = int(float(row.get("수량") or 1))
        self.cell(self.col_widths[5], 7, str(qty), 1, 0, "R")
        amount = int(float(row.get("금액", 0) or 0)) * qty
        self.cell(self.col_widths[6], 7, "{:,}".format(amount), 1, 0, "R")
        self.cell(self.col_widths[7], 7, get("여행자"), 1)
        self.cell(self.col_widths[8], 7, get("비고"), 1)
        self.ln()

    def add_table(self, expense_df):
        self.add_table_header()
        for idx, (_, row) in enumerate(expense_df.iterrows(), 1):
            self.add_expense_row(idx, row)

    def add_summary(self, total, balance):
        self.ln(3)
        self.set_font("NanumGothic", "B", 11)
        self.cell(0, 9, f"집행 총계: ￦{total:,}    잔여 예산: ￦{balance:,}", 0, 1, "R")

def generate_pdf_report_bytes(expense_df, report_title="예산 집행내역서", project_name="", period=""):
    pdf = ExpenseReportPDF(report_title, project=project_name, period=period)
    pdf.add_page()
    if "수량" not in expense_df.columns:
        expense_df = expense_df.copy()
        expense_df["수량"] = 1
    if "비고" not in expense_df.columns:
        expense_df["비고"] = ""
    pdf.add_table(expense_df)
    total_spent = sum(int(float(row["금액"]) if pd.notnull(row["금액"]) else 0) *
                      int(float(row.get("수량", 1) or 1)) for _, row in expense_df.iterrows())
    budget_total = st.session_state.budget.get("total", 0) if st.session_state.budget else 0
    balance = budget_total - total_spent if budget_total > 0 else 0
    pdf.add_summary(total_spent, balance)
    return pdf.output(dest='S').encode('latin1')

# --- OCR, 이미지 ---
def extract_expense_info_from_image(image):
    text = pytesseract.image_to_string(image, lang="kor+eng")
    amount, date = 0, None
    import re
    amounts = re.findall(r"\d{3,}", text.replace(",", ""))
    if amounts: amount = max(map(int, amounts))
    date_match = re.search(r"((19|20)\d{2}[-/.](0[1-9]|1[0-2])[-/.](0[1-9]|[12][0-9]|3[01]))", text)
    if date_match: date = date_match.group(1).replace(".", "-").replace("/", "-")
    return date, amount
def img_to_base64(img):
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()
def base64_to_img(img_str):
    buffered = io.BytesIO(base64.b64decode(img_str))
    return Image.open(buffered)

# --- 정산 ---
def get_settlement_info(df):
    if df.empty: return [], 0, {}
    travelers = df["여행자"].unique().tolist()
    total = df["금액"].sum()
    per_person = total / len(travelers) if travelers else 0
    per_person_amount = {}
    for t in travelers:
        spent = df[df["여행자"] == t]["금액"].sum()
        per_person_amount[t] = spent
    balances = {t: round(per_person - amt) for t, amt in per_person_amount.items()}
    return travelers, per_person, balances

# --- 가이드 ---
def show_guide_page():
    st.header("📋 다목적 예산 집행/정산 시스템 안내")
    st.markdown("""
    ### 🧑‍💼 주요 특징  
    - **다목적**: 행사, 여행, 워크숍, 동아리, 학회, 출장 등 모든 예산/경비 집행 및 정산에 사용!
    - **간편 입력:** 영수증 OCR, 직접입력, CSV 일괄 등록 지원
    - **정산 자동화:** 더치페이, 예산대비 집행, 통계 분석, 실무형 PDF 보고서
    - **컬러 시각화·전문 보고:** Streamlit 대시보드, 집행내역서 표식 출력  
    ---
    ### 🔎 사용 방법
    1. **예산/분류 설정**: 목적, 예산, 분류 생성 (관리자)
    2. **경비 등록**: 이미지, 수기, CSV 
    3. **현황/분석**: 표, 그래프, 상세 내역
    4. **정산**: 더치페이, 잔액 자동계산
    5. **보고서**: 맞춤제목, 행사명, 기간 저장·다운로드
    6. **데이터 관리**: CSV 내보내기/불러오기  
    ---
    ### 💡 활용 예시
    - 행사/워크숍 집행내역서
    - 출장/연수비 정산, 사무실 소모품·운영비 관리
    - 소모임, 학회, 학생회 회계장부
    - 여럿이 여행가서 더치페이까지
    """)

def main():
    st.set_page_config(page_title="다목적 예산 집행/정산 시스템", layout="wide")
    st.title("📊 다목적 예산 집행·정산 시스템")

    st.sidebar.header("🔐 관리자 로그인")
    password_input = st.sidebar.text_input("관리자 비밀번호 입력", type="password")
    is_admin = password_input == ADMIN_PASSWORD
    if is_admin: st.sidebar.success("관리자 로그인 성공")
    else: st.sidebar.info("관리자만 고급 기능 접근 가능")

    # 프로젝트 선택 및 신규 프로젝트 추가/삭제 UI
    st.sidebar.markdown("### 프로젝트 선택 및 관리")
    # 신규 프로젝트 추가
    new_project_name = st.sidebar.text_input("새 프로젝트 이름 추가")
    if st.sidebar.button("프로젝트 추가"):
        np = new_project_name.strip()
        if np and np not in st.session_state.projects:
            st.session_state.projects.append(np)
            st.success(f"프로젝트 '{np}'가 추가되었습니다.")
        elif not np:
            st.sidebar.warning("프로젝트 이름을 입력하세요.")
        else:
            st.sidebar.warning("이미 존재하는 프로젝트입니다.")

    # 프로젝트 삭제 (관리자 전용)
    if is_admin:
        project_to_delete = st.sidebar.selectbox("프로젝트 삭제", options=st.session_state.projects)
        if st.sidebar.button("프로젝트 삭제하기"):
            if project_to_delete and project_to_delete != "전체 프로젝트":
                # 삭제 전 안내 및 처리
                confirm = st.sidebar.checkbox(f"'{project_to_delete}' 프로젝트 삭제 확인")
                if confirm:
                    # 프로젝트 관련 경비 모두 삭제
                    st.session_state.expense_db = st.session_state.expense_db[st.session_state.expense_db["프로젝트"] != project_to_delete]
                    st.session_state.projects.remove(project_to_delete)
                    st.success(f"프로젝트 '{project_to_delete}'가 삭제되었습니다.")
            else:
                st.sidebar.warning("전체 프로젝트는 삭제할 수 없습니다.")

    # 선택 가능한 프로젝트 목록
    selected_project = st.sidebar.selectbox(
        "프로젝트 선택",
        options=st.session_state.projects,
        index=0 if "전체 프로젝트" in st.session_state.projects else None,
        help="보고 관리할 프로젝트를 선택하세요"
    )

    # 프로젝트 필터링 함수
    def filter_expenses_by_project(df, project):
        if project == "전체 프로젝트":
            return df
        else:
            return df[df["프로젝트"] == project]

    menu = [
        "시스템 설명",
        "예산/분류 관리",
        "경비 등록",
        "경비 현황/분석",
        "여행자 정산/더치페이",
        "집행내역서 보고서(PDF)",
        "데이터 입/출력"
    ]
    choice = st.sidebar.selectbox("기능 선택", menu)

    if choice == "시스템 설명":
        show_guide_page()

    elif choice == "예산/분류 관리":
        if not is_admin:
            st.warning("관리자만 접근 가능합니다.")
            return
        st.header("예산/카테고리 관리")
        with st.form("budget_form2"):
            total_budget = st.number_input("총 예산(원)", min_value=0, value=st.session_state.budget.get("total", 0))
            dict_budget = {c: st.number_input(f"{c} 예산(원)", min_value=0, value=st.session_state.budget.get(c, 0))
                           for c in st.session_state.categories}
            submit_budget = st.form_submit_button("저장")
            if submit_budget:
                dict_budget["total"] = total_budget
                st.session_state.budget = dict_budget
                st.success("예산/카테고리 저장")
        with st.expander("카테고리 추가/삭제"):
            new_cat = st.text_input("새 카테고리")
            if st.button("카테고리 추가"):
                if new_cat and new_cat not in st.session_state.categories:
                    st.session_state.categories.append(new_cat)
                    st.success(f"‘{new_cat}’ 추가")
            cat_del = st.selectbox("삭제할 카테고리", st.session_state.categories)
            if st.button("카테고리 삭제"):
                if cat_del in st.session_state.categories and len(st.session_state.categories) > 1:
                    st.session_state.categories.remove(cat_del)
                    st.success(f"‘{cat_del}’ 삭제")
        if st.session_state.budget:
            filtered_expense_df = filter_expenses_by_project(st.session_state.expense_db, selected_project)
            total_spent = filtered_expense_df["금액"].sum()
            st.write(f"**총 지출:** {total_spent:,} 원 / **총 예산:** {st.session_state.budget.get('total', 0):,} 원")
            if total_spent > st.session_state.budget.get("total", 0) > 0:
                st.error("⚠️ 총 예산 초과!")
            for cat in st.session_state.categories:
                cat_spent = filtered_expense_df[filtered_expense_df["분류"] == cat]["금액"].sum()
                budget_val = st.session_state.budget.get(cat, 0)
                st.write(f"• {cat} 지출: {cat_spent:,} 원 / 예산: {budget_val:,} 원")
                if cat_spent > budget_val > 0:
                    st.error(f"⚠️ '{cat}' 예산초과!")

    elif choice == "경비 등록":
        st.header(f"경비 등록 / 영수증 OCR / CSV 업로드 (프로젝트: {selected_project})")
        with st.expander("영수증 이미지 업로드 (jpg, png, jpeg)"):
            uploaded_file = st.file_uploader("영수증 사진", type=["png", "jpg", "jpeg"])
            ocr_date, ocr_amount = None, 0
            img_str = ""
            if uploaded_file:
                img = Image.open(uploaded_file)
                st.image(img, caption="영수증 이미지")
                ocr_date, ocr_amount = extract_expense_info_from_image(img)
                st.write(f"OCR 추출: 날짜 {ocr_date}, 금액 {ocr_amount:,} 원")
                img_str = img_to_base64(img)
        with st.expander("CSV 파일 업로드로 경비 일괄 등록"):
            csv_file = st.file_uploader("CSV 파일 업로드 (프로젝트, 분류, 날짜, 금액, 설명, 여행자, 수량[선택], 비고[선택])", type=["csv"])
            if csv_file:
                try:
                    df_csv = pd.read_csv(csv_file)
                    # 프로젝트 컬럼 자동 추가 if 없으면 선택 프로젝트 또는 "기본 프로젝트"
                    if "프로젝트" not in df_csv.columns:
                        df_csv["프로젝트"] = selected_project if selected_project != "전체 프로젝트" else "기본 프로젝트"
                    required_cols = {"프로젝트", "분류", "날짜", "금액", "설명", "여행자"}
                    if not required_cols.issubset(df_csv.columns):
                        st.error(f"필수 컬럼 누락: {required_cols}")
                    else:
                        start_id = len(st.session_state.expense_db) + 1
                        if "ID" in df_csv.columns:
                            df_csv.drop(columns=["ID"], inplace=True)
                        df_csv.reset_index(drop=True, inplace=True)
                        df_csv["ID"] = range(start_id, start_id + len(df_csv))
                        cols = df_csv.columns.tolist()
                        cols = ["ID", "프로젝트"] + [c for c in cols if c not in ("ID", "프로젝트")]
                        df_csv = df_csv[cols]
                        for c in ["이미지", "수량", "비고"]:
                            if c not in df_csv.columns:
                                df_csv[c] = "" if c != "수량" else 1
                        st.session_state.expense_db = pd.concat([st.session_state.expense_db, df_csv], ignore_index=True)
                        for t in df_csv["여행자"].dropna().unique().tolist():
                            if t not in st.session_state.travelers and t != '':
                                st.session_state.travelers.append(t)
                        for p in df_csv["프로젝트"].dropna().unique().tolist():
                            if p not in st.session_state.projects:
                                st.session_state.projects.append(p)
                        st.success(f"CSV 경비 {len(df_csv)}건 등록 완료")
                except Exception as e:
                    st.error(f"CSV 처리 오류: {e}")
        with st.form("manual_entry"):
            st.write(f"등록 프로젝트: {selected_project}")
            category = st.selectbox("경비 분류", st.session_state.categories)
            date = st.date_input("경비 날짜", value=datetime.date.today() if 'ocr_date' not in locals() or ocr_date is None else pd.to_datetime(ocr_date))
            amount = st.number_input("금액(원)", min_value=0, value=ocr_amount if ocr_amount else 0)
            description = st.text_area("설명/용도")
            traveler = st.text_input("참여자")
            qty = st.number_input("수량", min_value=1, value=1)
            note = st.text_input("비고 (선택)", value="")
            submit = st.form_submit_button("등록")
            if submit:
                new_id = len(st.session_state.expense_db) + 1
                project_name_this = selected_project if selected_project != "전체 프로젝트" else "기본 프로젝트"
                new_row = {
                    "ID": new_id,
                    "프로젝트": project_name_this,
                    "분류": category,
                    "날짜": str(date),
                    "금액": amount,
                    "설명": description,
                    "여행자": traveler,
                    "이미지": img_str,
                    "수량": qty,
                    "비고": note
                }
                st.session_state.expense_db = pd.concat([st.session_state.expense_db, pd.DataFrame([new_row])], ignore_index=True)
                if traveler and traveler not in st.session_state.travelers:
                    st.session_state.travelers.append(traveler)
                if project_name_this not in st.session_state.projects:
                    st.session_state.projects.append(project_name_this)
                st.success("경비가 등록되었습니다.")

    elif choice == "경비 현황/분석":
        st.header(f"경비 현황 및 분석 (프로젝트: {selected_project})")

        df_filtered = filter_expenses_by_project(st.session_state.expense_db, selected_project)
        if df_filtered.empty:
            st.info("등록된 경비가 없습니다.")
        else:
            # 활동기간 필터 추가: 시작일, 종료일 (분석용)
            st.subheader("활동 기간 필터 (선택적)")
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("시작일", value=df_filtered["날짜"].min() if not df_filtered.empty else datetime.date.today())
            with col2:
                end_date = st.date_input("종료일", value=df_filtered["날짜"].max() if not df_filtered.empty else datetime.date.today())
            # 날짜 필터 적용
            try:
                df_filtered_dates = df_filtered[
                    (pd.to_datetime(df_filtered["날짜"]) >= pd.to_datetime(start_date)) &
                    (pd.to_datetime(df_filtered["날짜"]) <= pd.to_datetime(end_date))
                ]
            except Exception as e:
                df_filtered_dates = df_filtered  # 필터 오류시 원본 유지
                st.warning(f"날짜 필터 적용 중 오류: {e}")

            tab1, tab2, tab3 = st.tabs(["전체 내역", "분류별 통계", "일자별 추이"])
            with tab1:
                st.write(f"#### 전체 경비 내역 - [{selected_project}]")
                view_cols = ["ID", "여행자", "분류", "날짜", "금액", "설명", "수량", "비고"]
                show_df = df_filtered_dates[view_cols].astype(str)
                st.dataframe(show_df, use_container_width=True)
                def show_detail(row):
                    st.write(row.to_dict())
                    if row["이미지"]:
                        st.image(base64_to_img(row["이미지"]), width=300)
                detail_id = st.number_input("상세보기 ID", min_value=1, step=1)
                if detail_id in df_filtered_dates["ID"].values:
                    row = df_filtered_dates[df_filtered_dates["ID"] == detail_id].iloc[0]
                    st.write("상세 내역")
                    show_detail(row)
            with tab2:
                st.write(f"#### [분류별 집행 통계 - {selected_project}]")
                cat_totals = df_filtered_dates.groupby("분류")["금액"].sum().sort_values(ascending=False)
                fig, ax = plt.subplots(figsize=(8, 5))
                cat_totals.plot(kind="bar", ax=ax, color="#90caf9")
                set_korean_font(ax)
                ax.set_xlabel("분류")
                ax.set_ylabel("합계(원)")
                ax.set_title("분류별 집행액")
                plt.xticks(rotation=0, ha='center')
                plt.tight_layout()
                st.pyplot(fig)
            with tab3:
                st.write(f"#### [일자별 집행 추이 - {selected_project}]")
                date_totals = df_filtered_dates.groupby("날짜")["금액"].sum().sort_index()
                fig2, ax2 = plt.subplots(figsize=(8, 5))
                date_totals.plot(kind="line", marker='o', ax=ax2, color="#4caf50")
                set_korean_font(ax2)
                ax2.set_xlabel("날짜")
                ax2.set_ylabel("합계(원)")
                ax2.set_title("일자별 집행 추이")
                plt.xticks(rotation=0, ha='center')
                plt.tight_layout()
                st.pyplot(fig2)

    elif choice == "여행자 정산/더치페이":
        st.header(f"참여자별 정산 (프로젝트: {selected_project})")
        df_filtered = filter_expenses_by_project(st.session_state.expense_db, selected_project)
        travelers, per_person, balances = get_settlement_info(df_filtered)
        st.write(f"총 지출액: {df_filtered['금액'].sum():,} 원")
        st.write(f"참여자 수: {len(travelers)}")
        st.write(f"1인당 평균 부담금: {per_person:,.0f} 원")
        st.dataframe(pd.DataFrame({
            "참여자": list(balances.keys()),
            "개인 지출": [balances[t] + per_person for t in balances],
            "정산 필요 금액 (양수:더 부담, 음수:환급)": list(balances.values())
        }))
        st.info("💡 양수: 추가 부담, 음수: 환급")

    elif choice == "집행내역서 보고서(PDF)":
        st.header(f"집행내역서 보고서 생성 및 다운로드 (프로젝트: {selected_project})")
        report_title = st.text_input("보고서 제목", value="예산 집행내역서")
        project_name = selected_project if selected_project != "전체 프로젝트" else ""
        period = st.text_input("활동 기간", value="")
        df_filtered = filter_expenses_by_project(st.session_state.expense_db, selected_project)
        if df_filtered.empty:
            st.info("등록된 경비가 없습니다.")
        else:
            pdf_bytes = generate_pdf_report_bytes(df_filtered, report_title, project_name, period)
            st.download_button("📄 PDF 보고서 다운로드", data=pdf_bytes,
                               file_name=f"{report_title}.pdf",
                               mime="application/pdf")

    elif choice == "데이터 입/출력":
        st.header("CSV 내보내기/불러오기")
        st.download_button(
            "CSV 다운로드",
            st.session_state.expense_db.to_csv(index=False).encode("utf-8-sig"),
            file_name="expense_data.csv")
        uploaded_csv = st.file_uploader("CSV 불러오기", type=["csv"])
        if uploaded_csv:
            try:
                df = pd.read_csv(uploaded_csv)
                required = {"ID", "프로젝트", "분류", "날짜", "금액", "설명", "여행자", "이미지", "수량", "비고"}
                if required.issubset(df.columns):
                    st.session_state.expense_db = df
                    st.session_state.travelers = df["여행자"].dropna().unique().tolist()
                    for p in df["프로젝트"].dropna().unique().tolist():
                        if p not in st.session_state.projects:
                            st.session_state.projects.append(p)
                    if "budget" not in st.session_state or not st.session_state.budget:
                        st.session_state.budget = {}
                    st.success("CSV 데이터 정상 반영")
                else:
                    st.warning(f"필수 컬럼 누락: {required}")
            except Exception as e:
                st.error(f"CSV 파일 오류: {e}")

if __name__ == "__main__":
    main()
