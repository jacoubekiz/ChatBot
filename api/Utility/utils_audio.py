import os
import shutil
import subprocess
import tempfile
import requests
from .utils_whatsapp_api import _raise_for_api_error


GRAPH_VERSION = "v20.0"
TIMEOUT = 60


class WhatsAppApiError(Exception):
    pass


def which(cmd):
    """Check if a command is available in the system PATH."""
    return shutil.which(cmd)


def ffmpeg_has_opus_encoder():
    """Return 'libopus' or 'opus' if available in ffmpeg encoders, else None."""
    if not which("ffmpeg"):
        return None
    try:
        out = subprocess.check_output(["ffmpeg", "-encoders"], stderr=subprocess.STDOUT)
        out = out.decode("utf-8", "ignore")
    except Exception:
        return None
    if "libopus" in out:
        return "libopus"
    if "\nopus" in out or " A.... opus" in out:
        return "opus"
    return None


def run(cmd):
    """Run a subprocess command with error checking."""
    subprocess.run(cmd, check=True)


def convert_to_ogg_opus_mono(input_path, target_path, bitrate_kbps=24):
    """
    Convert ANY input to OGG/Opus mono, 48kHz.
    Preferred: ffmpeg decode -> opusenc encode.
    Fallback: ffmpeg if it has an opus encoder.
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError("Input file not found: {}".format(input_path))

    dirname = os.path.dirname(os.path.abspath(target_path))
    if dirname and not os.path.exists(dirname):
        os.makedirs(dirname)

    # Path 1: opusenc available (RECOMMENDED) + ffmpeg for decode
    if which("opusenc"):
        if not which("ffmpeg"):
            raise RuntimeError("opusenc is available but ffmpeg is not installed. Install ffmpeg for decoding.")
        with tempfile.TemporaryDirectory() as td:
            wav_path = os.path.join(td, "temp.wav")
            # Decode to mono, 48k, 16-bit PCM WAV
            run(["ffmpeg", "-y", "-i", input_path, "-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le", wav_path])
            # Encode to Ogg Opus mono at given bitrate
            run(["opusenc", "--bitrate", str(bitrate_kbps), "--downmix-mono", "--vbr", "--comp", "10", wav_path, target_path])
        return

    # Path 2: ffmpeg has opus encoder
    enc = ffmpeg_has_opus_encoder()
    if enc:
        run(["ffmpeg", "-y", "-i", input_path, "-c:a", enc, "-b:a", "{}k".format(bitrate_kbps),
             "-ac", "1", "-ar", "48000", target_path])
        return

    raise RuntimeError(
        "No Opus encoder available. Install 'opusenc' (opus-tools) and 'ffmpeg', "
        "or upgrade ffmpeg to a build that includes the 'libopus' or 'opus' encoder."
    )


def upload_audio_get_media_id(phone_number_id, access_token, ogg_path):
    """Upload audio file to WhatsApp and return media ID."""
    url = "https://graph.facebook.com/{}/{}".format(GRAPH_VERSION, phone_number_id) + "/media"
    headers = {"Authorization": "Bearer {}".format(access_token)}
    data = {"messaging_product": "whatsapp", "type": "audio/ogg"}
    with open(ogg_path, "rb") as f:
        files = {"file": (os.path.basename(ogg_path), f, "audio/ogg")}
        resp = requests.post(url, headers=headers, data=data, files=files, timeout=TIMEOUT)
    _raise_for_api_error(resp)
    media_id = resp.json().get("id")
    if not media_id:
        raise WhatsAppApiError("Upload succeeded but no media id in response: {}".format(resp.text))
    return media_id


def send_voice_note_with_media_id(phone_number_id, access_token, to, media_id):
    """Send voice note using media ID."""
    url = "https://graph.facebook.com/{}/{}".format(GRAPH_VERSION, phone_number_id) + "/messages"
    headers = {"Authorization": "Bearer {}".format(access_token), "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "audio",
        "audio": {"id": media_id, "voice": True}
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=TIMEOUT)
    _raise_for_api_error(resp)
    j = resp.json()
    try:
        return j["messages"][0]["id"]
    except Exception:
        return str(j)


def process_and_send_voice_note(input_audio_path, phone_number_id, access_token, recipient, bitrate_kbps=24):
    """
    Convert the given file to WhatsApp-PTT-compatible OGG/Opus mono and send it.
    Returns the WhatsApp message id (wamid...).
    """
    if not os.path.exists(input_audio_path):
        raise FileNotFoundError(input_audio_path)

    with tempfile.TemporaryDirectory() as td:
        out_ogg = os.path.join(td, "voice_note.ogg")
        convert_to_ogg_opus_mono(input_audio_path, out_ogg, bitrate_kbps=bitrate_kbps)

        # Ensure <16 MB
        size_mb = os.path.getsize(out_ogg) / (1024.0 * 1024.0)
        if size_mb > 16.0:
            raise RuntimeError("Converted file is {:.2f} MB (>16MB). Reduce bitrate_kbps or trim the input.".format(size_mb))

        media_id = upload_audio_get_media_id(phone_number_id, access_token, out_ogg)
        wamid = send_voice_note_with_media_id(phone_number_id, access_token, recipient, media_id)
        return wamid
