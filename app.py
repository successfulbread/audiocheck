"""AudioCheQ v2.5.0 - integrated source evidence and readable forensic findings."""
from __future__ import annotations

import html
from pathlib import Path
import re
import tempfile
import logging

import streamlit as st

APP_VERSION = "2.5.0"
st.set_page_config(page_title="AudioCheQ v2.5.0 | Find the clues", page_icon=":material/graphic_eq:", layout="centered", initial_sidebar_state="collapsed")

# Load this release's uniquely named engine from the SAME directory as app.py.
# This avoids a stale analyzer.py left in GitHub or an unrelated `analyzer`
# module elsewhere on the Python import path. There is no fallback to an old
# analyzer, because it would silently undo the fixed NDR detection.
import importlib.util
ENGINE_PATH = Path(__file__).resolve().with_name("audiocheq_engine_v250.py")
if not ENGINE_PATH.is_file():
    st.error("AudioCheQ v2.5.0 is missing its audio engine file.")
    st.write("Missing: **audiocheq_engine_v250.py** beside **app.py**.")
    st.info("Upload both files from the v2.5.0 two-file update into the GitHub repository root, then reboot your Streamlit app. Do not upload the ZIP itself.")
    st.stop()
try:
    _spec = importlib.util.spec_from_file_location("audiocheq_engine_v250", ENGINE_PATH)
    if not _spec or not _spec.loader:
        raise ImportError("Cannot load engine from the local Python file")
    _engine = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_engine)
except Exception as exc:
    st.error("AudioCheQ could not load its v2.5.0 audio engine.")
    st.code(f"{type(exc).__name__}: {exc}", language="text")
    st.write(f"Engine file: `{ENGINE_PATH.name}`")
    st.info("Check that the complete ZIP contents are in the repository root and that Streamlit has finished installing packages.txt and requirements.txt.")
    st.stop()

_analyzer_loaded = getattr(_engine, "ANALYZER_VERSION", "missing")
_required_exports = ("MAX_BYTES", "analyze", "analyze_path", "ANALYZER_VERSION")
_missing_exports = [name for name in _required_exports if not hasattr(_engine, name)]
if _analyzer_loaded != APP_VERSION or _missing_exports:
    st.error("The website and its dedicated audio engine have different versions.")
    st.write(f"Website: **{APP_VERSION}**; engine: **{_analyzer_loaded}**.")
    if _missing_exports:
        st.write("Missing engine fields: " + ", ".join(_missing_exports))
    st.write(f"Loaded engine file: `{ENGINE_PATH.name}`")
    st.info("Replace app.py and audiocheq_engine_v250.py together from the v2.5.0 update ZIP, then reboot the app.")
    st.stop()

MAX_BYTES = _engine.MAX_BYTES
ANALYZER_VERSION = _engine.ANALYZER_VERSION
LOGGER = logging.getLogger("audiocheq")
analyze = _engine.analyze
analyze_path = _engine.analyze_path
from archive_source import fetch_archive_audio

