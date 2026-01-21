export PYTHONPATH=.:$PYTHONPATH
BASE_DIR=/home/dongmin/userdata/open-score-string-quartets/ossq-v2.1.0-20251029
# python3 ./scripts/detect_systems.py -d $BASE_DIR -t synthetic
# python3 ./scripts/crop_systems.py -d $BASE_DIR -t synthetic
# python3 ./scripts/resize_imgs.py -d $BASE_DIR -t 18 -p synthetic
python3 ./scripts/crop_system_partwise.py -d $BASE_DIR -t synthetic