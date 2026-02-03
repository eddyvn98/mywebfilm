import os
import sys
from unittest.mock import patch, MagicMock

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import ffmpeg_service as ff

def test_encoder_selection():
    print("Testing Encoder Selection Logic...")
    
    # Mock FFmpeg -encoders output
    h264_encoders = " V..... libx264             libx264 H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10\n V..... h264_nvenc           NVIDIA NVENC H.264 encoder"
    hevc_encoders = " V..... libx265             libx265 H.265 / HEVC\n V..... hevc_nvenc           NVIDIA NVENC HEVC encoder"
    all_encoders = h264_encoders + "\n" + hevc_encoders

    with patch('subprocess.run') as mock_run:
        # Case 1: H.264 preferred, NVENC available
        mock_run.return_value = MagicMock(stdout=all_encoders, returncode=0)
        encoder = ff.get_best_gpu_encoder("h264")
        print(f"H.264 Preferred (NVENC available) -> Expected: h264_nvenc, Got: {encoder}")
        assert encoder == "h264_nvenc"

        # Case 2: HEVC preferred, NVENC available
        encoder = ff.get_best_gpu_encoder("hevc")
        print(f"HEVC Preferred (NVENC available) -> Expected: hevc_nvenc, Got: {encoder}")
        assert encoder == "hevc_nvenc"

        # Case 3: HEVC preferred, only CPU available
        mock_run.return_value = MagicMock(stdout=" V..... libx264\n V..... libx265", returncode=0)
        encoder = ff.get_best_gpu_encoder("hevc")
        print(f"HEVC Preferred (Only CPU available) -> Expected: libx265, Got: {encoder}")
        assert encoder == "libx265"

        # Case 4: Invalid codec (fallback to H.264)
        mock_run.return_value = MagicMock(stdout=all_encoders, returncode=0)
        encoder = ff.get_best_gpu_encoder("invalid")
        print(f"Invalid codec -> Expected: h264_nvenc, Got: {encoder}")
        assert encoder == "h264_nvenc"

    print("\nAll logical tests passed!")

if __name__ == "__main__":
    try:
        test_encoder_selection()
    except AssertionError as e:
        print(f"Test Failed!")
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)
