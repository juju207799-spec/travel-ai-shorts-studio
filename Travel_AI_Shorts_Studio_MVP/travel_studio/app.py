import asyncio
import os
import subprocess
import tempfile
from pathlib import Path

import imageio_ffmpeg
import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageOps

st.set_page_config(page_title='Travel AI Shorts Studio 3.0', page_icon='✈️', layout='wide')
st.title('✈️ Travel AI Shorts Studio 3.0')
st.caption('사진 + 동영상 혼합 업로드 → 장면 자동 연결 → 자막·선택적 여성 음성 → MP4 다운로드')
st.info('이 버전은 사용자가 업로드한 사진·동영상으로 편집합니다. AI 영상 생성 및 자동 자료 조사는 아직 연결되지 않았습니다.')

FONT_PATHS = ['/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 'C:/Windows/Fonts/malgun.ttf']

def get_font(size):
    for path in FONT_PATHS:
        if os.path.isfile(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()

def call_ffmpeg(args):
    cmd = [imageio_ffmpeg.get_ffmpeg_exe(), '-hide_banner', '-loglevel', 'error', '-y', *args]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=240)
    if result.returncode:
        raise RuntimeError(result.stderr[-1800:] or 'FFmpeg 처리 실패')

def caption_png(text, target):
    image = Image.new('RGBA', (720, 1280), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    f = get_font(42)
    lines = []
    for paragraph in text.splitlines():
        line = ''
        for char in paragraph:
            trial = line + char
            if draw.textbbox((0, 0), trial, font=f)[2] > 630 and line:
                lines.append(line)
                line = char
            else:
                line = trial
        if line:
            lines.append(line)
    lines = lines[:5]
    if lines:
        line_height = 61
        top = 960 - (len(lines)-1)*line_height//2
        draw.rounded_rectangle((30, top-25, 690, top+len(lines)*line_height+20), radius=24, fill=(0,0,0,170))
        for idx, line in enumerate(lines):
            bounds = draw.textbbox((0, 0), line, font=f)
            width = bounds[2]-bounds[0]
            draw.text(((720-width)/2, top+idx*line_height), line, font=f, fill='white', stroke_width=2, stroke_fill='black')
    image.save(target)

async def tts_save(text, output):
    import edge_tts
    communicate = edge_tts.Communicate(text, 'ko-KR-SunHiNeural')
    await communicate.save(str(output))

st.subheader('① 영상 설정')
col1, col2, col3 = st.columns(3)
with col1:
    duration = st.selectbox('완성 영상 길이', [15, 30, 60], index=1, format_func=lambda v: f'{v}초')
with col2:
    voice_on = st.checkbox('여성 AI 내레이션 시도', value=False, help='인터넷 음성 서비스 연결이 필요합니다. 실패하면 무음 영상으로 제작합니다.')
with col3:
    resolution = st.selectbox('화질', ['720 × 1280 (빠른 제작)', '1080 × 1920 (고화질)'], index=0)
    w, h = ((720, 1280) if resolution.startswith('720') else (1080, 1920))

st.subheader('② 사진·동영상 업로드')
files = st.file_uploader('사진 JPG/PNG 및 동영상 MP4/MOV/WEBM을 합쳐 최대 30개 업로드하세요.', type=['jpg','jpeg','png','webp','mp4','mov','webm'], accept_multiple_files=True)
if files:
    st.write(f'업로드한 소재: **{len(files)}개**')
    if len(files) > 30:
        st.error('한 번에 최대 30개까지 가능합니다. 파일을 줄여주세요.')
    st.caption('장면 순서는 아래 번호로 바꿀 수 있습니다. 같은 번호가 있으면 업로드 순서를 따릅니다.')
    rows = [{'순서': i+1, '파일 이름': f.name, '자막': ''} for i, f in enumerate(files)]
    edits = st.data_editor(rows, hide_index=True, num_rows='fixed', use_container_width=True, column_config={'파일 이름': st.column_config.TextColumn(disabled=True), '순서': st.column_config.NumberColumn(min_value=1, max_value=30, step=1)})
else:
    edits = []

st.subheader('③ 내레이션 및 자막')
script = st.text_area('전체 내레이션 대본 (선택 사항)', placeholder='발리에서 특별한 휴가를 꿈꾸시나요? 아름다운 풀빌라를 소개합니다.', height=100)
st.caption('장면별 자막을 비워두면 전체 대본을 장면 수에 맞춰 나누어 표시합니다. 음성은 전체 대본으로 생성합니다.')

if st.button('🎬 MP4 영상 제작하기', type='primary', disabled=not files or len(files)>30, use_container_width=True):
    try:
        indexed = sorted(range(len(files)), key=lambda i: (int(edits[i]['순서'] or (i+1)), i))
        ordered = [(files[i], str(edits[i]['자막'] or '').strip()) for i in indexed]
        segment_duration = duration / len(ordered)
        sentences = [x.strip() for x in script.replace('!', '!|').replace('?', '?|').replace('.', '.|').split('|') if x.strip()]
        captions = [item[1] or (sentences[min(int(i*len(sentences)/len(ordered)), len(sentences)-1)] if sentences else '') for i,item in enumerate(ordered)]
        progress = st.progress(0, text='영상 제작을 준비하고 있습니다...')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            segments = []
            for i, (uploaded, _) in enumerate(ordered):
                ext = Path(uploaded.name).suffix.lower()
                source = root / f'input_{i:02d}{ext}'
                source.write_bytes(uploaded.getvalue())
                overlay = root / f'caption_{i:02d}.png'
                caption_png(captions[i], overlay)
                output = root / f'segment_{i:02d}.mp4'
                vf = f'scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1,fps=24,format=yuv420p'
                if ext in ('.jpg','.jpeg','.png','.webp'):
                    args = ['-loop','1','-framerate','24','-i',str(source),'-loop','1','-framerate','24','-i',str(overlay),'-filter_complex',f'[0:v]{vf}[bg];[1:v]scale={w}:{h}[cap];[bg][cap]overlay=0:0:shortest=1[v]','-map','[v]','-t',f'{segment_duration:.3f}','-an','-c:v','libx264','-preset','ultrafast','-crf','25','-pix_fmt','yuv420p','-movflags','+faststart',str(output)]
                else:
                    args = ['-stream_loop','-1','-i',str(source),'-loop','1','-framerate','24','-i',str(overlay),'-filter_complex',f'[0:v]{vf}[bg];[1:v]scale={w}:{h}[cap];[bg][cap]overlay=0:0:shortest=1[v]','-map','[v]','-t',f'{segment_duration:.3f}','-an','-c:v','libx264','-preset','ultrafast','-crf','25','-pix_fmt','yuv420p','-movflags','+faststart',str(output)]
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
                    asyncio.run(tts_save(script, voice))
                    call_ffmpeg(['-i',str(joined),'-i',str(voice),'-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','128k','-af',f'apad=whole_dur={duration}','-t',str(duration),'-movflags','+faststart',str(final)])
                    st.success('여성 내레이션이 추가되었습니다.')
                except Exception as exc:
                    st.warning(f'음성 생성에 실패하여 무음 영상으로 제작했습니다: {exc}')
                    final.write_bytes(joined.read_bytes())
            else:
                final.write_bytes(joined.read_bytes())
            data = final.read_bytes()
            progress.progress(100, text='완성!')
            st.video(data)
            st.download_button('⬇️ 완성 MP4 다운로드', data=data, file_name='travel_ai_shorts.mp4', mime='video/mp4', use_container_width=True)
            st.caption('다운로드 버튼을 누르기 전까지 결과는 현재 화면에만 있습니다. 원본 영상 음성은 제거되며, 장면은 균등하게 배분됩니다.')
    except subprocess.TimeoutExpired:
        st.error('영상 처리 시간이 초과되었습니다. 더 짧거나 작은 파일로 다시 시도해 주세요.')
    except Exception as exc:
        st.error(f'영상 제작 중 오류가 발생했습니다: {exc}')

st.divider()
st.caption('사용 권한이 있는 영상만 업로드하세요. 실제 호텔 정보·시설은 게시 전에 확인해 주세요. Streamlit 무료 서버는 큰 파일이나 고화질 편집 시 메모리/시간 제한이 있을 수 있습니다.')
