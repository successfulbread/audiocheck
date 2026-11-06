"""AudioCheck v0.9 — simple light-theme Streamlit audio clues."""
from __future__ import annotations

import html
from pathlib import Path
import tempfile

import streamlit as st

from analyzer import MAX_BYTES, analyze, analyze_path
from youtube_source import download_youtube_audio

st.set_page_config(page_title='AudioCheck | Recording clues',
                   page_icon=':material/graphic_eq:', layout='centered',
                   initial_sidebar_state='collapsed')

st.markdown('''
<style>
.stApp {background:#F7FAFF; color:#14233D;}
.block-container {max-width:930px; padding-top:1.25rem; padding-bottom:3rem;}
header[data-testid="stHeader"] {background:transparent;}
.ac-hero {background:linear-gradient(112deg,#E6F2FF 0%,#F2EDFF 55%,#FFF5DE 100%);
 border:1px solid #D9E3F4; border-radius:22px; padding:29px 29px 25px;
 box-shadow:0 6px 22px #263d6010; margin:3px 0 22px;}
.ac-kicker {font-size:.73rem; font-weight:850; text-transform:uppercase;
 letter-spacing:.13em; color:#365BB0; margin-bottom:9px;}
.ac-title {font-size:clamp(2.3rem,6vw,3.55rem); font-weight:900;
 line-height:1.05; letter-spacing:-.055em; color:#162747; margin:0 0 10px;}
.ac-title b {color:#2564C4;}
.ac-sub {color:#3D516E; font-size:.96rem; line-height:1.6; max-width:680px;}
.ac-tags {display:flex;gap:8px;flex-wrap:wrap;margin-top:16px;}
.ac-tag {background:#FFFFFFBB;border:1px solid #D6E0F1;color:#325274;
 border-radius:99px;padding:6px 11px;font-size:.73rem;font-weight:750;}
.ac-heading {color:#1A3050;font-size:1.28rem;font-weight:850;margin:18px 0 8px;}
.ac-help {font-size:.9rem;line-height:1.5;color:#465D78;margin-bottom:11px;}
.ac-meta {background:#FFFFFF; border:1px solid #E1E7F2; border-radius:13px;
 padding:12px 15px; font-size:.81rem;color:#516580;margin:12px 0 18px;}
.ac-meta strong {display:block;color:#182D4C;font-size:.94rem;margin-bottom:4px;}
.ac-source {background:#FFFFFF;border:1px solid #C7DBF1;border-left:6px solid #276AC4;
 border-radius:19px;padding:20px 22px;box-shadow:0 8px 26px #2C4D7D12;margin:12px 0 16px;}
.ac-eyepill {color:#3560AB;text-transform:uppercase;letter-spacing:.11em;
 font-size:.7rem;font-weight:850;margin-bottom:7px;}
.ac-source-title {font-size:1.52rem;color:#14365D;line-height:1.25;font-weight:850;margin-bottom:7px;}
.ac-source-small {color:#405873;font-size:.86rem;line-height:1.56;}
.ac-grid {display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));
 gap:12px;margin:11px 0 19px;}
.ac-card {background:white;border:1px solid #DEE6F1;border-left:5px solid #5180C4;
 border-radius:15px;padding:15px 17px 13px;box-shadow:0 4px 13px #38567C0B;}
.ac-card.good {border-left-color:#128667;}
.ac-card.possible {border-left-color:#3C6DC5;}
.ac-card.weak {border-left-color:#CA8221;}
.ac-label {font-size:.71rem;color:#516782;letter-spacing:.06em;
 font-weight:850;text-transform:uppercase;margin-bottom:7px;}
.ac-result {color:#152C4C;font-size:1.07rem;line-height:1.37;font-weight:850;margin-bottom:10px;}
.ac-badge {display:inline-block;font-size:.7rem;font-weight:780;border-radius:99px;padding:4px 9px;}
.ac-badge.good {background:#DDF6E9;color:#096444;}
.ac-badge.possible {background:#E8F0FF;color:#2457AE;}
.ac-badge.weak {background:#FFF0D6;color:#86510B;}
.ac-card details {border-top:1px solid #E7ECF4;margin-top:11px;padding-top:9px;}
.ac-card summary {color:#325A91;font-size:.8rem;font-weight:750;cursor:pointer;}
.ac-card details p {color:#51617B;font-size:.8rem;line-height:1.55;margin:9px 0 0;}
.ac-explain {background:#EDF8FA;border:1px solid #CEE7E9;border-radius:15px;
 padding:17px 19px;margin:13px 0 21px;}
.ac-explain h4 {margin:0 0 7px;font-size:.94rem;color:#12576B;}
.ac-explain p {margin:0;line-height:1.65;font-size:.89rem;color:#31576B;}
.ac-foot {font-size:.79rem;color:#59708A;line-height:1.55;margin-top:13px;}
@media(max-width:650px){.ac-hero{padding:21px 19px;border-radius:16px;}
 .ac-grid{grid-template-columns:1fr}.ac-source{padding:18px 17px;}
 .block-container{padding-top:.6rem;}}
</style>
''', unsafe_allow_html=True)

