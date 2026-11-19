from pathlib import Path

root = Path("/tmp/koii-src/EP133_KOII_Windows_0.5.0")
def patch(path, pairs):
    p = root / path
    s = p.read_text(encoding="utf-8")
    for old, new in pairs:
        if old not in s:
            if new in s:
                continue
            raise SystemExit(f"Patch anchor missing in {path}: {old[:90]!r}")
        s = s.replace(old, new, 1)
    p.write_text(s, encoding="utf-8")

patch("src/engine.hpp", [
    ("constexpr int kPads=12, kSteps=16, kPatterns=4;", "constexpr int kPads=12, kSteps=64, kPatterns=4;")
])

patch("src/engine.cpp", [
    ("for(int i=0;i<16;i+=4) grid_[0][0][i].store(1);", "for(int i=0;i<kSteps;i+=16) grid_[0][0][i].store(1);"),
    ("grid_[0][1][4].store(1); grid_[0][1][12].store(1);", "for(int i=4;i<kSteps;i+=16) grid_[0][1][i].store(1);"),
    ("for(int i=0;i<16;i+=2) grid_[0][2][i].store(1);", "for(int i=0;i<kSteps;i+=2) grid_[0][2][i].store(1);"),
    ("grid_[0][3][0].store(1); grid_[0][3][8].store(1);", "for(int i=0;i<kSteps;i+=16) { grid_[0][3][i].store(1); grid_[0][3][i+8].store(1); }"),
    ("stepIndex_=(stepIndex_+1)%16;", "stepIndex_=(stepIndex_+1)%kSteps;")
])

p = root / "src/engine.cpp"
s = p.read_text(encoding="utf-8")
a = s.index("void Engine::saveProject(")
b = s.index("\nvoid Engine::exportWav(", a)
replacement = r'''void Engine::saveProject(const std::string& path) const {
 std::ofstream f(path, std::ios::binary);
 if(!f) throw std::runtime_error("Cannot create project file");
 f << "INFINITY_PROJECT 2\n" << std::setprecision(9)
   << tempo() << ' ' << swing() << ' ' << volume() << ' ' << pattern() << "\n";
 for(int p=0;p<kPatterns;p++) for(int d=0;d<kPads;d++) {
  for(int st=0;st<kSteps;st++) f << (step(p,d,st)?'1':'0');
  f << '\n';
 }
 for(const auto& samplePath:samplePaths_) f << std::quoted(samplePath) << '\n';
 if(!f) throw std::runtime_error("Project write failed");
}
void Engine::loadProject(const std::string& path) {
 std::ifstream f(path, std::ios::binary);
 if(!f) throw std::runtime_error("Cannot open project file");
 std::string magic; int version=0; f >> magic >> version;
 if(!((magic=="INFINITY_PROJECT" && version==2) || (magic=="KOII_PROJECT" && version==1))) throw std::runtime_error("Unsupported project format");
 float bpm=120.f, sw=0.f, vol=.8f; int pat=0;
 if(!(f >> bpm >> sw >> vol >> pat) || !std::isfinite(bpm) || !std::isfinite(sw) || !std::isfinite(vol) || pat<0 || pat>=kPatterns)
  throw std::runtime_error("Corrupt project settings");
 std::array<std::array<std::array<uint8_t,kSteps>,kPads>,kPatterns> next{};
 for(int p=0;p<kPatterns;p++) for(int d=0;d<kPads;d++) {
  std::string bits; f >> bits;
  const size_t expected=version==1?16u:size_t(kSteps);
  if(bits.size()!=expected) throw std::runtime_error("Corrupt project pattern data");
  for(size_t st=0;st<bits.size();st++) {
   if(bits[st]!='0'&&bits[st]!='1') throw std::runtime_error("Corrupt project step");
   next[p][d][st]=bits[st]=='1';
  }
 }
 std::array<std::string,kPads> paths{};
 for(auto& samplePath:paths) { if(!(f >> std::quoted(samplePath))) throw std::runtime_error("Corrupt project sample list"); }
 std::array<std::vector<float>,kPads> loaded{};
 for(int d=0;d<kPads;d++) if(!paths[d].empty()) {
  auto sample=readWav(paths[d]);
  if(sample.sampleRate==44100) loaded[d]=std::move(sample.mono);
  else { size_t n=std::max<size_t>(1,size_t(double(sample.mono.size())*44100.0/sample.sampleRate)); loaded[d].resize(n); for(size_t i=0;i<n;i++){ double x=double(i)*sample.sampleRate/44100.0; size_t a=std::min<size_t>(size_t(x),sample.mono.size()-1), b=std::min(a+1,sample.mono.size()-1); float t=float(x-a); loaded[d][i]=sample.mono[a]+(sample.mono[b]-sample.mono[a])*t; } }
 }
 for(int p=0;p<kPatterns;p++) for(int d=0;d<kPads;d++) for(int st=0;st<kSteps;st++) grid_[p][d][st].store(next[p][d][st],std::memory_order_release);
 for(int d=0;d<kPads;d++) { samples_[d]=std::move(loaded[d]); samplePaths_[d]=std::move(paths[d]); sliceStart_[d].store(0,std::memory_order_release); sliceEnd_[d].store(samples_[d].size(),std::memory_order_release); }
 setTempo(bpm); setSwing(sw); setVolume(vol); setPattern(pat); stepIndex_=0; nextStepFrame_=frame_;
}
'''
s = s[:a] + replacement + s[b:]
p.write_text(s, encoding="utf-8")

