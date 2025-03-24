python -m rattq.baseline.nl2q_simple_zero_shot --debug --result_dir output/test1/
python -m rattq.evaluate --result_dir output/test1/
python -m rattq.baseline.nl2q_simple_zero_shot --debug --result_dir output/test/ -n 3
python -m rattq.evaluate --result_dir output/test/
