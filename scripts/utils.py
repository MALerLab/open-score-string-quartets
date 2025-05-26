import os
from datetime import datetime
import time
import argparse
import subprocess
import shutil
from pathlib import Path
from typing import Union, Any, Optional
from tempfile import NamedTemporaryFile, TemporaryDirectory

import json

from tqdm.auto import tqdm

import cv2
import numpy as np
import partitura as pt

import pdfplumber

from modules.svdp.svdp import bbox_utils


get_ts = lambda: datetime.now().strftime('%Y-%m-%d-%H:%M:%S')
dformat = lambda d: json.dumps(d, indent=2)
dprint = lambda d: print(dformat(d))

PathLike = Union[Path, str]


def get_argument_parser(args=None):
  parser = argparse.ArgumentParser()

  if args is None:
    args = [
      ('-d', '--base_dir', True, str),
    ]

  for short, full, required, type_ in args:
    parser.add_argument(
      short,
      full,
      required=required,
      type=type_
    )
  
  return parser


def load_bboxs(file_path, merge=True):
  with open(file_path, 'r') as f:
    lines = f.readlines()
  
  bboxs = [ 
    [ int(p) for p in line.strip().split(' ') ] # lx, ly, rx, ry, (height)
    for line in lines
  ]

  if not merge:
    return bboxs

  # sort by y, x
  bboxs = sorted( bboxs, key=lambda x: (x[1], x[0]) )
  
  # merge overlapping bboxs
  bboxs = bbox_utils.merge_match_bboxs(bboxs)

  return bboxs


def delete_old_musicxml_files(metadata, score_dir):
  """
  Delete all MusicXML files in the data directory.
  """
  for ossq_id, infos in metadata.items():
    ossq_id = f'sq{ossq_id}'
    
    mscore_dir = score_dir / infos['path'] 
    musicxml_path = mscore_dir / f"{ossq_id}.musicxml"
    
    image_paths = (mscore_dir / 'images' / 'original').glob('*.png')
    image_paths = list(sorted(image_paths))
    
    assert musicxml_path.exists(), f"old score: {str(musicxml_path)} does not exist"
    assert all([ p.exists() for p in image_paths ]), f"old score: some images do not exist"
    
    # delete old files
    musicxml_path.unlink()
    for p in image_paths:
      p.unlink()


def merge_external_files(metadata, score_dir, out_dir):
  score_pbar = tqdm(metadata.items())
  
  for ossq_id, infos in score_pbar:
    ossq_id = f'sq{ossq_id}'
    
    score_pbar.set_description(f"{ossq_id}")
    
    new_mscore_dir = out_dir / infos['path']
    new_musicxml_path = new_mscore_dir / f'{ossq_id}.musicxml'
    new_image_paths = (new_mscore_dir / 'images' / 'original').glob('*.png')
    new_image_paths = list(sorted(new_image_paths))
    
    assert new_musicxml_path.exists(), f"{str(new_musicxml_path)} does not exist"
    assert all([ p.exists() for p in new_image_paths ]), f"some images do not exist"
    
    mscore_dir = score_dir / infos['path'] 
    musicxml_path = mscore_dir / f"{ossq_id}.musicxml"
    image_dir = mscore_dir / 'images' / 'original'
    
    # copy new files
    shutil.copy(new_musicxml_path, musicxml_path)
    for src_img in new_image_paths:
      shutil.copy(src_img, image_dir / src_img.name)


def delete_old_lmxe(metadata, score_dir):
  score_pbar = tqdm(metadata.items())
  for mscore_id, infos in score_pbar:
    ossq_id = f'sq{mscore_id}'
    score_pbar.set_description(f"{ossq_id}")
    
    mscore_dir = score_dir / infos['path'] 
    lmxe_paths = (mscore_dir / 'lmxe').glob('*.lmxe')
    
    for p in lmxe_paths:
      p.unlink()