st.markdown("""
<style>
html, body, .stApp {font-family:Inter,system-ui,-apple-system,"Segoe UI",sans-serif;}
.stApp {background:linear-gradient(165deg,#101827 0%,#151329 60%,#101827 100%);color:#F2F6FF;}
.block-container {max-width:980px;padding-top:1.1rem;padding-bottom:3rem;}
header[data-testid="stHeader"] {background:transparent;}
.ac-hero {position:relative;overflow:hidden;background:linear-gradient(111deg,#4F46E5 0%,#9333EA 54%,#E34E83 100%);
 border:1px solid #B9A3FF;border-radius:24px;box-shadow:0 16px 32px #03071355;padding:26px 29px;margin:0 0 20px;}
.ac-brand {position:relative;z-index:1;font-size:clamp(2.3rem,6vw,3.4rem);line-height:1.09;letter-spacing:-.05em;
 font-weight:900;color:#FFFFFF;margin:0 0 8px;text-shadow:0 2px 7px #25144755;}
.ac-brand span {color:#FFE58F;}
.ac-intro {position:relative;z-index:1;max-width:620px;font-size:1rem;color:#F9EEFF;margin:0;line-height:1.5;}
.ac-hero-mark {position:absolute;right:16px;top:12px;width:220px;height:132px;opacity:.75;pointer-events:none;}
.ac-tagline {position:relative;z-index:1;font-size:1.10rem;font-weight:850;letter-spacing:.01em;color:#FFECB9;margin:0 0 5px;}
.ac-heading {font-size:1.37rem;font-weight:850;color:#FFFFFF;margin:18px 0 12px;}
.ac-meta {font-size:.82rem;color:#B7BED2;margin:-3px 0 15px;overflow-wrap:anywhere;}
.ac-grid {display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:13px;margin-bottom:17px;}
.ac-card {border:1.7px solid;border-radius:19px;padding:16px 17px 13px;min-width:0;
 box-shadow:0 9px 24px #00000031;}
.ac-card.strong {background:linear-gradient(135deg,#D9FFED,#F2FFF8);border-color:#24CC89;}
.ac-card.good {background:linear-gradient(135deg,#DCEEFF,#F2F8FF);border-color:#43A4FF;}
.ac-card.maybe {background:linear-gradient(135deg,#FFF0CB,#FFF9EB);border-color:#F1A83B;}
.ac-card.none {background:#293143;border-color:#515A70;box-shadow:none;color:#B4BCCB;}
.ac-top {display:flex;align-items:center;gap:7px;margin-bottom:11px;}
.ac-icon {font-size:1.15rem;line-height:1.2;flex:none;}
.ac-label {font-size:.85rem;font-weight:800;color:#243F60;flex:1;}
.ac-card.none .ac-label{color:#CCD2DF;}
.ac-pill {border-radius:999px;font-size:.68rem;font-weight:850;padding:5px 9px;white-space:nowrap;}
.ac-card.strong .ac-pill {background:#A0EECC;color:#075C38;}
.ac-card.good .ac-pill {background:#A9D6FF;color:#143E76;}
.ac-card.maybe .ac-pill {background:#FFD998;color:#704306;}
.ac-card.none .ac-pill {background:#465269;color:#E0E5EF;}
.ac-sub {font-size:.8rem;font-weight:680;color:#415E79;margin-top:8px;}
.ac-result {font-size:1.23rem;line-height:1.3;font-weight:850;color:#182F56;overflow-wrap:anywhere;min-height:1.4em;}
.ac-card.none .ac-result {font-size:1.03rem;color:#E0E6F0;}
.ac-card.none .ac-sub {color:#AEB9CA;}
.ac-card details {border-top:1px solid #7482964A;margin-top:13px;padding-top:10px;overflow:hidden;}
.ac-card summary {font-size:.9rem;font-weight:800;color:#1658A8;cursor:pointer;}
.ac-card.none summary {color:#86B9FA;}
.ac-card details p,.ac-card details li {font-size:.9rem;line-height:1.57;color:#293E57;}
.ac-card details p {margin:10px 0 4px;}
.ac-card details ul {margin:9px 0 0;padding-left:20px;}
.ac-card details li {margin:6px 0;}
.ac-card.none details p,.ac-card.none details li {color:#D5DCEA;}
.ac-card.has-spectrogram {grid-column:1 / -1;}
.ac-metrics {display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:7px;
 margin:13px 0;padding:10px;background:#FFFFFF80;border-radius:10px;}
.ac-metric {display:flex;flex-direction:column;font-size:.75rem;line-height:1.34;gap:3px;color:#405570;}
.ac-metric strong {color:#172D4B;font-size:.84rem;}
.ac-card.none .ac-metrics {background:#3B465C;}
.ac-card.none .ac-metric,.ac-card.none .ac-metric strong {color:#E1E8F2;}
.ac-observation-title {font-weight:850;color:#0A5E7C;font-size:.85rem;margin:7px 0 8px;}
.ac-interpret-label {font-size:.80rem;color:#496582;font-weight:820;margin-top:13px;}
.ac-observations {background:#FFFFFF8A;border:1px solid #C7D4E2;border-radius:11px;
 padding:10px 12px 10px 30px !important;margin:8px 0 13px !important;}
.ac-observations li {font-size:.82rem !important;margin:5px 0 !important;line-height:1.48 !important;}
.ac-card.none .ac-observation-title {color:#78E4E0;}
.ac-card.none .ac-interpret-label{color:#ADC4E6;}
.ac-card.none .ac-observations{background:#36435B;border-color:#59657A;}
.ac-evidence-intro {margin-top:14px;margin-bottom:8px;color:#254C75;font-weight:850;font-size:.85rem;}
.ac-card.none .ac-evidence-intro {color:#D8E3F6;}
.ac-evidence {margin:10px 0 15px;padding:9px;background:#FFFFFF;border:1px solid #AFC5DD;border-radius:13px;}
.ac-evidence img {width:100%;height:auto;display:block;border-radius:8px;}
.ac-evidence figcaption {font-size:.8rem;color:#34455E;margin:9px 2px 0;line-height:1.48;}
.ac-card details.ac-raw {border-top:1px dashed #9EADC0;margin-top:13px;padding-top:9px;}
.ac-card details.ac-raw summary {font-size:.79rem;font-weight:700;color:#375873;}
.ac-card.none details.ac-raw summary {color:#A8D3F8;}
.ac-card details.ac-raw li {font-size:.79rem;line-height:1.5;}
.ac-card .ac-interpret-label {margin-bottom:5px;}
.ac-foot {font-size:.78rem;color:#AFBED1;margin-top:16px;}
/* Standard native Streamlit file picker: keep all clickable text readable on dark. */
.stTabs [data-baseweb="tab"] {color:#E4EBFF !important;font-weight:800 !important;}
.stTabs [aria-selected="true"] {color:#FFF1AC !important;}
[data-testid="stFileUploader"] {border:2px solid #67E5E0 !important;border-radius:16px;
 background:#24354F !important;padding:13px 14px 7px;}
[data-testid="stFileUploader"] label,
[data-testid="stFileUploader"] label p,
[data-testid="stFileUploader"] small,
[data-testid="stFileUploader"] span,
[data-testid="stFileUploader"] [data-testid="stFileDropzoneInstructions"] {color:#F8FBFF !important;opacity:1 !important;}
[data-testid="stFileUploader"] section {background:#263C58 !important;border:1.5px dashed #8BDCF2 !important;}
[data-testid="stFileUploader"] button,
[data-testid="stFileUploader"] [data-testid="baseButton-secondary"] {background:#FFF0AC !important;
 color:#182437 !important;border:2px solid #F7D659 !important;opacity:1 !important;
 font-weight:900 !important;min-height:46px;box-shadow:0 2px 0 #0003;}
[data-testid="stFileUploader"] button *,
[data-testid="stFileUploader"] button p,
[data-testid="stFileUploader"] button span {color:#182437 !important;opacity:1 !important;}
[data-testid="stFileUploader"] button:hover {background:#FFFFFF !important;}
[data-testid="stButton"] button[kind="primary"],
[data-testid="stBaseButton-primary"] {background:#46E7D0 !important;color:#10223A !important;
 border:2px solid #A4FFF2 !important;font-weight:900 !important;
 min-height:53px !important;border-radius:12px !important;opacity:1 !important;}
[data-testid="stButton"] button[kind="primary"] *,
[data-testid="stBaseButton-primary"] * {color:#10223A !important;opacity:1 !important;}
[data-testid="stButton"] button[kind="primary"]:hover,
[data-testid="stBaseButton-primary"]:hover {background:#B5FFF0 !important;}
[data-testid="stButton"] button:disabled {background:#52647A !important;color:#ECF2F8 !important;
 border-color:#61778B !important;opacity:1 !important;}
[data-testid="stButton"] button:disabled * {color:#ECF2F8 !important;opacity:1 !important;}
[data-testid="stFormSubmitButton"] button {background:#CBB7FF !important;color:#1E1B36 !important;
 border:2px solid #E8E0FF !important;font-weight:900 !important;min-height:46px !important;}
[data-testid="stFormSubmitButton"] button * {color:#1E1B36 !important;opacity:1 !important;}
/* File state label above the primary action. */
.ac-step {font-size:.99rem;font-weight:850;color:#FFFFFF;margin:9px 0 9px;}
.ac-file-ready {background:#173F47;border:1px solid #61EACD;border-radius:12px;
 padding:11px 14px;color:#ECFFF8;font-weight:750;margin:11px 0 13px;
 overflow-wrap:anywhere;}
.ac-file-waiting {font-size:.85rem;color:#C7D2E8;margin:11px 0 13px;}
@media(max-width:675px){.ac-grid{grid-template-columns:1fr;gap:11px;}
 .ac-hero{padding:21px 18px}.ac-hero-mark{width:115px;right:2px;top:2px;opacity:.23;}
 .block-container{padding-top:.55rem}.ac-card{padding:14px 15px 12px;}.ac-top{margin-bottom:8px;}}

.ac-build {position:relative;z-index:1;font-size:.74rem;font-weight:750;color:#FFEDC8;margin-top:12px;letter-spacing:.02em;}
.ac-choices {display:flex;flex-wrap:wrap;gap:6px;margin:5px 0 11px;}
.ac-choice {font-size:.75rem;font-weight:760;border:1px solid transparent;border-radius:9px;padding:7px 10px;line-height:1.2;white-space:normal;}
.ac-choice.ac-muted {background:#D8DEEA;color:#718095;border-color:#CCD3E0;opacity:.81;}
.ac-choice.ac-chosen {background:#117E63;color:#fff;border-color:#0D6E58;box-shadow:0 1px 3px #0002;opacity:1;}
.ac-card.good .ac-chosen {background:#195FA5;border-color:#15518E;color:#fff;}
.ac-card.maybe .ac-chosen {background:#99600B;border-color:#89530B;color:#fff;}
.ac-card.none .ac-choice.ac-muted {background:#3D495F;color:#A0ACC0;border-color:#4C586C;}
.ac-card.none .ac-choice.ac-chosen {background:#798398;color:#101C32;border-color:#A3ADC0;}
.ac-quick {display:flex;gap:7px;flex-wrap:wrap;margin-top:10px;}
.ac-quick-one {padding:7px 10px;border:1px solid #A7C3D0;border-radius:10px;background:#FFFFFFA6;display:flex;flex-direction:column;gap:2px;min-width:106px;max-width:100%;}
.ac-quick-one span {font-size:.68rem;font-weight:720;color:#506078;}
.ac-quick-one strong {font-size:.94rem;font-weight:850;color:#193951;overflow-wrap:anywhere;}
.ac-card.none .ac-quick-one {background:#3B465D;border-color:#546278;}
.ac-card.none .ac-quick-one span {color:#AEB9CF;}
.ac-card.none .ac-quick-one strong {color:#E6F2FF;}
.ac-card details p {margin:12px 0 7px;line-height:1.63;font-size:.91rem;}
.ac-analysis-build {color:#B9D5E8;font-size:.78rem;margin:-9px 0 12px;}
.ac-warning-note {color:#3A160B;background:#FFE3B3;padding:10px 13px;border-radius:12px;margin-bottom:12px;font-size:.87rem;font-weight:650;}

/* Expert measurements remain inside the single Why disclosure. */
.ac-measure-head {font-weight:850;font-size:.82rem;margin:15px 0 7px;color:#204C72;}
.ac-card.none .ac-measure-head {color:#A7E8E1;}
.ac-measure-list {padding-left:20px !important;margin:0 0 10px !important;}
.ac-measure-list li {font-size:.80rem !important;line-height:1.52 !important;overflow-wrap:anywhere;}
.ac-tag-fields {max-height:360px;overflow:auto;display:grid;gap:5px;background:#FFFFFF99;
 border:1px solid #B2CADC;border-radius:12px;padding:9px;}
.ac-tag-field {display:grid;grid-template-columns:minmax(70px,115px) minmax(0,1fr);gap:4px 8px;
 padding:6px 5px;border-bottom:1px solid #BFD2E2;font-size:.78rem;overflow-wrap:anywhere;}
.ac-tag-field strong{color:#20385E}.ac-tag-field span{color:#1C3452}
.ac-tag-field small{color:#66829D;grid-column:2;}
.ac-card.none .ac-tag-fields{background:#35445B;border-color:#567087}
.ac-card.none .ac-tag-field strong,.ac-card.none .ac-tag-field span{color:#EAF2FC}
.ac-source-scores{font-size:.79rem;line-height:1.5;margin:11px 0;color:#385A75;}
.ac-card.none .ac-source-scores{color:#DDE9F2;}
</style>
""", unsafe_allow_html=True)

