import os
import sys
import json


def write_language_cache(language):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, ".cache_lang")
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(language)
        print('write language to .cache_lang')
    except Exception as e:
        print(f'write language error: {str(e)}')


def run_python(param_json_string):
    #param_json_string: {'command': 'write_language_cache', 'params': ['es-MX']}
    print(f"receive param from js: {param_json_string}")
    try:
        param = json.loads(param_json_string)
        print(f"receive param from js json:: {param}")
        if param['command'] == 'write_language_cache':
            language_code = param['params'][0]
            write_language_cache(language_code)

        result = {
            "success": True,
            "code": 0
        }
        return json.dumps(result, indent=4)
    except Exception as e:
        # 异常处理代码
        print(f"An error occurred: {e}")
        result = {
            "success": False,
            "code": -1,
            "message": f"An error occurred: {e}"
        }
        return json.dumps(result, indent=4)