def spawn_xvfb_process(display_id=':99'):
  xvfb_process = subprocess.Popen([
      'Xvfb', display_id, '-screen', '0', '1024x768x24', '-ac'
  ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
  
  time.sleep(2)  # Give Xvfb time to start
  
  return xvfb_process


def terminate_xvfb_process(xvfb_process):
  try:
    xvfb_process.terminate()
    xvfb_process.wait(timeout=5)
  except subprocess.TimeoutExpired:
    xvfb_process.kill()
    xvfb_process.wait()


def convert_mscx_to_musicxml(
  metadata, 
  score_dir, 
  script_path, 
  virtual_display=':99'
):
  display_id = ':99'
  xvfb_process = spawn_xvfb_process(display_id=display_id)
  
  env = os.environ.copy()
  env.update({
      'DISPLAY': virtual_display,
      'QT_QPA_PLATFORM': 'xcb',
      'QT_X11_NO_MITSHM': '1',
      'XDG_RUNTIME_DIR': '/tmp'
  })
  
  score_pbar = tqdm(metadata.items())
  for ossq_id, infos in score_pbar:
    ossq_id = f'sq{ossq_id}'
    
    mscore_dir = score_dir / infos['path'] 
    
    mscx_path = mscore_dir / f"{ossq_id}.mscx"
    musicxml_path = mscore_dir / f"{ossq_id}.musicxml"
    
    cmd = [script_path, "-o", str(musicxml_path), str(mscx_path)]
      
    try:
      # convert MuseScore file to MusicXML
      ps = subprocess.run(
        cmd, env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
      )
      
      if ps.returncode != 0:
        raise Exception(
          "Command {} failed with code {}. MuseScore " "error messages:\n {}"
          .format(cmd, ps.returncode, ps.stderr.decode("UTF-8"))
        )
    
    except Exception as e:
      raise Exception(
        'Executing "{}" \nreturned  {}.'.format(" ".join(cmd), e)
      )
  
  terminate_xvfb_process(xvfb_process)


def render_mscx(
  mscx_path:Union[PathLike,None],
  out_path:PathLike,
  env,
  dpi:Optional[int]=300,
  mscore_exec:str='./mscore',
) -> PathLike:
  """
  render .mscx file as .pdf using MuseScore

  Parameters
  ----------
  mscx_path : PathLike or None
    MuseScore file path to be rendered
  out_path : Path to output PDF file
  dpi : int, optional
    Image resolution. 
    This option is ignored when `fmt` is 'pdf'. 
    Defaults to 90.

  Returns
  -------
  out : PathLike
    Path to the output PDF file if rendering was successful, 
    otherwise None.
  """

  img_fh = Path(out_path)
  
  cmd = [
    mscore_exec,
    "-r",
    "{}".format(int(dpi)),
    "-o",
    str(img_fh),
    str(mscx_path),
  ]
  
  try:
    ps = subprocess.run(
      cmd, env=env,
      stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    
    if ps.returncode != 0:
      raise Exception(
        "Command {} failed with code {}; stdout: {}; stderr: {}"
        .format(
          " ".join(cmd),
          ps.returncode,
          ps.stdout.decode("UTF-8"),
          ps.stderr.decode("UTF-8"),
        )
      )
    
    return img_fh if img_fh.exists() else None
  
  except Exception as e:
    raise Exception(
      'Executing "{}" returned  {}.'
      .format(" ".join(cmd), e),
    )
  
  return None


def convert_mscx_to_pdf(metadata, score_dir, script_path):
  display_id = ':99'
  xvfb_process = spawn_xvfb_process(display_id=display_id)
  
  env = os.environ.copy()
  env.update({
      'DISPLAY': display_id,
      'QT_QPA_PLATFORM': 'xcb',
      'QT_X11_NO_MITSHM': '1',
      'XDG_RUNTIME_DIR': '/tmp'
  })
  
  score_pbar = tqdm(metadata.items())
  for ossq_id, infos in score_pbar:
    ossq_id = f'sq{ossq_id}'
    
    mscore_dir = score_dir / infos['path'] 
    mscx_path = mscore_dir / f"{ossq_id}.mscx"
    
    pdf_path = mscore_dir / f"{ossq_id}_synthetic.pdf"
    
    render_mscx(
      mscx_path=mscx_path,
      out_path=pdf_path,
      env=env,
      dpi=300,
      mscore_exec=script_path,
      virtual_display=display_id,
    )
  
  # Clean up Xvfb
  terminate_xvfb_process(xvfb_process)


def split_pdf(pdf_path):
  if not pdf_path.exists():
    print(f"PDF file does not exist:{str(pdf_path)}")
    return
  
  img_dir = pdf_path.parent / 'images' / 'synthetic' / 'original'
  img_dir.mkdir(parents=True, exist_ok=True)
    
  pdf = pdfplumber.open(str(pdf_path))

  for page in pdf.pages:
    page_number = str(page.page_number).zfill(4)
    image = page.to_image(resolution=300)
    
    image_path = img_dir / f'{pdf_path.stem.split("_")[0]}:{page_number}.png'
    image.save(str(image_path))


def convert_pdf_to_images(metadata:dict, score_dir:PathLike):
  score_pbar = tqdm(metadata.items())
  for ossq_id, infos in score_pbar:
    ossq_id = f'sq{ossq_id}'
    
    mscore_dir = score_dir / infos['path'] 
    pdf_path = mscore_dir / f"{ossq_id}_synthetic.pdf"
    
    split_pdf(pdf_path)

