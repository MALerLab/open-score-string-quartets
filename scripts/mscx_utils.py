import os
from datetime import datetime
import operator
import time
import argparse
import subprocess
import shutil
from pathlib import Path
from typing import Union, Any, Optional
from tempfile import NamedTemporaryFile, TemporaryDirectory

import multiprocessing

import json
import cv2

from tqdm.auto import tqdm

import xml.etree.ElementTree as ET
import pdfplumber

from modules.lsyolo import bbox_utils 
from modules.lmxe.lmxe import load_lmx, delinearize_lmx
from modules.lmxe.lmxe import delinearize_lmxe
from modules.lmxe.lmxe.LMXEFile import LMXEFile

from .utils import get_ts, PathLike
from .utils import spawn_processes, terminate_processes
from .utils import strip_musicXML, crop_white_space


DEFAULT_ENV = {
  'QT_QPA_PLATFORM': 'xcb',
  'QT_X11_NO_MITSHM': '1',
  # 'XDG_RUNTIME_DIR': '/home/dongmin/tmp'
}



def convert_mscx_to_musicxml(
  metadata, 
  score_dir, 
  script_path, 
  style_path='',
  virtual_display=':99',
):
  env = os.environ.copy()
  env.update({
    'DISPLAY': virtual_display,
    **DEFAULT_ENV
  })
  
  process_configs = [
    ['Xvfb', virtual_display, '-screen', '0', '2560x1440x24', '-ac'],
    [script_path]
  ]
  
  processes = spawn_processes(process_configs, env)
  
  score_pbar = tqdm(metadata.items())
  for ossq_id, infos in score_pbar:
    ossq_id = f'sq{ossq_id}'
    
    mscore_dir = score_dir / infos['path'] 
    
    mscx_path = mscore_dir / f"{ossq_id}.mscx"
    musicxml_path = mscore_dir / f"{ossq_id}.musicxml"
    
    paths = (musicxml_path, mscx_path)
    
    cmd = [script_path, f"-S {style_path}", "-o", str(paths[0]), str(paths[1])]
    
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
  
  terminate_processes(processes)


def convert_musicxml_to_mscx(
  xml:str,
  out_dir:PathLike,
  script_path, 
  style_path='',
  virtual_display=':99',
):
  xml = strip_musicXML(xml)

  if not isinstance(out_dir, Path):
    out_dir = Path(out_dir)
  
  env = os.environ.copy()
  env.update({
    'DISPLAY': virtual_display,
    **DEFAULT_ENV
  })
  
  process_configs = [
    ['Xvfb', virtual_display, '-screen', '0', '2560x1440x24', '-ac'],
    [script_path]
  ]
  
  processes = spawn_processes(process_configs, env)
  
  temp_xml_path = out_dir / 'temp.musicxml'
  out_path = out_dir / 'temp.mscx'
  
  with open(temp_xml_path, 'w', encoding='utf-8') as f:
    f.write(xml)
  
  cmd = [script_path, "-S", f"{style_path}", "-o", str(out_path), str(temp_xml_path)]
  
  try:
    # convert MusicXML to .mscx file
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
  
  # temp_xml_path.unlink()
  
  terminate_processes(processes)
  
  return out_path


def render_mscx(
  mscx_path:Union[PathLike,None],
  out_path:PathLike,
  env,
  dpi:Optional[int]=300,
  mscore_exec:str='./mscore',
  style_path:str='',
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
    f"-S {style_path}", 
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


def convert_mscx_to_pdf(
  metadata, 
  score_dir, 
  script_path,
  style_path='',
  display_id=':99'
):
  
  env = os.environ.copy()
  env.update({
    'DISPLAY': display_id,
    **DEFAULT_ENV
  })
  
  process_configs = [
    ['Xvfb', display_id, '-screen', '0', '2560x1440x24', '-ac'],
    [script_path]
  ]
  
  processes = spawn_processes(process_configs, env)
  
  
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
      style_path=style_path,
    )
  
  # Clean up Xvfb
  terminate_processes(processes)


