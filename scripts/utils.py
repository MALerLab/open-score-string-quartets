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



####### LEGACY FUNCTIONS #######
####### NOT USED/MAINTAINED #######

def pt_load_mscx(
  filename:PathLike,
  mscore_exec:str='musescore3',
  validate:bool=False,
  force_note_ids:Union[bool,str]='keep',
):
  """
  modified function from partitura.io.musescore.load_via_musescore
  """
  if isinstance(filename, Path):
    filename = str(filename)
  
  with NamedTemporaryFile(suffix=".musicxml") as xml_fh:
    cmd = [mscore_exec, "-o", xml_fh.name, filename, "-f"]
    
    try:
      # convert MuseScore file to MusicXML
      ps = subprocess.run(
        cmd, 
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
      )
      
      if ps.returncode != 0:
        raise Exception(
          "Command {} failed with code {}. MuseScore " "error messages:\n {}"
          .format(cmd, ps.returncode, ps.stderr.decode("UTF-8"))
        )
    
    except Exception as e:
      raise Exception(
        'Executing "{}" returned  {}.'.format(" ".join(cmd), e)
      )

    score = pt.load_musicxml(
      filename=xml_fh.name,
      validate=validate,
      force_note_ids=force_note_ids,
    )
  
  return score


def pt_render_musescore(
  score_data: pt.score.ScoreLike,
  fmt:str='png',
  out:Union[PathLike,None]=None,
  dpi:Optional[int]=90,
  mscore_exec:str='musescore3'
) -> Union[list[PathLike],list[np.array],None]:
  """
  modified function from partitura.io.musescore.render_musescore
  Render a score-like object using musescore.

  Parameters
  ----------
  score_data : ScoreLike
    Score-like object to be rendered
  fmt : {'png', 'pdf'}
    Output image format
  out : Path or str or None
    'png': OPTIONAL
    'pdf': REQUIRED
  dpi : int, optional
    Image resolution. 
    This option is ignored when `fmt` is 'pdf'. 
    Defaults to 90.

  Returns
  -------
  out : 
    1. list[PathLike]: list of paths to output images if out is provided
    2. list[np.array]: list of images if out is not provided
    3. None: if no image was generated
  """
  
  assert fmt in {'png', 'pdf'}, "Unsupported output format"
  
  if fmt == 'pdf':
    assert out is not None, "Output path is required for 'pdf' format"

  with TemporaryDirectory() as tmpdir:
    xml_fh = Path(tmpdir) / "score.musicxml"
    img_fh = Path(tmpdir) / f"score.{fmt}"

    pt.save_musicxml(score_data, xml_fh)

    cmd = [
      mscore_exec,
      # "-T",
      # "10",
      "-r",
      "{}".format(int(dpi)),
      "-o",
      os.fspath(img_fh),
      os.fspath(xml_fh),
      "-f",
    ]
    try:
      ps = subprocess.run(
        cmd, 
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
      )
      
      if ps.returncode != 0:
        raise Exception(
          "Command {} failed with code {}; stdout: {}; stderr: {}"
          .format(
            cmd,
            ps.returncode,
            ps.stdout.decode("UTF-8"),
            ps.stderr.decode("UTF-8"),
          )
        )
    
    except Exception as e:
      raise Exception(
        'Executing "{}" returned  {}.'
        .format(" ".join(cmd), e),
      )
    
    if fmt == "png":
      # gether all generated image files
      img_files = list(sorted(Path(tmpdir).glob(f"*.{fmt}")))
      
      # if no image was generated
      if len(img_files) < 1:
        return None
      
      # return images if out is not provided
      if out is None:
        out_images = [ cv2.imread(i_fp) for i_fp in img_files ]
        return out_images

      # return paths of images if out is provided
      else:
        out_files = [ out/i_fp.name for i_fp in img_files ]
        for i_fp, o_fp in zip(img_files, out_files):
          # make background white
          o_i = cv2.imread(i_fp, cv2.IMREAD_UNCHANGED)
          transparent_mask = o_i[:,:,3] == 0
          o_i[transparent_mask] = [255, 255, 255, 255]
          o_i = cv2.cvtColor(o_i, cv2.COLOR_BGRA2BGR)
          cv2.imwrite(o_fp, o_i)
        return out_files
    
    elif fmt == "pdf":
      if img_fh.is_file():
        shutil.copy(img_fh, out/img_fh.name)
      else:
        return None
    
    # if no image was generated
    return None


def render_lilypond(
  musicxml_path:PathLike,
  fmt:str="png",
  out:Optional[PathLike]=None,
) -> Union[list[PathLike],list[np.array],None]:
  """
  Render a score-like object using Lilypond

  Parameters
  ----------
  musicxml_path : PathLike
  fmt : {'png', 'pdf'}
    Output image format

  Returns
  -------
  out : 
    1. list[PathLike]: list of paths to output images if out is provided
    2. list[np.array]: list of images if out is not provided
    3. None: if no image was generated
  """
  assert fmt in {'png', 'pdf'}, "Unsupported output format"
  
  if fmt == 'pdf':
    assert out is not None, "Output path is required for 'pdf' format"

  with TemporaryDirectory() as tmpdir:
    pt_xml = Path(tmpdir) / "score.xml"
    pt.save_musicxml(pt.load_musicxml(musicxml_path), pt_xml)
    
    # convert musicxml to lilypond format (use stdout pipe)
    cmd1 = ["musicxml2ly", "-o-", str(pt_xml)]
    try:
      ps1 = subprocess.run(
        cmd1, stdout=subprocess.PIPE, check=False
      )
      if ps1.returncode != 0:
        raise Exception(
          "Command {} failed with code {}".format(cmd1, ps1.returncode)
        )
    
    except Exception as e:
      raise Exception(
        'Executing "{}" returned  {}.'
        .format(" ".join(cmd1), e),
      )

    # convert lilypond format (read from pipe of ps1) to image, and save to
    # temporary filename
    cmd2 = [
      "lilypond",
      "--{}".format(fmt),
      "-dprint-pages",
      "-o{}".format(tmpdir + '/score'),
      "-",
    ]
    try:
      ps2 = subprocess.run(cmd2, input=ps1.stdout, check=False)
      
      if ps2.returncode != 0:
        raise Exception(
          "Command {} failed with following error {}".format(cmd2, ps2.stderr)
        )
    
    except Exception as e:
      print(e)
      return
    
    if fmt == "png":
      # gether all generated image files
      img_files = list(sorted(Path(tmpdir).glob(f"*.{fmt}")))
      
      # if no image was generated
      if len(img_files) < 1:
        return None
      
      # return images if out is not provided
      if out is None:
        out_images = [ cv2.imread(i_fp) for i_fp in img_files ]
        return out_images

      # return paths of images if out is provided
      else:
        out_files = [ out/i_fp.name for i_fp in img_files ]
        for i_fp, o_fp in zip(img_files, out_files):
          shutil.copy(i_fp, o_fp)
        return out_files
    
    elif fmt == "pdf":
      pdf_file, *_ = list(Path(tmpdir).glob(f"*.{fmt}"))
      
      if pdf_file.is_file():
        shutil.copy(pdf_file, out/pdf_file.name)
      else:
        return None
    
    # if no image was generated
    return None