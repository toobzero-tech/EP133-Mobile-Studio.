from pathlib import Path

root = Path("/tmp/koii-src/EP133_KOII_Windows_0.5.0")
required = {
    "CMakeLists.txt": ["project(Infinity_Windows VERSION 0.8.0", "add_executable(Infinity WIN32"],
    "src/engine.hpp": ["kSteps=64", "restartRequested_"],
    "src/engine.cpp": ["INFINITY_PROJECT 3", "writeU32LE", "void Engine::setPlaying(bool value)"],
    "src/sample.cpp": ["RIFF boundary", "blockAlign < minimumAlign"],
    "src/main.cpp": ["waveOutWrite", "WHDR_PREPARED", "audioRun.store(false"],
    "tests/engine_tests.cpp": ["roundtrip.infinity", "lowrate.wav", "truncated.infinity"],
    "README_RU.md": ["Встраивание аудиосемплов", "0.8.0"],
}

for relative, markers in required.items():
    path = root / relative
    if not path.is_file():
        raise SystemExit(f"Missing reviewed source file: {relative}")
    content = path.read_text(encoding="utf-8")
    for marker in markers:
        if marker not in content:
            raise SystemExit(f"Review validation failed: {relative} lacks {marker!r}")

print("Infinity 0.8.0 source review passed; no patching or source rewriting is performed.")
