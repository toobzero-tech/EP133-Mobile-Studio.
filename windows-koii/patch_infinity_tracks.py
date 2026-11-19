from pathlib import Path

root = Path("/tmp/koii-src/EP133_KOII_Windows_0.5.0")

def rep(rel, old, new):
    p = root / rel
    s = p.read_text(encoding="utf-8")
    if new in s:
        return
    if old not in s:
        raise SystemExit(f"Track patch anchor missing: {rel}: {old[:90]!r}")
    p.write_text(s.replace(old, new, 1), encoding="utf-8")

rep("src/engine.hpp", "constexpr int kPads=12, kSteps=64, kPatterns=4;",
    "constexpr int kPads=12, kTracks=8, kSteps=64, kPatterns=4;")
rep("src/engine.hpp", "  void setStep(int pattern,int pad,int step,bool on) noexcept;\n  bool step(int pattern,int pad,int step) const noexcept;",
"""  void setStep(int pattern,int pad,int step,bool on) noexcept;
  bool step(int pattern,int pad,int step) const noexcept;
  void setTrackStep(int pattern,int track,int step,bool on) noexcept;
  bool trackStep(int pattern,int track,int step) const noexcept;
  void setTrackPad(int track,int pad) noexcept;
  int trackPad(int track) const noexcept;
  void setTrackVolume(int track,float value) noexcept;
  float trackVolume(int track) const noexcept;
  void setTrackPan(int track,float value) noexcept;
  float trackPan(int track) const noexcept;
  void setTrackMute(int track,bool value) noexcept;
  bool trackMute(int track) const noexcept;
  void setTrackSolo(int track,bool value) noexcept;
  bool trackSolo(int track) const noexcept;""")
rep("src/engine.hpp", "  struct Voice { int pad{-1}; uint64_t age{}; float phase{},env{},velocity{}; size_t samplePos{}; bool sampled{false}; };",
    "  struct Voice { int pad{-1}; uint64_t age{}; float phase{},env{},velocity{},pan{}; size_t samplePos{}; bool sampled{false}; };")
rep("src/engine.hpp", "  std::array<std::array<std::array<std::atomic<uint8_t>,kSteps>,kPads>,kPatterns> grid_{};",
"""  std::array<std::array<std::array<std::atomic<uint8_t>,kSteps>,kPads>,kPatterns> grid_{};
  std::array<std::array<std::array<std::atomic<uint8_t>,kSteps>,kTracks>,kPatterns> trackGrid_{};
  std::array<std::atomic<int>,kTracks> trackPads_{};
  std::array<std::atomic<float>,kTracks> trackVolumes_{},trackPans_{};
  std::array<std::atomic<uint8_t>,kTracks> trackMutes_{},trackSolos_{};""")
rep("src/engine.hpp", "  void startVoice(int pad,float velocity) noexcept;",
    "  void startVoice(int pad,float velocity,int track=-1) noexcept;")

rep("src/engine.cpp",
"""    for (auto& pattern : grid_)
        for (auto& pad : pattern)
            for (auto& value : pad) value.store(0, std::memory_order_relaxed);
""",
"""    for (auto& pattern : grid_)
        for (auto& pad : pattern)
            for (auto& value : pad) value.store(0, std::memory_order_relaxed);
    for (auto& pattern : trackGrid_)
        for (auto& track : pattern)
            for (auto& value : track) value.store(0, std::memory_order_relaxed);
    for (int track=0; track<kTracks; ++track) {
        trackPads_[track].store(track, std::memory_order_relaxed);
        trackVolumes_[track].store(1.0f, std::memory_order_relaxed);
        trackPans_[track].store(0.0f, std::memory_order_relaxed);
        trackMutes_[track].store(0, std::memory_order_relaxed);
        trackSolos_[track].store(0, std::memory_order_relaxed);
    }
""")
# Keep the original starter groove and mirror its first four lanes into tracks.
for old,new in [
("for (int step = 0; step < kSteps; step += 16) grid_[0][0][step].store(1);",
 "for (int step = 0; step < kSteps; step += 16) { grid_[0][0][step].store(1); trackGrid_[0][0][step].store(1); }"),
("for (int step = 4; step < kSteps; step += 16) grid_[0][1][step].store(1);",
 "for (int step = 4; step < kSteps; step += 16) { grid_[0][1][step].store(1); trackGrid_[0][1][step].store(1); }"),
("for (int step = 0; step < kSteps; step += 2) grid_[0][2][step].store(1);",
 "for (int step = 0; step < kSteps; step += 2) { grid_[0][2][step].store(1); trackGrid_[0][2][step].store(1); }"),
("grid_[0][3][step].store(1);\n        grid_[0][3][step + 8].store(1);",
 "grid_[0][3][step].store(1); trackGrid_[0][3][step].store(1);\n        grid_[0][3][step + 8].store(1); trackGrid_[0][3][step + 8].store(1);")]:
    rep("src/engine.cpp",old,new)