st.markdown('''<div class="ac-hero">
<svg class="ac-hero-mark" aria-hidden="true" viewBox="0 0 240 144" xmlns="http://www.w3.org/2000/svg">
 <defs><linearGradient id="ac-waves" x1="0" y1="1" x2="1" y2="0"><stop stop-color="#A8FFF2"/><stop offset="1" stop-color="#FFE58F"/></linearGradient></defs>
 <rect x="10" y="15" width="215" height="113" rx="20" fill="#170E4A" fill-opacity=".27" stroke="#C9C5FF" stroke-opacity=".40"/>
 <path d="M19 48 L36 48 L43 31 L51 72 L62 21 L72 77 L84 47 L95 48 L105 37 L114 66 L125 40 L133 48 L145 48 L155 27 L164 80 L174 48 L192 48 L202 38 L213 48" fill="none" stroke="url(#ac-waves)" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/>
 <path d="M23 111 L39 104 L52 106 L67 96 L80 101 L96 89 L107 91 L121 106 L135 110 L148 93 L166 87 L182 95 L198 91 L214 81" fill="none" stroke="#FFE58F" stroke-width="2.6" stroke-linecap="round"/>
 <path d="M104 107 L122 120 L137 107" fill="none" stroke="#86FFF0" stroke-width="3" stroke-linecap="round"/>
 <circle cx="122" cy="120" r="3.4" fill="#86FFF0"/>
 <text x="24" y="129" fill="#F3EFFF" font-size="9" font-weight="700" font-family="sans-serif">SIGNAL</text>
 <text x="177" y="129" fill="#F3EFFF" font-size="9" font-weight="700" font-family="sans-serif">10 kHz</text>
</svg>
<div class="ac-brand">Audio<span>CheQ</span></div>
<p class="ac-tagline">Find the story hidden in the sound.</p>
<p class="ac-intro">Audio forensics for mystery recordings: vinyl, tape, radio, pitch, speed and broadcast fingerprints.</p><div class="ac-build">v2.5.0 &nbsp;·&nbsp; NDR notch detector 2.4</div></div>''', unsafe_allow_html=True)

if "report" not in st.session_state:
    st.session_state.report = None
if "report_error" not in st.session_state:
    st.session_state.report_error = None
if "upload_nonce" not in st.session_state:
    st.session_state.upload_nonce = 0


def store_report(rows, meta, name, kind):
    # Do not store the uploaded bytes: only the small resulting report.
    st.session_state.report = {"rows": rows, "meta": meta, "name": name, "kind": kind}
    st.session_state.report_error = None


def meaningful(item):
    if not isinstance(item, dict):
        return False
    certainty = str(item.get('certainty', 'Unclear'))
    result = str(item.get('result', '')).lower()
    if certainty not in ('Strong', 'High', 'Possible', 'Tentative'):
        return False
    return not any(phrase in result for phrase in (
        'none detected', 'none found', 'not measurable', 'unclear',
        'no reliable', 'no clear', 'no distinctive', 'source uncertain',
        'cannot assess', 'unavailable', 'no confirmed', 'no pilot found',
        'no embedded', 'no broadcast'))


def badge_class(item):
    if not meaningful(item):
        return 'none'
    return {'Strong': 'strong', 'High': 'strong', 'Possible': 'good',
            'Tentative': 'maybe'}.get(str(item.get('certainty', '')), 'none')


LABELS = {
    'Likely audio source': ('Most likely origin', '&#9835;'),
    'NDR-style 10 kHz dip': ('10 kHz broadcast-filter dip', '&#9836;'),
    'Stereo / phase': ('Stereo, mono & channel alignment', '&#8646;'),
    'Vinyl rotation': ('Record rotation', '&#9673;'),
    'Likely power system': ('Electrical hum', '&#9889;'),
    'Radio / TV signals': ('TV scanning signals', '&#9737;'),
    'FM stereo pilot': ('FM stereo pilot (19 kHz)', '&#9687;'),
    'Wow and flutter': ('Wow / flutter', '&#8767;'),
    'Pitch / musical tuning': ('Musical pitch / tuning', '&#9839;'),
    'Playback speed': ('Playback speed', '&#8635;'),
    'Digital file history': ('Digital file age', '&#128197;'),
    'Embedded metadata': ('Embedded track metadata', '&#128209;'),
    'RDS / RadioText': ('RDS / station text', '&#128225;'),
}


