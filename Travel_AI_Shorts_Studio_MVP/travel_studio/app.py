import asyncio
import os
import subprocess
import tempfile
from pathlib import Path

import imageio_ffmpeg
import streamlit as st

st.set_page_config(page_title='Travel AI Shorts Studio 3.2', page_icon='✈️', layout='wide')
st.title('✈️ Travel AI Shorts Studio 3.2')
st.caption('사진 + 동영상 혼합 업로드 → 장면 자동 연결 → 다양한 AI 목소리 → MP4 다운로드')
st.info('이 버전은 사용자가 업로드한 사진·동영상으로 편집합니다. AI 영상 생성 및 자동 자료 조사는 아직 연결되지 않았습니다.')

def call_ffmpeg(args):
    cmd = [imageio_ffmpeg.get_ffmpeg_exe(), '-hide_banner', '-loglevel', 'error', '-y', *args]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=240)
    if result.returncode:
        raise RuntimeError(result.stderr[-1800:] or 'FFmpeg 처리 실패')

VOICE_OPTIONS = {
    '한국어 · 여성 · 선희': 'ko-KR-SunHiNeural',
    '한국어 · 남성 · 인준': 'ko-KR-InJoonNeural',
    '한국어 · 남성 · 현수(다국어)': 'ko-KR-HyunsuMultilingualNeural',
    '영어(미국) · 여성 · 아리아': 'en-US-AriaNeural',
    '영어(미국) · 남성 · 가이': 'en-US-GuyNeural',
    '일본어 · 여성 · 나나미': 'ja-JP-NanamiNeural',
}

async def tts_save(text, output, voice, rate, pitch):
    import edge_tts
    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    await communicate.save(str(output))

st.subheader('① 영상 설정')
col1, col2 = st.columns(2)
with col1:
    duration = st.selectbox('완성 영상 길이', [15, 30, 60], index=1, format_func=lambda v: f'{v}초')
with col2:
    resolution = st.selectbox('화질', ['720 × 1280 (빠른 제작)', '1080 × 1920 (고화질)'], index=0)
    w, h = ((720, 1280) if resolution.startswith('720') else (1080, 1920))

st.subheader('② 사진·동영상 업로드')
files = st.file_uploader('사진 JPG/PNG 및 동영상 MP4/MOV/WEBM을 합쳐 최대 30개 업로드하세요.', type=['jpg','jpeg','png','webp','mp4','mov','webm'], accept_multiple_files=True)
if files:
    st.write(f'업로드한 소재: **{len(files)}개**')
    if len(files) > 30:
        st.error('한 번에 최대 30개까지 가능합니다. 파일을 줄여주세요.')
    st.caption('장면 순서는 아래 번호로 바꿀 수 있습니다. 같은 번호가 있으면 업로드 순서를 따릅니다.')
    rows = [{'순서': i+1, '파일 이름': f.name} for i, f in enumerate(files)]
    edits = st.data_editor(rows, hide_index=True, num_rows='fixed', use_container_width=True, column_config={'파일 이름': st.column_config.TextColumn(disabled=True), '순서': st.column_config.NumberColumn(min_value=1, max_value=30, step=1)})
else:
    edits = []

st.subheader('③ AI 내레이션 설정 (자막 없음)')
voice_on = st.checkbox('AI 내레이션 넣기', value=True, help='온라인 음성 서비스가 실패하면 무음 영상으로 제작합니다.')
voice_label = st.selectbox('목소리 선택', list(VOICE_OPTIONS), disabled=not voice_on)
voice_id = VOICE_OPTIONS[voice_label]
col_rate, col_pitch = st.columns(2)
with col_rate:
    speed = st.slider('말하기 속도', min_value=-40, max_value=40, value=0, step=5, format='%d%%', disabled=not voice_on)
with col_pitch:
    pitch = st.slider('목소리 높낮이', min_value=-20, max_value=20, value=0, step=5, format='%d Hz', disabled=not voice_on)