needle="""bool Engine::step(int pattern, int pad, int stepIndex) const noexcept {
    return pattern >= 0 && pattern < kPatterns && pad >= 0 && pad < kPads &&
           stepIndex >= 0 && stepIndex < kSteps &&
           grid_[pattern][pad][stepIndex].load(std::memory_order_acquire) != 0;
}
"""
api=needle+"""void Engine::setTrackStep(int p,int t,int s,bool on) noexcept {
    if(p>=0&&p<kPatterns&&t>=0&&t<kTracks&&s>=0&&s<kSteps)
        trackGrid_[p][t][s].store(on?1:0,std::memory_order_release);
}
bool Engine::trackStep(int p,int t,int s) const noexcept {
    return p>=0&&p<kPatterns&&t>=0&&t<kTracks&&s>=0&&s<kSteps&&
        trackGrid_[p][t][s].load(std::memory_order_acquire)!=0;
}
void Engine::setTrackPad(int t,int p) noexcept { if(t>=0&&t<kTracks&&p>=0&&p<kPads) trackPads_[t].store(p,std::memory_order_release); }
int Engine::trackPad(int t) const noexcept { return t>=0&&t<kTracks?trackPads_[t].load(std::memory_order_acquire):-1; }
void Engine::setTrackVolume(int t,float v) noexcept { if(t>=0&&t<kTracks&&std::isfinite(v)) trackVolumes_[t].store(std::clamp(v,0.0f,1.0f),std::memory_order_release); }
float Engine::trackVolume(int t) const noexcept { return t>=0&&t<kTracks?trackVolumes_[t].load(std::memory_order_acquire):0.0f; }
void Engine::setTrackPan(int t,float v) noexcept { if(t>=0&&t<kTracks&&std::isfinite(v)) trackPans_[t].store(std::clamp(v,-1.0f,1.0f),std::memory_order_release); }
float Engine::trackPan(int t) const noexcept { return t>=0&&t<kTracks?trackPans_[t].load(std::memory_order_acquire):0.0f; }
void Engine::setTrackMute(int t,bool v) noexcept { if(t>=0&&t<kTracks) trackMutes_[t].store(v?1:0,std::memory_order_release); }
bool Engine::trackMute(int t) const noexcept { return t>=0&&t<kTracks&&trackMutes_[t].load(std::memory_order_acquire)!=0; }
void Engine::setTrackSolo(int t,bool v) noexcept { if(t>=0&&t<kTracks) trackSolos_[t].store(v?1:0,std::memory_order_release); }
bool Engine::trackSolo(int t) const noexcept { return t>=0&&t<kTracks&&trackSolos_[t].load(std::memory_order_acquire)!=0; }
"""
rep("src/engine.cpp",needle,api)
rep("src/engine.cpp","void Engine::startVoice(int pad, float velocity) noexcept {",
    "void Engine::startVoice(int pad, float velocity,int track) noexcept {")
rep("src/engine.cpp",
    "*voice = Voice{pad, 0, 0.0f, 1.0f, velocity, hasSample ? start : 0, hasSample};",
    """const float gain=track>=0&&track<kTracks?trackVolumes_[track].load(std::memory_order_relaxed):1.0f;
    const float pan=track>=0&&track<kTracks?trackPans_[track].load(std::memory_order_relaxed):0.0f;
    *voice = Voice{pad, 0, 0.0f, 1.0f, velocity*gain, pan, hasSample ? start : 0, hasSample};""")