def split_pdf(pdf_path, pdf_type='synthetic', log=None):
  if not pdf_path.exists():
    print(f"PDF file does not exist:{str(pdf_path)}", file=None)
    return
  
  img_dir = pdf_path.parent / 'images' / pdf_type / 'original'
  img_dir.mkdir(parents=True, exist_ok=True)
  
  try:
    pdf = pdfplumber.open(str(pdf_path))

    for page in pdf.pages:
      page_number = str(page.page_number).zfill(4)
      image = page.to_image(resolution=300)
      
      image_path = img_dir / f'{pdf_path.stem.split("_")[0]}:{page_number}.png'
      image.save(str(image_path))
  except Exception as e:
    print(f"Failed to split:{str(pdf_path)}", file=log)


def convert_pdf_to_images(metadata:dict, score_dir:PathLike, pdf_type='synthetic', log_path:Optional[PathLike]=None):
  score_pbar = tqdm(metadata.items())
  log = None
  if log_path is not None:
    log = open(log_path, 'w', encoding='utf-8')
  
  for ossq_id, infos in score_pbar:
    ossq_id = f'sq{ossq_id}'
    
    mscore_dir = score_dir / infos['path'] 
    pdf_path = mscore_dir / f"{ossq_id}_{pdf_type}.pdf"
    
    split_pdf(pdf_path, pdf_type=pdf_type, log=log)
  
  log.close()



lmx_func = {
  'lmx': (load_lmx, delinearize_lmx),
  'lmxe': (None, delinearize_lmxe),
}

def single_render(render_data):
  l_p, out_dir, _, delinearize_fn, dpi, script_path, style_path, env = render_data

  out_sub_dir = out_dir / l_p.stem.replace('.system', '').replace('.page', '')
  out_sub_dir.mkdir(exist_ok=True)
  
  xml = delinearize_fn(l_p)
  xml = ET.tostring(xml.tree.getroot(), encoding='utf-8', xml_declaration=True).decode('utf-8')
  
  mscx_path = convert_musicxml_to_mscx(xml, out_sub_dir, script_path, style_path)

  pdf_path = out_sub_dir / 'temp.pdf'

  render_mscx(
    mscx_path=mscx_path,
    out_path=pdf_path,
    env=env,
    dpi=dpi,
    mscore_exec=script_path,
    style_path=style_path,
  )

  mscx_path.unlink()
  
  pdf = pdfplumber.open(str(pdf_path))
  image = pdf.pages[0].to_image(resolution=300)
  image_path = out_sub_dir.with_suffix('.png')
  image.save(str(image_path))

  return image_path


def render_lmx(
  lmxe_paths:list[PathLike],
  out_dir:PathLike,
  type='lmx',
  dpi:Optional[int]=300,
  script_path:str='./mscore',
  style_path:str='',
  display_id = ':99',
):
  if not isinstance(out_dir, Path):
    out_dir = Path(out_dir)
  
  load, delinearize = lmx_func[type]
  
  env = os.environ.copy()
  env.update({
    'DISPLAY': display_id,
    'QT_QPA_PLATFORM': 'xcb',
    'QT_X11_NO_MITSHM': '1',
    'XDG_RUNTIME_DIR': '/home/dongmin/tmp'
  })
  
  process_configs = [
    ['Xvfb', display_id, '-screen', '0', '2560x1440x24', '-ac'],
    [script_path]
  ]
  
  processes = spawn_processes(process_configs, env)
  
  total_paths = []

  for render_data in [(p, out_dir, load, delinearize, dpi, script_path, style_path, env) for p in lmxe_paths]:
    try:
      image_path = single_render(render_data)
      total_paths.append(image_path)
    except Exception as e:
      print(f"[ERROR] Rendering {render_data[0]} failed: {e}")
      total_paths.append(None)

  terminate_processes(processes)
  
  return total_paths