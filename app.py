import streamlit as st
import google.generativeai as genai
import os
import json
import datetime
from duckduckgo_search import DDGS
from dataclasses import dataclass
from typing import List

# -----------------------------------------------------------------------------
# 1. 설정 및 상수
# -----------------------------------------------------------------------------

st.set_page_config(
    page_title="NRF Insight",
    page_icon="🏢",
    layout="centered",
    initial_sidebar_state="collapsed"
)

API_KEY = os.environ.get("API_KEY") 
if not API_KEY and "API_KEY" in st.secrets:
    API_KEY = st.secrets["API_KEY"]

if not API_KEY:
    st.error("Google Gemini API Key 설정이 필요합니다.")
    st.stop()

genai.configure(api_key=API_KEY)

# 검색어(Query)를 조금 더 구체적인 '뉴스 키워드'로 변경했습니다.
SECTIONS = {
    "NRF_NEWS": {
        "label": "한국연구재단 주요 기사", 
        "short_label": "재단소식", 
        "query": "한국연구재단 사업 공모 선정 결과 보도자료", 
        "icon": "🏢"
    },
    "SCI_TECH": {
        "label": "과학기술분야 동향", 
        "short_label": "과기동향", 
        "query": "과학기술정보통신부 R&D 예산 정책 기술개발 뉴스", 
        "icon": "⚛️"
    },
    "HUMANITIES": {
        "label": "인문사회분야 동향", 
        "short_label": "인문동향", 
        "query": "인문사회 학술연구지원사업 정책 동향 뉴스", 
        "icon": "📖"
    },
    "UNI_SUPPORT": {
        "label": "대학재정지원사업 동향", 
        "short_label": "대학지원", 
        "query": "교육부 대학지원사업 RISE 글로컬대학3.0 선정 뉴스", 
        "icon": "🎓"
    }
}

# -----------------------------------------------------------------------------
# 2. 스타일링 (CSS)
# -----------------------------------------------------------------------------

