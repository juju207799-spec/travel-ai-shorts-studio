import streamlit as st
import os, json, tempfile, subprocess, textwrap, math, wave, struct, shutil
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps
import imageio_ffmpeg

st.set_page_config(page_title='Travel AI Shorts Studio', page_icon='✈️', layout='wide')
st.title('✈️ Travel AI Shorts Studio')
st.caption('작동하는 첫 버전 · 조사 → 팩트체크 → 대본 → TTS → 컷 배치 → MP4 내보내기')

FONT_CANDIDATES=['/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc','C:/Windows/Fonts/malgun.ttf','/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf']
FONT=next((p for p in FONT_CANDIDATES if os.path.exists(p)),None)

def font(size):
    return ImageFont.truetype(FONT,size) if FONT else ImageFont.load_default()

def wrap_text(text,draw,f,maxwidth):
    lines=[]
    for paragraph in str(text).split('\n'):
        buf=''
        for ch in paragraph:
            if draw.textbbox((0,0),buf+ch,font=f)[2] > maxwidth and buf:
                lines.append(buf);buf=ch
            else:buf+=ch
        lines.append(buf)
    return lines

def make_frame(text,idx,n,upload=None):
    size=(540,960)
    if upload:
        im=Image.open(upload).convert('RGB');im=ImageOps.fit(im,size)
    else:
        colors=[(20,49,62),(35,65,65),(50,49,70),(52,71,77),(42,57,70),(33,63,67)]
        im=Image.new('RGB',size,colors[idx%len(colors)])
        d=ImageDraw.Draw(im)
        for k in range(12):
            y=110+k*80
            d.line((0,y,540,y-120),fill=(70,90,95),width=2)
        d.text((35,50),'TRAVEL AI SHORTS',font=font(26),fill='#e8d6ac')
    overlay=Image.new('RGBA',size,(0,0,0,0));d=ImageDraw.Draw(overlay)
    d.rectangle((0,620,540,960),fill=(0,0,0,190))
    f=font(37);lines=wrap_text(text,d,f,470)
    if len(lines)>5:lines=lines[:5]
    y=700-max(0,len(lines)-3)*23
    for line in lines:
        d.text((270,y),line,font=f,anchor='mt',fill='white',stroke_width=1,stroke_fill='black')
        y+=54
    d.text((30,913),f'{idx+1:02d} / {n:02d}',font=font(19),fill='#d7d7d7')
    return Image.alpha_composite(im.convert('RGBA'),overlay).convert('RGB')

def make_video(texts,uploads,seconds=30):
    ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
    temp=tempfile.mkdtemp(prefix='travel_studio_')
    clips=[]
    per=seconds/len(texts)
    for i,t in enumerate(texts):
        frame=make_frame(t,i,len(texts),uploads[i] if i<len(uploads) else None)
        jpg=os.path.join(temp,f'frame_{i}.jpg');frame.save(jpg,quality=90)
        clip=os.path.join(temp,f'clip_{i}.mp4')
        cmd=[ffmpeg,'-hide_banner','-loglevel','error','-y','-loop','1','-framerate','25','-i',jpg,'-t',str(per),'-vf','scale=540:960,format=yuv420p','-r','25','-c:v','libx264','-preset','ultrafast','-pix_fmt','yuv420p',clip]
        subprocess.run(cmd,check=True,timeout=90)
        clips.append(clip)
    concat=os.path.join(temp,'concat.txt')
    with open(concat,'w',encoding='utf8') as f:
        for c in clips:f.write("file '"+c.replace("'","'\\''")+"'\n")
    output=os.path.join(temp,'short.mp4')
    subprocess.run([ffmpeg,'-hide_banner','-loglevel','error','-y','-f','concat','-safe','0','-i',concat,'-c','copy',output],check=True,timeout=90)
    return output,temp

DEFAULT_SCENES=[
'이런 호텔, 여행 목록에 저장해 두세요',
'창밖 풍경과 객실 분위기부터 확인하세요',
'수영장과 조식은 공식 사진으로 비교하세요',
'예약 전에 위치와 이동 시간을 확인하세요',
'취소 규정과 세금 포함 최종 금액도 확인!',
'마음에 들면 저장하고 숙소 정보를 비교해 보세요'
]

with st.sidebar:
    st.header('기본 설정')
    st.selectbox('콘텐츠 분야',['호텔·리조트','풀빌라','여행지'],index=0)
    st.selectbox('조사 기간',['최근 7일','최근 1일','최근 30일'],index=0)
    seconds=st.selectbox('영상 길이(초)',[30,15,45,60],index=0)
    voice=st.selectbox('음성 스타일',['여성','남성'],index=0)
    st.info('여성 음성은 브라우저의 TTS 미리듣기로 지원합니다. MP4 음성 삽입은 다음 버전 기능입니다.')

