import os
import sys
import time
from pathlib import Path
from collections import Counter, defaultdict
from operator import itemgetter
from tempfile import NamedTemporaryFile

import math
import random

import json
import csv
import strictyaml as syaml

from tqdm import tqdm
import matplotlib.pyplot as plt

import cv2
import numpy as np
import partitura as pt

from bs4 import BeautifulSoup
import requests


if __name__ == '__main__':
  data_dir = Path('data')
  
  with open(data_dir / 'scores_w_url.yaml') as f:
    metadata = syaml.load(f.read())
  
  metadata = metadata.data
  
  request_pdf_format = 'https://imslp.org/wiki/Special:ImagefromIndex/%(imslp_id)s/xe11'
  disclaimer_url_format = 'https://imslp.org/wiki/Special:IMSLPDisclaimerAccept/%(imslp_id)s'
  
  targets = { k: v for k, v in metadata.items() if not v['imslp_url'] }
  
  if len(targets.keys()) < 1:
    print('No scores to download')
    sys.exit(0)
  
  cnt = 0
  
  for mscore_id, obj in tqdm(targets.items()):
    start_time = time.time()
    
    imslp_id = obj['imslp'][1:]
    
    res = requests.get(request_pdf_format % { 'imslp_id': imslp_id })
    
    if res.status_code != 200:
      break
    
    soup = BeautifulSoup(res.text, 'lxml')
    
    if 'Disclaimer' in soup.title.string:
      res = requests.get(disclaimer_url_format % { 'imslp_id': imslp_id })
      soup = BeautifulSoup(res.text, 'lxml')
    
    if '.pdf' in res.url:
      pdf_url = res.url
    else:
      pdf_url = soup.select_one('#sm_dl_wait').get('data-id')
    
    metadata[mscore_id]['imslp_url'] = pdf_url
    
    cnt += 1
    
    if cnt > 9:
      break
    
    else:
      time.sleep( max( 30, 60 - ( time.time() - start_time ) ) )
  
  
  with open(data_dir / 'scores_w_url.yaml', 'w') as f:
    f.write(syaml.as_document(metadata).as_yaml())