export PYTHONPATH=.:$PYTHONPATH
python3 ./scripts/convert_krn_to_musicxml_post.py \
  -d "$(pwd)"