rep("src/engine.cpp",
"""            for (int pad = 0; pad < kPads; ++pad)
                if (step(activePattern, pad, stepIndex_)) startVoice(pad, 1.0f);""",
"""            bool anySolo=false;
            for(int t=0;t<kTracks;++t) anySolo=anySolo||trackSolos_[t].load(std::memory_order_relaxed)!=0;
            for(int t=0;t<kTracks;++t) {
                const bool muted=trackMutes_[t].load(std::memory_order_relaxed)!=0;
                const bool solo=trackSolos_[t].load(std::memory_order_relaxed)!=0;
                if(!muted&&(!anySolo||solo)&&trackStep(activePattern,t,stepIndex_))
                    startVoice(trackPads_[t].load(std::memory_order_relaxed),1.0f,t);
            }""")
rep("src/engine.cpp",
"""        float mixed = 0.0f;
        for (auto& voice : voices_) mixed += synth(voice);""",
"""        float mixedLeft=0.0f,mixedRight=0.0f;
        for(auto& voice:voices_) {
            const float sample=synth(voice);
            const float left=std::sqrt(std::max(0.0f,1.0f-voice.pan))*0.70710678f;
            const float right=std::sqrt(std::max(0.0f,1.0f+voice.pan))*0.70710678f;
            mixedLeft+=sample*left; mixedRight+=sample*right;
        }
        const float mixed=(mixedLeft+mixedRight)*0.5f;""")
rep("src/engine.cpp",
"""        output[i * 2] = outputSample;
        output[i * 2 + 1] = outputSample;""",
"""        const float balance=std::clamp((mixedRight-mixedLeft)*0.5f,-0.5f,0.5f);
        output[i*2]=std::clamp(outputSample-balance*std::abs(outputSample),-1.0f,1.0f);
        output[i*2+1]=std::clamp(outputSample+balance*std::abs(outputSample),-1.0f,1.0f);""")

# Project v4 stores track grid and mixer/routing state. v1-v3 are migrated to 8 tracks.
rep("src/engine.cpp",'file << "INFINITY_PROJECT 3\\n"',
    'file << "INFINITY_PROJECT 4\\n"')
rep("src/engine.cpp",
"""    for (int pad = 0; pad < kPads; ++pad) {
        const uint64_t count = samples_[pad].size();""",
"""    for(int p=0;p<kPatterns;++p) for(int t=0;t<kTracks;++t) {
        for(int st=0;st<kSteps;++st) file.put(trackStep(p,t,st)?'1':'0');
        file.put('\\n');
    }
    for(int t=0;t<kTracks;++t)
        file << trackPad(t) << ' ' << trackVolume(t) << ' ' << trackPan(t) << ' '
             << (trackMute(t)?1:0) << ' ' << (trackSolo(t)?1:0) << '\\n';
    for (int pad = 0; pad < kPads; ++pad) {
        const uint64_t count = samples_[pad].size();""")
rep("src/engine.cpp","(version == 2 || version == 3)","(version == 2 || version == 3 || version == 4)")
rep("src/engine.cpp",
"""    std::array<std::string, kPads> nextPaths{};
    std::array<std::vector<float>, kPads> nextSamples{};
    if (version == 3) {""",
"""    std::array<std::array<std::array<uint8_t,kSteps>,kTracks>,kPatterns> nextTrackGrid{};
    std::array<int,kTracks> nextTrackPads{};
    std::array<float,kTracks> nextTrackVolumes{},nextTrackPans{};
    std::array<uint8_t,kTracks> nextTrackMutes{},nextTrackSolos{};
    for(int t=0;t<kTracks;++t){nextTrackPads[t]=t;nextTrackVolumes[t]=1.0f;nextTrackPans[t]=0.0f;}
    if(version==4) {
        for(int p=0;p<kPatterns;++p) for(int t=0;t<kTracks;++t) {
            std::string bits;
            if(!(file>>bits)||bits.size()!=size_t(kSteps)) throw std::runtime_error("Corrupt track pattern data");
            for(int st=0;st<kSteps;++st) {
                if(bits[st]!='0'&&bits[st]!='1') throw std::runtime_error("Corrupt track step");
                nextTrackGrid[p][t][st]=bits[st]=='1'?1:0;
            }
        }
        for(int t=0;t<kTracks;++t) {
            int pad=0,mute=0,solo=0; float vol=1.0f,pan=0.0f;
            if(!(file>>pad>>vol>>pan>>mute>>solo)||pad<0||pad>=kPads||
               !std::isfinite(vol)||!std::isfinite(pan)||(mute!=0&&mute!=1)||(solo!=0&&solo!=1))
                throw std::runtime_error("Corrupt track mixer data");
            nextTrackPads[t]=pad; nextTrackVolumes[t]=std::clamp(vol,0.0f,1.0f);
            nextTrackPans[t]=std::clamp(pan,-1.0f,1.0f);
            nextTrackMutes[t]=uint8_t(mute); nextTrackSolos[t]=uint8_t(solo);
        }
    } else {
        for(int p=0;p<kPatterns;++p) for(int t=0;t<kTracks;++t)
            for(int st=0;st<kSteps;++st) nextTrackGrid[p][t][st]=nextGrid[p][t][st];
    }
    std::array<std::string, kPads> nextPaths{};
    std::array<std::vector<float>, kPads> nextSamples{};
    if (version >= 3) {""")