def display_result(key, item):
    item = item if isinstance(item, dict) else {}
    raw = str(item.get('result') or 'Unclear')
    metrics = item.get('metrics') if isinstance(item.get('metrics'), dict) else {}
    if key == 'NDR-style 10 kHz dip':
        if meaningful(item):
            center = metrics.get('notch_median_hz')
            return f'Dip detected near {center:,.0f} Hz' if isinstance(center, (int, float)) else '10 kHz dip detected'
        if item.get('certainty') == 'Not measurable':
            return 'Cannot assess 10 kHz'
        return 'No confirmed 10 kHz dip'
    if key == 'Stereo / phase':
        return raw
    if key == 'Vinyl rotation' and not meaningful(item):
        return 'No reliable RPM pattern'
    if key == 'FM stereo pilot' and not meaningful(item):
        return 'No pilot confirmed' if item.get('certainty') != 'Not measurable' else '19 kHz unavailable'
    return raw


def why(key, item):
    """One readable explanation with measurements that belong to this recording."""
    item = item if isinstance(item, dict) else {}
    m = item.get('metrics') if isinstance(item.get('metrics'), dict) else {}
    raw = str(item.get('result') or '')
    detail = str(item.get('detail') or '')
    positive = meaningful(item)

    def number(name, digits=1):
        v = m.get(name)
        return f'{v:,.{digits}f}' if isinstance(v, (float, int)) and not isinstance(v, bool) else None

    if key == 'NDR-style 10 kHz dip':
        center = number('notch_median_hz', 0) or number('notch_candidate_hz', 0)
        depth = number('notch_depth_db', 2)
        hits = m.get('notch_sections')
        total = m.get('notch_tested_sections')
        counted = (f' in {hits} of {total} sections examined' if isinstance(hits, int) and isinstance(total, int) else '')
        if positive and center and depth:
            return (f'There is a repeatable gap in the upper-frequency sound near {center} Hz. '
                    f'The strongest dip is {depth} dB below the neighbouring frequencies and appears{counted}. '
                    'A fixed dip like this is consistent with a filter used somewhere in an older broadcast or copying chain. '
                    'The centre can shift when tape speed changes. It does not by itself identify NDR as the station.')
        if positive:
            return 'The detector reports a possible 10 kHz gap, but this saved result has no numeric measurements. Re-upload the recording with v2.5 to obtain a measured centre, depth and consistency check. A filter notch alone cannot identify NDR.'
        if center and depth:
            return (f'The strongest candidate was at {center} Hz and {depth} dB below adjacent sound, '
                    'but it was not deep or repeatable enough on both sides to qualify. '
                    'A smooth loss of treble is not the same as an intentional narrow broadcast notch.')
        return ('This file did not provide enough usable upper-frequency sound to assess a narrow notch '
                'around 10 kHz. A negative result does not prove the original recording lacked that filter.')

    if key == 'Stereo / phase':
        fmt=str(item.get('format_result') or 'Unclear')
        phase=str(item.get('phase_result') or 'Unclear')
        corr=m.get('median_zero_corr', m.get('zero_corr', m.get('stereo_median_corr')))
        delay=m.get('median_delay_ms',m.get('delay_ms'))
        parts=[]
        if isinstance(corr,(float,int)):
            parts.append(f'left/right correlation {corr:+.3f} (1.000 means identical channels)')
        if isinstance(delay,(float,int)):
            parts.append(f'channel offset {delay:+.3f} ms')
        measured=(' Measured: '+', '.join(parts)+'.') if parts else ''
        if fmt=='Mono':
            return ('This file stores one sound channel. There is no left-versus-right phase to compare.'
                    ' It could still be a mono copy of a stereo original.'+measured)
        if 'dual mono' in fmt.lower():
            return ('This file stores two channels carrying essentially the same sound. That often means a mono signal'
                    ' was copied into a stereo file, not that the original recording was mono.'+measured)
        if 'polarity' in phase.lower() or 'opposite-phase' in phase.lower():
            consequence='Parts of the shared sound have opposite polarity, which can cancel when the recording is played in mono.'
        elif 'delay' in phase.lower():
            consequence='A small offset between channels may reflect a tape-head alignment problem or later stereo processing.'
        else:
            consequence='Different instruments and effects in each channel naturally reduce correlation; that alone is not a phase fault.'
        return ('The two stored channels are different enough to count as stereo. '+consequence+measured+
                ' Phase clues describe the transfer or mix, not necessarily the equipment used for the original performance.')

    if key == 'Likely audio source':
        guess=str(item.get('result') or 'Unknown')
        evidence=item.get('evidence') if isinstance(item.get('evidence'),list) else []
        context=item.get('context') if isinstance(item.get('context'),list) else []
        clue=' '.join(str(x).rstrip('.')+'.' for x in evidence[:4] if x)
        scores=(m.get('clue_scores') or {}) if isinstance(m.get('clue_scores'),dict) else {}
        ordered=sorted(((str(k),v) for k,v in scores.items() if isinstance(v,(int,float))),
                       key=lambda kv:-kv[1])
        points=' Evidence scores: '+', '.join(f'{k} {v:.1f}' for k,v in ordered[:3])+'.' if ordered else ''
        freq=item.get('frequency_clue') if isinstance(item.get('frequency_clue'),dict) else {}
        freq_note= (' Measured frequency range: '+str(freq.get('result'))+'. '
                    +str(freq.get('detail') or '')[:270] if freq and
                    freq.get('certainty') not in ('Not measurable','Unclear') else '')
        if item.get('fallback_guess'):
            intro=('This is only the closest remaining guess: the file has no convincing record, tape or FM fingerprint. '
                   'A clean digitization of an old recording can look digital too. ')
        else:
            intro=(f'{guess} fits the strongest measured recording-path clues. ')
        return (intro+clue+freq_note+points+(' '+str(context[0]) if context else '')+
            ' The score compares clues and is not a probability of the original studio format.')

    if key == 'Vinyl rotation':
        count = m.get('click_events')
        period = number('fitted_rotation_period_s', 3)
        err = number('click_fit_error_ms', 1)
        if positive and count and period:
            return (f'{count} sharp events repeat about every {period} seconds'
                    + (f' (timing variation {err} ms)' if err else '') + '. '
                    'This can suggest the turntable speed, but drumbeats and other repeated sounds can produce similar intervals.')
        return 'No convincing repeating click sequence matched 33⅓, 45 or 78 RPM. A quiet record transfer may have no usable rotational clicks.'

    if key == 'Likely power system':
        observed = detail if positive and detail else ('No reliable 50 or 60 Hz pattern was confirmed in this recording.')
        countries_50=('50 Hz examples: Germany, France, United Kingdom, Ireland, Spain, Italy, Portugal, '
            'Netherlands, Belgium, Switzerland, Austria, Poland, Sweden, Norway, Finland, Russia, '
            'Ukraine, China, India, Pakistan, Australia, New Zealand, South Africa, Egypt, '
            'Argentina, Chile and Vietnam.')
        countries_60=('60 Hz examples: United States, Canada, Mexico, Brazil, Colombia, Venezuela, Peru, '
            'Ecuador, Costa Rica, Guatemala, Panama, Dominican Republic, South Korea, Taiwan and the Philippines.')
        exception=('Japan uses 50 Hz in the east (including Tokyo) and 60 Hz in the west (including Osaka). '
                   'Some territories or facilities have exceptions. This identifies electrical interference somewhere '
                   'in the recording or copying chain, not the nationality of the artist.')
        return (observed+' Electrical hum from mains electricity may occur at 50 or 60 Hz, often with harmonics at 100 or 120 Hz. It may have entered during copying or digitization. '
                +countries_50+' '+countries_60+' '+exception)

    if key == 'Radio / TV signals':
        if positive and detail:
            return detail + ' The known reference frequencies are 15,734.26 Hz (NTSC) and 15,625 Hz (PAL/SECAM). A stable scanning tone could have entered during a later transfer; it is not proof the music came from television.'
        return 'No stable narrow peak near 15,734.26 Hz (NTSC) or 15,625 Hz (PAL/SECAM) was confirmed. Lossy encoding or a limited frequency range can erase these clues.'

    if key == 'FM stereo pilot':
        hz = number('measured_hz', 1)
        prominence = number('prominence_db', 1)
        sections = m.get('strong_sections', m.get('pilot_hits'))
        if positive and hz:
            return (f'A narrow signal was measured at {hz} Hz, near the 19,000 Hz FM stereo pilot.'
                    + (f' It rises {prominence} dB above nearby sound.' if prominence else '')
                    + (f' {sections} sampled sections passed the strongest checks.' if isinstance(sections,int) else '')
                    + ' This is evidence of an FM-related signal: the 19 kHz pilot helps the tuner reconstruct the 38 kHz stereo subcarrier. Other electronic tones can resemble it.')
        return 'No reliable 19,000 Hz pilot was measured. Most FM tuners deliberately remove the pilot before sending out audio, so this does not rule out an FM recording.'

    if key == 'Wow and flutter' and 'unreliable' in raw.lower():
        rejected=number('rejected_rms_cents',1)
        return (f'A possible tone shifted by {rejected} cents RMS, far too much to trust as normal mechanical wow. '
                if rejected else 'The reference-tone pitch track was unreliable. ')+(
                'The analyzer rejects this candidate rather than confusing a musical note or wrong harmonic '
                'with tape speed variation. No usable wow/flutter conclusion can be drawn.')
    if key == 'Wow and flutter':
        rms = number('rms_cents', 2)
        rate = number('rate_hz', 2)
        if positive and rms and rate:
            return (f'A trackable reference tone varies by about {rms} cents RMS at a recurring rate of {rate} cycles per second. '
                    'This can suggest small mechanical playback-speed variations. It cannot reliably separate tape from vinyl without other evidence.')
        return 'There was no stable reference tone that could be followed accurately enough to measure speed wobble. This is not evidence that the recording has no wow or flutter.'

    if key == 'Pitch / musical tuning':
        cents = m.get('deviation_cents')
        votes = m.get('votes')
        if isinstance(cents, (int,float)):
            return (f'Instrumental peaks group around {cents:+.1f} cents from standard A=440 tuning'
                    + (f', using {votes} candidate peaks' if isinstance(votes,int) else '') + '. '
                    'That may indicate the musical tuning, but it does not establish that the playback speed is wrong. The players may have tuned differently.')
        return 'The music did not contain a sufficiently consistent group of steady notes to estimate its overall tuning. Vocals, harmonics and instruments moving between notes make this uncertain.'

    if key == 'Playback speed':
        err = m.get('speed_error_percent')
        corr = m.get('correction_percent')
        obs = m.get('observed_hz')
        nom = m.get('nominal_hz')
        if isinstance(err,(float,int)) and isinstance(corr,(float,int)):
            return (f'A suspected reference signal measures {obs:,.2f} Hz versus an expected {nom:,.2f} Hz, '
                    f'which would correspond to {err:+.2f}% apparent speed error and {corr:+.2f}% correction. '
                    'This only applies if the tone was present before the recording was sped up or slowed down. '
                    'If it was added during a later transfer, the calculation says nothing about the original song speed.')
        return 'No verified hum, TV scanning line or FM pilot provides a trustworthy absolute speed reference. Musical tuning alone is not enough to say the recording should be faster or slower.'

    if key == 'Digital file history':
        facts = item.get('facts') if isinstance(item.get('facts'), dict) else {}
        codec = facts.get('codec')
        bitrate = facts.get('bitrate_kbps')
        encoder = facts.get('encoder')
        parts = ([str(codec).upper() + ' audio'] if codec else [])
        if bitrate:
            parts.append(f'{bitrate} kbps')
        if encoder:
            parts.append(f'encoder {encoder}')
        if parts:
            return ('This particular digital file uses ' + ', '.join(parts) + '. '
                    + (detail[:280] if detail else '') + ' Its encoding date is not the recording date; an old cassette could have been converted much later.')
        return detail or 'No reliable encoder or file age clue is present. A file timestamp rarely dates the original recording.'

    if key == 'Embedded metadata':
        entries = item.get('tags') if isinstance(item.get('tags'),list) else []
        samples = '; '.join(f'{x.get("field", "field")}: {str(x.get("value", ""))[:80]}' for x in entries[:2] if isinstance(x,dict))
        if entries:
            return (f'{len(entries)} readable tags were found in this file. '
                    + (f'Examples: {samples}. ' if samples else '')
                    + 'These can reveal sources and original filenames, but tags are editable and do not authenticate an artist. All fields appear in File details below.')
        return 'No readable text tags were found. This does not mean the recording never had tags; they may have been stripped in an earlier conversion.'

    if key == 'RDS / RadioText':
        decoded = item.get('decoded') if isinstance(item.get('decoded'),dict) else {}
        if decoded:
            samples = '; '.join(f'{k}: {str(v)[:80]}' for k,v in list(decoded.items())[:2])
            return f'FM broadcast metadata was decoded: {samples}. A station may send text that changes over time.'
        return ('No actual station text was recovered from the audio. A 19 kHz pilot or 57 kHz-band peak alone is not decoded RDS; '
                'most ordinary music recordings do not preserve the raw 57 kHz FM subcarrier. File tags are checked separately.')

    return detail or 'This was measured from the recording but does not by itself identify the original recording equipment.'


