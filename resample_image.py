import os
import argparse
from pathlib import Path
from operator import itemgetter

from typing import Union, List

import csv
import json
import strictyaml as syaml

import numpy as np
import cv2

from tqdm import tqdm

PathLike = Union[Path, str]


INTERPOLATION_METHODS = [
  cv2.INTER_NEAREST, 
  cv2.INTER_LINEAR, 
  cv2.INTER_CUBIC, 
  cv2.INTER_AREA, 
  cv2.INTER_LANCZOS4,
]

INTERPOLATION_METHOD_NAMES = [
  'nearest', 
  'linear', 
  'cubic', 
  'area', 
  'lanczos4', 
]

INTERPOLATION_OPTIONS = { name: method for name, method in zip(INTERPOLATION_METHOD_NAMES, INTERPOLATION_METHODS) }

HD_RES_LIST = [
  (854, 480),
  (1280, 720),
  (1920, 1080)
]

HD_RES_BY_HEIGHT = { h: (w, h) for w, h in HD_RES_LIST }
HD_RES_BY_HEIGHT[478] = HD_RES_BY_HEIGHT[480]



def resize_img_by_height(img, target_height, interpolation=cv2.INTER_LINEAR):
  # interpolation: [ None, cv2.INTER_LINEAR, cv2.INTER_NEAREST, cv2.INTER_AREA, cv2.INTER_CUBIC, cv2.INTER_LANCZOS4 ]
  
  og_h, og_w = img.shape[:2]
  
  resize_ratio = target_height / og_h
  resize_width = int(og_w * resize_ratio)
  
  return cv2.resize(img, dsize=(resize_width, target_height), interpolation=interpolation)


def resample_img(
  data_dir:Union[Path,str],
  target_height:int, 
  tags:List[str], 
  interpolation:str='linear', 
  threshold:bool=False,
  threshold_value:int=200,
  process_fn=None,
):
  
  assert interpolation is None or isinstance(INTERPOLATION_OPTIONS.get(interpolation, False), int), "interpolation should be one of followings: None, linear, nearest, cubic, area, lanczos4"
  
  interpolation = INTERPOLATION_OPTIONS.get(interpolation, cv2.INTER_LINEAR)
  
  assert isinstance(threshold, bool), "threshold should be bool type"
  
  tag_str = str(target_height) + '_' + '_'.join(tags)
  
  # path str to Path object
  if not isinstance(data_dir, Path):
    data_dir = Path(data_dir)
  
  with open(data_dir / 'metadata-mp4.csv', 'r') as f:
    video_infos = list(csv.reader(f))[1:]
  
  video_infos = [ 
    ( genre, yt_id, composer, tuple(json.loads(video_size)) ) 
    for genre, yt_id, composer, _, _, video_size, *_ in video_infos 
  ]
  
  for genre, yt_id, composer, video_size in tqdm(video_infos, desc='videos'):
    img_dir = data_dir / genre / 'segments' / composer / yt_id / 'images'
    src_dir = img_dir / 'original'
    img_paths = sorted( src_dir.glob('*.png') )
    
    save_path = img_dir / 'resampled' / tag_str
    
    if save_path.exists():
      print(f"You already have resampled data with tag {tag_str} for {composer}'s {yt_id}")
      continue

    save_path.mkdir(parents=True)
    
    w, h = video_size

    hd_w, h = HD_RES_BY_HEIGHT[h]
    pad_w = (hd_w - w) // 2
    
    target_width, _ = HD_RES_BY_HEIGHT[target_height]

    for i_p in tqdm(img_paths, desc='pieces', leave=False):
      if process_fn:
        i = process_fn( i_p, pad_w )

      else:
        i = cv2.imread( i_p )
        i = cv2.cvtColor(i, cv2.COLOR_RGB2GRAY)
        i = np.pad(i, ( (0,), (pad_w,) ), mode='constant', constant_values=0)
        
        if threshold:
          i = cv2.GaussianBlur(i, (0, 0), 0.8)
          
          assert isinstance(threshold_value, int), "threshold_value should be positive int"
          
          if not threshold_value:
            i = cv2.threshold(i, 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)[1]
            
          else:
            i = cv2.threshold(i, threshold_value, 255, cv2.THRESH_BINARY)[1]

      # i = resize_img_by_height(i, target_height, interpolation=interpolation)
      i = cv2.resize(i, dsize=(target_width, target_height), interpolation=interpolation)
      
      i_n = i_p.name
      cv2.imwrite( str(save_path / i_n), i )