rep("src/engine.cpp",
"""    for (int pad = 0; pad < kPads; ++pad) {
        samples_[pad] = std::move(nextSamples[pad]);""",
"""    for(int p=0;p<kPatterns;++p) for(int t=0;t<kTracks;++t)
        for(int st=0;st<kSteps;++st) trackGrid_[p][t][st].store(nextTrackGrid[p][t][st],std::memory_order_release);
    for(int t=0;t<kTracks;++t) {
        trackPads_[t].store(nextTrackPads[t],std::memory_order_release);
        trackVolumes_[t].store(nextTrackVolumes[t],std::memory_order_release);
        trackPans_[t].store(nextTrackPans[t],std::memory_order_release);
        trackMutes_[t].store(nextTrackMutes[t],std::memory_order_release);
        trackSolos_[t].store(nextTrackSolos[t],std::memory_order_release);
    }
    for (int pad = 0; pad < kPads; ++pad) {
        samples_[pad] = std::move(nextSamples[pad]);""")

# Win32 UI: select one of eight tracks, edit its steps, level/pan/mute/solo.
rep("src/main.cpp",
"static HWND root,statusText; static int selectedPad=0,stepPage=0; static HWND tempoSlider{},swingSlider{},volumeSlider{},sliceStartSlider{},sliceEndSlider{},delaySlider{},reverbSlider{},saturationSlider{},compressionSlider{};",
"static HWND root,statusText; static int selectedPad=0,selectedTrack=0,stepPage=0; static HWND tempoSlider{},swingSlider{},volumeSlider{},sliceStartSlider{},sliceEndSlider{},delaySlider{},reverbSlider{},saturationSlider{},compressionSlider{},trackVolumeSlider{},trackPanSlider{};")
rep("src/main.cpp",
"engine.step(engine.pattern(),selectedPad,stepPage*16+s)",
"engine.trackStep(engine.pattern(),selectedTrack,stepPage*16+s)")
rep("src/main.cpp",
' label(h,L"64-STEP SEQUENCER  |  4 BANKS x 16 STEPS",20,325,420,20);for(int p=0;p<4;p++){',
' label(h,L"8 INDEPENDENT TRACKS",20,325,260,20);for(int t=0;t<kTracks;t++){wchar_t n[16];swprintf_s(n,L"TRACK %d",t+1);CreateWindowW(L"BUTTON",n,WS_CHILD|WS_VISIBLE|BS_PUSHBUTTON,20+t*98,347,88,28,h,(HMENU)(INT_PTR)(200+t),nullptr,nullptr);}\\n label(h,L"64-STEP SEQUENCER",20,380,220,20);for(int p=0;p<4;p++){')
rep("src/main.cpp","440+p*68,320,62,26","440+p*68,376,62,26")
rep("src/main.cpp","20+s*42,354,38,36","20+s*42,410,38,36")
rep("src/main.cpp",
' label(h,L"SLICE START",20,390,90,20);sliceStartSlider=makeSlider(h,20,20,410,300,0,1000,0);label(h,L"SLICE END",365,390,80,20);sliceEndSlider=makeSlider(h,21,365,410,300,0,1000,1000);',
' label(h,L"TRACK LEVEL",20,452,90,20);trackVolumeSlider=makeSlider(h,26,110,446,140,0,100,100);label(h,L"TRACK PAN",280,452,80,20);trackPanSlider=makeSlider(h,27,365,446,140,-100,100,0);CreateWindowW(L"BUTTON",L"MUTE",WS_CHILD|WS_VISIBLE|BS_AUTOCHECKBOX,540,448,70,28,h,(HMENU)401,nullptr,nullptr);CreateWindowW(L"BUTTON",L"SOLO",WS_CHILD|WS_VISIBLE|BS_AUTOCHECKBOX,620,448,70,28,h,(HMENU)402,nullptr,nullptr);\\n label(h,L"SLICE START",20,486,90,20);sliceStartSlider=makeSlider(h,20,20,506,300,0,1000,0);label(h,L"SLICE END",365,486,80,20);sliceEndSlider=makeSlider(h,21,365,506,300,0,1000,1000);')
# Move master FX and bottom row down to make room.
for old,new in [("20,450,100,18","20,548,100,18"),("130,450,55,18","130,548,55,18"),("180,444,105","180,542,105"),("300,450,60,18","300,548,60,18"),("360,444,105","360,542,105"),("480,450,85,18","480,548,85,18"),("565,444,85","565,542,85"),("665,450,45,18","665,548,45,18"),("710,444,85","710,542,85"),("20,500,145,34","20,596,145,34"),("180,500,125,34","180,596,125,34"),("320,500,125,34","320,596,125,34"),("460,500,130,34","460,596,130,34"),("20,555,760,24","20,642,760,24"),("840,650,nullptr,nullptr,inst,nullptr","840,710,nullptr,nullptr,inst,nullptr")]:
    rep("src/main.cpp",old,new)
