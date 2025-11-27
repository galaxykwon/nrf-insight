import streamlit as st
import google.generativeai as genai
import os
import json
import re  # 정규표현식(강력한 텍스트 필터) 모듈 추가
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

# API 키 설정
API_KEY = os.environ.get("API_KEY") 
if not API_KEY and "API_KEY" in st.secrets:
    API_KEY = st.secrets["API_KEY"]

if not API_KEY:
    st.error("Google Gemini API Key 설정이 필요합니다.")
    st.stop()

genai.configure(api_key=API_KEY)

SECTIONS = {
    "NRF_NEWS": {"label": "한국연구재단 주요 기사", "short_label": "재단소식", "query": "한국연구재단 최근 주요 뉴스 보도자료 성과", "icon": "🏢"},
    "SCI_TECH": {"label": "과학기술분야 동향", "short_label": "과기동향", "query": "대한민국 과학기술 R&D 정책 기술 개발 최신 동향 뉴스", "icon": "⚛️"},
    "HUMANITIES": {"label": "인문사회분야 동향", "short_label": "인문동향", "query": "대한민국 인문사회 학술 연구 지원 정책 최신 뉴스 동향", "icon": "📖"},
    "UNI_SUPPORT": {"label": "대학재정지원사업 동향", "short_label": "대학지원", "query": "교육부 대학재정지원사업 RISE 사업 글로컬대학 LINC 3.0 BK21 최신 뉴스", "icon": "🎓"}
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
# 3. 데이터 및 로직 (여기가 수정됨!)
# -----------------------------------------------------------------------------

@dataclass
class NewsArticle:
    title: str
    url: str
    source: str
    date: str
    snippet: str

def fetch_news_from_gemini(topic_query: str) -> List[NewsArticle]:
    # 2.0-flash가 검색에 더 최적화되어 있으나, 안정성을 위해 1.5-flash 유지하되 도구 설정 강화
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
      You are a news aggregator. Search for the latest Korean news articles about "{topic_query}".
      
      CRITICAL INSTRUCTIONS:
      1. Find 5 distinct news articles from reputable Korean sources.
      2. Output MUST be a valid JSON array.
      3. Do NOT use markdown code blocks (no ```json).
      4. Do NOT add any introductory text. Just the JSON.
      
      JSON Format:
      [
        {{
          "title": "Headline",
          "date": "YYYY.MM.DD",
          "source": "Publisher Name",
          "url": "Link",
          "snippet": "Short summary"
        }}
      ]
    """
    
    try:
        # tools 설정을 명확하게 지정
        response = model.generate_content(
            prompt, 
            tools='google_search_retrieval'
        )
        
        text = response.text
        
        # [강력 필터] 텍스트에서 JSON 부분만 정규표현식으로 추출
        match = re.search(r'\[.*\]', text, re.DOTALL)
        
        if match:
            json_str = match.group()
            data = json.loads(json_str)
            
            articles = [NewsArticle(
                title=item.get('title', '제목 없음'),
                url=item.get('url', '#'),
                source=item.get('source', 'News'),
                date=item.get('date', ''),
                snippet=item.get('snippet', '')
            ) for item in data]
            
            return sorted(articles, key=lambda x: x.date, reverse=True)
        else:
            # JSON을 못 찾았을 경우 에러 발생시키기 (디버깅용)
            raise ValueError(f"JSON 형식을 찾을 수 없음: {text[:100]}...")
            
    except Exception as e:
        # 화면에 에러를 출력해서 원인을 파악할 수 있게 함
        st.error(f"뉴스 검색 중 오류 발생: {e}")
        return []

# -----------------------------------------------------------------------------
# 4. 메인 화면 구성
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
        <img src="[https://www.nrf.re.kr/resources/img/contents/character/nulph_intro.png](https://www.nrf.re.kr/resources/img/contents/character/nulph_intro.png)" class="mascot-img">
    </div>
    """, unsafe_allow_html=True)

    tab_labels = [config['short_label'] for config in SECTIONS.values()]
    tabs = st.tabs(tab_labels)

    for i, (section_key, config) in enumerate(SECTIONS.items()):
        with tabs[i]:
            news_items = []
            
            # 새로고침 버튼 (위쪽으로 이동)
            if st.button("🔄 뉴스 새로고침", key=f"refresh_{i}", use_container_width=True):
                if section_key in st.session_state.news_cache:
                    del st.session_state.news_cache[section_key]
                st.rerun()

            if section_key in st.session_state.news_cache:
                news_items = st.session_state.news_cache[section_key]
            else:
                with st.spinner(f"'{config['label']}' 검색 중..."):
                    news_items = fetch_news_from_gemini(config['query'])
                    if news_items:
                        st.session_state.news_cache[section_key] = news_items

            if news_items:
                for article in news_items:
                    d_date = article.date[5:] if len(article.date) >= 10 else article.date
                    st.markdown(f"""
                    <a href="{article.url}" target="_blank" class="news-card">
                        <div class="card-meta">
                            <span class="source-tag">{article.source}</span>
                            <span class="date-tag">{d_date}</span>
                        </div>
                        <h3 class="card-title">{article.title}</h3>
                        <p class="card-snippet">{article.snippet}</p>
                    </a>
                    """, unsafe_allow_html=True)
            elif section_key not in st.session_state.news_cache:
                # 에러 메시지가 위에 떴을 테니 여기선 조용히
                pass

if __name__ == "__main__":
    main()
