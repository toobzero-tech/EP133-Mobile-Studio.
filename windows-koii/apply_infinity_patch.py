from pathlib import Path

root = Path("/tmp/koii-src/EP133_KOII_Windows_0.5.0")

def replace_once(relative, old, new):
    path = root / relative
    source = path.read_text(encoding="utf-8")
    if old not in source:
        if new in source:
            return
        raise SystemExit(f"Compatibility patch anchor missing in {relative}: {old[:100]!r}")
    path.write_text(source.replace(old, new, 1), encoding="utf-8")

# MinGW 10 has incomplete std::bit_cast support even in its C++20 mode.
replace_once("src/sample.cpp", "#include <bit>\n", "")
replace_once(
    "src/sample.cpp",
    "return float(std::bit_cast<int32_t>(u32(q))) / 2147483648.0f;",
    "int32_t signedValue{};\n        const uint32_t rawValue = u32(q);\n"
    "        std::memcpy(&signedValue, &rawValue, sizeof(signedValue));\n"
    "        return float(signedValue) / 2147483648.0f;"
)

replace_once("src/engine.cpp", "#include <bit>\n", "#include <cstring>\n")
replace_once(
    "src/engine.cpp",
    "uint32_t readU32LE(std::istream& in) {\n"
    "    unsigned char bytes[4]{};\n"
    "    in.read(reinterpret_cast<char*>(bytes), sizeof(bytes));\n"
    "    if (!in) throw std::runtime_error(\"Truncated embedded sample data\");\n"
    "    return uint32_t(bytes[0]) | (uint32_t(bytes[1]) << 8) |\n"
    "           (uint32_t(bytes[2]) << 16) | (uint32_t(bytes[3]) << 24);\n"
    "}\n}",
    "uint32_t readU32LE(std::istream& in) {\n"
    "    unsigned char bytes[4]{};\n"
    "    in.read(reinterpret_cast<char*>(bytes), sizeof(bytes));\n"
    "    if (!in) throw std::runtime_error(\"Truncated embedded sample data\");\n"
    "    return uint32_t(bytes[0]) | (uint32_t(bytes[1]) << 8) |\n"
    "           (uint32_t(bytes[2]) << 16) | (uint32_t(bytes[3]) << 24);\n"
    "}\n"
    "uint32_t floatToBits(float value) noexcept {\n"
    "    uint32_t bits{};\n"
    "    std::memcpy(&bits, &value, sizeof(bits));\n"
    "    return bits;\n"
    "}\n"
    "float bitsToFloat(uint32_t bits) noexcept {\n"
    "    float value{};\n"
    "    std::memcpy(&value, &bits, sizeof(value));\n"
    "    return value;\n"
    "}\n}"
)
replace_once("src/engine.cpp", "std::bit_cast<uint32_t>(safe)", "floatToBits(safe)")
replace_once("src/engine.cpp", "std::bit_cast<float>(readU32LE(file))", "bitsToFloat(readU32LE(file))")

for old, new in [
    ("(HMENU)(10+p)", "(HMENU)(INT_PTR)(10+p)"),
    ("(HMENU)(100+p)", "(HMENU)(INT_PTR)(100+p)"),
    ("(HMENU)(30+p)", "(HMENU)(INT_PTR)(30+p)"),
    ("(HMENU)(300+s)", "(HMENU)(INT_PTR)(300+s)"),
]:
    replace_once("src/main.cpp", old, new)

replace_once("CMakeLists.txt", "project(Infinity_Windows VERSION 0.8.0", "project(Infinity_Windows VERSION 0.9.0")
replace_once("README_RU.md",
    "**БЕСКОНЕЧНОСТЬ ∞** — ранний Windows-грувбокс и сэмплер. Версия 0.8.0 сосредоточена на надёжности аудиодвижка и сохранения проектов.",
    "**БЕСКОНЕЧНОСТЬ ∞** — Windows-грувбокс и сэмплер. Версия 0.9.0 добавляет мастер-эффекты Delay, Reverb, Saturation и Compressor.")

