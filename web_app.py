import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import time
import os
from datetime import datetime
from io import BytesIO
from supabase import create_client, Client

# ==========================================
# 🔑 JUNG 님의 클라우드 열쇠 (KEY를 꼭 다시 넣어주세요!)
# ==========================================
SUPABASE_URL = "https://wztxohkucxbfklwdxykb.supabase.co"
SUPABASE_KEY = "sb_publishable_7Y_z-wVoCsqJR-juqk0h3w_JgKe-oTj"

# 클라우드 데이터베이스 연결!
@st.cache_resource
def init_connection():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase: Client = init_connection()

# ==========================================
# 필수 함수 모음
# ==========================================
def load_books():
    response = supabase.table("books").select("*").execute()
    return response.data

def is_duplicate_title(new_title, books_list):
    if not new_title: return False
    clean_new = str(new_title).replace(" ", "").lower()
    for b in books_list:
        existing_title = b.get('title', '')
        if not existing_title: continue
        clean_existing = str(existing_title).replace(" ", "").lower()
        if clean_new == clean_existing:
            return True
    return False

def parse_excel_cell(val):
    if pd.isna(val): return []
    val_str = str(val).strip()
    if not val_str: return []
    return [v.strip() for v in val_str.split(',') if v.strip()]

def format_stars(rating):
    if rating is not None and rating > 0: return "⭐" * rating
    return "평가 안함"

# ==========================================
# 화면 기본 세팅
# ==========================================
st.set_page_config(page_title="내 서재 관리", page_icon="📚", layout="wide")

if 'scroll_up' not in st.session_state: st.session_state['scroll_up'] = False
if 'toast_msg' not in st.session_state: st.session_state['toast_msg'] = None
if 'toast_icon' not in st.session_state: st.session_state['toast_icon'] = None
if 'pending_batch' not in st.session_state: st.session_state['pending_batch'] = None
if 'dup_titles' not in st.session_state: st.session_state['dup_titles'] = []
if 'pending_excel' not in st.session_state: st.session_state['pending_excel'] = None
if 'excel_dup_titles' not in st.session_state: st.session_state['excel_dup_titles'] = []

if st.session_state['toast_msg']:
    st.toast(st.session_state['toast_msg'], icon=st.session_state['toast_icon'])
    st.session_state['toast_msg'] = None
    st.session_state['toast_icon'] = None

if st.session_state['scroll_up']:
    components.html("""
        <script>
            const parent = window.parent;
            parent.scrollTo(0, 0);
            const mainElements = parent.document.querySelectorAll('.main, [data-testid="stAppViewBlockContainer"], [data-testid="stAppViewContainer"]');
            mainElements.forEach(el => { el.scrollTo({top: 0, behavior: 'auto'}); });
        </script>
    """, height=0)
    st.session_state['scroll_up'] = False

st.title("📚 JUNG의 도서 관리 앱 (클라우드 연동 ☁️)")

books = load_books()

# ==========================================
# ⚠️ 중복 확인 모달창
# ==========================================
if st.session_state.get('pending_batch') or st.session_state.get('pending_excel'):
    st.markdown("---")
    st.error("### ⚠️ 이미 등록된 도서가 있습니다!")
    
    is_batch = bool(st.session_state.get('pending_batch'))
    dup_list = st.session_state['dup_titles'] if is_batch else st.session_state['excel_dup_titles']
    
    st.warning(f"서재에 이미 똑같은 이름의 책이 있습니다.\n\n**중복 의심 도서:** {', '.join(dup_list)}\n\n그래도 무시하고 등록하시겠습니까?")
    
    col_y, col_n, _ = st.columns([2, 2, 6])
    with col_y:
        if st.button("✅ 예 (무시하고 등록)"):
            added = 0
            db_inserts = []
            
            if is_batch:
                for item in st.session_state['pending_batch']:
                    cover_filename = None
                    if item['cover_bytes'] is not None:
                        cover_filename = f"{int(time.time()*1000)}_{added}.png"
                        supabase.storage.from_("covers").upload(cover_filename, item['cover_bytes'])
                    
                    db_inserts.append({
                        "title": item['title'], "writer": item['writer'], "illustrator": item['illustrator'],
                        "publisher": item['publisher'], "format": item['format'], "status": item['status'],
                        "rating": item['rating'], "start_date": item['start_date'], "completion_date": item['completion_date'],
                        "cover_image": cover_filename
                    })
                    added += 1
                st.session_state['pending_batch'] = None
                st.session_state['dup_titles'] = []
            else:
                for item in st.session_state['pending_excel']:
                    db_inserts.append(item)
                    added += 1
                st.session_state['pending_excel'] = None
                st.session_state['excel_dup_titles'] = []
            
            if db_inserts:
                supabase.table("books").insert(db_inserts).execute()
                
            st.session_state['toast_msg'] = f"✅ 중복을 허용하여 {added}권이 등록되었습니다!"
            st.session_state['toast_icon'] = "🎉"
            st.session_state['scroll_up'] = True
            st.rerun()
            
    with col_n:
        if st.button("❌ 아니오 (취소)"):
            st.session_state['pending_batch'] = None
            st.session_state['dup_titles'] = []
            st.session_state['pending_excel'] = None
            st.session_state['excel_dup_titles'] = []
            st.session_state['toast_msg'] = "등록이 취소되었습니다."
            st.session_state['toast_icon'] = "🚫"
            st.session_state['scroll_up'] = True
            st.rerun()
            
    st.stop()