script = st.text_area('전체 내레이션 대본', placeholder='쿠알라룸푸르에서 특별한 하루를 보내고 싶다면, 르 메르디앙을 만나보세요.', height=130, disabled=not voice_on)
st.caption('영상에는 자막과 검은색 배경이 전혀 들어가지 않습니다. 음성 길이가 영상 길이보다 길면 마지막 부분이 잘릴 수 있습니다.')

if st.button('🎬 MP4 영상 제작하기', type='primary', disabled=not files or len(files)>30, use_container_width=True):
    try:
        indexed = sorted(range(len(files)), key=lambda i: (int(edits[i]['순서'] or (i+1)), i))
        ordered = [files[i] for i in indexed]
        segment_duration = duration / len(ordered)
        progress = st.progress(0, text='영상 제작을 준비하고 있습니다...')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            segments = []
            for i, uploaded in enumerate(ordered):
                ext = Path(uploaded.name).suffix.lower()
                source = root / f'input_{i:02d}{ext}'
                source.write_bytes(uploaded.getvalue())
                output = root / f'segment_{i:02d}.mp4'
                vf = f'scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1,fps=24,format=yuv420p'
                if ext in ('.jpg', '.jpeg', '.png', '.webp'):
                    args = ['-loop', '1', '-framerate', '24', '-i', str(source),
                            '-vf', vf, '-t', f'{segment_duration:.3f}', '-an',
                            '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '25',
                            '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(output)]
                else:
                    args = ['-stream_loop', '-1', '-i', str(source),
                            '-vf', vf, '-t', f'{segment_duration:.3f}', '-an',
                            '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '25',
                            '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(output)]
                call_ffmpeg(args)
                segments.append(output)
                progress.progress(int(80*(i+1)/len(ordered)), text=f'{i+1}/{len(ordered)}개 장면 처리 완료')
            concat_file = root / 'list.txt'
            concat_file.write_text(''.join(f"file '{p.name}'\n" for p in segments), encoding='utf-8')
            joined = root / 'joined.mp4'
            call_ffmpeg(['-f','concat','-safe','0','-i',str(concat_file),'-c','copy',str(joined)])
            final = root / 'final.mp4'
            if voice_on and script.strip():
                try:
                    voice = root / 'voice.mp3'
                    asyncio.run(tts_save(script, voice, voice_id, f'{speed:+d}%', f'{pitch:+d}Hz'))
                    call_ffmpeg(['-i',str(joined),'-i',str(voice),'-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','128k','-af',f'apad=whole_dur={duration}','-t',str(duration),'-movflags','+faststart',str(final)])
                    st.success(f'{voice_label} 내레이션이 추가되었습니다.')
                except Exception as exc:
                    st.warning(f'음성 생성에 실패하여 무음 영상으로 제작했습니다: {exc}')
                    final.write_bytes(joined.read_bytes())
            else:
                final.write_bytes(joined.read_bytes())
            data = final.read_bytes()
            progress.progress(100, text='완성!')
            st.video(data)
            st.download_button('⬇️ 완성 MP4 다운로드', data=data, file_name='travel_ai_shorts.mp4', mime='video/mp4', use_container_width=True)
            st.caption('다운로드 버튼을 누르기 전까지 결과는 현재 화면에만 있습니다. 자막은 없으며, 원본 영상 음성은 제거되고 장면 길이는 균등하게 배분됩니다.')
    except subprocess.TimeoutExpired:
        st.error('영상 처리 시간이 초과되었습니다. 더 짧거나 작은 파일로 다시 시도해 주세요.')
    except Exception as exc:
        st.error(f'영상 제작 중 오류가 발생했습니다: {exc}')

st.divider()
st.caption('사용 권한이 있는 영상만 업로드하세요. 실제 호텔 정보·시설은 게시 전에 확인해 주세요. Streamlit 무료 서버는 큰 파일이나 고화질 편집 시 메모리/시간 제한이 있을 수 있습니다.')