required = {
    "CMakeLists.txt": ["project(Infinity_Windows VERSION 0.9.0", "add_executable(Infinity WIN32"],
    "src/engine.hpp": ["kSteps=64", "restartRequested_"],
    "src/engine.cpp": ["INFINITY_PROJECT 3", "floatToBits", "bitsToFloat", "void Engine::setPlaying(bool value)"],
    "src/sample.cpp": ["RIFF boundary", "blockAlign < minimumAlign", "rawValue"],
    "src/main.cpp": ["waveOutWrite", "WHDR_PREPARED", "audioRun.store(false", "(HMENU)(INT_PTR)(10+p)"],
    "tests/engine_tests.cpp": ["roundtrip.infinity", "lowrate.wav", "truncated.infinity"],
    "README_RU.md": ["Встраивание аудиосемплов", "0.9.0"],
}
for relative, markers in required.items():
    path = root / relative
    if not path.is_file():
        raise SystemExit(f"Missing reviewed source file: {relative}")
    source = path.read_text(encoding="utf-8")
    for marker in markers:
        if marker not in source:
            raise SystemExit(f"Review validation failed: {relative} lacks {marker!r}")
if "std::bit_cast" in (root / "src/engine.cpp").read_text(encoding="utf-8"):
    raise SystemExit("Unsupported std::bit_cast remains in engine.cpp")
if "std::bit_cast" in (root / "src/sample.cpp").read_text(encoding="utf-8"):
    raise SystemExit("Unsupported std::bit_cast remains in sample.cpp")

print("Infinity 0.8.0 source review and MinGW compatibility fixes passed.")


# Infinity 0.9.0: fixed-buffer master effects and visible controls.
replace_once("src/engine.hpp",
    "  void setVolume(float volume) noexcept;\n",
    """  void setVolume(float volume) noexcept;
  // Master-bus effects; normalized parameters are safe to update from the UI thread.
  void setEffects(float delay, float reverb, float saturation, float compression) noexcept;
  float delayAmount() const noexcept { return delayAmount_.load(std::memory_order_acquire); }
  float reverbAmount() const noexcept { return reverbAmount_.load(std::memory_order_acquire); }
  float saturationAmount() const noexcept { return saturationAmount_.load(std::memory_order_acquire); }
  float compressionAmount() const noexcept { return compressionAmount_.load(std::memory_order_acquire); }
""")
replace_once("src/engine.hpp",
    "  std::atomic<float> bpm_{120.f},swing_{0.f},volume_{0.8f};\n",
    """  std::atomic<float> bpm_{120.f},swing_{0.f},volume_{0.8f};
  std::atomic<float> delayAmount_{0.f}, reverbAmount_{0.f}, saturationAmount_{0.f}, compressionAmount_{0.f};
  // Fixed-size delay lines: no allocation or locking in the real-time render path.
  std::array<float, 44100> delayBuffer_{};
  std::array<float, 8192> reverbBuffer_{};
  size_t delayCursor_{0}, reverbCursor_{0};
""")
replace_once("src/engine.cpp",
    """void Engine::setVolume(float value) noexcept {
    if (!std::isfinite(value)) return;
    volume_.store(std::clamp(value, 0.0f, 1.0f), std::memory_order_release);
}
""",
    """void Engine::setVolume(float value) noexcept {
    if (!std::isfinite(value)) return;
    volume_.store(std::clamp(value, 0.0f, 1.0f), std::memory_order_release);
}
void Engine::setEffects(float delay, float reverb, float saturation, float compression) noexcept {
    if (std::isfinite(delay)) delayAmount_.store(std::clamp(delay, 0.0f, 1.0f), std::memory_order_release);
    if (std::isfinite(reverb)) reverbAmount_.store(std::clamp(reverb, 0.0f, 1.0f), std::memory_order_release);
    if (std::isfinite(saturation)) saturationAmount_.store(std::clamp(saturation, 0.0f, 1.0f), std::memory_order_release);
    if (std::isfinite(compression)) compressionAmount_.store(std::clamp(compression, 0.0f, 1.0f), std::memory_order_release);
}
""")
replace_once("src/engine.cpp",
    "    const float masterVolume = volume_.load(std::memory_order_relaxed);\n    const uint64_t baseFrames",
    """    const float masterVolume = volume_.load(std::memory_order_relaxed);
    const float delayWet = delayAmount_.load(std::memory_order_relaxed);
    const float reverbWet = reverbAmount_.load(std::memory_order_relaxed);
    const float drive = 1.0f + saturationAmount_.load(std::memory_order_relaxed) * 11.0f;
    const float compression = compressionAmount_.load(std::memory_order_relaxed);
    const float delayFeedback = 0.18f + delayWet * 0.62f;
    const uint64_t baseFrames""")