rep("src/main.cpp",
"if(id==8)engine.setVolume(float(v)/100.f);if(id>=22&&id<=25){",
"if(id==8)engine.setVolume(float(v)/100.f);if(id==26)engine.setTrackVolume(selectedTrack,float(v)/100.f);if(id==27)engine.setTrackPan(selectedTrack,float(v)/100.f);if(id>=22&&id<=25){")
rep("src/main.cpp",
"  if(id>=30&&id<34){stepPage=id-30;syncSteps(h);",
"""  if(id>=200&&id<208){selectedTrack=id-200;syncSteps(h);SendMessageW(GetDlgItem(h,401),BM_SETCHECK,engine.trackMute(selectedTrack)?BST_CHECKED:BST_UNCHECKED,0);SendMessageW(GetDlgItem(h,402),BM_SETCHECK,engine.trackSolo(selectedTrack)?BST_CHECKED:BST_UNCHECKED,0);return 0;}
  if(id==401){engine.setTrackMute(selectedTrack,SendMessageW(GetDlgItem(h,401),BM_GETCHECK,0,0)==BST_CHECKED);return 0;}
  if(id==402){engine.setTrackSolo(selectedTrack,SendMessageW(GetDlgItem(h,402),BM_GETCHECK,0,0)==BST_CHECKED);return 0;}
  if(id>=30&&id<34){stepPage=id-30;syncSteps(h);""")
rep("src/main.cpp",
"engine.setStep(engine.pattern(),selectedPad,s,SendMessageW(GetDlgItem(h,id),BM_GETCHECK,0,0)==BST_CHECKED)",
"engine.setTrackStep(engine.pattern(),selectedTrack,s,SendMessageW(GetDlgItem(h,id),BM_GETCHECK,0,0)==BST_CHECKED)")
rep("src/main.cpp",
"if(sliceStartSlider&&sliceEndSlider){",
"if(trackVolumeSlider)SendMessageW(trackVolumeSlider,TBM_SETPOS,TRUE,(int)(engine.trackVolume(selectedTrack)*100));if(trackPanSlider)SendMessageW(trackPanSlider,TBM_SETPOS,TRUE,(int)(engine.trackPan(selectedTrack)*100));if(sliceStartSlider&&sliceEndSlider){")

rep("CMakeLists.txt","project(Infinity_Windows VERSION 0.10.0","project(Infinity_Windows VERSION 0.11.0")
rep("README_RU.md","Версия 0.10.0 добавляет 16-полосный анализатор спектра в реальном времени и мастер-эффекты.",
    "Версия 0.11.0 добавляет 8 независимых секвенсорных дорожек и трековый микшер.")
rep("README_RU.md","- Живой 16-полосный Goertzel-анализатор спектра с плавной индикацией.",
    "- Живой 16-полосный Goertzel-анализатор спектра с плавной индикацией.\n- 8 независимых дорожек по 64 шага в каждом из четырёх паттернов.\n- Назначение любого из 12 пэдов на дорожку, индивидуальные Level/Pan, Mute и Solo.\n- Формат проекта v4 с сохранением треков и автоматической миграцией проектов v1-v3.")
print("Infinity 0.11.0: 8-track engine, mixer and project format patch applied.")
