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

rep("src/main.cpp",
"static HWND root,statusText; static int selectedPad=0,stepPage=0; static HWND tempoSlider{},swingSlider{},volumeSlider{},sliceStartSlider{},sliceEndSlider{},delaySlider{},reverbSlider{},saturationSlider{},compressionSlider{};",
"static HWND root,statusText; static int selectedPad=0,selectedTrack=0,stepPage=0; static HWND tempoSlider{},swingSlider{},volumeSlider{},sliceStartSlider{},sliceEndSlider{},delaySlider{},reverbSlider{},saturationSlider{},compressionSlider{},trackVolumeSlider{},trackPanSlider{};")
rep("src/main.cpp",
"engine.step(engine.pattern(),selectedPad,stepPage*16+s)",
"engine.trackStep(engine.pattern(),selectedTrack,stepPage*16+s)")
rep("src/main.cpp",
' label(h,L"64-STEP SEQUENCER  |  4 BANKS x 16 STEPS",20,325,420,20);for(int p=0;p<4;p++){',
' label(h,L"8 INDEPENDENT TRACKS",20,325,260,20);for(int t=0;t<kTracks;t++){wchar_t n[16];swprintf_s(n,L"TRACK %d",t+1);CreateWindowW(L"BUTTON",n,WS_CHILD|WS_VISIBLE|BS_PUSHBUTTON,20+t*98,347,88,28,h,(HMENU)(INT_PTR)(200+t),nullptr,nullptr);}\n label(h,L"64-STEP SEQUENCER",20,380,220,20);for(int p=0;p<4;p++){')
rep("src/main.cpp","440+p*68,320,62,26","440+p*68,376,62,26")
rep("src/main.cpp","20+s*42,354,38,36","20+s*42,410,38,36")
rep("src/main.cpp",
' label(h,L"SLICE START",20,390,90,20);sliceStartSlider=makeSlider(h,20,20,410,300,0,1000,0);label(h,L"SLICE END",365,390,80,20);sliceEndSlider=makeSlider(h,21,365,410,300,0,1000,1000);',
' label(h,L"TRACK LEVEL",20,452,90,20);trackVolumeSlider=makeSlider(h,26,110,446,140,0,100,100);label(h,L"TRACK PAN",280,452,80,20);trackPanSlider=makeSlider(h,27,365,446,140,-100,100,0);CreateWindowW(L"BUTTON",L"MUTE",WS_CHILD|WS_VISIBLE|BS_AUTOCHECKBOX,540,448,70,28,h,(HMENU)401,nullptr,nullptr);CreateWindowW(L"BUTTON",L"SOLO",WS_CHILD|WS_VISIBLE|BS_AUTOCHECKBOX,620,448,70,28,h,(HMENU)402,nullptr,nullptr);\n label(h,L"SLICE START",20,486,90,20);sliceStartSlider=makeSlider(h,20,20,506,300,0,1000,0);label(h,L"SLICE END",365,486,80,20);sliceEndSlider=makeSlider(h,21,365,506,300,0,1000,1000);')
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


