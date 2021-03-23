import sys
import time
import json
import requests
import threading
from main import return_item_ids, add_to_cart, checkout

class Session(requests.Session):
    """
    セッション情報の処理
    GET：商品情報やステータス、在庫情報の取得
    POST：カート格納処理や決済処理の登録
    """
    def __init__(self):
        super().__init__()

    def get(self, url, **kwargs):
        if self.event.is_set():
            sys.exit()
        return self.request('GET', url, **kwargs)

    def post(self, url, **kwargs):
        if self.event.is_set():
            sys.exit()
        return self.request('POST', url, **kwargs)

class Task(threading.Thread):
    """
    コンストラクタでタスク稼働に必要な情報を入れる
    プロキシは標準ではなしの設定となる
    """
    def __init__(self, positive_keywords, negative_keywords, category, size, color, profile_data, proxy, delay, task_name, screenlock):
        threading.Thread.__init__(self)

        self.positive_keywords = positive_keywords
        self.negative_keywords = negative_keywords
        self.category = category
        self.size = size
        self.color = color
        self.profile_data = profile_data
        self.proxy = proxy
        self.delay = delay
        self.task_name = task_name
        self.screenlock = screenlock
        self.event = threading.Event()
        self.session = Session()
        self.session.event = self.event

    def run(self):
        # set_session_proxy(self.session, self.proxy)
        run_task(
            self.session,
            self.positive_keywords,
            self.negative_keywords,
            self.category,
            self.size,
            self.color,
            self.profile_data,
            self.delay,
            self.task_name,
            self.screenlock
        )

    def stop(self):
        self.event.set()

def run_task(session, positive_keywords, negative_keywords, category, size, color, profile_data, delay, task_name, screenlock):
    """
    タスク実行
    """
    while True:
        with screenlock:
            print("{}: 検索中。。。 {}",task_name,positive_keywords)

        start_checkout_time = time.time()
        item_id, size_id, style_id = return_item_ids(session, positive_keywords, negative_keywords, category, size, color, task_name, screenlock)
        session, successful_atc = add_to_cart(session, item_id, size_id, style_id, task_name, screenlock)
        print(add_to_cart)
        if successful_atc and checkout(session, profile_data, delay, task_name, start_checkout_time, screenlock):
            break

def get_profile_data(profile_id, profiles_file):
    """
    個人情報の取得
    事前に入力しておくこと
    """
    with open(profiles_file,encoding='utf-8') as f:
        profiles = json.load(f)
    # 内包表記で個人情報のJSONの先頭配列のオブジェクトを取得する
    # ただし自身で任意につけられるprofile_idを引数で渡すのでよく意味が分からない。
    # 重複していた場合か
    index = [profiles.index(profile) for profile in profiles if profile['id'] == profile_id]

    if index:
        index = index[0]
        return profiles[index]
    else:
        return None


def create_threads(tasks_file, profiles_file):
    with open(tasks_file) as f:
        tasks = json.load(f)

    task_threads = []
    screenlock = threading.Lock()

    for task in tasks:
        task_name = task["task_name"]
        positive_keywords = task["pos_kws"]
        negative_keywords = task["neg_kws"]
        delay = task["delay"]

        category = task["category"]
        color = task["color"]
        size = task["size"]
        proxy = task["proxy"]

        profile_id = task["profile_id"]
        profile_data = get_profile_data(profile_id, profiles_file)

        if not profile_data:
            print("ERROR: 個人情報がありません。 '{}'", task_name)
        else:
            task_thread = Task(positive_keywords, negative_keywords, category, size, color, profile_data, proxy, delay, task_name, screenlock)
            task_threads.append(task_thread)
    return task_threads

def run_all(tasks_file, profiles_file):
    """
    タスクのスレッドごとに分けて実行
    """

    threads = create_threads(tasks_file, profiles_file)
    if threads:
        for t in threads:
            t.start()

    input() # Allow user to stop all tasks by entering any combination of keys
    for t in threads:
        t.stop()
    for t in threads: # t.join() # Wait for thread to terminate before handing back control
        t.join()
