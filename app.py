"""다국어 번역기 - Streamlit + OpenAI"""

import logging
import os

import openai
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("translator")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL")
MAX_CHARS = 5000

LANGUAGES = {"영어": "English", "일본어": "Japanese", "베트남어": "Vietnamese"}

SYSTEM_PROMPT = (
    "You are a professional translator. Translate the user's text into {target_language}. "
    "Output only the translated text without explanations, quotes, or notes. "
    "Preserve line breaks and formatting."
)


class TranslationError(Exception):
    """사용자에게 보여줄 한국어 메시지를 담은 예외."""


def translate(text: str, target_language: str) -> str:
    """text를 target_language(영문 언어명)로 번역해 번역문만 반환한다."""
    if os.getenv("MOCK_TRANSLATE") == "1":
        # 테스트용: API를 호출하지 않고 더미 결과 반환 (호출 여부는 로그로 확인)
        logger.info("MOCK_TRANSLATE_CALLED target=%s", target_language)
        if text.strip() == "__MOCK_ERROR__":
            raise TranslationError("번역 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")
        return f"[{target_language}] {text}"
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(target_language=target_language)},
        {"role": "user", "content": text},
    ]
    try:
        try:
            response = client.chat.completions.create(
                model=OPENAI_MODEL, messages=messages, temperature=0.2
            )
        except openai.BadRequestError as e:
            # 일부 모델은 temperature를 지원하지 않으므로 해당 파라미터 없이 재시도
            if "temperature" not in str(e):
                raise
            response = client.chat.completions.create(model=OPENAI_MODEL, messages=messages)
    except openai.AuthenticationError:
        logger.exception("OpenAI authentication failed")
        raise TranslationError("API 키를 확인해주세요.")
    except openai.NotFoundError:
        logger.exception("OpenAI model not found: %s", OPENAI_MODEL)
        raise TranslationError("모델명(OPENAI_MODEL)을 확인해주세요.")
    except openai.RateLimitError:
        logger.exception("OpenAI rate limit")
        raise TranslationError("요청이 많습니다. 잠시 후 다시 시도해주세요.")
    except Exception:
        logger.exception("Translation failed")
        raise TranslationError("번역 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")

    return (response.choices[0].message.content or "").strip()


CUSTOM_CSS = """
<style>
.block-container { max-width: 760px; padding-top: 2.5rem; }
h1 { word-break: keep-all; }
.char-count { text-align: right; font-size: 0.85rem; color: rgba(128, 128, 128, 0.95); margin-top: -0.5rem; }
.char-count.over { color: #e5484d; font-weight: 600; }
.app-subtitle { color: rgba(128, 128, 128, 0.95); margin-top: -0.75rem; margin-bottom: 1.25rem; }
div[data-testid="stButton"] > button {
    border-radius: 999px;
    padding: 0.55rem 0.75rem;
    font-weight: 600;
    border: 1px solid rgba(128, 128, 128, 0.35);
    transition: transform 0.12s ease, box-shadow 0.12s ease, border-color 0.12s ease;
}
div[data-testid="stButton"] > button:hover:enabled {
    transform: translateY(-1px);
    border-color: #4f7cff;
    box-shadow: 0 4px 14px rgba(79, 124, 255, 0.25);
}
div[data-testid="stTextArea"] textarea { font-size: 1rem; line-height: 1.6; }
div[data-testid="stCode"] pre { font-size: 1rem; line-height: 1.6; padding: 1rem 1.1rem; }
div[data-testid="stCode"] pre,
div[data-testid="stCode"] code,
div[data-testid="stCode"] code span {
    font-family: "Source Sans 3", "Source Sans Pro", "Malgun Gothic", "Apple SD Gothic Neo",
                 "Hiragino Sans", "Yu Gothic", sans-serif !important;
    white-space: pre-wrap;
}
@media (max-width: 640px) {
    .block-container { padding-left: 1rem; padding-right: 1rem; padding-top: 1.5rem; }
    h1 { font-size: 2rem !important; }
    div[data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; gap: 0.5rem; }
    div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] { min-width: 0 !important; width: auto !important; flex: 1 1 0 !important; }
    div[data-testid="stButton"] > button { padding: 0.5rem 0.25rem; font-size: 0.9rem; }
}
</style>
"""

st.set_page_config(page_title="다국어 번역기", page_icon="🌐", layout="centered")
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

st.title("🌐 다국어 번역기")
st.markdown(
    '<p class="app-subtitle">번역할 문장을 입력하고 언어를 선택하세요.</p>',
    unsafe_allow_html=True,
)

config_missing = not OPENAI_API_KEY or not OPENAI_MODEL
if config_missing:
    st.error(".env 파일에 OPENAI_API_KEY와 OPENAI_MODEL을 설정해주세요.")

# max_chars는 초과 붙여넣기를 안내 없이 통째로 버리므로 사용하지 않고 직접 검사한다
text = st.text_area(
    "번역할 문장",
    height=180,
    placeholder="여기에 번역할 문장을 입력하세요...",
    label_visibility="collapsed",
)
over_limit = len(text) > MAX_CHARS
st.markdown(
    f'<p class="char-count{" over" if over_limit else ""}">{len(text):,} / {MAX_CHARS:,}자</p>',
    unsafe_allow_html=True,
)
if over_limit:
    st.warning(
        f"입력은 최대 {MAX_CHARS:,}자까지 번역할 수 있습니다. "
        f"현재 {len(text):,}자이니 {len(text) - MAX_CHARS:,}자를 줄여주세요."
    )

clicked = None
cols = st.columns(len(LANGUAGES))
for col, label in zip(cols, LANGUAGES):
    if col.button(label, key=f"btn_{label}", disabled=config_missing, width="stretch"):
        clicked = label

if clicked and not over_limit:
    if not text.strip():
        st.warning("번역할 내용을 입력해주세요.")
    else:
        try:
            with st.spinner("번역 중..."):
                result = translate(text, LANGUAGES[clicked])
            st.session_state["result"] = result
            st.session_state["result_label"] = clicked
        except TranslationError as e:
            # 이전 결과가 현재 결과로 오해되지 않도록 제거
            st.session_state.pop("result", None)
            st.session_state.pop("result_label", None)
            st.error(str(e))

if "result" in st.session_state:
    st.subheader(f"번역 결과 ({st.session_state['result_label']})")
    st.code(st.session_state["result"], language=None, wrap_lines=True)