st.markdown("""
<style>
    @import url("https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.8/dist/web/static/pretendard.css");
    
    html, body, [class*="css"] {
        font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif !important;
        background-color: #F2F4F6;
        color: #333333;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;} 
    .stDeployButton {display:none;}
    
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 5rem !important;
        max-width: 600px;
    }

    .app-header {
        background-color: white;
        padding: 1.5rem;
        border-radius: 20px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.05);
        margin-bottom: 1.5rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .app-title {
        font-size: 1.6rem;
        font-weight: 800;
        color: #1a1f27;
        margin: 0;
        letter-spacing: -0.5px;
    }
    .mascot-img {
        width: 45px;
        height: 45px;
        border-radius: 50%;
        object-fit: cover;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }

    .news-card {
        background-color: white;
        padding: 1.25rem;
        border-radius: 18px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.03);
        margin-bottom: 1rem;
        border: 1px solid white;
        text-decoration: none !important;
        display: block;
        transition: all 0.2s ease;
    }
    .news-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.08);
        border-color: #E5E8EB;
    }
    .news-card:active {
        transform: scale(0.98);
    }
    
    .card-meta {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 8px;
    }
    .source-tag {
        font-size: 0.75rem;
        font-weight: 700;
        color: #3182F6;
        background-color: rgba(49, 130, 246, 0.1);
        padding: 4px 8px;
        border-radius: 6px;
    }
    .date-tag {
        font-size: 0.75rem;
        color: #8B95A1;
    }
    .card-title {
        font-size: 1.15rem;
        font-weight: 700;
        color: #191F28;
        margin: 0 0 6px 0;
        line-height: 1.4;
        word-break: keep-all;
    }
    .card-snippet {
        font-size: 0.9rem;
        color: #4E5968;
        line-height: 1.5;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
        margin: 0;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: transparent;
        padding: 0 0 15px 0;
    }
    .stTabs [data-baseweb="tab"] {
        height: 40px;
        padding: 0 16px;
        border-radius: 20px;
        background-color: white;
        border: 1px solid #E5E8EB;
        font-weight: 600;
        font-size: 0.9rem;
        color: #6B7684;
    }
    .stTabs [aria-selected="true"] {
        background-color: #3182F6 !important;
        color: white !important;
        border: none !important;
        box-shadow: 0 4px 12px rgba(49, 130, 246, 0.3);
    }
    .stSpinner > div {
        border-top-color: #3182F6 !important;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 3. 데이터 및 로직 (핵심 수정됨)
# -----------------------------------------------------------------------------

@dataclass
class NewsArticle:
    title: str
    url: str
    source: str
    date: str
    snippet: str

def fetch_news_hybrid(topic_query: str) -> List[NewsArticle]:
    raw_results = []
    
    # [수정됨] .text() 대신 .news() 함수를 사용해서 진짜 '뉴스'만 가져옵니다.
    try:
        with DDGS() as ddgs:
            # region='kr-kr'로 한국 뉴스만 타겟팅
            news_gen = ddgs.news(
                keywords=topic_query,
                region='kr-kr',
                safesearch='off',
                max_results=5
            )
            for r in news_gen:
                raw_results.append(r)
    except Exception as e:
        print(f"News Search Error: {e}")
        # 뉴스 검색 실패시 일반 검색으로 백업 시도 (하지만 '뉴스' 키워드 추가)
        try:
            with DDGS() as ddgs:
                text_gen = ddgs.text(f"{topic_query} 뉴스", region='kr-kr', max_results=5)
                for r in text_gen:
                    raw_results.append(r)
        except:
            pass

    if not raw_results:
        return []

    # AI에게 데이터 정리 요청
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # AI가 헷갈리지 않게 데이터 구조를 설명해주는 프롬프트
    prompt = f"""
    Here is a raw list of search results about "{topic_query}":
    {json.dumps(raw_results, ensure_ascii=False)}

    Please convert this into a JSON array of news objects.
    - "title": Clean up the headline.
    - "date": If the source has a date, use it. If not, use "{datetime.date.today().strftime('%Y.%m.%d')}".
    - "source": Extract the press/media name (e.g. 연합뉴스, 전자신문).
    - "url": The direct link.
    - "snippet": Summarize the content into 1 simple Korean sentence.

    IMPORTANT: Return ONLY the JSON array. No markdown, no code blocks.
    """
    
    try:
        response = model.generate_content(prompt)
        text = response.text.replace("```json", "").replace("```", "").strip()
        data = json.loads(text)
        
        articles = [NewsArticle(
            title=item.get('title', '제목 없음'),
            url=item.get('url', '#'),
            source=item.get('source', 'News'),
            date=item.get('date', ''),
            snippet=item.get('snippet', '')
        ) for item in data]
        
        return articles
    except Exception as e:
        # AI 변환 실패 시 원본 데이터로 최대한 보여주기
        fallback = []
        for r in raw_results:
            # ddgs.news와 ddgs.text의 리턴 키값이 조금 다를 수 있어 처리
            title = r.get('title')
            url = r.get('url') or r.get('href')
            source = r.get('source') or 'Search'
            body = r.get('body') or r.get('snippet') or ''
            date = r.get('date') or datetime.date.today().strftime('%m.%d')
            
            # 날짜 포맷이 이상하게 길면 자르기
            if date and len(str(date)) > 10:
                date = str(date)[:10]

            fallback.append(NewsArticle(
                title=title,
                url=url,
                source=source,
                date=date,
                snippet=body
            ))
        return fallback

# -----------------------------------------------------------------------------
# 4. 메인 화면
# -----------------------------------------------------------------------------

def main():
    if 'news_cache' not in st.session_state:
        st.session_state.news_cache = {}

    st.markdown(f"""
    <div class="app-header">
        <div>
            <div style="font-size:0.8rem; color:#8B95A1; font-weight:600; margin-bottom:2px;">KOREA RESEARCH FOUNDATION</div>
            <h1 class="app-title">NRF Insight</h1>
        </div>
        <img src="https://www.nrf.re.kr/resources/img/contents/character/nulph_intro.png" class="mascot-img">
    </div>
    """, unsafe_allow_html=True)

    tab_labels = [config['short_label'] for config in SECTIONS.values()]
    tabs = st.tabs(tab_labels)

    for i, (section_key, config) in enumerate(SECTIONS.items()):
        with tabs[i]:
            news_items = []
            
            if st.button("🔄 뉴스 새로고침", key=f"refresh_{i}", use_container_width=True):
                if section_key in st.session_state.news_cache:
                    del st.session_state.news_cache[section_key]
                st.rerun()

            if section_key in st.session_state.news_cache:
                news_items = st.session_state.news_cache[section_key]
            else:
                with st.spinner(f"'{config['short_label']}' 관련 최신 기사를 찾는 중..."):
                    news_items = fetch_news_hybrid(config['query'])
                    if news_items:
                        st.session_state.news_cache[section_key] = news_items

            if news_items:
                for article in news_items:
                    st.markdown(f"""
                    <a href="{article.url}" target="_blank" class="news-card">
                        <div class="card-meta">
                            <span class="source-tag">{article.source}</span>
                            <span class="date-tag">{article.date}</span>
                        </div>
                        <h3 class="card-title">{article.title}</h3>
                        <p class="card-snippet">{article.snippet}</p>
                    </a>
                    """, unsafe_allow_html=True)
            elif section_key not in st.session_state.news_cache:
                pass

if __name__ == "__main__":
    main()
