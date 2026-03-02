## tee vigade_log tühjaks
## genereeri random_testcased.csv
python generate_random_testcases.py
## kasuta testcase programmis
streamlit run run_app_fixed.py
## genereeri random_testcases_with_expected.csv
python fill_expected_topk.py
## genereeri testjuhtumid.xlsx
python build_testjuhtumid_from_log.py