tabs=st.tabs(['① 조사','② 팩트체크','③ 대본','④ TTS','⑤ 소재·컷 배치','⑥ 내보내기'])
with tabs[0]:
    st.subheader('여행 주제 조사')
    topic=st.text_input('영상 주제','발리 호텔 예약 전에 확인할 5가지',key='topic')
    st.write('아래 링크로 최근 7일 검색을 직접 확인할 수 있습니다. 이 버전은 검색 결과를 자동 수집하지 않습니다.')
    from urllib.parse import quote
    st.link_button('Google에서 최근 7일 검색',f'https://www.google.com/search?q={quote(topic)}&tbs=qdr:w')
    st.link_button('YouTube에서 관련 영상 검색',f'https://www.youtube.com/results?search_query={quote(topic)}')
    source=st.text_area('확인한 공식 출처 URL / 조사 메모',placeholder='공식 숙소 페이지, 확인한 시설·위치·예약 규정 등을 입력')
with tabs[1]:
    st.subheader('사실 확인 체크리스트')
    checked={}
    for item in ['숙소 이름·위치','시설·서비스·객실 정보','가격·세금·취소 규정','이미지·영상 상업적 사용 권리','제휴 광고 고지']:
        checked[item]=st.checkbox(item,key='check_'+item)
    st.caption('가격과 예약 가능 여부는 변동됩니다. 실제 호텔 소개는 공식 출처를 직접 확인하세요.')
with tabs[2]:
    st.subheader('30초 숏폼 대본·장면')
    st.caption('첫 버전은 편집 가능한 템플릿입니다. AI 자동 대본 생성은 다음 연결 단계입니다.')
    scenes=[]
    for i,default in enumerate(DEFAULT_SCENES):
        scenes.append(st.text_input(f'{i+1}번 컷 (약 {seconds/6:g}초)',default,key=f'scene{i}'))
    narration=st.text_area('전체 내레이션',value=' '.join(DEFAULT_SCENES),height=120)
    affiliate=st.text_input('광고 고지 문구','이 콘텐츠에는 제휴 링크가 포함될 수 있으며 구매 시 수수료를 받을 수 있습니다.')
with tabs[3]:
    st.subheader('여성 목소리 TTS 미리듣기')
    st.write('아래 버튼을 누르면 브라우저에 설치된 한국어 음성으로 대본을 읽어줍니다. 브라우저와 운영체제에 따라 목소리가 달라질 수 있습니다.')
    import streamlit.components.v1 as components
    st.button('대본 확인 완료',key='tts_confirm')
    import json as _json
    safe_script=_json.dumps(narration,ensure_ascii=False).replace('<','\\u003c')
    components.html(f'''<button onclick="speak()" style="padding:12px;border-radius:8px;cursor:pointer">▶ 여성 목소리로 듣기</button> <button onclick="speechSynthesis.cancel()" style="padding:12px;border-radius:8px">■ 정지</button><script>function speak(){{speechSynthesis.cancel();let u=new SpeechSynthesisUtterance({safe_script});u.lang='ko-KR';u.rate=1;let v=speechSynthesis.getVoices().find(x=>x.lang.startsWith('ko')&&/female|woman|여성|heami|sunhi|유나/i.test(x.name))||speechSynthesis.getVoices().find(x=>x.lang.startsWith('ko'));if(v)u.voice=v;speechSynthesis.speak(u);}}</script>''',height=75)
with tabs[4]:
    st.subheader('사진 소재 및 컷 배치')
    st.write('사용 허가를 받은 호텔 사진을 업로드하면 장면 배경으로 사용합니다. 사진이 없으면 기본 디자인 배경으로 영상을 만듭니다.')
    files=st.file_uploader('사진 업로드 (최대 6장, JPG/PNG)',type=['jpg','jpeg','png'],accept_multiple_files=True)
    if files:
        st.image([Image.open(f) for f in files[:6]],width=120)
    st.warning('AI로 생성한 가상 숙소 장면을 실제 호텔의 모습으로 표시하지 마세요.')
with tabs[5]:
    st.subheader('MP4 내보내기')
    st.write('현재 버전은 9:16, 540×960, 30초의 **무음 자막형 MP4**를 실제로 생성합니다. 영상 속 내레이션 음성 삽입과 SNS 자동 게시 기능은 아직 없습니다.')
    st.write('제작된 영상에는 직접 입력한 컷 문구와 업로드한 사진(또는 기본 배경)이 사용됩니다.')
    if st.button('🎬 MP4 영상 만들기',type='primary'):
        try:
            with st.spinner('영상을 렌더링 중입니다. 잠시 기다려 주세요...'):
                output,temp=make_video(scenes,files[:6] if files else [],seconds)
                with open(output,'rb') as f:st.session_state['mp4']=f.read()
                shutil.rmtree(temp,ignore_errors=True)
            st.success('MP4 영상 제작 완료!')
        except Exception as e:
            st.error('렌더링 실패: '+str(e))
    if 'mp4' in st.session_state:
        st.video(st.session_state['mp4'])
        st.download_button('⬇ MP4 다운로드',st.session_state['mp4'],file_name='travel_short_30s.mp4',mime='video/mp4')
    st.download_button('대본·제휴 문구 JSON 저장',json.dumps({'topic':topic,'source':source,'scenes':scenes,'narration':narration,'affiliate_disclosure':affiliate,'fact_check':checked},ensure_ascii=False,indent=2),file_name='travel_short_project.json',mime='application/json')
