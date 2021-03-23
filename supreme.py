import os
import json
import logging
import threading
from harvester import Harvester
from main import run_all

def profiles_exist(profiles_file):
    """
    個人情報存在チェック
    """

    with open(profiles_file) as f:
        profiles = json.load(f)
    if profiles:
        return True

def tasks_exist(tasks_file):
    """
    タスクの存在チェック
    """

    with open(tasks_file) as f:
        if json.load(f):
            return True

def main():

    tasks_path = os.path.abspath("data//tasks.json")
    profiles_path = os.path.abspath("data//profiles.json")

    if not tasks_exist(tasks_path):
        print("タスクが存在しません")
    elif not profiles_exist(tasks_path):
        print("個人情報が存在しません")
    else:
        run_all(tasks_path, profiles_path)

def start_captcha_server():
    """
    recaptcha対策
    このThreadで5つまでrecaptchaトークンをためる
    Threadの書き込み競合を避けるためにロックフラグを持つこと
    """
    logging.getLogger('harvester').setLevel(logging.CRITICAL)
    harvester = Harvester()

    harvester.intercept_recaptcha_v2(
        domain='www.supremenewyork.com',
        sitekey='6LeWwRkUAAAAAOBsau7KpuC9AV-6J8mhw4AjC3Xz'
    )

    server_thread = threading.Thread(target=harvester.serve, daemon=True)
    server_thread.start()
    harvester.launch_browser()

if __name__ == "__main__":
    start_captcha_server()
    main()

    
 