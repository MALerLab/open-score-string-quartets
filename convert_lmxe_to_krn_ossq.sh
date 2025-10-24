export PYTHONPATH=.:$PYTHONPATH
python3 ./scripts/convert_lmxe_to_krn_ossq.py \
  -d $(pwd) \
  -r 0 \
  -v 1 \
  -c 0 \