patch("src/main.cpp", [
    ("static HWND root,statusText; static int selectedPad=0; static HWND tempoSlider{},swingSlider{},volumeSlider{},sliceStartSlider{},sliceEndSlider{};",
     "static HWND root,statusText; static int selectedPad=0,stepPage=0; static HWND tempoSlider{},swingSlider{},volumeSlider{},sliceStartSlider{},sliceEndSlider{};"),
    ("static void syncSteps(HWND h){for(int s=0;s<16;s++)SendMessageW(GetDlgItem(h,300+s),BM_SETCHECK,engine.step(engine.pattern(),selectedPad,s)?BST_CHECKED:BST_UNCHECKED,0);if(sliceStartSlider&&sliceEndSlider){SendMessageW(sliceStartSlider,TBM_SETPOS,TRUE,(int)(engine.sliceStart(selectedPad)*1000));SendMessageW(sliceEndSlider,TBM_SETPOS,TRUE,(int)(engine.sliceEnd(selectedPad)*1000));}}",
     "static void syncSteps(HWND h){for(int s=0;s<16;s++)SendMessageW(GetDlgItem(h,300+s),BM_SETCHECK,engine.step(engine.pattern(),selectedPad,stepPage*16+s)?BST_CHECKED:BST_UNCHECKED,0);if(sliceStartSlider&&sliceEndSlider){SendMessageW(sliceStartSlider,TBM_SETPOS,TRUE,(int)(engine.sliceStart(selectedPad)*1000));SendMessageW(sliceEndSlider,TBM_SETPOS,TRUE,(int)(engine.sliceEnd(selectedPad)*1000));}}"),
    ("static void build(HWND h){", "static void build(HWND h){"),
    ("label(h,L\"EP-133 KO II  |  WINDOWS STUDIO 0.6.0\",20,58,480,24);",
     "label(h,L\"INFINITY  |  GROOVE STATION 0.7.0\",20,58,480,24);"),
    ("label(h,L\"PATTERN\",20,88,75,20);for(int p=0;p<4;p++){wchar_t n[24];swprintf_s(n,L\"PATTERN %d\",p+1);CreateWindowW(L\"BUTTON\",n,WS_CHILD|WS_VISIBLE|BS_PUSHBUTTON,100+p*112,82,104,30,h,(HMENU)(10+p),nullptr,nullptr);}",
     "label(h,L\"PATTERN\",20,88,75,20);for(int p=0;p<4;p++){wchar_t n[24];swprintf_s(n,L\"PATTERN %c\",L'A'+p);CreateWindowW(L\"BUTTON\",n,WS_CHILD|WS_VISIBLE|BS_PUSHBUTTON,100+p*112,82,104,30,h,(HMENU)(10+p),nullptr,nullptr);}"),
    ("label(h,L\"16-STEP SEQUENCER  |  choose pad and pattern, then toggle steps\",20,325,520,20);",
     "label(h,L\"64-STEP SEQUENCER  |  4 BANKS x 16 STEPS\",20,325,420,20);for(int p=0;p<4;p++){wchar_t n[16];swprintf_s(n,L\"%d-%d\",p*16+1,p*16+16);CreateWindowW(L\"BUTTON\",n,WS_CHILD|WS_VISIBLE|BS_PUSHBUTTON,440+p*68,320,62,26,h,(HMENU)(30+p),nullptr,nullptr);}"),
    ("CreateWindowW(L\"BUTTON\",L\"IMPORT WAV TO PAD\",WS_CHILD|WS_VISIBLE,20,420,145,34,h,(HMENU)4,nullptr,nullptr);",
     "label(h,L\"SLICE START\",20,390,90,20);sliceStartSlider=makeSlider(h,20,20,410,300,0,1000,0);label(h,L\"SLICE END\",365,390,80,20);sliceEndSlider=makeSlider(h,21,365,410,300,0,1000,1000);\n CreateWindowW(L\"BUTTON\",L\"IMPORT WAV TO PAD\",WS_CHILD|WS_VISIBLE,20,455,145,34,h,(HMENU)4,nullptr,nullptr);"),
     "label(h,L\"SLICE START\",20,405,90,20);sliceStartSlider=makeSlider(h,20,115,398,220,0,1000,0);label(h,L\"SLICE END\",365,405,80,20);sliceEndSlider=makeSlider(h,21,450,398,220,0,1000,1000);\n CreateWindowW(L\"BUTTON\",L\"IMPORT WAV TO PAD\",WS_CHILD|WS_VISIBLE,20,455,145,34,h,(HMENU)4,nullptr,nullptr);"),
    ("CreateWindowW(L\"BUTTON\",L\"SAVE PROJECT\",WS_CHILD|WS_VISIBLE,180,420,125,34,h,(HMENU)5,nullptr,nullptr);",
     "CreateWindowW(L\"BUTTON\",L\"SAVE PROJECT\",WS_CHILD|WS_VISIBLE,180,455,125,34,h,(HMENU)5,nullptr,nullptr);"),
    ("CreateWindowW(L\"BUTTON\",L\"LOAD PROJECT\",WS_CHILD|WS_VISIBLE,320,420,125,34,h,(HMENU)6,nullptr,nullptr);",
     "CreateWindowW(L\"BUTTON\",L\"LOAD PROJECT\",WS_CHILD|WS_VISIBLE,320,455,125,34,h,(HMENU)6,nullptr,nullptr);"),
    ("CreateWindowW(L\"BUTTON\",L\"EXPORT 8s WAV\",WS_CHILD|WS_VISIBLE,460,420,130,34,h,(HMENU)3,nullptr,nullptr);",
     "CreateWindowW(L\"BUTTON\",L\"EXPORT 8s WAV\",WS_CHILD|WS_VISIBLE,460,455,130,34,h,(HMENU)3,nullptr,nullptr);"),
    ("statusText=CreateWindowW(L\"STATIC\",L\"Audio engine ready\",WS_CHILD|WS_VISIBLE,20,475,650,24,h,nullptr,GetModuleHandleW(nullptr),nullptr);",
     "statusText=CreateWindowW(L\"STATIC\",L\"Starting audio device...\",WS_CHILD|WS_VISIBLE,20,510,650,24,h,nullptr,GetModuleHandleW(nullptr),nullptr);"),
    ("if(id>=10&&id<14){engine.setPattern(id-10);syncSteps(h);wchar_t msg[64];swprintf_s(msg,L\"Selected PATTERN %d\",id-9);setStatus(msg);return 0;}",
     "if(id>=10&&id<14){engine.setPattern(id-10);syncSteps(h);wchar_t msg[64];swprintf_s(msg,L\"Selected PATTERN %c\",L'A'+id-10);setStatus(msg);return 0;}\n  if(id>=30&&id<34){stepPage=id-30;syncSteps(h);wchar_t msg[64];swprintf_s(msg,L\"Steps %d-%d\",stepPage*16+1,stepPage*16+16);setStatus(msg);return 0;}"),
    ("if(id>=300&&id<316){int s=id-300;engine.setStep(engine.pattern(),selectedPad,s,SendMessageW(GetDlgItem(h,id),BM_GETCHECK,0,0)==BST_CHECKED);return 0;}",
     "if(id>=300&&id<316){int s=stepPage*16+(id-300);engine.setStep(engine.pattern(),selectedPad,s,SendMessageW(GetDlgItem(h,id),BM_GETCHECK,0,0)==BST_CHECKED);return 0;}"),
    ("760,610,nullptr", "760,590,nullptr"),
    ("if(!h)return 1;ShowWindow(h,show);startAudio();MSG msg{};",
     "if(!h)return 1;ShowWindow(h,show);startAudio();if(audioRun.load())setStatus(L\"Audio device ready | 44.1 kHz stereo\");else setStatus(L\"Audio device unavailable | check Windows sound output\");MSG msg{};")
])

