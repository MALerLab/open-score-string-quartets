import os
import subprocess
from typing import Union, Optional
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

import strictyaml as syaml

from tqdm import tqdm

import cv2
import numpy as np

PathLike = Union[Path, str]


def render_musescore(
  mscore_path:Union[PathLike,None],
  fmt:str='png',
  out:PathLike=None,
  dpi:Optional[int]=90,
  mscore_exec:str='musescore3'
) -> Union[list[PathLike],list[np.array],None]:
  """
  modified function from partitura.io.musescore.render_musescore
  Render a score-like object using musescore.

  Parameters
  ----------
  mscore_path : PathLike or None
    MuseScore file path to be rendered
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
    img_fh = Path(tmpdir) / f"score.{fmt}"
    
    cmd = [
      mscore_exec,
      # "-T",
      # "10",
      "-r",
      "{}".format(int(dpi)),
      "-o",
      os.fspath(img_fh),
      os.fspath(mscore_path),
      "-f",
    ]
    try:
      ps = subprocess.run(
        cmd, 
        stdout=subprocess.PIPE, stderr=subprocess.PIPE
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
        out_files = [ 
          out / f'{mscore_path.stem}:{str(int(i_fp.stem.split("-")[-1])).zfill(4)}.png'
          for i_fp in img_files 
        ]
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


if __name__ == '__main__':
  root_dir = Path(os.getcwd())
  data_dir = root_dir / 'data'
  score_dir = root_dir / 'scores'
  
  print('data_dir:', data_dir)
  print('score_dir:', score_dir)
  
  # load metadata
  with open(data_dir / 'scores.yaml') as f:
    score_metadata = syaml.load(f.read())

  score_metadata = score_metadata.data
  
  # mscore_id = "7362818"
  mscore_id = "7300376"
  mscore_data = [ dict( mscore_id=mscore_id, **score_metadata[mscore_id] ) ]

  # mscore_data = [ dict( mscore_id=mscore_id, **obj ) for mscore_id, obj in score_metadata.items() ]
  
  # render MuseScore files
  for d in tqdm(mscore_data):
    mscore_dir = score_dir / d['path']
    mscore_path = mscore_dir / f"sq{d['mscore_id']}.mscx"
    
    mscore_out_dir = mscore_dir / 'images' / 'original'
    
    # if mscore_out_dir.is_dir():
    #   continue
    
    mscore_out_dir.mkdir(parents=True, exist_ok=True)

    render_musescore(
      mscore_path,
      fmt='png',
      out=mscore_out_dir,
      dpi=300,
    )