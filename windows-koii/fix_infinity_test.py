from pathlib import Path

root = Path("/tmp/koii-src/EP133_KOII_Windows_0.5.0")
test = root / "tests" / "engine_tests.cpp"
source = test.read_text(encoding="utf-8")

old = """    restored.trigger(0);
    restored.setTempo(120.0f);
    restored.setSwing(0.20f);
    restored.setPlaying(false);
    restored.exportWav("full_pattern.wav");
    const AudioSample exported = readWav("full_pattern.wav");
"""
new = """    restored.setTempo(120.0f);
    restored.setSwing(0.20f);
    restored.setPlaying(false);
    restored.exportWav("full_pattern.wav");
    const AudioSample exported = readWav("full_pattern.wav");
"""
if old in source:
    source = source.replace(old, new, 1)
elif new not in source:
    raise SystemExit("Could not find the export/sample-test sequence")

old_check = """    std::vector<float> restoredBuffer(400);
    restored.render(restoredBuffer.data(), 200);
"""
new_check = """    // Export renders the engine for nine seconds. Trigger only after export,
    // otherwise the short embedded sample is correctly consumed during export.
    restored.trigger(0);
    std::vector<float> restoredBuffer(400);
    restored.render(restoredBuffer.data(), 200);
"""
if old_check in source:
    source = source.replace(old_check, new_check, 1)
elif new_check not in source:
    raise SystemExit("Could not find restored sample playback check")

test.write_text(source, encoding="utf-8")
print("Infinity 0.14.0: fixed sample round-trip regression test ordering.")