# Final UI routing selector and additional v4 regression checks.
rep("src/main.cpp",
"static HWND root,statusText; static int selectedPad=0,selectedTrack=0,stepPage=0; static HWND tempoSlider{},swingSlider{},volumeSlider{},sliceStartSlider{},sliceEndSlider{},delaySlider{},reverbSlider{},saturationSlider{},compressionSlider{},trackVolumeSlider{},trackPanSlider{};",
"static HWND root,statusText; static int selectedPad=0,selectedTrack=0,stepPage=0; static HWND tempoSlider{},swingSlider{},volumeSlider{},sliceStartSlider{},sliceEndSlider{},delaySlider{},reverbSlider{},saturationSlider{},compressionSlider{},trackVolumeSlider{},trackPanSlider{},trackPadCombo{};")
rep("src/main.cpp",
"if(trackPanSlider)SendMessageW(trackPanSlider,TBM_SETPOS,TRUE,(int)(engine.trackPan(selectedTrack)*100));if(sliceStartSlider&&sliceEndSlider){",
"if(trackPanSlider)SendMessageW(trackPanSlider,TBM_SETPOS,TRUE,(int)(engine.trackPan(selectedTrack)*100));if(trackPadCombo)SendMessageW(trackPadCombo,CB_SETCURSEL,engine.trackPad(selectedTrack),0);if(sliceStartSlider&&sliceEndSlider){")
rep("src/main.cpp",
'CreateWindowW(L"BUTTON",L"SOLO",WS_CHILD|WS_VISIBLE|BS_AUTOCHECKBOX,620,448,70,28,h,(HMENU)402,nullptr,nullptr);',
'CreateWindowW(L"BUTTON",L"SOLO",WS_CHILD|WS_VISIBLE|BS_AUTOCHECKBOX,620,448,70,28,h,(HMENU)402,nullptr,nullptr);label(h,L"PAD",700,432,50,16);trackPadCombo=CreateWindowW(L"COMBOBOX",L"",WS_CHILD|WS_VISIBLE|CBS_DROPDOWNLIST,700,448,105,180,h,(HMENU)403,nullptr,nullptr);for(int p=0;p<kPads;p++){wchar_t name[16];swprintf_s(name,L"PAD %02d",p+1);SendMessageW(trackPadCombo,CB_ADDSTRING,0,(LPARAM)name);}')
rep("src/main.cpp",
"  if(id==402){engine.setTrackSolo(selectedTrack,SendMessageW(GetDlgItem(h,402),BM_GETCHECK,0,0)==BST_CHECKED);return 0;}",
"  if(id==402){engine.setTrackSolo(selectedTrack,SendMessageW(GetDlgItem(h,402),BM_GETCHECK,0,0)==BST_CHECKED);return 0;}\n  if(id==403&&HIWORD(wp)==CBN_SELCHANGE){const int pad=(int)SendMessageW(trackPadCombo,CB_GETCURSEL,0,0);if(pad>=0)engine.setTrackPad(selectedTrack,pad);return 0;}")

rep("tests/engine_tests.cpp",
"    sampler.setStep(2, 4, 9, true);",
"    sampler.setTrackStep(2,5,9,true); sampler.setTrackStep(2,5,63,true);\n    sampler.setTrackPad(5,10); sampler.setTrackVolume(5,0.42f); sampler.setTrackPan(5,-0.35f);\n    sampler.setTrackMute(5,true); sampler.setTrackSolo(5,true);\n    sampler.setStep(2, 4, 9, true);")
rep("tests/engine_tests.cpp",
"    assert(restored.step(2, 4, 9));",
"    assert(restored.step(2, 4, 9));\n    assert(restored.trackStep(2,5,9)&&restored.trackStep(2,5,63));\n    assert(restored.trackPad(5)==10);\n    assert(restored.trackVolume(5)>0.419f&&restored.trackVolume(5)<0.421f);\n    assert(restored.trackPan(5)>-0.351f&&restored.trackPan(5)<-0.349f);\n    assert(restored.trackMute(5)&&restored.trackSolo(5));")

p = root / "README_RU.md"
r = p.read_text(encoding="utf-8")
r = r.replace("64 шага на паттерн и пэд", "64 шага на каждую из 8 дорожек в каждом паттерне")
r = r.replace("Чтение старых проектов форматов v1/v2.", "Чтение старых проектов форматов v1/v2/v3 с переносом шагов на первые 8 дорожек.")
r = r.replace("Пока отсутствуют полноценные 8 независимых дорожек, микшер и FX-цепочки, MIDI,", "Пока отсутствуют индивидуальные FX-цепочки на дорожках, MIDI,")
p.write_text(r, encoding="utf-8")


