import sys
import os

# ПРИНУДИТЕЛЬНО отключаем torchcodec, чтобы torchaudio даже не пытался его найти
sys.modules['torchcodec'] = None 

import torch
import torchaudio
import torch.serialization
from pathlib import Path
import shutil
import subprocess

# Импортируем soundfile напрямую (нужно будет установить: pip install soundfile)
import soundfile as sf

from demucs.hdemucs import HDemucs
from demucs.apply import apply_model

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

model = None 
MODEL_PATH = resource_path("larsnet/pretrained_larsnet_models/drumsep_model")

def load_drum_model():
    global model
    if model is not None:
        return model
    
    print("Loading drum separation model...")
    torch.serialization.add_safe_globals([HDemucs])
    
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(f"Model not found at {MODEL_PATH}")
        
    checkpoint = torch.load(MODEL_PATH, map_location="cpu", weights_only=False)
    model = checkpoint["klass"](*checkpoint["args"], **checkpoint["kwargs"])
    model.load_state_dict(checkpoint["state"])
    model.eval()
    print("Model loaded")
    return model

def separate(audio_path, output_root):
    current_model = load_drum_model()
    
    # ЗАМЕНА torchaudio.load на soundfile.read
    # Это обходит проблему с FFmpeg и TorchCodec
    data, sr = sf.read(audio_path)
    # Превращаем в тензор Torch (формат [каналы, время])
    if len(data.shape) == 1: # моно
        waveform = torch.from_numpy(data).float().unsqueeze(0)
    else: # стерео
        waveform = torch.from_numpy(data.T).float()

    with torch.no_grad():
        sources = apply_model(current_model, waveform.unsqueeze(0))

    sources = sources.squeeze(0)
    output_dir = Path(output_root) / f"{Path(audio_path).stem}_stems"
    
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    stem_names = ["kick", "snare", "cymbals", "toms"]
    for i, name in enumerate(stem_names):
        # Сохраняем тоже через soundfile
        stem_data = sources[i].cpu().numpy().T
        sf.write(str(output_dir / f"{name}.wav"), stem_data, sr)

    if subprocess.os.name == 'nt':
        subprocess.run(["explorer", str(output_dir)])
    else:
        subprocess.run(["open", str(output_dir)])

    return output_dir