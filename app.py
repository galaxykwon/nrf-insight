
import streamlit as st
import google.generativeai as genai
import os
import json
import datetime
from dataclasses import dataclass
from typing import List

# -----------------------------------------------------------------------------
# 1. 설정 및 상수 (Configuration & Constants)
# -----------------------------------------------------------------------------

st.set_page_config(
    page_title="NRF Insight",
    page_icon="🏢",
    layout="centered",  # 모바일 느낌을 위해 centered 유지
    initial_sidebar_state="collapsed"
)

# API 키 설정 (환경변수 또는 st.secrets 사용 권장)
# 로컬 실행 시 os.environ.get("API_KEY") 부분에 본인의 키를 직접 입력해도 됩니다.
API_KEY = os.environ.get("API_KEY") 

if not API_KEY and "API_KEY" in st.secrets:
    API_KEY = st.secrets["API_KEY"]

if not API_KEY:
    st.error("Google Gemini API Key가 설정되지 않았습니다. 환경변수 API_KEY를 설정해주세요.")
    st.stop()

genai.configure(api_key=API_KEY)

# 섹션 정의 (React 코드의 constants.ts 대응)
SECTIONS = {
    "NRF_NEWS": {
        "label": "한국연구재단 주요 기사",
        "short_label": "재단소식",
        "query": "한국연구재단 최근 주요 뉴스 보도자료 성과",
        "icon": "🏢"
    },
    "SCI_TECH": {
        "label": "과학기술분야 동향",
        "short_label": "과기동향",
        "query": "대한민국 과학기술 R&D 정책 기술 개발 최신 동향 뉴스",
        "icon": "⚛️"
    },
    "HUMANITIES": {
        "label": "인문사회분야 동향",
        "short_label": "인문동향",
        "query": "대한민국 인문사회 학술 연구 지원 정책 최신 뉴스 동향",
        "icon": "📖"
    },
    "UNI_SUPPORT": {
        "label": "대학재정지원사업 동향",
        "short_label": "대학지원",
        "query": "교육부 대학재정지원사업 RISE 사업 글로컬대학 LINC 3.0 BK21 최신 뉴스",
        "icon": "🎓"
    }
}

# -----------------------------------------------------------------------------
# 2. 스타일링 (CSS) - React 앱의 디자인을 모방
# -----------------------------------------------------------------------------