# Infinity 0.12.0: preserve true stereo through the master bus.
# Track pan is now audible as a real left/right balance; delay and room buffers
# are stereo as well, so a hard-panned source cannot leak into the opposite side.
rep("src/engine.cpp",
    "        const float mixed=(mixedLeft+mixedRight)*0.5f;\n",
    "")
rep("src/engine.cpp",
"""        float processed = std::tanh(mixed * drive) / std::max(1.0f, std::tanh(drive));
        const float magnitude = std::abs(processed);
        const float threshold = 0.92f - compression * 0.62f;
        if (magnitude > threshold && compression > 0.001f) {
            const float over = magnitude - threshold;
            processed = std::copysign(threshold + over / (1.0f + compression * 8.0f), processed);
        }
        // Fixed 500 ms echo and short feedback comb. No allocations in render().
        const float delayed = delayBuffer_[delayCursor_];
        delayBuffer_[delayCursor_] = std::clamp(processed + delayed * delayFeedback, -1.5f, 1.5f);
        delayCursor_ = (delayCursor_ + 1) % delayBuffer_.size();
        const float echoMix = processed * (1.0f - delayWet * 0.48f) + delayed * delayWet * 0.48f;
        const float room = reverbBuffer_[reverbCursor_];
        reverbBuffer_[reverbCursor_] = std::clamp(echoMix + room * 0.72f, -1.5f, 1.5f);
        reverbCursor_ = (reverbCursor_ + 1) % reverbBuffer_.size();
        const float wet = echoMix * (1.0f - reverbWet * 0.32f) + room * reverbWet * 0.32f;
        const float outputSample = std::tanh(wet * 1.25f) * masterVolume * 0.72f;
        const float balance=std::clamp((mixedRight-mixedLeft)*0.5f,-0.5f,0.5f);
        output[i*2]=std::clamp(outputSample-balance*std::abs(outputSample),-1.0f,1.0f);
        output[i*2+1]=std::clamp(outputSample+balance*std::abs(outputSample),-1.0f,1.0f);
""",
"""        const float normalization = std::max(1.0f, std::tanh(drive));
        float processedLeft = std::tanh(mixedLeft * drive) / normalization;
        float processedRight = std::tanh(mixedRight * drive) / normalization;
        const float threshold = 0.92f - compression * 0.62f;
        auto compress = [compression, threshold](float sample) noexcept {
            const float magnitude = std::abs(sample);
            if (magnitude <= threshold || compression <= 0.001f) return sample;
            const float over = magnitude - threshold;
            return std::copysign(threshold + over / (1.0f + compression * 8.0f), sample);
        };
        processedLeft = compress(processedLeft);
        processedRight = compress(processedRight);

        // Interleaved stereo buffers: 22,050 frames = 500 ms at 44.1 kHz.
        const size_t delayIndex = delayCursor_ * 2;
        const float delayedLeft = delayBuffer_[delayIndex];
        const float delayedRight = delayBuffer_[delayIndex + 1];
        delayBuffer_[delayIndex] = std::clamp(processedLeft + delayedLeft * delayFeedback, -1.5f, 1.5f);
        delayBuffer_[delayIndex + 1] = std::clamp(processedRight + delayedRight * delayFeedback, -1.5f, 1.5f);
        delayCursor_ = (delayCursor_ + 1) % (delayBuffer_.size() / 2);
        const float echoLeft = processedLeft * (1.0f - delayWet * 0.48f) + delayedLeft * delayWet * 0.48f;
        const float echoRight = processedRight * (1.0f - delayWet * 0.48f) + delayedRight * delayWet * 0.48f;

        // Independent short stereo room buffers; no allocation or locks in render().
        const size_t reverbIndex = reverbCursor_ * 2;
        const float roomLeft = reverbBuffer_[reverbIndex];
        const float roomRight = reverbBuffer_[reverbIndex + 1];
        reverbBuffer_[reverbIndex] = std::clamp(echoLeft + roomLeft * 0.72f, -1.5f, 1.5f);
        reverbBuffer_[reverbIndex + 1] = std::clamp(echoRight + roomRight * 0.72f, -1.5f, 1.5f);
        reverbCursor_ = (reverbCursor_ + 1) % (reverbBuffer_.size() / 2);
        const float wetLeft = echoLeft * (1.0f - reverbWet * 0.32f) + roomLeft * reverbWet * 0.32f;
        const float wetRight = echoRight * (1.0f - reverbWet * 0.32f) + roomRight * reverbWet * 0.32f;
        output[i * 2] = std::clamp(std::tanh(wetLeft * 1.25f) * masterVolume * 0.72f, -1.0f, 1.0f);
        output[i * 2 + 1] = std::clamp(std::tanh(wetRight * 1.25f) * masterVolume * 0.72f, -1.0f, 1.0f);
""")
rep("tests/engine_tests.cpp",
    "    engine.render(nullptr, 32);\n",
"""    engine.render(nullptr, 32);

    // A hard-left track must remain silent in the right channel through the
    // complete master bus, rather than being narrowed back to mono.
    Engine stereo;
    stereo.setTrackPad(0, 0);
    stereo.setTrackPan(0, -1.0f);
    stereo.setTrackStep(0, 0, 0, true);
    stereo.setPlaying(true);
    std::vector<float> stereoBuffer(1024);
    stereo.render(stereoBuffer.data(), 512);
    float leftPeak = 0.0f, rightPeak = 0.0f;
    for (size_t i = 0; i < stereoBuffer.size(); i += 2) {
        leftPeak = std::max(leftPeak, std::abs(stereoBuffer[i]));
        rightPeak = std::max(rightPeak, std::abs(stereoBuffer[i + 1]));
    }
    assert(leftPeak > 0.01f);
    assert(rightPeak < 0.000001f);
""")
rep("CMakeLists.txt",
    "project(Infinity_Windows VERSION 0.11.0",
    "project(Infinity_Windows VERSION 0.12.0")
