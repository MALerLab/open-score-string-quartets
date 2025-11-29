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
  'XDG_RUNTIME_DIR': '/home/issyun/tmp'
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
    "-r",
    "{}".format(int(dpi)),
    "-o",
    str(img_fh),
    str(mscx_path),
  ]
  
  if style_path:
    cmd.insert(1, "-S")
    cmd.insert(2, style_path)
  
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


def render_musicxml_to_pdf(
  musicxml_path: PathLike,
  output_pdf_path: PathLike,
  dpi: Optional[int] = 300,
  script_path: str = './mscore',
  style_path: str = '',
  display_id: str = ':99',
  cleanup_temp_files: bool = True,
) -> PathLike:
  """
  Render a MusicXML file to PDF using MuseScore.
  
  This function converts a MusicXML file to an intermediate .mscx format,
  then renders it as a PDF file. It requires MuseScore and Xvfb (virtual display).
  
  Parameters
  ----------
  musicxml_path : PathLike
    Path to the input MusicXML file (.musicxml or .xml)
  output_pdf_path : PathLike
    Path where the output PDF should be saved
  dpi : int, optional
    Image resolution for rendering. Defaults to 300.
  script_path : str, optional
    Path to MuseScore executable. Defaults to './mscore'.
  style_path : str, optional
    Path to MuseScore style file (.mss). Defaults to empty string.
  display_id : str, optional
    Virtual display ID for Xvfb. Defaults to ':99'.
  cleanup_temp_files : bool, optional
    Whether to delete temporary .mscx file after rendering. Defaults to True.
  
  Returns
  -------
  PathLike
    Path to the output PDF file if rendering was successful.
  
  Raises
  ------
  FileNotFoundError
    If the input MusicXML file does not exist.
  Exception
    If MuseScore conversion or rendering fails.
  
  Example
  -------
  >>> render_musicxml_to_pdf(
  ...     musicxml_path='input.musicxml',
  ...     output_pdf_path='output.pdf',
  ...     script_path='/usr/bin/mscore',
  ... )
  """
  musicxml_path = Path(musicxml_path)
  output_pdf_path = Path(output_pdf_path)
  
  if not musicxml_path.exists():
    raise FileNotFoundError(f"MusicXML file not found: {musicxml_path}")
  
  # Create output directory if it doesn't exist
  output_pdf_path.parent.mkdir(parents=True, exist_ok=True)
  
  # Setup environment with audio/jack disabled
  env = os.environ.copy()
  env.update({
    'DISPLAY': display_id,
    **DEFAULT_ENV,
    # Disable Jack audio to prevent connection errors
    'JACK_NO_START_SERVER': '1',
    'JACK_NO_AUDIO_RESERVATION': '1',
    # Disable PulseAudio
    'PULSE_SERVER': '/dev/null',
    # Disable ALSA
    'ALSA_CARD': 'none',
    # Additional Qt settings for headless operation
    'QT_LOGGING_RULES': '*.debug=false;qt.qpa.*=false',
  })
  
  # Start virtual display and MuseScore
  process_configs = [
    ['Xvfb', display_id, '-screen', '0', '2560x1440x24', '-ac'],
    [script_path]
  ]
  
  processes = spawn_processes(process_configs, env)
  
  # Give Xvfb time to start up
  time.sleep(2)
  
  try:
    # Read MusicXML content
    with open(musicxml_path, 'r', encoding='utf-8') as f:
      xml_content = f.read()
    
    # Strip and prepare XML
    xml_content = strip_musicXML(xml_content)
    
    # Create temporary directory for intermediate files
    temp_dir = output_pdf_path.parent / '.temp_musicxml_render'
    temp_dir.mkdir(exist_ok=True)
    
    # Write temporary MusicXML file
    temp_xml_path = temp_dir / 'temp.musicxml'
    with open(temp_xml_path, 'w', encoding='utf-8') as f:
      f.write(xml_content)
    
    # Convert MusicXML to .mscx
    temp_mscx_path = temp_dir / 'temp.mscx'
    cmd_convert = [
      script_path,
      "-o", str(temp_mscx_path), 
      str(temp_xml_path)
    ]
    if style_path:
      cmd_convert.insert(1, "-S")
      cmd_convert.insert(2, style_path)
    
    ps = subprocess.run(
      cmd_convert, env=env,
      stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    
    if ps.returncode != 0:
      raise Exception(
        f"MusicXML to MSCX conversion failed. Command: {' '.join(cmd_convert)}\n"
        f"Return code: {ps.returncode}\n"
        f"Stderr: {ps.stderr.decode('UTF-8')}\n"
        f"Stdout: {ps.stdout.decode('UTF-8')}"
      )
    
    # Render .mscx to PDF
    render_mscx(
      mscx_path=temp_mscx_path,
      out_path=output_pdf_path,
      env=env,
      dpi=dpi,
      mscore_exec=script_path,
      style_path=style_path,
    )
    
    # Verify PDF was created
    if not output_pdf_path.exists():
      raise Exception(f"PDF rendering failed - output file not created: {output_pdf_path}")
    
    # Cleanup temporary files
    if cleanup_temp_files:
      shutil.rmtree(temp_dir, ignore_errors=True)
    
    return output_pdf_path
  
  except Exception as e:
    raise Exception(f"Failed to render MusicXML to PDF: {e}")
  
  finally:
    # Always cleanup virtual display processes
    terminate_processes(processes)