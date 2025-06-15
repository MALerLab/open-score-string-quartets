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

import pdfplumber

from modules.lsyolo import bbox_utils 
from modules.lmxe.lmxe import load_lmx, delinearize_lmx
from modules.lmxe.lmxe import load_lmxe, delinearize_lmxe

from .utils import get_ts, PathLike
from .utils import spawn_processes, terminate_processes



def convert_mscx_to_musicxml(
  metadata, 
  score_dir, 
  script_path, 
  virtual_display=':99',
):
  env = os.environ.copy()
  env.update({
    'DISPLAY': virtual_display,
    'QT_QPA_PLATFORM': 'xcb',
    'QT_X11_NO_MITSHM': '1',
    'XDG_RUNTIME_DIR': '/tmp'
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
    
    cmd = [script_path, "-S ./ossq.mss", "-o", str(paths[0]), str(paths[1])]
      
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
  virtual_display=':99',
):
  if not isinstance(out_dir, Path):
    out_dir = Path(out_dir)
  
  env = os.environ.copy()
  env.update({
    'DISPLAY': virtual_display,
    'QT_QPA_PLATFORM': 'xcb',
    'QT_X11_NO_MITSHM': '1',
    'XDG_RUNTIME_DIR': '/tmp'
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
  
  cmd = [script_path, "-S", "./ossq.mss", "-o", str(out_path), str(temp_xml_path)]
  
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
  
  temp_xml_path.unlink()
  
  terminate_processes(processes)
  
  return out_path


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
    "-S ./ossq.mss", 
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
  display_id=':99'
):
  
  env = os.environ.copy()
  env.update({
      'DISPLAY': display_id,
      'QT_QPA_PLATFORM': 'xcb',
      'QT_X11_NO_MITSHM': '1',
      'XDG_RUNTIME_DIR': '/tmp'
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
    )
  
  # Clean up Xvfb
  terminate_processes(processes)


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



lmx_func = {
  'lmx': (load_lmx, delinearize_lmx),
  'lmxe': (load_lmxe, delinearize_lmxe),
}

def render_lmx(
  lmxe_paths:list[PathLike],
  out_dir:PathLike,
  type='lmx',
  dpi:Optional[int]=300,
  script_path:str='./mscore',
  display_id = ':99',
):
  if not isinstance(out_dir, Path):
    out_dir = Path(out_dir)
  
  env = os.environ.copy()
  env.update({
      'DISPLAY': display_id,
      'QT_QPA_PLATFORM': 'xcb',
      'QT_X11_NO_MITSHM': '1',
      'XDG_RUNTIME_DIR': '/tmp'
  })
  
  process_configs = [
    ['Xvfb', display_id, '-screen', '0', '2560x1440x24', '-ac'],
    [script_path]
  ]
  
  processes = spawn_processes(process_configs, env)
  
  total_paths = []
  
  for l_p in tqdm(lmxe_paths):
    out_sub_dir = out_dir / l_p.stem
    out_sub_dir.mkdir(exist_ok=True)
    
    load, delinearize = lmx_func[type]
    
    lmx = load(l_p)
    xml = delinearize(lmx)
    
    mscx_path = convert_musicxml_to_mscx(xml, out_sub_dir, './mscore')
  
    pdf_path = out_sub_dir / 'temp.pdf'
  
    render_mscx(
      mscx_path=mscx_path,
      out_path=pdf_path,
      env=env,
      dpi=dpi,
      mscore_exec=script_path,
    )
  
    mscx_path.unlink()
  
    image_paths = []
    
    pdf = pdfplumber.open(str(pdf_path))
    for page in pdf.pages:
      page_number = str(page.page_number).zfill(4)
      image = page.to_image(resolution=300)
      
      image_path = out_sub_dir / f'{page_number}.png'
      image.save(str(image_path))
      image_paths.append(image_path)
    
    pdf_path.unlink()
    
    total_paths.append(image_paths)
  
  
  terminate_processes(processes)
  
  return total_paths