rep("README_RU.md",
    "Версия 0.11.0 добавляет 8 независимых секвенсорных дорожек и трековый микшер.",
    "Версия 0.12.0 сохраняет полноценную стереопанораму через мастер-обработку.")
rep("README_RU.md",
    "- DSP на фиксированных буферах без выделения памяти в аудиопотоке.",
    "- DSP на фиксированных буферах без выделения памяти в аудиопотоке.\n- Настоящий стереотракт: панорама дорожек сохраняется через сатурацию, компрессию, Delay и Reverb.\n- Стерео Delay 500 мс и независимые стереоканалы Room без взаимного протекания.")
print("Infinity 0.12.0: stereo master bus and hard-pan regression test applied.")

# Remove the former mono fold-down declaration; both channels are processed independently.
rep("src/engine.cpp",
    "        const float mixed=(mixedLeft+mixedRight)*0.5f;\n",
    "        // Keep the stereo image intact through all master processing.\n")
rep("tests/engine_tests.cpp", "#include <cassert>\n", "#include <algorithm>\n#include <cassert>\n")

rep("tests/engine_tests.cpp",
    "    stereo.setTrackPan(0, -1.0f);\n",
    "    stereo.setTrackPan(0, -1.0f);\n    for (int track = 1; track < kTracks; ++track) stereo.setTrackMute(track, true);\n")

# Infinity 0.13.0: export a complete 64-step pattern at the current tempo,
# then render a one-second effects tail instead of cutting Delay/Reverb abruptly.
rep("src/engine.hpp",
    '  void exportWav(const std::string& path,float seconds=8.f);',
    '  void exportWav(const std::string& path,float seconds=0.0f);')