# ==========================================
# CSS 스타일링
# ==========================================
st.markdown("""
    <style>
    [data-testid="stForm"] [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(1),
    [data-testid="stForm"] [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(2),
    [data-testid="stForm"] [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(3) {
        border-right: 2px dashed #999999 !important; padding-right: 20px !important;
    }
    [data-testid="column"] > .element-container { height: 100% !important; display: flex; flex-direction: column; }
    [data-testid="stVerticalBlockBorderWrapper"] { height: 100% !important; display: flex; flex-direction: column; flex-grow: 1; }
    [data-testid="stVerticalBlockBorderWrapper"] > [data-testid="stVerticalBlock"] { height: 100% !important; display: flex; flex-direction: column; flex-grow: 1; }
    [data-testid="stVerticalBlockBorderWrapper"] > [data-testid="stVerticalBlock"] > .element-container:first-child { flex-grow: 1; }
    [data-testid="stVerticalBlockBorderWrapper"] > [data-testid="stVerticalBlock"] > .element-container:last-child { margin-top: auto !important; }
    div[data-baseweb="select"] > div { border: 1px solid #888888 !important; border-radius: 5px !important; }
    </style>
""", unsafe_allow_html=True)

if 'edit_book_id' not in st.session_state:
    st.session_state['edit_book_id'] = None

tab1, tab2, tab3 = st.tabs(["📖 서재 갤러리", "➕ 직접 추가하기", "📁 엑셀(한셀) 파일로 대량 추가"])
platforms_list = ["네이버", "카카오", "리디", "레진코믹스", "봄툰"]