def get_flattend_img_ch(tags:list[str])->Union[int,slice]:
  ch = slice(None, None)
  
  if 'gray' in tags:
    ch = 0
  
  elif 'bootleg' in tags:
    if '3' in tags:
      ch = slice(0, 3)
    
    elif '4' in tags:
      ch = slice(None, None)
  
  return ch


def resample_flattened_img(
  metadata_path:PathLike,
  data_dir:PathLike,
  target_height:int, 
  tags:List[str], 
  interpolation:str='linear', 
  threshold:bool=False,
  threshold_value:int=200,
  process_fn=None,
):
  
  assert interpolation is None or isinstance(INTERPOLATION_OPTIONS.get(interpolation, False), int), "interpolation should be one of followings: None, linear, nearest, cubic, area, lanczos4"
  
  interpolation = INTERPOLATION_OPTIONS.get(interpolation, cv2.INTER_LINEAR)
  
  assert isinstance(threshold, bool), "threshold should be bool type"
  
  tag_str = str(target_height) + '_' + '_'.join(tags)
  
  ch = get_flattend_img_ch(tags)
  
  # path str to Path object
  if not isinstance(metadata_path, Path):
    metadata_path = Path(metadata_path)
  if not isinstance(data_dir, Path):
    data_dir = Path(data_dir)
  
  assert metadata_path.exists(), f"metadata file not found: {metadata_path}"
  assert metadata_path.suffix == '.yaml', "metadata file should be yaml file"
  
  with open(metadata_path, 'r') as f:
    score_metadata = syaml.load(f.read())
  
  score_metadata = score_metadata.data
  
  score_infos = [ 
    ( mscore_id, data_dir / infos['path'], infos['pages'] )
    for mscore_id, infos in score_metadata.items()
  ][1:]
  
  resize_metadata_path = metadata_path.parent / f'flattened_{tag_str}_metadata.csv'
  resize_metadata_file = open(resize_metadata_path, 'a')
  
  for mscore_id, mscore_dir, pages in tqdm(score_infos, desc='score'):
    img_dir = mscore_dir / 'images'
    
    src_dir = img_dir / 'flattened'
    
    save_dir = img_dir / 'flattened_resampled' / tag_str
    save_dir.mkdir(parents=True, exist_ok=True)
    
    for p in tqdm(pages, desc='pages', leave=False):
      page_index, n_staff = itemgetter('page_index', 'n_staff')(p)
      
      img_filename = f'sq{mscore_id}:{page_index}.png'
      
      src_img_path = src_dir / img_filename
      tgt_img_path = save_dir / img_filename
      
      i_src = cv2.imread( src_img_path, cv2.IMREAD_UNCHANGED )
      h, w = i_src.shape[:2]
      
      resize_ratio = target_height / h
      target_width = int(w * resize_ratio)
      i_tgt = i_src[..., ch]

      if threshold and isinstance(ch, int):
        i_tgt = cv2.GaussianBlur(i_tgt, (0, 0), 0.8)
        
        assert isinstance(threshold_value, int), "threshold_value should be positive int"
        
        if not threshold_value:
          i_tgt = cv2.threshold(i_tgt, 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)[1]
        
        else:
          i_tgt = cv2.threshold(i_tgt, threshold_value, 255, cv2.THRESH_BINARY)[1]
      
      i_tgt = cv2.resize(i_tgt, dsize=(target_width, target_height), interpolation=interpolation)
      
      cv2.imwrite( tgt_img_path, i_tgt )
      print(mscore_id, page_index, target_width, target_height, n_staff, sep=',', file=resize_metadata_file)
  
  resize_metadata_file.close()


if __name__ == '__main__':
  
  parser = argparse.ArgumentParser(
    prog='Latent Score Dataset: Image Resampler',
    description='image resampler for resizing, thresholding',
  )
  
  parser.add_argument('meata_data_path', type=str)
  parser.add_argument('data_dir', type=str)
  parser.add_argument('target_height', type=int)
  parser.add_argument('--tags', nargs='+', required=True)
  parser.add_argument('--interpolation')
  parser.add_argument('--threshold', action='store_true', default=False)
  parser.add_argument('--threshold-value', type=int)
  parser.add_argument('--is-flattened', type=bool, default=False)
  
  args = parser.parse_args()
  
  print(args)
  
  if args.is_flattened:
    resample_flattened_img(
      Path(args.meata_data_path),
      Path(args.data_dir), 
      args.target_height, 
      args.tags, 
      args.interpolation, 
      args.threshold,
      args.threshold_value,
    )
    
  else:
    resample_img(
      Path(args.data_dir),
      args.target_height, 
      args.tags, 
      args.interpolation, 
      args.threshold,
      args.threshold_value,
    )