patch("tests/engine_tests.cpp", [
    ("e.setStep(0,5,7,true);assert(e.step(0,5,7));e.setStep(0,5,7,false);assert(!e.step(0,5,7));",
     "e.setStep(0,5,7,true);assert(e.step(0,5,7));e.setStep(0,5,7,false);assert(!e.step(0,5,7));\n e.setStep(3,11,63,true); assert(e.step(3,11,63));"),
    ("sampler.setStep(2,4,9,true); sampler.setTempo(133);",
     "sampler.setStep(2,4,9,true); sampler.setStep(2,4,63,true); sampler.setTempo(133);"),
    ("assert(restored.step(2,4,9)); assert(restored.pattern()==2);",
     "assert(restored.step(2,4,9)); assert(restored.step(2,4,63)); assert(restored.pattern()==2);")
])

patch("CMakeLists.txt", [
    ("project(EP133_KOII_Windows VERSION 0.6.0 LANGUAGES CXX)", "project(Infinity_Windows VERSION 0.7.0 LANGUAGES CXX)"),
    ("add_executable(EP133_KOII WIN32", "add_executable(Infinity WIN32"),
    ("target_link_libraries(EP133_KOII PRIVATE", "target_link_libraries(Infinity PRIVATE"),
    ("target_compile_definitions(EP133_KOII PRIVATE", "target_compile_definitions(Infinity PRIVATE")
])


