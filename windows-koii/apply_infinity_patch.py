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

required = {
    "CMakeLists.txt": ["project(Infinity_Windows VERSION 0.8.0", "add_executable(Infinity WIN32"],
    "src/engine.hpp": ["kSteps=64", "restartRequested_"],
    "src/engine.cpp": ["INFINITY_PROJECT 3", "floatToBits", "bitsToFloat", "void Engine::setPlaying(bool value)"],
    "src/sample.cpp": ["RIFF boundary", "blockAlign < minimumAlign", "rawValue"],
    "src/main.cpp": ["waveOutWrite", "WHDR_PREPARED", "audioRun.store(false", "(HMENU)(INT_PTR)(10+p)"],
    "tests/engine_tests.cpp": ["roundtrip.infinity", "lowrate.wav", "truncated.infinity"],
    "README_RU.md": ["Встраивание аудиосемплов", "0.8.0"],
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