def card(label, item, key=None, evidence_plots=None):
    """One clear result, grey alternatives, two short measurements, one Why."""
    key = key or label
    item = item if isinstance(item, dict) else {}
    cls = badge_class(item)
    raw = str(item.get('result') or '').lower()
    m = item.get('metrics') if isinstance(item.get('metrics'), dict) else {}
    positive = meaningful(item)
    icon = LABELS.get(key, (label, '&#9835;'))[1]
    result = display_result(key, item)
    pill = {'strong':'Clear finding', 'good':'Possible', 'maybe':'Tentative', 'none':'Not confirmed'}[cls]
    if evidence_plots:
        cls += ' has-spectrogram'

    # Options are evidence labels, not interactive buttons. Highlight exactly
    # one conclusion, including an explicit neutral/no-measurement outcome.
    available = {
        'Likely audio source': ['Vinyl','Cassette','FM','AM','Digital','Unclear'],
        'Vinyl rotation': ['33⅓ RPM','45 RPM','78 RPM','No pattern'],
        'Likely power system': ['50 Hz','60 Hz','Unclear'],
        'Radio / TV signals': ['NTSC','PAL/SECAM','No signal','Unclear'],
        'FM stereo pilot': ['Detected','Not detected','Unavailable'],
        'NDR-style 10 kHz dip': ['Detected','Not detected','Unavailable'],
        'Stereo / phase': ['Mono','Dual mono','Stereo','Unclear'],
        'Wow and flutter': ['Detected','No clear wobble','Unmeasurable'],
        'Pitch / musical tuning': ['Near A440','Flat','Sharp','Unclear'],
        'Playback speed': ['Too slow','Too fast','Near normal','Unknown'],
        'Digital file history': ['Age clue','No age clue'],
        'Embedded metadata': ['Tags found','No tags'],
        'RDS / RadioText': ['Decoded','Possible signal','No RDS text','Unavailable'],
    }
    choice = None
    if key == 'Likely audio source':
        choice = next((v for v,w in [('Vinyl','vinyl'),('Cassette','cassette'),('FM','fm radio'),
                                   ('AM','am radio'),('Digital','digital')] if w in raw), 'Unclear')
    elif key == 'Vinyl rotation':
        choice = next((v for v,w in [('33⅓ RPM','33⅓'),('45 RPM','45'),('78 RPM','78')] if w in raw), 'No pattern')
    elif key == 'Likely power system':
        choice = '50 Hz' if '50 hz' in raw else '60 Hz' if '60 hz' in raw else 'Unclear'
    elif key == 'Radio / TV signals':
        choice = 'NTSC' if 'ntsc' in raw else 'PAL/SECAM' if 'pal' in raw or 'secam' in raw else 'Unclear' if 'unavailable' in raw else 'No signal'
    elif key in ('FM stereo pilot', 'NDR-style 10 kHz dip'):
        choice = 'Detected' if positive else 'Unavailable' if item.get('certainty') == 'Not measurable' else 'Not detected'
    elif key == 'Stereo / phase':
        choice = 'Dual mono' if 'dual mono' in raw else 'Mono' if raw == 'mono' else 'Stereo' if raw == 'stereo' else 'Unclear'
    elif key == 'Wow and flutter':
        choice = 'Detected' if positive else 'Unmeasurable' if item.get('certainty') == 'Not measurable' else 'No clear wobble'
    elif key == 'Pitch / musical tuning':
        choice = 'Near A440' if 'near a440' in raw else 'Flat' if 'flat' in raw else 'Sharp' if 'sharp' in raw else 'Unclear'
    elif key == 'Playback speed':
        choice = 'Too slow' if 'slow' in raw else 'Too fast' if 'fast' in raw else 'Near normal' if 'near reference speed' in raw else 'Unknown'
    elif key == 'Digital file history':
        choice = 'Age clue' if positive else 'No age clue'
    elif key == 'Embedded metadata':
        choice = 'Tags found' if item.get('tags') else 'No tags'
    elif key == 'RDS / RadioText':
        choice = 'Decoded' if item.get('decoded') else 'Possible signal' if positive else 'Unavailable' if item.get('certainty')=='Not measurable' else 'No RDS text'

    choices = available.get(key, [])
    options_html = ('<div class="ac-choices" role="group" aria-label="Possible outcomes">'
        + ''.join('<span class="ac-choice '+('ac-chosen' if opt==choice else 'ac-muted')+'" '
                  + ('aria-current="true"' if opt==choice else 'aria-current="false"')+'>'
                  + html.escape(opt)+'</span>' for opt in choices) + '</div>') if choices else ''

    short=[]
    def add_metric(name, value, fmt='{}'):
        if value is None or isinstance(value, bool):
            return
        try:
            rendered=fmt.format(value)
        except (ValueError,TypeError):
            return
        short.append((name, rendered))
    if key == 'NDR-style 10 kHz dip':
        add_metric('Centre',m.get('notch_median_hz',m.get('notch_candidate_hz')),'{:,.0f} Hz')
        depth=m.get('notch_depth_db')
        total=m.get('notch_tested_sections')
        repeats=m.get('notch_sections')
        if isinstance(depth,(int,float)):
            info=f'{depth:.2f} dB'
            if isinstance(repeats,int) and isinstance(total,int) and total:
                info+=f' · {repeats}/{total} sections'
            add_metric('Dip depth / persistence',info)
    elif key == 'Stereo / phase':
        add_metric('Stored channels',1 if raw=='mono' else 2 if raw in ('stereo','dual mono') else None)
        add_metric('Channel correlation',m.get('median_zero_corr',m.get('zero_corr',m.get('stereo_median_corr'))),'{:+.3f}')
        add_metric('Channel offset',m.get('median_delay_ms',m.get('delay_ms')),'{:+.3f} ms')
    elif key == 'FM stereo pilot':
        add_metric('Measured peak',m.get('measured_hz'),'{:,.1f} Hz')
        add_metric('Peak above nearby sound',m.get('prominence_db'),'{:.1f} dB')
    elif key == 'Vinyl rotation':
        add_metric('Aligned clicks',m.get('click_events'))
        add_metric('Click interval',m.get('fitted_rotation_period_s'),'{:.3f} s')
    elif key == 'Wow and flutter':
        add_metric('Wobble RMS',m.get('rms_cents'),'{:.2f} cents')
        add_metric('Wobble rate',m.get('rate_hz'),'{:.2f} Hz')
    elif key == 'Pitch / musical tuning':
        add_metric('Relative to A440',m.get('deviation_cents'),'{:+.1f} cents')
        add_metric('Peak votes',m.get('votes'))
    elif key == 'Playback speed':
        add_metric('Speed vs reference',m.get('speed_error_percent'),'{:+.2f}%')
        add_metric('Conditional correction',m.get('correction_percent'),'{:+.2f}%')
    elif key == 'Likely audio source':
        add_metric('Evidence score',m.get('leading_score'),'{:.1f} points')
        add_metric('Independent clues',m.get('independent_supports'))
    elif key == 'Embedded metadata':
        add_metric('Text fields',len(item.get('tags') or []))
        for tagname in ('Title','Artist'):
            entry=next((t for t in (item.get('tags') or []) if isinstance(t,dict)
                        and str(t.get('field','')).lower()==tagname.lower()),None)
            if entry is not None:
                add_metric(tagname,str(entry.get('value',''))[:100])
    elif key == 'RDS / RadioText':
        add_metric('Decoded groups',(m.get('rds_groups') if m else None))
    elif key == 'Digital file history':
        f = item.get('facts') if isinstance(item.get('facts'),dict) else {}
        add_metric('Bitrate',f.get('bitrate_kbps'),'{} kbps')

    quick_html = ('<div class="ac-quick">' + ''.join(
        '<div class="ac-quick-one"><span>'+html.escape(str(k))+'</span><strong>'+
        html.escape(str(v))+'</strong></div>' for k,v in short[:3])+'</div>') if short else ''
    detail_html = '<p>'+html.escape(why(key,item))+'</p>'
    # Expert measurements are shown inside the SAME Why disclosure, below
    # the plain-language explanation. Never turn them into another tab.
    raw_notes=item.get('observations') if isinstance(item.get('observations'),list) else []
    numeric_notes=[str(x) for x in raw_notes if any(c.isdigit() for c in str(x))]
    if numeric_notes:
        limit=8 if key in ('Likely audio source','Likely power system','Stereo / phase') else 6
        # Show measurements first, not generic protocol boilerplate.
        detail_html += ('<div class="ac-measure-head">Measured in this recording</div>'
                        '<ul class="ac-measure-list">'+''.join(
            '<li>'+html.escape(note[:500])+'</li>' for note in numeric_notes[:limit])+'</ul>')
    if key=='Embedded metadata' and isinstance(item.get('tags'),list) and item['tags']:
        tagrows=[]
        for entry in item['tags'][:90]:
            if not isinstance(entry,dict):
                continue
            field=html.escape(str(entry.get('field','(unlabelled)'))[:105])
            value=html.escape(str(entry.get('value',''))[:340])
            source=html.escape(str(entry.get('source',''))[:105])
            tagrows.append('<div class="ac-tag-field"><strong>'+field+'</strong>'
                           +'<span>'+value+'</span><small>'+source+'</small></div>')
        detail_html += ('<div class="ac-measure-head">Embedded text fields</div>'
                        '<div class="ac-tag-fields">'+''.join(tagrows)+'</div>')
    if key=='Likely audio source' and isinstance(m.get('clue_scores'),dict):
        info=sorted(m['clue_scores'].items(),key=lambda t:-t[1])
        detail_html += '<div class="ac-source-scores">Relative clue scores (not probabilities): '+html.escape(
            ' · '.join(f'{name} {val:.1f}' for name,val in info))+'</div>'
    if evidence_plots:
        for entry in evidence_plots[:2]:
            img=entry.get('image_base64','')
            if not isinstance(img,str) or not re.fullmatch(r'[A-Za-z0-9+/=]{100,400000}',img):
                continue
            measured_caption=str(entry.get('caption',''))
            if key == 'Stereo / phase':
                measured_caption='Example excerpt (the card values are medians across sampled sections). ' + measured_caption
            elif key == 'NDR-style 10 kHz dip':
                measured_caption='Strongest excerpt shown; the centre above summarizes all qualifying excerpts. ' + measured_caption
            caption=html.escape(measured_caption)
            detail_html += ('<figure class="ac-evidence"><img loading="lazy" '
                            'alt="Measured evidence from the uploaded file" '
                            f'src="data:image/png;base64,{img}" /><figcaption>{caption}</figcaption></figure>')
    return (f'<section class="ac-card {cls}">'
            f'<div class="ac-top"><span class="ac-icon">{icon}</span>'
            f'<span class="ac-label">{html.escape(label)}</span>'
            f'<span class="ac-pill">{pill}</span></div>'
            f'{options_html}'
            f'<div class="ac-result">{html.escape(result)}</div>'
            f'{quick_html}'
            f'<details><summary>Why?</summary>{detail_html}</details>'
            '</section>')