replace_once("src/engine.cpp",
    """        float mixed = 0.0f;
        for (auto& voice : voices_) mixed += synth(voice);
        mixed = std::tanh(mixed * 1.25f) * masterVolume * 0.72f;
        output[i * 2] = mixed;
        output[i * 2 + 1] = mixed;
""",
    """        float mixed = 0.0f;
        for (auto& voice : voices_) mixed += synth(voice);
        // Master saturation and soft-knee compression.
        float processed = std::tanh(mixed * drive) / std::max(1.0f, std::tanh(drive));
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
        output[i * 2] = outputSample;
        output[i * 2 + 1] = outputSample;
""")
replace_once("src/main.cpp",
    "static HWND tempoSlider{},swingSlider{},volumeSlider{},sliceStartSlider{},sliceEndSlider{};",
    "static HWND tempoSlider{},swingSlider{},volumeSlider{},sliceStartSlider{},sliceEndSlider{},delaySlider{},reverbSlider{},saturationSlider{},compressionSlider{};")
replace_once("src/main.cpp",
    "if(id==8)engine.setVolume(float(v)/100.f);if(id==20||id==21){",
    "if(id==8)engine.setVolume(float(v)/100.f);if(id>=22&&id<=25){engine.setEffects(SendMessageW(delaySlider,TBM_GETPOS,0,0)/100.f,SendMessageW(reverbSlider,TBM_GETPOS,0,0)/100.f,SendMessageW(saturationSlider,TBM_GETPOS,0,0)/100.f,SendMessageW(compressionSlider,TBM_GETPOS,0,0)/100.f);}if(id==20||id==21){")
replace_once("src/main.cpp",
    """ CreateWindowW(L"BUTTON",L"IMPORT WAV TO PAD",WS_CHILD|WS_VISIBLE,20,455,145,34,h,(HMENU)4,nullptr,nullptr);
 CreateWindowW(L"BUTTON",L"SAVE PROJECT",WS_CHILD|WS_VISIBLE,180,455,125,34,h,(HMENU)5,nullptr,nullptr);
 CreateWindowW(L"BUTTON",L"LOAD PROJECT",WS_CHILD|WS_VISIBLE,320,455,125,34,h,(HMENU)6,nullptr,nullptr);
 CreateWindowW(L"BUTTON",L"EXPORT 8s WAV",WS_CHILD|WS_VISIBLE,460,455,130,34,h,(HMENU)3,nullptr,nullptr);
 statusText=CreateWindowW(L"STATIC",L"Starting audio device...",WS_CHILD|WS_VISIBLE,20,510,650,24,h,nullptr,GetModuleHandleW(nullptr),nullptr);syncSteps(h);""",
    """ label(h,L"MASTER FX",20,450,100,18);
 label(h,L"DELAY",130,450,55,18);delaySlider=makeSlider(h,22,180,444,105,0,100,0);
 label(h,L"REVERB",300,450,60,18);reverbSlider=makeSlider(h,23,360,444,105,0,100,0);
 label(h,L"SATURATION",480,450,85,18);saturationSlider=makeSlider(h,24,565,444,85,0,100,0);
 label(h,L"COMP",665,450,45,18);compressionSlider=makeSlider(h,25,710,444,85,0,100,0);
 CreateWindowW(L"BUTTON",L"IMPORT WAV TO PAD",WS_CHILD|WS_VISIBLE,20,500,145,34,h,(HMENU)4,nullptr,nullptr);
 CreateWindowW(L"BUTTON",L"SAVE PROJECT",WS_CHILD|WS_VISIBLE,180,500,125,34,h,(HMENU)5,nullptr,nullptr);
 CreateWindowW(L"BUTTON",L"LOAD PROJECT",WS_CHILD|WS_VISIBLE,320,500,125,34,h,(HMENU)6,nullptr,nullptr);
 CreateWindowW(L"BUTTON",L"EXPORT 8s WAV",WS_CHILD|WS_VISIBLE,460,500,130,34,h,(HMENU)3,nullptr,nullptr);
 statusText=CreateWindowW(L"STATIC",L"Starting audio device...",WS_CHILD|WS_VISIBLE,20,555,760,24,h,nullptr,GetModuleHandleW(nullptr),nullptr);syncSteps(h);""")
