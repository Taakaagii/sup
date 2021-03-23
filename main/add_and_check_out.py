import sys
import time
import requests

def add_to_cart(session, item_id, size_id, style_id, task_name, screenlock):
    """
    カート追加処理
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 13_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/80.0.3987.95 Mobile/15E148 Safari/604.1",
        "Accept": "application/json",
        "Accept-Language": "ja",
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": "https://www.supremenewyork.com",
        "DNT": "1",
        "Connection": "keep-alive",
        "Referer": "https://www.supremenewyork.com/mobile/",
        "Pragma": "no-cache",
        "Cache-Control": "no-cache",
        "TE": "Trailers",
    }

    # chkを削除予定
    data = {
        "size": size_id,
        "style": style_id,
        "qty": "1"
    }
    atc_url = f"https://www.supremenewyork.com/shop/{item_id}/add.json"

    # 成功するまでチェックアウト処理をやり続ける
    while True:
        atc_response = session.post(atc_url, headers=headers, data=data)
        if atc_response.status_code == 200:
            break
        session.event.wait(timeout=1.25)

    atc_json = atc_response.json()

    # レスポンスJSONの内容を確認
    if atc_json and atc_json[0]["in_stock"]:
        with screenlock:
            print("{}: Added to Cart", task_name)
        return session, True
    return session, False

def make_checkout_parameters(session, profile, headers):
    """
    決済用のデータを作成
    """
    # ページコンテンツのデータを取得
    # checkout_page_content = session.get("https://www.supremenewyork.com/mobile/#checkout", headers=headers)

    #Cookie情報を取得
    cookie_sub = session.cookies.get_dict()["pure_cart"].split("%2C%22cookie")[0] + "%7D"
    checkout_params = {}
    checkout_params["cookie-sub"] = cookie_sub
    checkout_params["order[billing_name]"] = profile["order[billing_name]"]
    checkout_params["order[email]"] = profile["order[email]"]
    checkout_params["order[tel]"] = profile["order[tel]"]
    checkout_params["order[billing_zip]"] = profile["order[billing_zip]"]
    checkout_params["order[billing_state]"] = profile["order[billing_state]"]
    checkout_params["order[billing_city]"] = profile["order[billing_city]"]
    checkout_params["order[billing_address]"] = profile["order[billing_address]"]
    checkout_params["credit_card[type]"] = profile["credit_card[type]"]
    checkout_params["credit_card[cnb]"] = profile["credit_card[cnb]"]
    checkout_params["credit_card[month]"] = profile["credit_card[month]"]
    checkout_params["credit_card[year]"] = profile["credit_card[year]"]
    checkout_params["credit_card[vval]"] = profile["credit_card[vval]"]
    checkout_params["from_mobile"] = 1
    checkout_params["order[terms]"] = 0
    checkout_params["order[terms]"] = 1
    checkout_params["same_as_billing_address"] = 1
    checkout_params["utf8"] = profile["utf8"]
    checkout_params["store_credit_id"] = None
    checkout_params["store_address"] = 1

    # パラメータの取得ができない場合、処理を終了する
    if not checkout_params:
        sys.exit("Error with parsing checkout parameters")
    return checkout_params

def fetch_captcha(session, checkout_params, task_name, screenlock):
    """
    recaptchaの設定
    """
    with screenlock:
        print("{}: Waiting for Captcha...", task_name)

    while True:
        try:
            captcha_response = session.get("http://127.0.0.1:5000/www.supremenewyork.com/token", timeout=0.1)
            if captcha_response.status_code == 200:
                return captcha_response.text
        except requests.exceptions.Timeout:
            pass

def send_checkout_request(session, profile, delay, task_name, start_checkout_time, screenlock):
    """
    決済処理
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 13_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/80.0.3987.95 Mobile/15E148 Safari/604.1",
        "Accept": "*/*",
        "Accept-Language": "ja",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Pragma": "no-cache",
        "Cache-Control": "no-cache",
        "TE": "Trailers",
    }
    checkout_url = "https://www.supremenewyork.com/checkout.json"
    checkout_params = make_checkout_parameters(session, profile, headers)
    checkout_params["g-recaptcha-response"] = fetch_captcha(session, checkout_params, task_name, screenlock)

    with screenlock:
        print("{}: Waiting Checkout Delay...", task_name)
    session.event.wait(timeout=delay)

    while True: # keep sending checkout request until 200 status code
        checkout_request = session.post(checkout_url, headers=headers, data=checkout_params)
        if checkout_request.status_code == 200:
            total_checkout_time = round(time.time() - start_checkout_time, 2)
            with screenlock:
                print("{}: Sent Checkout Data ({} seconds)", task_name,total_checkout_time)
            return checkout_request
        session.event.wait(timeout=1.25)

def get_slug_status(session, slug):
    """
    ステータス情報の取得
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 13_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/80.0.3987.95 Mobile/15E148 Safari/604.1",
        "Accept": "*/*",
        "Accept-Language": "ja",
        "X-Requested-With": "XMLHttpRequest",
        "Connection": "keep-alive",
        "Referer": "https://www.supremenewyork.com/mobile/",
        "TE": "Trailers"
    }
    status_url = f"https://www.supremenewyork.com/checkout/{slug}/status.json"

    slug_content = session.get(status_url, headers=headers).json()
    slug_status = slug_content["status"]
    return slug_status

def display_slug_status(session, checkout_response, task_name, screenlock):
    """
    現在の商品の状況を表示
    """

    slug = checkout_response["slug"]
    while True:
        slug_status = get_slug_status(session, slug)

        with screenlock:
            if slug_status == "queued":
                print("{}: Getting Order Status", task_name)
            elif slug_status == "paid":
                print("{}: Check Email!", task_name)
                break
            elif slug_status == "failed":
                print("{}: Checkout Failed", task_name)
                return "failed"
        session.event.wait(timeout=10)

def get_order_status(session, checkout_request, task_name, screenlock):
    """
    発注状況のステータス取得
    """
    checkout_response = checkout_request.json()
    if checkout_response["status"] == "failed":
        with screenlock:
            print("{}: Checkout Failed", task_name)
        return False

    elif checkout_response["status"] == "queued":
        status = display_slug_status(session, checkout_response, task_name, screenlock)
        if status != "failed":
            return True

def checkout(session, profile, delay, task_name, start_checkout_time, screenlock):
    """
    決済処理
    """
    checkout_request = send_checkout_request(session, profile, delay, task_name, start_checkout_time, screenlock)
    if get_order_status(session, checkout_request, task_name, screenlock):
        return True