def summary(found):
    found = found if isinstance(found,dict) else {}
    statements=[]
    source=found.get('Likely audio source') or {}
    statements.append(str(source.get('result') or 'Source unknown'))
    notch=found.get('NDR-style 10 kHz dip') or {}
    if meaningful(notch):
        center=(notch.get('metrics') or {}).get('notch_median_hz')
        statements.append(f'10 kHz-band dip detected near {center:,.0f} Hz' if isinstance(center,(int,float)) else '10 kHz-band dip detected')
    return ' · '.join(statements)


def combine_stereo_phase(stereo, phase):
    """One honest recording-format result with phase as a supporting measurement.

    Stereo correlation is not itself a diagnosis of a faulty phase relationship.
    Values reflect the sampled FILE, not necessarily an original master tape.
    """
    stereo = stereo if isinstance(stereo,dict) else {}
    phase = phase if isinstance(phase,dict) else {}
    f = str(stereo.get('result') or 'Unclear')
    p = str(phase.get('result') or 'Unclear')
    fm = stereo.get('metrics') if isinstance(stereo.get('metrics'),dict) else {}
    pm = phase.get('metrics') if isinstance(phase.get('metrics'),dict) else {}
    if f == 'Mono':
        state = 'Mono'
        line = 'One stored audio channel; left/right phase cannot be measured.'
    elif 'dual mono' in f.lower():
        state = 'Dual mono'
        line = 'Two stored channels contain virtually identical sound.'
    elif f == 'Stereo':
        state = 'Stereo'
        line = 'The file contains two measurably different channels.'
    else:
        state = 'Unclear'
        line = 'The stored channel arrangement could not be classified reliably.'
    return {'result':state, 'certainty':stereo.get('certainty','Unclear'),
            'detail':line, 'format_result':f, 'phase_result':p,
            'metrics':{**fm, **pm, 'phase_classification':p, 'format_classification':f},
            'observations':list(stereo.get('observations') or [])+list(phase.get('observations') or [])}


