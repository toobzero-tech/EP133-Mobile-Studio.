#!/usr/bin/env python3
"""Build a small, redistributable starter library for Infinity."""
from pathlib import Path
import math, random, struct, wave, zipfile, urllib.request, shutil, subprocess

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

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    archive=ROOT/"meta.zip"
    fetch("https://codeload.github.com/facebookincubator/Meta-open-sound/zip/refs/heads/main",archive)
    with zipfile.ZipFile(archive) as z: z.extractall(SRC)
    repo=next(SRC.glob("Meta-open-sound-*"))
    # Meta's CC0 instrument preview samples. Keep a compact, useful subset.
    picks = {
      "meta-piano": ("Piano", 16),
      "meta-nylon-guitar": ("Guitar_Nylon", 18),
      "meta-steel-guitar": ("Guitar_Steel", 18),
    }
    for ident,(folder,limit) in picks.items():
        src=repo/"systems"/"instruments"/ident/"ogg"
        files=sorted(src.glob("*.ogg")) if src.exists() else []
        # Spread picks across the set instead of taking adjacent duplicate notes.
        if files:
            stride=max(1,len(files)//limit)
            selected=files[::stride][:limit]
            dest=OUT/"Instruments"/folder
            dest.mkdir(parents=True,exist_ok=True)
            for f in selected:
                target=dest/(f.stem+".wav")
                subprocess.run(["ffmpeg","-y","-loglevel","error","-i",str(f),"-ar",str(RATE),"-ac","1",str(target)],check=True)
        lic=repo/"systems"/"instruments"/ident/"LICENSE"
        if lic.exists(): shutil.copy2(lic,OUT/"Licenses"/(ident+"-LICENSE.txt"))
        spec=repo/"systems"/"instruments"/ident/"README.md"
        if spec.exists(): shutil.copy2(spec,OUT/"Instruments"/folder/"SOURCE_README.md")
    make_original_kit()
    (OUT/"README_RU.txt").write_text(
      "INFINITY SAMPLE LIBRARY - STARTER 01\n"
      "Содержит оригинальные процедурно синтезированные ударные и компактные наборы инструментальных WAV-сэмплов Meta Open Sound.\n"
      "Инструментальные коллекции Meta Piano / Meta Nylon Guitar / Meta Steel Guitar опубликованы под CC0 1.0.\n"
      "Оригинальные ударные сгенерированы скриптом проекта Infinity и могут свободно использоваться в музыке.\n"
      "Формат: WAV PCM, 48 kHz, mono. Для каждого стороннего набора сохранены исходные сведения о лицензии.\n"
      "Источник Meta Open Sound: https://github.com/facebookincubator/Meta-open-sound\n"
      "Проверяйте файл LICENSE в папке Licenses перед повторным распространением отдельных исходных коллекций.\n",
      encoding="utf-8")
    zip_path=Path("Infinity_Sample_Library_Starter_01.zip")
    with zipfile.ZipFile(zip_path,"w",zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for f in OUT.rglob("*"):
            if f.is_file(): z.write(f,f.relative_to(OUT.parent))
    print(f"Created {zip_path} ({zip_path.stat().st_size} bytes)")
if __name__=="__main__": main()