# ==========================================
# 탭 1: 서재 갤러리 (강력한 정렬 기능 포함)
# ==========================================
with tab1:
    if st.session_state['edit_book_id'] is not None:
        target_id = st.session_state['edit_book_id']
        book = next((b for b in books if b['id'] == target_id), None)
        
        if book:
            st.subheader("✏️ 책 정보 수정")
            st.markdown("**책 제목**")
            edit_title = st.text_input("책 제목", value=book.get('title', ''), label_visibility="collapsed")
            
            col_w1, col_w2 = st.columns(2)
            with col_w1:
                st.markdown("**글작가**")
                edit_writer = st.text_input("글작가", value=book.get('writer', ''), label_visibility="collapsed")
            with col_w2:
                st.markdown("**그림작가**")
                edit_illust = st.text_input("그림작가", value=book.get('illustrator', ''), label_visibility="collapsed")
            
            saved_pub = book.get('publisher', [])
            if not saved_pub: saved_pub = []
            st.markdown("**플랫폼** (중복 선택 가능)")
            edit_publisher = []
            p_cols = st.columns(len(platforms_list))
            for i, p_name in enumerate(platforms_list):
                with p_cols[i]:
                    if st.checkbox(p_name, value=p_name in saved_pub, key=f"edit_pub_{i}"):
                        edit_publisher.append(p_name)
            
            saved_fmt = book.get('format', [])
            if not saved_fmt: saved_fmt = []
            st.markdown("**소장 형태** (중복 선택 가능)")
            edit_fmt = []
            fmt_col1, fmt_col2 = st.columns(2)
            with fmt_col1:
                if st.checkbox("e-book", value="e-book" in saved_fmt, key="edit_fmt_ebook"): edit_fmt.append("e-book")
            with fmt_col2:
                if st.checkbox("도서", value="도서" in saved_fmt, key="edit_fmt_book"): edit_fmt.append("도서")
            
            saved_status = book.get("status", [])
            if not saved_status: saved_status = []
            st.markdown("**상태** (중복 선택 가능)")
            edit_status = []
            st_col1, st_col2, st_col3 = st.columns(3)
            with st_col1:
                if st.checkbox("연재중", value="연재중" in saved_status, key="edit_st_ing"): edit_status.append("연재중")
            with st_col2:
                if st.checkbox("완결", value="완결" in saved_status, key="edit_st_end"): edit_status.append("완결")
            with st_col3:
                if st.checkbox("휴재", value="휴재" in saved_status, key="edit_st_pause"): edit_status.append("휴재")
            
            st.markdown("---")
            
            st.markdown("**별점**")
            current_rating = book.get('rating', 0)
            star_options = [5, 4, 3, 2, 1, 0]
            edit_rating = st.selectbox("별점", star_options, index=star_options.index(current_rating if current_rating else 0), format_func=format_stars, label_visibility="collapsed")
            
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                st.markdown("**연재 시작일** (선택사항)")
                edit_start_date = st.text_input("연재 시작일", value=book.get('start_date', ''), placeholder="예: 2026-01-01", label_visibility="collapsed")
            with col_d2:
                st.markdown("**완결일** (선택사항)")
                edit_comp_date = st.text_input("완결일", value=book.get('completion_date', ''), placeholder="예: 2026-09-06", label_visibility="collapsed")
                
            st.markdown("---")
            
            st.markdown("**표지 이미지**")
            old_cover = book.get("cover_image")
            if old_cover:
                cover_url = supabase.storage.from_("covers").get_public_url(old_cover)
                st.markdown(f'<img src="{cover_url}" style="width: 140px; border: 1px solid #ccc;">', unsafe_allow_html=True)
            
            edit_cover = st.file_uploader("새 표지 이미지 (선택)", type=['png', 'jpg', 'jpeg'], label_visibility="collapsed")
            
            st.write("")
            col1, col2, col3 = st.columns([1, 1, 8])
            with col1:
                if st.button("💾 저장"):
                    update_data = {
                        "title": edit_title, "writer": edit_writer, "illustrator": edit_illust,
                        "publisher": edit_publisher, "format": edit_fmt, "status": edit_status,
                        "rating": edit_rating, "start_date": edit_start_date, "completion_date": edit_comp_date
                    }
                    if edit_cover is not None:
                        new_cover_name = f"{int(time.time()*1000)}_edit.png"
                        supabase.storage.from_("covers").upload(new_cover_name, edit_cover.getvalue())
                        update_data["cover_image"] = new_cover_name
                        
                    supabase.table("books").update(update_data).eq("id", target_id).execute()
                    
                    st.session_state['scroll_up'] = True
                    st.session_state['edit_book_id'] = None
                    st.session_state['toast_msg'] = "책 정보가 성공적으로 수정되었습니다!"
                    st.session_state['toast_icon'] = "✅"
                    st.rerun()
                    
            with col2:
                if st.button("🗑️ 삭제"):
                    supabase.table("books").delete().eq("id", target_id).execute()
                    
                    st.session_state['scroll_up'] = True
                    st.session_state['edit_book_id'] = None
                    st.session_state['toast_msg'] = "책이 삭제되었습니다."
                    st.session_state['toast_icon'] = "🗑️"
                    st.rerun()
                    
            with col3:
                if st.button("❌ 취소"):
                    st.session_state['scroll_up'] = True
                    st.session_state['edit_book_id'] = None
                    st.rerun()

    else:
        st.subheader("📖 나의 서재 (전체 목록)")
        
        if not books:
            st.info("아직 등록된 책이 없습니다. '추가하기' 탭에서 책을 등록해 보세요!")
        else:
            search_query = st.text_input("🔍 도서명 또는 작가명으로 검색하세요...", "")
            
            filter_col, sort_col = st.columns([3, 1])
            with filter_col:
                with st.expander("🔍 상세 필터로 골라보기"):
                    st.markdown("**플랫폼 필터**")
                    f_pubs = []
                    f_p_cols = st.columns(len(platforms_list))
                    for i, p_name in enumerate(platforms_list):
                        with f_p_cols[i]:
                            if st.checkbox(p_name, key=f"f_pub_{i}"): f_pubs.append(p_name)
                    
                    st.markdown("**소장 형태 필터**")
                    f_fmts = []
                    f_f1, f_f2 = st.columns(2)
                    with f_f1:
                        if st.checkbox("e-book", key="f_fmt_eb"): f_fmts.append("e-book")
                    with f_f2:
                        if st.checkbox("도서", key="f_fmt_bk"): f_fmts.append("도서")
                    
                    st.markdown("**상태 필터**")
                    f_stats = []
                    f_s1, f_s2, f_s3 = st.columns(3)
                    with f_s1:
                        if st.checkbox("연재중", key="f_st_ing"): f_stats.append("연재중")
                    with f_s2:
                        if st.checkbox("완결", key="f_st_end"): f_stats.append("완결")
                    with f_s3:
                        if st.checkbox("휴재", key="f_st_pause"): f_stats.append("휴재")
            
            # 🔥 새로 추가된 고급 정렬 기능
            with sort_col:
                st.markdown("**정렬 방식**")
                sort_order = st.selectbox("정렬 기준", ["등록일순", "이름순", "별점순", "연재 시작일순", "완결일순", "연재기간순"], label_visibility="collapsed")
                sort_direction = st.selectbox("오름/내림차순", ["내림차순 (최신/높은순) ⬇️", "오름차순 (과거/낮은순) ⬆️"], label_visibility="collapsed")
            
            st.write("---")
            
            filtered_books = []
            for book in books:
                if search_query:
                    q = search_query.lower()
                    if not (q in book.get('title', '').lower() or q in (book.get('writer') or '').lower() or q in (book.get('illustrator') or '').lower()):
                        continue
                
                b_pubs = book.get("publisher") or []
                b_fmts = book.get("format") or []
                b_stats = book.get("status") or []
                
                if f_pubs and not any(p in b_pubs for p in f_pubs): continue
                if f_fmts and not any(f in b_fmts for f in f_fmts): continue
                if f_stats and not any(s in b_stats for s in f_stats): continue
                
                filtered_books.append(book)
            
            # 🔥 정렬 로직 실행
            is_reverse = True if "내림차순" in sort_direction else False
            
            if sort_order == "이름순":
                filtered_books.sort(key=lambda x: x.get('title', ''), reverse=is_reverse)
            elif sort_order == "별점순":
                filtered_books.sort(key=lambda x: x.get('rating') or 0, reverse=is_reverse)
            elif sort_order == "등록일순":
                filtered_books.sort(key=lambda x: x.get('created_at', ''), reverse=is_reverse)
            elif sort_order == "연재 시작일순":
                # 날짜 빈칸 처리: 내림차순일 땐 맨 아래(0000), 오름차순일 땐 맨 아래(9999)로 보내기
                empty_date = "0000-00-00" if is_reverse else "9999-99-99"
                filtered_books.sort(key=lambda x: x.get('start_date') or empty_date, reverse=is_reverse)
            elif sort_order == "완결일순":
                empty_date = "0000-00-00" if is_reverse else "9999-99-99"
                filtered_books.sort(key=lambda x: x.get('completion_date') or empty_date, reverse=is_reverse)
            elif sort_order == "연재기간순":
                def calc_duration(b):
                    start = b.get("start_date") or ""
                    comp = b.get("completion_date") or ""
                    stat = b.get("status") or []
                    
                    empty_val = -999999 if is_reverse else 999999
                    if not start: return empty_val
                    
                    try:
                        s_dt = datetime.strptime(start, "%Y-%m-%d")
                        if comp:
                            c_dt = datetime.strptime(comp, "%Y-%m-%d")
                            return (c_dt - s_dt).days + 1
                        elif "연재중" in stat:
                            return (datetime.now() - s_dt).days + 1
                        else:
                            return empty_val
                    except:
                        return empty_val
                        
                filtered_books.sort(key=calc_duration, reverse=is_reverse)
            
            if not filtered_books:
                st.warning("🔍 조건에 일치하는 책이 없습니다.")
            else:
                cols = st.columns(5)
                for display_idx, book in enumerate(filtered_books):
                    with cols[display_idx % 5]:
                        with st.container(border=True):
                            cover_filename = book.get("cover_image")
                            if cover_filename:
                                cover_url = supabase.storage.from_("covers").get_public_url(cover_filename)
                            else:
                                cover_url = "https://via.placeholder.com/150x210.png?text=No+Cover&bg=f0f2f6"
                            
                            title = book.get('title', '')
                            writer = book.get('writer') or "-"
                            illustrator = book.get('illustrator') or "-"
                            
                            pub_val = book.get("publisher") or []
                            pub_str = ", ".join(pub_val) if pub_val else "미입력"
                            
                            fmt_val = book.get("format") or []
                            fmt_str = ", ".join(fmt_val) if fmt_val else "미입력"
                            
                            raw_status = book.get("status") or []
                            status_str = ", ".join(raw_status) if raw_status else "미입력"
                            
                            start_date = book.get("start_date") or ""
                            comp_date = book.get("completion_date") or ""
                            date_str = "&nbsp;"
                            days_str = "&nbsp;"
                            
                            if start_date or comp_date:
                                date_str = f"기간: {start_date if start_date else '?'} ~ {comp_date if comp_date else '?'}"
                                if start_date and comp_date:
                                    try:
                                        s_dt = datetime.strptime(start_date, "%Y-%m-%d")
                                        c_dt = datetime.strptime(comp_date, "%Y-%m-%d")
                                        days = (c_dt - s_dt).days + 1
                                        if days > 0: days_str = f"총 {days}일"
                                    except ValueError: pass
                                elif start_date and "연재중" in raw_status:
                                    try:
                                        s_dt = datetime.strptime(start_date, "%Y-%m-%d")
                                        c_dt = datetime.now()
                                        days = (c_dt - s_dt).days + 1
                                        if days > 0: days_str = f"연재 {days}일차"
                                    except ValueError: pass
                            
                            book_rating = book.get('rating') or 0
                            rating_str = "⭐" * book_rating if book_rating > 0 else "⭐ 평가 없음"
                            
                            card_html = f"""<div style="display: flex; flex-direction: column; height: 100%;">
<div style="display: flex; flex-direction: row; gap: 12px; margin-bottom: 12px;">
<div style="flex: 0 0 45%;">
<img src="{cover_url}" style="width: 100%; aspect-ratio: 150/210; object-fit: contain; background-color: #f0f2f6; border: 1px solid #eee; border-radius: 2px;">
</div>
<div style="flex: 1; display: flex; flex-direction: column; justify-content: flex-start; padding-top: 2px;">
<div style="font-size: 1.3em; font-weight: 800; color: #111; margin-bottom: 8px; line-height: 1.1;">{pub_str}</div>
<div style="font-size: 0.9em; color: #444; margin-bottom: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">글: {writer}</div>
<div style="font-size: 0.9em; color: #444; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">그림: {illustrator}</div>
</div>
</div>
<div style="font-size: 1.05em; font-weight: 700; color: #222; margin-bottom: 12px; line-height: 1.3; min-height: 1.3em;">{title}</div>
<div style="font-size: 0.9em; color: #333; margin-bottom: 4px;">{date_str}</div>
<div style="font-size: 0.9em; color: #333; margin-bottom: 8px;">{days_str}</div>
<div style="font-size: 0.75em; color: #999; margin-bottom: 10px;">[형태: {fmt_str} | 상태: {status_str}]</div>
<div style="font-size: 1.2em; color: #FFD700; font-weight: bold; margin-bottom: 5px;">{rating_str}</div>
</div>"""
                            st.markdown(card_html, unsafe_allow_html=True)
                            
                            if st.button("수정", key=f"edit_btn_{book['id']}"):
                                st.session_state['edit_book_id'] = book['id']
                                st.session_state['scroll_up'] = True
                                st.rerun()