def sorted_findings(rows):
    items = dict(rows or [])
    items['Stereo / phase'] = combine_stereo_phase(
        items.get('Stereo format',{}),items.get('Stereo phase / delay',{}))
    order = list(LABELS)
    levels = {'strong': 3,'good': 2,'maybe': 1,'none': 0}
    # Source always first. A real NDR notch should be easy to find rather than
    # buried among unrelated cards. Other supported clues come before unknowns.
    def rank(key):
        if key == 'Likely audio source':
            return (-3,0,0)
        if key == 'NDR-style 10 kHz dip' and meaningful(items.get(key)):
            return (-2,0,0)
        return (-1,-levels[badge_class(items.get(key,{}))],order.index(key))
    return [(key,items.get(key,{'certainty':'Unclear','result':'Unclear'})) for key in sorted(order,key=rank)]


st.markdown('<div class="ac-heading">Check a song</div>', unsafe_allow_html=True)
file_tab, archive_tab = st.tabs(["Upload audio", "Archive.org link"])
with file_tab:
    # Regular Streamlit uploader OUTSIDE a form: the selected filename appears
    # as soon as the browser has successfully delivered the file to Streamlit.
    st.markdown('<div class="ac-step">1. Choose an audio file</div>', unsafe_allow_html=True)
    uploaded = st.file_uploader(
        "Select MP3, WAV, FLAC, M4A or OGG (max 5 minutes / 100 MB)",
        type=["mp3", "mpeg", "mpga", "wav", "flac", "ogg", "m4a"],
        accept_multiple_files=False,
        max_upload_size=100,
        key=f"audio_file_{st.session_state.upload_nonce}",
        help="Pick one file. Its name appears below when it has reached the app.",
    )
    if uploaded is not None:
        ready_name = html.escape(Path(uploaded.name).name)
        ready_mb = uploaded.size / (1024 * 1024)
        st.markdown(
            f'<div class="ac-file-ready">&#10003; File received: {ready_name} '
            f'({ready_mb:.1f} MB)</div>', unsafe_allow_html=True)
    else:
        st.markdown(
            '<div class="ac-file-waiting">Your selected filename will appear here. '
            'Then press Analyze.</div>', unsafe_allow_html=True)
    st.markdown('<div class="ac-step">2. Analyze</div>', unsafe_allow_html=True)
    pressed = st.button(
        "ANALYZE SELECTED AUDIO", key="analyze_upload", type="primary",
        use_container_width=True, disabled=uploaded is None,
    )
    if pressed and uploaded is not None:
        st.session_state.report_error = None
        upload_success = False
        if uploaded.size > MAX_BYTES:
            st.session_state.report_error = "File too large (100 MB max)."
        else:
            try:
                with st.spinner("Listening for clues..."):
                    name = Path(uploaded.name).name
                    rows, meta = analyze(uploaded.getvalue(), name, charts=True)
                store_report(rows, meta, name, "Upload")
                upload_success = True
            except ValueError as exc:
                st.session_state.report_error = str(exc)
            except Exception as exc:
                LOGGER.exception("Upload analysis failed (%s, %s bytes)",
                                 Path(uploaded.name).suffix.lower(), uploaded.size)
                initial_type = type(exc).__name__
                # A graph failure must not discard usable audio measurements.
                try:
                    with st.spinner("Trying audio analysis without graphs..."):
                        name = Path(uploaded.name).name
                        rows, meta = analyze(uploaded.getvalue(), name, charts=False)
                    meta["graph_warning"] = (
                        "The measurements succeeded, but a graph could not be drawn "
                        f"({initial_type}). No spectral findings were changed."
                    )
                    store_report(rows, meta, name, "Upload")
                    upload_success = True
                except ValueError as retry_exc:
                    st.session_state.report_error = str(retry_exc)
                except Exception as retry_exc:
                    LOGGER.exception("Upload analysis failed even without graphs")
                    st.session_state.report_error = (
                        "Analysis could not finish. Diagnostic: "
                        f"{type(retry_exc).__name__}. "
                        "Please send this error type and the traceback from Manage app > Logs."
                    )
        # Never catch Streamlit's rerun control-flow exception as an analysis
        # failure; call rerun ONLY after both analysis try/except blocks.
        if upload_success:
            st.session_state.upload_nonce += 1
            st.rerun()
