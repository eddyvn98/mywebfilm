import os
import subprocess

from constants import FFMPEG_PATH
from ffmpeg_runtime import FFMPEG_LONG_TIMEOUT, ffmpeg_subprocess_kwargs


def remux_ts_to_mp4(input_path, output_path, semaphore):
    with semaphore:
        try:
            cmd = [
                FFMPEG_PATH, "-loglevel", "error", "-y",
                "-fflags", "+genpts",
                "-err_detect", "ignore_err",
                "-i", input_path,
                "-map", "0:v:0?", "-map", "0:a:0?",
                "-c", "copy",
                "-bsf:a", "aac_adtstoasc",
                "-movflags", "+faststart",
                output_path,
            ]
            res = subprocess.run(
                cmd, capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=FFMPEG_LONG_TIMEOUT,
                **ffmpeg_subprocess_kwargs(),
            )
            if res.returncode == 0:
                return True

            cmd_no_bsf = [c for c in cmd if c not in ["-bsf:a", "aac_adtstoasc"]]
            res = subprocess.run(
                cmd_no_bsf, capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=FFMPEG_LONG_TIMEOUT,
                **ffmpeg_subprocess_kwargs(),
            )
            if res.returncode == 0:
                return True

            cmd_hybrid = [
                FFMPEG_PATH, "-loglevel", "error", "-y",
                "-fflags", "+genpts",
                "-i", input_path,
                "-c:v", "copy",
                "-c:a", "aac", "-b:a", "128k",
                "-movflags", "+faststart",
                output_path,
            ]
            res = subprocess.run(
                cmd_hybrid, capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=FFMPEG_LONG_TIMEOUT,
                **ffmpeg_subprocess_kwargs(),
            )
            return res.returncode == 0
        except Exception as exc:
            print(f"Remux Exception: {exc}")
            return False


def convert_ts_to_mp4(
    input_path,
    delete_src,
    *,
    semaphore,
    validate_output,
    get_encoder,
    remux,
):
    filename = os.path.basename(input_path)
    name, ext = os.path.splitext(filename)
    ext = ext.lower()

    output_path = os.path.join(os.path.dirname(input_path), f"{name}.mp4")
    temp_output = False
    if ext == ".mp4":
        output_path = os.path.join(
            os.path.dirname(input_path),
            f"{name}.converting.mp4",
        )
        temp_output = True

    if ext in {".ts", ".m2ts"} and remux(input_path, output_path):
        if validate_output(output_path):
            if delete_src:
                os.remove(input_path)
            return output_path
        if os.path.exists(output_path):
            os.remove(output_path)

    with semaphore:
        try:
            from config_manager import load_config

            pref_codec = load_config().get("preferred_codec", "h264").lower()
            encoder = get_encoder(pref_codec)
            cmd = [FFMPEG_PATH, "-loglevel", "error", "-y", "-i", input_path, "-c:v", encoder]

            if "libx264" in encoder or "libx265" in encoder:
                cmd.extend(["-preset", "veryfast", "-crf", "18"])
            elif "nvenc" in encoder:
                cmd.extend(["-rc", "vbr", "-cq", "18", "-qmin", "15", "-qmax", "22"])
                cmd.extend(["-preset", "p4"])
            elif "qsv" in encoder:
                cmd.extend(["-global_quality", "18", "-preset", "veryfast"])
            else:
                cmd.extend(["-b:v", "10M", "-maxrate", "15M", "-bufsize", "30M"])
                cmd.extend(["-preset", "veryfast"])

            cmd.extend([
                "-c:a", "aac", "-b:a", "192k",
                "-movflags", "+faststart",
                output_path,
            ])
            res = subprocess.run(
                cmd, capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=FFMPEG_LONG_TIMEOUT,
                **ffmpeg_subprocess_kwargs(),
            )
            if res.returncode != 0:
                return None
            if not validate_output(output_path):
                if os.path.exists(output_path) and output_path != input_path:
                    os.remove(output_path)
                return None

            final_path = output_path
            if temp_output and delete_src:
                original_final = os.path.join(
                    os.path.dirname(input_path),
                    f"{name}.mp4",
                )
                try:
                    os.replace(output_path, original_final)
                    final_path = original_final
                except Exception as exc:
                    print(f"Atomic Swap Error: {exc}")
                    try:
                        if os.path.exists(output_path):
                            os.remove(output_path)
                    except OSError:
                        pass
                    return None
            elif (
                not temp_output
                and delete_src
                and os.path.exists(output_path)
                and input_path != output_path
            ):
                try:
                    os.remove(input_path)
                except OSError:
                    pass

            return final_path
        except Exception as exc:
            print(f"Convert Exception: {exc}")
            return None
