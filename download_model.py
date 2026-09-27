"""
Download donut-base model to a local folder for pendrive transfer.

Run this on YOUR machine (Vrushti's laptop) BEFORE copying to pendrive.
Requirements: pip install transformers sentencepiece

Usage:
    python download_model.py
    python download_model.py --output_dir D:/pendrive/donut-base
"""

import argparse
from pathlib import Path

def download(output_dir: str):
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    print(f'Downloading naver-clova-ix/donut-base to: {output_path}')
    print('This is ~800 MB — will take a few minutes...\n')

    from transformers import DonutProcessor, VisionEncoderDecoderModel, VisionEncoderDecoderConfig

    print('[1/3] Downloading processor (tokenizer + image processor)...')
    processor = DonutProcessor.from_pretrained('naver-clova-ix/donut-base')
    processor.save_pretrained(str(output_path))
    print('      Done.')

    print('[2/3] Downloading config...')
    config = VisionEncoderDecoderConfig.from_pretrained('naver-clova-ix/donut-base')
    config.save_pretrained(str(output_path))
    print('      Done.')

    print('[3/3] Downloading model weights (~800 MB)...')
    model = VisionEncoderDecoderModel.from_pretrained('naver-clova-ix/donut-base')
    model.save_pretrained(str(output_path))
    print('      Done.\n')

    # Verify
    files = list(output_path.rglob('*'))
    total_mb = sum(f.stat().st_size for f in files if f.is_file()) / 1024**2
    print(f'Saved {len(files)} files  ({total_mb:.0f} MB)  →  {output_path}')
    print('\nReady to copy this folder to pendrive.')
    print('Friend should use:  python train_local.py --model_path ./donut-base ...')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output_dir', default='./donut-base',
                        help='Where to save the model (default: ./donut-base)')
    args = parser.parse_args()
    download(args.output_dir)