# ==========================================
# 탭 2: 직접 여러 권 추가하기
# ==========================================
with tab2:
    st.subheader("📚 여러 권 한 번에 추가하기")
    num_books = st.number_input("한 번에 등록할 책의 개수를 선택하세요:", min_value=1, max_value=20, value=4)
    
    with st.form("batch_add_form", clear_on_submit=True):
        batch_data = []
        for i in range(0, num_books, 4):
            cols = st.columns(4)
            for j in range(4):
                current_idx = i + j
                if current_idx < num_books:
                    with cols[j]:
                        with st.container(border=True):
                            st.markdown(f"**[{current_idx + 1}번째 책]**")
                            st.markdown("**책 제목**")
                            b_title = st.text_input("책 제목", key=f"title_{current_idx}", label_visibility="collapsed")
                            
                            c_w1, c_w2 = st.columns(2)
                            with c_w1:
                                b_writer = st.text_input("글작가", placeholder="글작가", key=f"writer_{current_idx}", label_visibility="collapsed")
                            with c_w2:
                                b_illust = st.text_input("그림작가", placeholder="그림작가", key=f"illust_{current_idx}", label_visibility="collapsed")
                            
                            st.markdown("**플랫폼** (중복 선택)")
                            b_pub = []
                            for p_idx, p_name in enumerate(platforms_list):
                                if st.checkbox(p_name, key=f"pub_chk_{current_idx}_{p_idx}"): b_pub.append(p_name)
                            
                            st.markdown("**소장 형태**")
                            b_fmt = []
                            if st.checkbox("e-book", key=f"fmt_eb_{current_idx}"): b_fmt.append("e-book")
                            if st.checkbox("도서", key=f"fmt_bk_{current_idx}"): b_fmt.append("도서")
                            
                            st.markdown("**상태**")
                            b_status = []
                            if st.checkbox("연재중", key=f"st_ing_{current_idx}"): b_status.append("연재중")
                            if st.checkbox("완결", key=f"st_end_{current_idx}"): b_status.append("완결")
                            if st.checkbox("휴재", key=f"st_pause_{current_idx}"): b_status.append("휴재")
                            
                            st.markdown("**별점**")
                            b_rating = st.selectbox("별점", [5, 4, 3, 2, 1, 0], index=5, format_func=format_stars, key=f"rating_{current_idx}", label_visibility="collapsed")
                            
                            c_d1, c_d2 = st.columns(2)
                            with c_d1:
                                b_start_date = st.text_input("연재 시작일", placeholder="연재 시작(2026-01-01)", key=f"start_{current_idx}", label_visibility="collapsed")
                            with c_d2:
                                b_comp_date = st.text_input("완결일", placeholder="완결(2026-09-06)", key=f"comp_{current_idx}", label_visibility="collapsed")
                            
                            st.markdown("**표지 이미지**")
                            b_cover = st.file_uploader("표지 이미지", type=['png', 'jpg', 'jpeg'], key=f"cover_{current_idx}", label_visibility="collapsed")
                            
                            batch_data.append({
                                "title": b_title, "writer": b_writer, "illustrator": b_illust,
                                "publisher": b_pub, "format": b_fmt, "status": b_status,
                                "rating": b_rating, "start_date": b_start_date, "completion_date": b_comp_date,
                                "cover_raw": b_cover
                            })
            
        submitted = st.form_submit_button("선택한 책 클라우드에 등록하기 ☁️")
        
        if submitted:
            valid_data = []
            dup_titles = []
            
            for data in batch_data:
                title = data['title'].strip()
                if title:
                    if is_duplicate_title(title, books):
                        dup_titles.append(title)
                    
                    cover_bytes = None
                    if data['cover_raw'] is not None:
                        cover_bytes = data['cover_raw'].getvalue()
                    
                    valid_data.append({
                        "title": title, "writer": data['writer'], "illustrator": data['illustrator'],
                        "publisher": data['publisher'], "format": data['format'], "status": data['status'],
                        "rating": data['rating'], "start_date": data['start_date'], "completion_date": data['completion_date'],
                        "cover_bytes": cover_bytes
                    })
            
            if not valid_data:
                st.warning("⚠️ 입력된 책 제목이 없습니다.")
            elif dup_titles:
                st.session_state['pending_batch'] = valid_data
                st.session_state['dup_titles'] = dup_titles
                st.session_state['scroll_up'] = True
                st.rerun()
            else:
                added_count = 0
                db_inserts = []
                for item in valid_data:
                    cover_filename = None
                    if item['cover_bytes'] is not None:
                        cover_filename = f"{int(time.time()*1000)}_{added_count}.png"
                        supabase.storage.from_("covers").upload(cover_filename, item['cover_bytes'])
                    
                    db_inserts.append({
                        "title": item['title'], "writer": item['writer'], "illustrator": item['illustrator'],
                        "publisher": item['publisher'], "format": item['format'], "status": item['status'],
                        "rating": item['rating'], "start_date": item['start_date'], "completion_date": item['completion_date'],
                        "cover_image": cover_filename
                    })
                    added_count += 1
                
                if db_inserts:
                    supabase.table("books").insert(db_inserts).execute()
                    
                st.session_state['toast_msg'] = f"✅ {added_count}권의 책이 클라우드에 등록되었습니다!"
                st.session_state['toast_icon'] = "🎉"
                st.session_state['scroll_up'] = True
                st.rerun()