with archive_tab:
    with st.form("archive_form", enter_to_submit=False):
        archive_link = st.text_input("Direct audio file URL", placeholder="https://archive.org/download/record-id/track.mp3")
        archive_allowed = st.checkbox("I may download and analyze this recording")
        archive_submit = st.form_submit_button("Analyze archive audio", use_container_width=True)
    if archive_submit:
        st.session_state.report_error = None
        if not archive_link.strip():
            st.session_state.report_error = "Paste a direct Internet Archive audio-file link."
        elif not archive_allowed:
            st.session_state.report_error = "Confirm you have permission to analyze the audio."
        else:
            try:
                with st.spinner("Fetching archive audio..."):
                    with tempfile.TemporaryDirectory(prefix="audiocheck_archive_") as td:
                        path, title = fetch_archive_audio(archive_link, Path(td))
                        rows, meta = analyze_path(path, title, charts=True)
                store_report(rows, meta, title, "Archive")
            except ValueError as exc:
                st.session_state.report_error = str(exc)
            except Exception as exc:
                LOGGER.exception("Archive analysis failed")
                st.session_state.report_error = (
                    f"Archive analysis failed ({type(exc).__name__}). "
                    "Try the direct MP3 upload or check Manage app > Logs."
                )

if st.session_state.report_error:
    st.error(st.session_state.report_error)

report = st.session_state.report
if report:
    meta = report.get("meta", {})
    if meta.get("graph_warning"):
        st.warning(str(meta["graph_warning"]))
    if meta.get("nonfatal_issues"):
        issues = meta["nonfatal_issues"]
        st.info(f"{len(issues)} optional forensic check(s) could not run; other results remain available.")
        with st.expander("Optional check diagnostics"):
            for issue in issues:
                st.write(str(issue))
    name = html.escape(str(report.get("name", "Recording")))
    duration = float(meta.get("duration", 0))
    st.markdown('<div class="ac-heading">What we found</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="ac-meta">{name} &middot; {duration:.0f} sec</div>', unsafe_allow_html=True)
    report_version = str(meta.get("analyzer_version") or "unknown / earlier version")
    st.markdown(f'<div class="ac-analysis-build">Analyzed with engine: {html.escape(report_version)} · Current engine: {html.escape(ANALYZER_VERSION)}</div>', unsafe_allow_html=True)
    if report_version != ANALYZER_VERSION:
        st.warning('This report was created by an older or unverified analyzer. Please upload the recording again after the v2.5.0 deployment completes.')
    results = sorted_findings(report.get("rows", []))
    plots = meta.get("spectrograms", {})
    st.markdown('<div class="ac-grid">' + "".join(
        card(LABELS[key][0], item, key, evidence_plots=(plots.get('Stereo phase / delay',[]) if key=='Stereo / phase' else plots.get(key,[])))
        for key, item in results) + '</div>', unsafe_allow_html=True)
    with st.expander("File details & all embedded tags"):
        info = meta.get("file_history", {}).get("facts", {})
        bits = info.get("bitrate_kbps")
        rate_text = f" · {bits} kbps" if bits else ""
        st.caption(f'Codec: {meta.get("codec", "unknown")}{rate_text} · '
                   f'Sample rate: {meta.get("input_rate", "?")} Hz · '
                   f'Channels: {meta.get("channels", "?")} · '
                   f'Container: {meta.get("container", "unknown")} · '
                   f'Sample type: {meta.get("sample_fmt") or "unknown"} · '
                   f'Stored bit depth: {meta.get("bits_per_sample") or "unknown"} · '
                   f'Size: {meta.get("file_size_bytes", 0):,} bytes · '
                   f'Analyzed: {meta.get("analyzed_seconds", 0):.1f} s')
        tags = meta.get('embedded_metadata') or {}
        entries = tags.get('tags', []) if isinstance(tags, dict) else []
        st.markdown(f'**Embedded fields:** {len(entries)} (artwork is not displayed).'
                 ' These are editable file tags, not authenticated song identifications.')
        if entries:
            st.dataframe(entries, hide_index=True, use_container_width=True)
        else:
            st.caption('No readable track / station / encoder text fields were found in this file.')
        scan = meta.get('ndr_screening') or []
        if scan:
            st.markdown('**10 kHz notch screening (independent excerpts)**')
            st.caption('These are measured candidates; qualifying indicates the dip passed the repeatability and comparison-band checks. A notch alone does not prove NDR origin.')
            st.dataframe(scan, hide_index=True, use_container_width=True)
        rds = meta.get('rds') or {}
        found_rds = rds.get('decoded') or {}
        if found_rds:
            st.markdown('**Decoded over-the-air RDS**')
            st.dataframe([{'field': k, 'value': v} for k, v in found_rds.items()],
                         hide_index=True, use_container_width=True)
        else:
            st.caption('No on-air RadioText, station name or RT+ artist/title was decoded.')
    st.markdown('<div class="ac-foot">Fun clues, not proof. Noise can come from a later recording or copy.</div>',
                unsafe_allow_html=True)