patch("src/main.cpp", [
    ('L"INFINITY  |  GROOVE STATION 0.7.0"', 'L"БЕСКОНЕЧНОСТЬ ∞"'),
    ('L"KOIIStudioWindow"', 'L"InfinityWindow"'),
    ('L"EP-133 KO II Studio 0.6.0"', 'L"Бесконечность ∞"'),
    ('L"KOII project\\0*.koii\\0All files\\0*.*\\0"', 'L"Проект Бесконечность\\0*.infinity\\0All files\\0*.*\\0"'),
    ('L"koii"', 'L"infinity"')
])


patch("src/wav.cpp", [
    ("#include <fstream>", "#include <fstream>\\n#include <filesystem>"),
    ("std::ifstream f(path,std::ios::binary);", "std::ifstream f(std::filesystem::u8path(path),std::ios::binary);")
])
patch("src/engine.cpp", [
    ("#include <iomanip>", "#include <iomanip>\\n#include <filesystem>"),
    ("std::ofstream f(path, std::ios::binary);", "std::ofstream f(std::filesystem::u8path(path), std::ios::binary);"),
    ("std::ifstream f(path, std::ios::binary);", "std::ifstream f(std::filesystem::u8path(path), std::ios::binary);")
])

(root / "README_RU.md").write_text("""# Бесконечность ∞

**Бесконечность ∞** — Windows-грувбокс и сэмплер с 12 пэдами, четырьмя сценами и 64-шаговым секвенсором.

## Текущий этап 0.7.0

- 12 пэдов с ручным запуском и загрузкой WAV.
- 4 сцены A–D.
- 64 шага на сцену и дорожку пэда, переключение страницами по 16 шагов.
- Темп, Swing и Master Volume.
- Срез семпла Start/End.
- Сохранение и загрузка проектов .infinity.
- Импорт старого формата проекта только для совместимости.
- Экспорт текущего микса в WAV.

## Запуск

Распакуйте архив и запустите Бесконечность.exe. Для звука выберите доступное устройство вывода Windows.

## Ограничения этого этапа

Это ранняя техническая сборка. Многодорожечный микшер, эффекты, MIDI, FLAC, запись входа, автоматизация и полноценные сцены с бесшовным переходом ещё не реализованы. Сборка и автоматические тесты не заменяют проверку на реальном ПК с аудиоустройством.
""", encoding="utf-8")

print("Infinity 0.7.0 source patch applied.")