st.markdown('''
<section class="ac-hero">
  <div class="ac-kicker">The audio archaeology lab</div>
  <div class="ac-title">Audio<b>Check</b></div>
  <div class="ac-sub">Discover clues about old recordings: vinyl and cassette artifacts,
  radio or TV traces, electrical hum and the famous NDR 10 kHz dip.</div>
  <div class="ac-tags">
    <span class="ac-tag">Up to 5 minutes</span>
    <span class="ac-tag">Simple best guesses</span>
    <span class="ac-tag">Audio evidence, explained</span>
  </div>
</section>''', unsafe_allow_html=True)

if 'report' not in st.session_state:
    st.session_state.report=None
if 'report_error' not in st.session_state:
    st.session_state.report_error=None

def store_report(rows, meta, name, kind):
    st.session_state.report={'rows':rows,'meta':meta,'name':name,'kind':kind}
    st.session_state.report_error=None

st.markdown('<div class="ac-heading">Check a recording</div>',unsafe_allow_html=True)
st.markdown('<div class="ac-help">Choose an audio file, then press <b>Analyze recording</b>. Alternatively, try a permitted YouTube link.</div>',unsafe_allow_html=True)
upload_tab, youtube_tab=st.tabs(['Upload audio','YouTube link (beta)'])
with upload_tab:
    with st.form('upload_form',clear_on_submit=False,enter_to_submit=False):
        uploaded=st.file_uploader('Choose audio file',type=['mp3','mpeg','mpga','wav','flac','ogg','m4a'],
                                  accept_multiple_files=False,max_upload_size=100)
        pressed=st.form_submit_button('Analyze recording',type='primary',use_container_width=True)
    if pressed:
        st.session_state.report=None
        if uploaded is None:
            st.session_state.report_error='No file arrived from your browser. Select the file again and press Analyze.'
        elif uploaded.size>MAX_BYTES:
            st.session_state.report_error='Please choose a file smaller than 100 MB.'
        else:
            try:
                with st.spinner('Checking recording clues...'):
                    name=Path(uploaded.name).name
                    rows,meta=analyze(uploaded.getvalue(),name)
                store_report(rows,meta,name,'Uploaded file')
            except ValueError as ex:
                st.session_state.report_error=str(ex)
            except Exception:
                st.session_state.report_error='Analysis failed; view the Streamlit app logs for details.'
with youtube_tab:
    st.caption('YouTube may block audio retrieval from Streamlit Cloud. Uploading a permitted audio file is more reliable.')
    with st.form('youtube_form',clear_on_submit=False,enter_to_submit=False):
        link=st.text_input('YouTube video address',placeholder='https://www.youtube.com/watch?v=...')
        permitted=st.checkbox('I am authorized to download and analyze this audio.')
        pressed_yt=st.form_submit_button('Analyze YouTube audio',type='primary',use_container_width=True)
    if pressed_yt:
        st.session_state.report=None
        if not link.strip():
            st.session_state.report_error='Please paste a YouTube URL.'
        elif not permitted:
            st.session_state.report_error='Please confirm that downloading this audio is permitted.'
        else:
            try:
                with st.spinner('Retrieving audio from YouTube...'):
                    with tempfile.TemporaryDirectory(prefix='audiocheck_yt_') as td:
                        path,title=download_youtube_audio(link,Path(td))
                        rows,meta=analyze_path(path,title)
                store_report(rows,meta,title,'YouTube audio')
            except ValueError as ex:
                st.session_state.report_error=str(ex)
            except Exception:
                st.session_state.report_error='This YouTube audio cannot be retrieved from Streamlit Cloud. Try a file upload.'

if st.session_state.report_error:
    st.error(st.session_state.report_error)


def meaningful(item):
    return item['certainty'] in {'Strong','High','Possible','Tentative'} and \
           not any(w in item['result'].lower() for w in ('none detected','not measurable','unclear','no reliable','no clear'))

def badge_class(item):
    return {'Strong':'good','High':'good','Possible':'possible','Tentative':'weak'}.get(item['certainty'],'weak')

def card(label,item):
    cls=badge_class(item)
    certainty={'Strong':'Strong clue','High':'Strong clue','Possible':'Good clue','Tentative':'Early clue'}.get(item['certainty'],'Unknown')
    return (f'<div class="ac-card {cls}"><div class="ac-label">{html.escape(label)}</div>'
            f'<div class="ac-result">{html.escape(str(item["result"]))}</div>'
            f'<span class="ac-badge {cls}">{certainty}</span>'
            '<details><summary>Why?</summary>'
            f'<p>{html.escape(str(item["detail"]))}</p></details></div>')


