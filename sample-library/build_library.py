#!/usr/bin/env python3
"""Build a small, redistributable starter library for Infinity."""
from pathlib import Path
import math, random, struct, wave, zipfile, urllib.request, shutil, subprocess, json, hashlib

ROOT = Path("sample-build")
SRC = ROOT / "meta-open-sound"
OUT = ROOT / "Infinity_Sample_Library"
RATE = 48000
random.seed(133)

def fetch(url, dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, dst)

def write_wav(path, samples):
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(RATE)
        frames = bytearray()
        for x in samples:
            v = max(-1.0, min(1.0, x))
            frames += struct.pack("<h", int(v * 32767))
        w.writeframes(frames)

def synth_kick(path, freq=48, decay=0.55, drive=1.0):
    n = int(RATE * decay); phase = 0; out=[]
    for i in range(n):
        t=i/RATE; f=freq + 95*math.exp(-t*35)
        phase += 2*math.pi*f/RATE
        env=math.exp(-t*7.5)
        out.append(math.tanh(math.sin(phase)*env*drive*2.2))
    write_wav(path,out)

def synth_snare(path, tone=185, decay=0.28):
    n=int(RATE*decay); out=[]
    for i in range(n):
        t=i/RATE; env=math.exp(-t*18)
        noise=random.uniform(-1,1)
        body=math.sin(2*math.pi*(tone-45*t)*t)*math.exp(-t*24)
        out.append(math.tanh((noise*.72+body*.5)*env*2))
    write_wav(path,out)

def synth_hat(path, decay=0.09, open_hat=False):
    n=int(RATE*decay); out=[]
    for i in range(n):
        t=i/RATE; env=math.exp(-t*(13 if open_hat else 48))
        noise=random.uniform(-1,1)
        metallic=sum(math.sin(2*math.pi*f*t) for f in (503, 811, 1297, 1733))/4
        out.append((noise*.65+metallic*.35)*env*.55)
    write_wav(path,out)

def synth_clap(path):
    n=int(RATE*.24); out=[]
    for i in range(n):
        t=i/RATE
        env=sum(math.exp(-max(0,t-d)*65) for d in (0,.012,.026,.044)) + .25*math.exp(-t*12)
        out.append(random.uniform(-1,1)*env*.35)
    write_wav(path,out)

def make_original_kit():
    d=OUT/"Drums"/"Infinity_Original"
    for name,freq,decay,drive in [
        ("Kick_Deep.wav",43,.62,1.4),("Kick_Tight.wav",58,.38,1.1),
        ("Kick_Punch.wav",52,.48,1.9),("Kick_Sub.wav",36,.85,1.0)]:
        synth_kick(d/name,freq,decay,drive)
    for name,tone,decay in [("Snare_Dry.wav",190,.25),("Snare_Body.wav",155,.34),("Snare_Crack.wav",220,.19)]:
        synth_snare(d/name,tone,decay)
    synth_clap(d/"Clap_Layer.wav")
    for i,decay in enumerate((.045,.07,.11,.19),1):
        synth_hat(d/f"Hat_{i:02}.wav",decay,i>=3)
    for i,f in enumerate((110,145,185,230),1):
        synth_snare(d/f"Perc_Tom_{i:02}.wav",f,.42)