replace_once("src/main.cpp",
    'CreateWindowW(wc.lpszClassName,L"Бесконечность ∞",WS_OVERLAPPEDWINDOW|WS_VISIBLE,CW_USEDEFAULT,CW_USEDEFAULT,760,590,nullptr,nullptr,inst,nullptr);',
    'CreateWindowW(wc.lpszClassName,L"Бесконечность ∞",WS_OVERLAPPEDWINDOW|WS_VISIBLE,CW_USEDEFAULT,CW_USEDEFAULT,840,650,nullptr,nullptr,inst,nullptr);')
replace_once("tests/engine_tests.cpp",
    "    assert(engine.volume() == 1.0f);\n    engine.setTempo",
    """    assert(engine.volume() == 1.0f);
    engine.setEffects(2.0f, -1.0f, 0.5f, 1.5f);
    assert(engine.delayAmount() == 1.0f);
    assert(engine.reverbAmount() == 0.0f);
    assert(engine.saturationAmount() == 0.5f);
    assert(engine.compressionAmount() == 1.0f);
    engine.setEffects(0.55f, 0.7f, 0.4f, 0.6f);
    engine.setTempo""")
replace_once("tests/engine_tests.cpp",
    "    engine.render(buffer.data(), 1024);\n    bool nonzero",
    "    engine.render(buffer.data(), 1024);\n    engine.render(buffer.data(), 1024); // Exercise FX buffers across blocks.\n    bool nonzero")
replace_once("README_RU.md",
    "**БЕСКОНЕЧНОСТЬ ∞** — ранний Windows-грувбокс и сэмплер. Версия 0.8.0 сосредоточена на надёжности аудиодвижка и сохранения проектов.",
    "**БЕСКОНЕЧНОСТЬ ∞** — Windows-грувбокс и сэмплер. Версия 0.9.0 добавляет мастер-эффекты Delay, Reverb, Saturation и Compressor.")
replace_once("README_RU.md",
    "- Экспорт текущего микса в WAV 16-bit.\n",
    "- Экспорт текущего микса в WAV 16-bit.\n- Мастер-эффекты в реальном времени: Delay, Room/Reverb, Saturation и Compressor.\n- DSP на фиксированных буферах без выделения памяти в аудиопотоке.\n")

# Infinity 0.10.0: live 16-band Goertzel spectrum display.
replace_once("src/main.cpp", "#include <cstdio>\\n", "#include <cstdio>\\n#include <cmath>\\n")
replace_once("src/main.cpp",
    "static std::vector<std::unique_ptr<AudioBuf>> buffers;\\n",
    """static std::vector<std::unique_ptr<AudioBuf>> buffers;
static std::atomic<float> spectrumBands[16]{};
static void updateSpectrum(const std::vector<float>& mix) noexcept {
 static constexpr float frequencies[16]={55.f,78.f,110.f,156.f,220.f,311.f,440.f,622.f,880.f,1245.f,1760.f,2490.f,3520.f,4980.f,7040.f,9960.f};
 for(int band=0;band<16;++band){
  const float coefficient=2.0f*std::cos(6.28318530718f*frequencies[band]/44100.0f);
  float s1=0.0f,s2=0.0f;
  for(int i=0;i<FRAMES;++i){const float sample=mix[size_t(i)*2];const float s=sample+coefficient*s1-s2;s2=s1;s1=s;}
  const float power=std::max(0.0f,s1*s1+s2*s2-coefficient*s1*s2);
  const float magnitude=std::sqrt(power)/float(FRAMES);
  const float level=std::clamp(magnitude*5.0f,0.0f,1.0f);
  const float previous=spectrumBands[band].load(std::memory_order_relaxed);
  spectrumBands[band].store(previous*0.58f+level*0.42f,std::memory_order_relaxed);
 }
}
""")
replace_once("src/main.cpp",
    "    engine.render(b->mix.data(),FRAMES);\\n",
    "    engine.render(b->mix.data(),FRAMES);\\n    updateSpectrum(b->mix);\\n")