def summary(found):
    notes=[]
    source=found['Likely audio source']['result'].lower()
    if 'record' in source:
        if meaningful(found.get('Disc surface noise', {})):
            notes.append('Sharp, irregular pops and crackle, including noise between musical sounds, are consistent with a record transfer.')
        else:
            notes.append('Some very short clicks have turntable-like timing, suggesting a disc somewhere in the recording chain.')
    elif 'fm radio' in source:
        notes.append('A narrow 19 kHz signal suggests the audio passed through an FM stereo broadcast chain.')
    elif 'tv / monitor' in source:
        notes.append('A TV-related scan tone suggests a television or monitor was part of the recording or transfer chain.')
    elif 'cassette' in source:
        notes.append('Tape-like interruptions are present, but similar defects can arise in other ways.')
    else:
        notes.append('The original medium is hard to distinguish from this sample, but some individual technical clues may still help.')
    rpm=found.get('Vinyl rotation',{})
    if meaningful(rpm):
        notes.append('Some unusually short pops repeat at a rate consistent with '+rpm['result'].replace('Likely ','').replace('Possible ','')+'.')
    broadcast=found.get('Radio / TV signals',{})
    if meaningful(broadcast):
        if 'NTSC' in broadcast['result']:
            notes.append('A narrow signal around 15,734 Hz matches an NTSC-type television scanning frequency.')
        elif 'PAL' in broadcast['result']:
            notes.append('A narrow signal around 15,625 Hz matches a PAL/SECAM-type television scanning frequency.')
        elif 'FM' in broadcast['result']:
            notes.append('A 19 kHz tone is compatible with an FM stereo pilot.')
    ndr=found.get('NDR-style 10 kHz dip',{})
    if meaningful(ndr):
        notes.append('A persistent dip near 10 kHz resembles an effect seen on some 1980s NDR radio tapes, but it is not unique to NDR.')
    electrical=found.get('Likely power system',{})
    if meaningful(electrical):
        family='50' if '50 Hz' in electrical['result'] else '60'
        notes.append(f'A {family} Hz-related electrical clue was found; it might have entered during a later copy.')
    return ' '.join(notes)

report=st.session_state.report
if report:
    rows,meta=report['rows'],report['meta']
    found=dict(rows)
    st.markdown('<div class="ac-heading">Your results</div>',unsafe_allow_html=True)
    st.markdown('<div class="ac-meta"><strong>'+html.escape(report['name'])+'</strong>'+
      html.escape(report['kind'])+f' · {meta["duration"]:.0f} sec · {meta["analyzed_seconds"]:.0f} sec analyzed</div>',
      unsafe_allow_html=True)
    src=found['Likely audio source']
    st.markdown('<section class="ac-source"><div class="ac-eyepill">Best guess: recording source</div>'+
                '<div class="ac-source-title">'+html.escape(src['result'])+'</div>'+
                '<div class="ac-source-small">'+html.escape('Evidence level: '+src['certainty'])+'</div></section>',
                unsafe_allow_html=True)
    st.markdown('<section class="ac-explain"><h4>What the clues suggest</h4><p>'+
                html.escape(summary(found))+'</p></section>',unsafe_allow_html=True)
    priority=[('Vinyl rotation','Record speed'),('Likely power system','Power region'),
              ('Radio / TV signals','TV / radio signal'),('NDR-style 10 kHz dip','NDR 10 kHz dip')]
    positive=[(short,found[key]) for key,short in priority if key in found and meaningful(found[key])]
    rank={'Strong':0,'High':0,'Possible':1,'Tentative':2}
    positive.sort(key=lambda entry:rank.get(entry[1]['certainty'],3))
    if positive:
        st.markdown('<div class="ac-heading">Other clues found</div>',unsafe_allow_html=True)
        st.markdown('<div class="ac-grid">'+''.join(card(*entry) for entry in positive)+'</div>',unsafe_allow_html=True)
    remaining=[(key,found[key]) for key in ('Disc surface noise','Possible tape dropouts',
      'Audio bandwidth','Stereo format') if key in found and meaningful(found[key])]
    if remaining:
        with st.expander('More audio details'):
            for key,item in remaining:
                st.markdown(f'**{key}:** {item["result"]}')
                st.caption(item['detail'])
    negative=[(key,item) for key,item in rows if key not in {'Likely audio source',
              'Recording-medium clues'} and not meaningful(item)]
    if negative:
        with st.expander('Checks without a clear finding'):
            for key,item in negative:
                st.write(f'**{key}:** {item["result"]}')
                st.caption(item['detail'])
    with st.expander('Technical file information'):
        st.write(f'Codec: {meta["codec"]} · Sample rate: {meta["input_rate"]:,} Hz · Channels: {meta["channels"]}')
        st.write(f'Sampled sections: {meta["diagnostics"]["sampled_sections"]}')
    st.markdown('<div class="ac-foot">Results are informed estimates, not verified probabilities. '
                'Electrical and broadcast interference can enter at any stage of copying or transfer.</div>',
                unsafe_allow_html=True)
else:
    st.markdown('<div class="ac-foot">AudioCheck looks for characteristic patterns rather than '
                'identifying a song or its performers. Results may be tentative.</div>',unsafe_allow_html=True)
