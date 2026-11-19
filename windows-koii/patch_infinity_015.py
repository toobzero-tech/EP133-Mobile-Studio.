from pathlib import Path

root = Path("/tmp/koii-src/EP133_KOII_Windows_0.5.0")

engine = root / "src/engine.cpp"
s = engine.read_text()
old = """    file << "INFINITY_PROJECT 4\\n" << std::setprecision(9)
         << tempo() << ' ' << swing() << ' ' << volume() << ' ' << pattern() << '\\n';"""
new = """    // v5 persists the complete master-bus state as well as the sequencer.
    file << "INFINITY_PROJECT 5\\n" << std::setprecision(9)
         << tempo() << ' ' << swing() << ' ' << volume() << ' ' << pattern() << ' '
         << delayAmount() << ' ' << reverbAmount() << ' ' << saturationAmount() << ' '
         << compressionAmount() << '\\n';"""
assert old in s
s = s.replace(old, new, 1)
s = s.replace("(version == 2 || version == 3 || version == 4)",
              "(version == 2 || version == 3 || version == 4 || version == 5)", 1)
old = """    if (!(file >> bpm >> swingValue >> volumeValue >> selected) ||
        !std::isfinite(bpm) || !std::isfinite(swingValue) || !std::isfinite(volumeValue) ||
        selected < 0 || selected >= kPatterns)
        throw std::runtime_error("Corrupt project settings");"""
new = """    if (!(file >> bpm >> swingValue >> volumeValue >> selected) ||
        !std::isfinite(bpm) || !std::isfinite(swingValue) || !std::isfinite(volumeValue) ||
        selected < 0 || selected >= kPatterns)
        throw std::runtime_error("Corrupt project settings");
    float delayValue = 0.0f, reverbValue = 0.0f, saturationValue = 0.0f, compressionValue = 0.0f;
    if (version >= 5 && (!(file >> delayValue >> reverbValue >> saturationValue >> compressionValue) ||
        !std::isfinite(delayValue) || !std::isfinite(reverbValue) ||
        !std::isfinite(saturationValue) || !std::isfinite(compressionValue)))
        throw std::runtime_error("Corrupt master effects settings");"""
assert old in s
s = s.replace(old, new, 1)
assert "if(version==4) {" in s
s = s.replace("if(version==4) {", "if(version>=4) {", 1)
old = """    setVolume(volumeValue);
    setPattern(selected);"""
new = """    setVolume(volumeValue);
    setEffects(delayValue, reverbValue, saturationValue, compressionValue);
    setPattern(selected);"""
assert old in s
engine.write_text(s.replace(old, new, 1))

main = root / "src/main.cpp"
s = main.read_text()
old = """SendMessageW(volumeSlider,TBM_SETPOS,TRUE,(int)(engine.volume()*100));syncSteps(h);startAudio();setStatus(save?L"Project saved":L"Project loaded");"""
new = """SendMessageW(volumeSlider,TBM_SETPOS,TRUE,(int)(engine.volume()*100));SendMessageW(delaySlider,TBM_SETPOS,TRUE,(int)(engine.delayAmount()*100));SendMessageW(reverbSlider,TBM_SETPOS,TRUE,(int)(engine.reverbAmount()*100));SendMessageW(saturationSlider,TBM_SETPOS,TRUE,(int)(engine.saturationAmount()*100));SendMessageW(compressionSlider,TBM_SETPOS,TRUE,(int)(engine.compressionAmount()*100));syncSteps(h);startAudio();setStatus(save?L"Project saved":L"Project loaded");"""
assert old in s
main.write_text(s.replace(old, new, 1))

test = root / "tests/engine_tests.cpp"
s = test.read_text()
old = """    sampler.setVolume(0.63f);
    sampler.setPattern(2);"""
new = """    sampler.setVolume(0.63f);
    sampler.setEffects(0.23f, 0.47f, 0.61f, 0.82f);
    sampler.setPattern(2);"""
assert old in s
s = s.replace(old, new, 1)
old = """    assert(restored.volume() > 0.629f && restored.volume() < 0.631f);
    assert(restored.sampleFrames(0) == 200);"""
new = """    assert(restored.volume() > 0.629f && restored.volume() < 0.631f);
    assert(restored.delayAmount() > 0.229f && restored.delayAmount() < 0.231f);
    assert(restored.reverbAmount() > 0.469f && restored.reverbAmount() < 0.471f);
    assert(restored.saturationAmount() > 0.609f && restored.saturationAmount() < 0.611f);
    assert(restored.compressionAmount() > 0.819f && restored.compressionAmount() < 0.821f);
    assert(restored.sampleFrames(0) == 200);"""
assert old in s
s = s.replace(old, new, 1)
old = """    assert(legacyLoaded.step(1, 2, 63));
    assert(legacyLoaded.sampleFrames(0) == 0);"""
new = """    assert(legacyLoaded.step(1, 2, 63));
    assert(legacyLoaded.sampleFrames(0) == 0);
    assert(legacyLoaded.delayAmount() == 0.0f && legacyLoaded.reverbAmount() == 0.0f);"""
assert old in s
test.write_text(s.replace(old, new, 1))

readme = root / "README_RU.md"
s = readme.read_text()
s = s.replace("Версия 0.13.0 экспортирует полный 64-шаговый паттерн с хвостом мастер-эффектов.",
              "Версия 0.15.0 сохраняет настройки мастер-эффектов вместе с проектом и восстанавливает их при загрузке.")
s = s.replace("- Формат проекта v4 с сохранением треков и автоматической миграцией проектов v1-v3.",
              "- Формат проекта v5: сохраняются дорожки, сэмплы и все четыре параметра мастер-эффектов; проекты v1-v4 автоматически мигрируют при загрузке.")
s = s.replace("## Что ещё не реализовано",
              "- При загрузке проекта интерфейс автоматически восстанавливает положения регуляторов Delay, Reverb, Saturation и Compressor.\n\n## Что ещё не реализовано")
readme.write_text(s)

cmake = root / "CMakeLists.txt"
s = cmake.read_text()
cmake.write_text(s.replace("project(Infinity_Windows VERSION 0.13.0 LANGUAGES CXX)",
                           "project(Infinity_Windows VERSION 0.15.0 LANGUAGES CXX)"))
print("Infinity 0.15.0 master FX persistence patch applied")