replace_once("src/main.cpp",
    'statusText=CreateWindowW(L"STATIC",L"Starting audio device...",WS_CHILD|WS_VISIBLE,20,555,760,24,h,nullptr,GetModuleHandleW(nullptr),nullptr);syncSteps(h);',
    'statusText=CreateWindowW(L"STATIC",L"Starting audio device...",WS_CHILD|WS_VISIBLE,20,555,760,24,h,nullptr,GetModuleHandleW(nullptr),nullptr);syncSteps(h);SetTimer(h,1,33,nullptr);')
replace_once("src/main.cpp",
    " case WM_CREATE:build(h);return 0;\\n",
    """ case WM_CREATE:build(h);return 0;
 case WM_TIMER:InvalidateRect(h,nullptr,FALSE);return 0;
 case WM_PAINT:{PAINTSTRUCT ps{};HDC dc=BeginPaint(h,&ps);RECT screen{570,52,810,120};HBRUSH bg=CreateSolidBrush(RGB(22,26,30));FillRect(dc,&screen,bg);DeleteObject(bg);SetBkMode(dc,TRANSPARENT);SetTextColor(dc,RGB(210,216,220));HFONT font=CreateFontW(10,0,0,0,FW_BOLD,FALSE,FALSE,FALSE,DEFAULT_CHARSET,OUT_DEFAULT_PRECIS,CLIP_DEFAULT_PRECIS,CLEARTYPE_QUALITY,DEFAULT_PITCH,L"Segoe UI");HGDIOBJ oldFont=SelectObject(dc,font);TextOutW(dc,580,56,L"LIVE SPECTRUM",13);for(int band=0;band<16;++band){const float level=spectrumBands[band].load(std::memory_order_relaxed);const int height=std::max(2,int(level*42.0f));RECT bar{580+band*14,112-height,590+band*14,112};HBRUSH color=CreateSolidBrush(RGB(255,118,38));FillRect(dc,&bar,color);DeleteObject(color);}SelectObject(dc,oldFont);DeleteObject(font);EndPaint(h,&ps);return 0;}
""")
replace_once("CMakeLists.txt", "project(Infinity_Windows VERSION 0.9.0", "project(Infinity_Windows VERSION 0.10.0")
replace_once("README_RU.md",
    "**БЕСКОНЕЧНОСТЬ ∞** — Windows-грувбокс и сэмплер. Версия 0.9.0 добавляет мастер-эффекты Delay, Reverb, Saturation и Compressor.",
    "**БЕСКОНЕЧНОСТЬ ∞** — Windows-грувбокс и сэмплер. Версия 0.10.0 добавляет 16-полосный анализатор спектра в реальном времени и мастер-эффекты.")
replace_once("README_RU.md",
    "- DSP на фиксированных буферах без выделения памяти в аудиопотоке.\\n",
    "- DSP на фиксированных буферах без выделения памяти в аудиопотоке.\\n- Живой 16-полосный Goertzel-анализатор спектра с плавной индикацией.\\n")
required["CMakeLists.txt"][0] = "project(Infinity_Windows VERSION 0.10.0"
required["README_RU.md"][1] = "0.10.0"
print("Infinity 0.10.0 live spectrum patch applied.")