st.markdown("""
<style>
    /* 전체 폰트 및 배경 설정 */
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Noto Sans KR', sans-serif;
        background-color: #f9fafb;
    }

    /* 헤더 스타일 */
    .header-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 1rem 0;
        border-bottom: 1px solid #e5e7eb;
        background-color: white;
        margin-bottom: 1rem;
    }
    .app-title {
        font-size: 1.5rem;
        font-weight: 900;
        color: #1e3a8a; /* blue-900 */
        margin: 0;
        line-height: 1.2;
    }
    .section-subtitle {
        font-size: 0.875rem;
        color: #6b7280;
        font-weight: 500;
        margin: 0;
    }
    .mascot-img {
        width: 50px;
        height: 50px;
        border-radius: 50%;
        border: 1px solid #f3f4f6;
        object-fit: cover;
        /* Streamlit 이미지 정렬 보정 */
        margin-left: 10px;
    }

    /* 뉴스 카드 스타일 */
    .news-card {
        background-color: white;
        padding: 1.2rem;
        border-radius: 0.75rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        border: 1px solid #f3f4f6;
        margin-bottom: 1rem;
        transition: transform 0.1s;
        text-decoration: none;
        display: block;
        color: inherit;
    }
    .news-card:hover {
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        text-decoration: none;
    }
    .card-meta {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin-bottom: 0.5rem;
    }
    .source-tag {
        font-size: 0.7rem;
        font-weight: 700;
        color: #1d4ed8;
        background-color: #eff6ff;
        padding: 0.1rem 0.4rem;
        border-radius: 0.25rem;
        border: 1px solid #dbeafe;
    }
    .date-tag {
        font-size: 0.7rem;
        color: #9ca3af;
        font-weight: 500;
    }
    .card-title {
        font-size: 1.1rem;
        font-weight: 700;
        color: #1f2937;
        margin: 0 0 0.5rem 0;
        line-height: 1.4;
        word-break: keep-all;
    }
    .card-snippet {
        font-size: 0.875rem;
        color: #6b7280;
        line-height: 1.5;
        margin: 0;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }
    
    /* Streamlit 기본 요소 숨기기 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display:none;}
    
    /* 탭 스타일 조정 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: white;
        padding: 10px 0;
        position: sticky;
        top: 0;
        z-index: 100;
    }
    .stTabs [data-baseweb="tab"] {
        height: auto;
        padding: 8px 16px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        background-color: #f3f4f6;
        border: none;
    }
    .stTabs [aria-selected="true"] {
        background-color: #eff6ff !important;
        color: #1d4ed8 !important;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 3. 서비스 로직 (Gemini Service)
# -----------------------------------------------------------------------------

@dataclass
class NewsArticle:
    title: str
    url: str
    source: str
    date: str
    snippet: str

def fetch_news_from_gemini(topic_query: str) -> List[NewsArticle]:
    """Gemini API를 사용하여 뉴스 기사를 검색하고 구조화된 데이터로 반환합니다."""
    
    model = genai.GenerativeModel('gemini-1.5-flash') # React 코드의 2.5 대신 안정적인 1.5 flash 사용
    
    prompt = f"""
      Search for the latest (last 7 days) Korean news articles about "{topic_query}". 
      Select the 6 most relevant and authoritative articles.
      Sort the list by date descending (newest article first).
      
      Return a raw JSON array (no markdown code blocks) of objects with these exact keys:
      - "title": A clear, concise headline in Korean (NOT a URL).
      - "date": The publication date in 'YYYY.MM.DD' format.
      - "source": The name of the news outlet.
      - "url": The direct link to the article.
      - "snippet": A 1-sentence summary.
    """

    try:
        # Google Search Tool 사용 설정
        response = model.generate_content(
            prompt,
            tools='google_search_retrieval'
        )
        
        text = response.text
        # Markdown 코드 블록 제거
        clean_text = text.replace("```json", "").replace("```", "").strip()
        
        data = json.loads(clean_text)
        
        articles = []
        for item in data:
            articles.append(NewsArticle(
                title=item.get('title', '제목 없음'),
                url=item.get('url', '#'),
                source=item.get('source', 'News'),
                date=item.get('date', ''),
                snippet=item.get('snippet', '')
            ))
            
        # 날짜 기준 내림차순 정렬 (최신순)
        articles.sort(key=lambda x: x.date, reverse=True)
        
        return articles

    except Exception as e:
        # JSON 파싱 실패 혹은 API 오류 시 빈 리스트 반환 (혹은 에러 처리)
        # 실제 운영 시에는 여기서 로깅을 하거나 사용자에게 알림
        print(f"Error fetching news: {e}")
        return []

# -----------------------------------------------------------------------------
# 4. 메인 앱 로직
# -----------------------------------------------------------------------------

def main():
    # 세션 상태 초기화 (데이터 캐싱용)
    if 'news_cache' not in st.session_state:
        st.session_state.news_cache = {}

    # 1. 헤더 영역 (커스텀 HTML로 React Header와 비슷하게 구성)
    # Streamlit 컬럼을 사용하여 레이아웃 배치
    col_header, col_refresh = st.columns([4, 1])
    
    with col_header:
        # 현재 선택된 탭을 세션 스테이트 등에서 추적하기 어려우므로 탭 내부에서 렌더링하거나
        # 탭 선택에 따라 바뀌는 서브타이틀은 아래 탭 로직에서 처리.
        # 여기서는 메인 타이틀만 표시
        st.markdown(
            f"""
            <div style="margin-top: 10px;">
                <h1 class="app-title">NRF Insight</h1>
            </div>
            """, 
            unsafe_allow_html=True
        )

    with col_refresh:
        # 새로고침 버튼과 마스코트
        # 버튼을 누르면 캐시를 비움
        if st.button("🔄", help="뉴스 새로고침"):
            st.session_state.news_cache = {}
            st.rerun()
            
        st.markdown(
            """
            <img src="https://www.nrf.re.kr/resources/img/contents/character/nulph_intro.png" class="mascot-img">
            """, 
            unsafe_allow_html=True
        )

    # 2. 탭 네비게이션
    tab_labels = [config['short_label'] for config in SECTIONS.values()]
    tabs = st.tabs(tab_labels)

    # 각 탭별 컨텐츠 렌더링
    for i, (section_key, config) in enumerate(SECTIONS.items()):
        with tabs[i]:
            # 서브타이틀 표시 (탭 내용 상단)
            st.markdown(f"<p class='section-subtitle'>📄 {config['label']}</p>", unsafe_allow_html=True)
            st.divider()

            # 데이터 로딩 로직
            news_items = []
            
            # 캐시에 있으면 캐시 사용, 없으면 API 호출
            if section_key in st.session_state.news_cache:
                news_items = st.session_state.news_cache[section_key]
            else:
                with st.spinner(f"'{config['short_label']}' 최신 기사를 분석 중입니다..."):
                    news_items = fetch_news_from_gemini(config['query'])
                    st.session_state.news_cache[section_key] = news_items

            # 뉴스 카드 렌더링
            if news_items:
                for article in news_items:
                    # 날짜 포맷팅 (YYYY.MM.DD -> MM.DD)
                    display_date = article.date
                    if len(display_date) >= 10:
                        display_date = display_date[5:] # 2024.05.21 -> 05.21

                    # HTML Card 렌더링
                    st.markdown(
                        f"""
                        <a href="{article.url}" target="_blank" class="news-card">
                            <div class="card-meta">
                                <span class="source-tag">{article.source}</span>
                                <span class="date-tag">{display_date}</span>
                            </div>
                            <h3 class="card-title">{article.title}</h3>
                            <p class="card-snippet">{article.snippet}</p>
                        </a>
                        """,
                        unsafe_allow_html=True
                    )
            else:
                st.info("관련된 최신 뉴스를 찾을 수 없습니다.")

if __name__ == "__main__":

    main()