def render_generated_content():
    """Create original breakbeat, acid and evolving ambient loops without third-party recordings."""
    import array
    loops = OUT/"Loops"
    atmos = OUT/"Atmospheres"
    acid = OUT/"Synth_Loops"/"Acid"
    for d in (loops, atmos, acid): d.mkdir(parents=True, exist_ok=True)

    def kick_samples(freq=48, decay=.42):
        n=int(RATE*decay); phase=0.0; a=[]
        for i in range(n):
            t=i/RATE; phase += 2*math.pi*(freq+105*math.exp(-t*32))/RATE
            a.append(math.tanh(math.sin(phase)*math.exp(-t*8)*2.1))
        return a
    def snare_samples(decay=.22):
        n=int(RATE*decay); a=[]
        for i in range(n):
            t=i/RATE
            a.append((random.uniform(-1,1)*.7 + math.sin(2*math.pi*190*t)*.3)*math.exp(-t*17))
        return a
    def hat_samples(decay=.055):
        n=int(RATE*decay); a=[]
        for i in range(n):
            t=i/RATE
            a.append(random.uniform(-1,1)*math.exp(-t*45)*.42)
        return a
    kick=kick_samples(); snare=snare_samples(); hat=hat_samples()
    for bpm,feel in ((85,"HalfTime"),(95,"TripHop"),(110,"Dusty"),(118,"Organic"),(124,"Broken"),(132,"Driving"),(140,"Rave"),(150,"Breaks")):
        bars=4; beats=bars*4; total=int(beats*60/bpm*RATE)
        mix=[0.0]*total
        step=60/bpm/4
        def place(src, when, gain=1.0):
            start=int(when*RATE)
            for j,v in enumerate(src):
                if start+j<total: mix[start+j]+=v*gain
        for s in range(beats*4):
            t=s*step
            # Syncopated, human-feeling 16th-note patterns.
            pos=s%16
            if pos in ((0,7,10,14) if bpm==110 else (0,6,10,13)):
                place(kick,t, .82 if pos else 1.0)
            if pos in (4,12): place(snare,t,.78)
            if s%2==0: place(hat,t,.26 if s%4 else .34)
            if bpm==124 and pos in (3,11): place(hat,t,.16)
        peak=max(max(abs(x) for x in mix),1e-9)
        write_wav(loops/f"Infinity_{feel}_Break_{bpm}BPM_4bar.wav",[x/peak*.88 for x in mix])

    # Original synthesized acid loops are clearly labeled as synth-generated additions.
    scale=[0,3,5,7,10,12,15]
    for bpm,root in ((118,45),(124,45),(128,43),(132,43),(138,40),(145,40)):
        bars=4; total=int(bars*4*60/bpm*RATE); mix=[0.0]*total
        step=60/bpm/4
        pattern=[0,-1,3,0,5,-1,3,7,0,-1,5,3,7,-1,5,3]
        for s in range(bars*16):
            note=pattern[s%16]
            if note < 0: continue
            midi=root+scale[note%len(scale)]
            freq=440*2**((midi-69)/12)
            start=int(s*step*RATE); length=int(step*RATE*.88)
            phase=0.0
            for j in range(length):
                t=j/RATE
                env=min(1,j/180)*math.exp(-t*3.2)
                phase += 2*math.pi*freq/RATE
                saw=2*((phase/(2*math.pi))%1)-1
                sub=math.sin(phase*.5)
                v=math.tanh((saw*.72+sub*.25)*1.8)*env
                if start+j<total: mix[start+j]+=v*.32
        peak=max(max(abs(x) for x in mix),1e-9)
        write_wav(acid/f"Infinity_Acid_{bpm}BPM_4bar.wav",[x/peak*.78 for x in mix])

    # Evolving, loopable-feeling pads/textures generated from layered oscillators and filtered noise.
    for idx,(name,base) in enumerate((("Blue_Hour",110),("Concrete_Dawn",82),("Deep_Current",65),("Glass_Rain",146),("Cold_Neon",98),("Submerged",55),("Afterimage",130),("Night_Transit",73))):
        seconds=12; n=RATE*seconds; out=[]
        phases=[0.0,0.0,0.0]
        for i in range(n):
            t=i/RATE
            lfo=.5+.5*math.sin(2*math.pi*t/seconds)
            val=0.0
            for k,ratio in enumerate((1,1.498,2.003)):
                f=base*ratio*(1+.002*math.sin(2*math.pi*(.035+k*.012)*t))
                phases[k]+=2*math.pi*f/RATE
                val+=math.sin(phases[k])*(.20 if k==0 else .11)
            noise=random.uniform(-1,1)
            val+=noise*(.012+.025*lfo)
            fade=min(1,t*2,(seconds-t)*2)
            out.append(math.tanh(val*1.35)*max(0,fade))
        write_wav(atmos/f"Infinity_Atmos_{name}_12s.wav",out)

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"Licenses").mkdir(parents=True,exist_ok=True)
    archive=ROOT/"meta.zip"
    fetch("https://codeload.github.com/facebookincubator/Meta-open-sound/zip/refs/heads/main",archive)
    with zipfile.ZipFile(archive) as z: z.extractall(SRC)
    repo=next(SRC.glob("Meta-open-sound-*"))
    # Full-resolution 24-bit / 48 kHz CC0 instrument recordings from Meta releases.
    collections = [
      ("Piano", "https://github.com/facebookincubator/Meta-open-sound/releases/download/meta-piano-v1.0.0/meta-open-sound-meta-piano-wav.zip"),
      ("Guitar_Nylon", "https://github.com/facebookincubator/Meta-open-sound/releases/download/meta-nylon-guitar-v1.0.0/meta-open-sound-meta-nylon-guitar-wav.zip"),
      ("Guitar_Steel", "https://github.com/facebookincubator/Meta-open-sound/releases/download/meta-steel-guitar-v1.0.0/meta-open-sound-meta-steel-guitar-wav.zip"),
    ]
    for folder, url in collections:
        pack = ROOT / (folder + "-full.wav.zip")
        fetch(url, pack)
        extract = ROOT / (folder + "-full")
        extract.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(pack) as z: z.extractall(extract)
        dest = OUT / "Instruments" / folder
        dest.mkdir(parents=True, exist_ok=True)
        copied = 0
        for src in extract.rglob("*"):
            if not src.is_file(): continue
            if src.suffix.lower() in (".wav", ".sfz", ".md", ".txt", ".json"):
                target = dest / src.name
                if target.exists() and src.suffix.lower() == ".wav":
                    target = dest / (src.parent.name + "_" + src.name)
                shutil.copy2(src, target)
                if src.suffix.lower() == ".wav": copied += 1
        license_id = {"Piano":"meta-piano", "Guitar_Nylon":"meta-nylon-guitar", "Guitar_Steel":"meta-steel-guitar"}[folder]
        license_file = repo / "systems" / "instruments" / license_id / "LICENSE"
        if license_file.exists(): shutil.copy2(license_file, dest / "LICENSE")
        source_readme = repo / "systems" / "instruments" / license_id / "README.md"
        if source_readme.exists(): shutil.copy2(source_readme, dest / "SOURCE_README.md")
        if copied < 100: raise RuntimeError(f"{folder}: expected full multisample set, got {copied}")
        print(f"{folder}: imported {copied} original WAV samples")

    # CC0 Phazite pack includes recorded percussion, foley, effects and an original breakbeat.
    phazite_url = "https://github.com/august-byrne/phazite-sounds/releases/download/v1/Phazite-Sounds-1.zip"
    phazite_zip = ROOT / "phazite-sounds.zip"
    fetch(phazite_url, phazite_zip)
    phazite_root = ROOT / "phazite"
    phazite_root.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(phazite_zip) as z: z.extractall(phazite_root)
    phazite_dest = OUT / "Community_CC0" / "Phazite"
    phazite_dest.mkdir(parents=True, exist_ok=True)
    phazite_count = 0
    for src in phazite_root.rglob("*"):
        if not src.is_file(): continue
        if src.suffix.lower() in (".flac", ".wav", ".ogg"):
            shutil.copy2(src, phazite_dest / src.name)
            phazite_count += 1
        elif src.name.lower() in ("license.txt", "readme.txt", "sources.json", "sources.txt"):
            shutil.copy2(src, phazite_dest / src.name)
    if phazite_count < 50: raise RuntimeError(f"Phazite CC0 pack import too small: {phazite_count}")

    make_original_kit()
    render_generated_content()
    (OUT/"README_RU.txt").write_text(
      "INFINITY SAMPLE LIBRARY - LIVE EXPANDED 04\\n"
      "Основа: полные мультисэмплы живого фортепиано и акустических гитар Meta Open Sound, оригинальные WAV 24-bit / 48 kHz, CC0 1.0.\\n"
      "Дополнение: Phazite Sounds, 85 CC0 звуков, включая записанные ударные, перкуссию, фоли, эффекты и брейкбит; исходные sources.json и LICENSE сохранены.\\n"
      "Процедурные ударные, Acid и атмосферные слои Infinity вынесены отдельно и не выдаются за живые записи.\\n"
      "Исходные форматы и разрешение аудио сохраняются; файлы Meta не перекодируются.\\n"
      "Источники: https://github.com/facebookincubator/Meta-open-sound и https://github.com/august-byrne/phazite-sounds\\n",
      encoding="utf-8")
    zip_path=Path("Infinity_Live_Sample_Library_04.zip")
    catalog = []
    audio_files = sorted(list(OUT.rglob("*.wav")) + list(OUT.rglob("*.flac")) + list(OUT.rglob("*.ogg")))
    for f in audio_files:
        rel = str(f.relative_to(OUT)).replace("\\\\", "/")
        probe = subprocess.run(["ffprobe","-v","error","-select_streams","a:0","-show_entries",
            "stream=sample_rate,channels,bits_per_sample,bits_per_raw_sample","-of","json",str(f)],
            capture_output=True,text=True,check=True)
        stream = json.loads(probe.stdout).get("streams",[{}])[0]
        catalog.append({"path": rel, "format": f.suffix[1:].upper(),
            "sample_rate": int(stream.get("sample_rate",0)) or None,
            "channels": stream.get("channels"),
            "bit_depth": stream.get("bits_per_raw_sample") or stream.get("bits_per_sample"),
            "category": rel.split("/")[0],
            "sha256": hashlib.sha256(f.read_bytes()).hexdigest()})
    (OUT/"manifest.json").write_text(json.dumps({"name":"Infinity Live Sample Library 04",
        "audio_files":len(catalog), "cc0_phazite_files":phazite_count, "files":catalog}, ensure_ascii=False, indent=2), encoding="utf-8")
    with zipfile.ZipFile(zip_path,"w",zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for f in OUT.rglob("*"):
            if f.is_file(): z.write(f,f.relative_to(OUT.parent))
    print(f"Created {zip_path} ({zip_path.stat().st_size} bytes), {len(catalog)} audio files")
if __name__=="__main__": main()