# ==========================================
# 탭 3: 엑셀(한셀) 파일로 대량 추가하기
# ==========================================
with tab3:
    st.subheader("📁 엑셀/한셀 파일로 클라우드에 대량 등록하기")
    st.info("""
    미리 작성된 엑셀(.xlsx) 파일을 업로드하면 수십 권의 책을 1초 만에 클라우드에 등록할 수 있습니다.  
    **팁:** 플랫폼, 소장 형태, 상태에 2개 이상 입력하려면 쉼표(,)로 구분해서 적어주세요. (예: `리디, 카카오페이지`)
    """)
    
    template_df = pd.DataFrame(columns=['책 제목', '글작가', '그림작가', '플랫폼', '소장 형태', '상태', '별점', '연재 시작일', '완결일'])
    template_output = BytesIO()
    with pd.ExcelWriter(template_output, engine='openpyxl') as writer:
        template_df.to_excel(writer, index=False, sheet_name='업로드양식')
    
    st.download_button("📥 업로드용 빈 양식 다운로드", data=template_output.getvalue(), file_name='upload_template.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    
    st.write("---")
    uploaded_file = st.file_uploader("작성한 엑셀/한셀 파일(.xlsx)을 업로드해주세요", type=['xlsx'])
    
    if uploaded_file is not None:
        if st.button("파일 속 데이터 클라우드에 등록하기 ☁️"):
            try:
                df_upload = pd.read_excel(uploaded_file)
                valid_data = []
                dup_titles = []
                
                for index, row in df_upload.iterrows():
                    title = str(row.get('책 제목', '')).strip()
                    if not title or title == 'nan': continue
                        
                    if is_duplicate_title(title, books):
                        dup_titles.append(title)
                        
                    writer = str(row.get('글작가', '')).strip()
                    if writer == 'nan': writer = ''
                    illustrator = str(row.get('그림작가', '')).strip()
                    if illustrator == 'nan': illustrator = ''
                    
                    pubs = parse_excel_cell(row.get('플랫폼', ''))
                    fmts = parse_excel_cell(row.get('소장 형태', ''))
                    stats = parse_excel_cell(row.get('상태', ''))
                    
                    try: rating = int(row.get('별점', 0))
                    except Exception: rating = 0
                        
                    start_date = str(row.get('연재 시작일', '')).strip()
                    if start_date == 'nan': start_date = ''
                    comp_date = str(row.get('완결일', '')).strip()
                    if comp_date == 'nan': comp_date = ''
                    
                    valid_data.append({
                        "title": title, "writer": writer, "illustrator": illustrator,
                        "publisher": pubs, "format": fmts, "status": stats,
                        "rating": rating, "start_date": start_date, "completion_date": comp_date,
                        "cover_image": None
                    })
                
                if not valid_data:
                    st.warning("⚠️ 등록할 데이터(책 제목)를 찾을 수 없습니다. 양식을 확인해주세요.")
                elif dup_titles:
                    st.session_state['pending_excel'] = valid_data
                    st.session_state['excel_dup_titles'] = dup_titles
                    st.session_state['scroll_up'] = True
                    st.rerun()
                else:
                    added = len(valid_data)
                    supabase.table("books").insert(valid_data).execute()
                    
                    st.session_state['toast_msg'] = f"✅ {added}권의 데이터가 클라우드에 완벽하게 등록되었습니다!"
                    st.session_state['toast_icon'] = "🎉"
                    st.session_state['scroll_up'] = True
                    st.rerun()
                    
            except Exception as e:
                st.error("파일을 읽는 중 문제가 발생했습니다. '업로드용 빈 양식'을 사용하셨는지 확인해주세요.")