rep("src/engine.cpp",
"""void Engine::exportWav(const std::string& path, float seconds) {
    if (!std::isfinite(seconds) || seconds <= 0.0f || seconds > 600.0f)
        throw std::runtime_error("Export duration out of range");
    const size_t frames = static_cast<size_t>(double(seconds) * 44100.0);
    if (frames == 0 || frames > (std::numeric_limits<size_t>::max() / 2))
        throw std::runtime_error("Export frame count out of range");

    std::vector<float> audio(frames * 2);
    const bool wasPlaying = playing();
    setPlaying(true);
    render(audio.data(), frames);
    setPlaying(wasPlaying);
    writeWav16(path, audio, 44100, 2);
}""",
"""void Engine::exportWav(const std::string& path, float seconds) {
    if (!std::isfinite(seconds) || seconds < 0.0f || seconds > 600.0f)
        throw std::runtime_error("Export duration out of range");

    // Zero means one complete 64-step pattern. Swing alternates short/long
    // steps, so an even 64-step cycle retains the exact average duration.
    const double patternSeconds = 64.0 * 60.0 / (double(tempo()) * 4.0);
    const double requestedSeconds = seconds == 0.0f ? patternSeconds : double(seconds);
    const size_t musicFrames = static_cast<size_t>(std::ceil(requestedSeconds * 44100.0));
    constexpr size_t tailFrames = 44100; // Let the master delay and room decay.
    if (musicFrames == 0 || musicFrames > (std::numeric_limits<size_t>::max() / 2) - tailFrames)
        throw std::runtime_error("Export frame count out of range");

    std::vector<float> audio((musicFrames + tailFrames) * 2);
    const bool wasPlaying = playing();
    setPlaying(true); // Restart at step 1 for a predictable full-pattern render.
    render(audio.data(), musicFrames);
    setPlaying(false);
    render(audio.data() + musicFrames * 2, tailFrames); // FX tail, no new steps.
    setPlaying(wasPlaying);
    writeWav16(path, audio, 44100, 2);
}""")
rep("src/main.cpp",
    'CreateWindowW(L"BUTTON",L"EXPORT 8s WAV",WS_CHILD|WS_VISIBLE,460,596,130,34,h,(HMENU)3,nullptr,nullptr);',
    'CreateWindowW(L"BUTTON",L"EXPORT PATTERN WAV",WS_CHILD|WS_VISIBLE,460,596,160,34,h,(HMENU)3,nullptr,nullptr);')
rep("src/main.cpp",
    'engine.exportWav(narrow(file.c_str()),8.f);startAudio();setStatus(L"WAV export completed");',
    'engine.exportWav(narrow(file.c_str()));startAudio();setStatus(L"Full pattern + FX tail exported to WAV");')
rep("tests/engine_tests.cpp",
    '    restored.trigger(0);',
    """    restored.trigger(0);
    restored.setTempo(120.0f);
    restored.setSwing(0.20f);
    restored.setPlaying(false);
    restored.exportWav("full_pattern.wav");
    const AudioSample exported = readWav("full_pattern.wav");
    // 64 sixteenth-note steps at 120 BPM = 8 seconds, plus a 1-second FX tail.
    assert(exported.sampleRate == 44100);
    assert(exported.channels == 2);
    assert(exported.mono.size() == 9u * 44100u);
    std::remove("full_pattern.wav");""")
rep("CMakeLists.txt",
    "project(Infinity_Windows VERSION 0.12.0",
    "project(Infinity_Windows VERSION 0.13.0")
rep("README_RU.md",
    "Версия 0.12.0 сохраняет полноценную стереопанораму через мастер-обработку.",
    "Версия 0.13.0 экспортирует полный 64-шаговый паттерн с хвостом мастер-эффектов.")
rep("README_RU.md",
    "- Экспорт текущего микса в WAV 16-bit.",
    "- Экспорт полного 64-шагового паттерна в WAV 16-bit с учётом текущего BPM и дополнительной секундой хвоста Delay/Reverb.")
print("Infinity 0.13.0: full-pattern WAV export and FX-tail regression test applied.")
