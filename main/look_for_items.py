import time
import sys

def get_stock(session):
    """
    在庫確認
    """

    # モバイル版のリクエストで在庫確認
    # User-Agentは要検討
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.104 Safari/537.36",
        "Accept": "application/json",
        "Accept-Language": "ja",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "close",
        "Pragma": "no-cache",
        "Cache-Control": "no-cache",
        "Referer": "https://www.supremenewyork.com/mobile/",
        "origin": "https://www.supremenewyork.com",
        "TE": "Trailers"
    }
    url = f"https://www.supremenewyork.com/mobile_stock.json"

    response = session.get(url, headers=headers)
    if response.status_code == 200:
        """
        products_and_categoriesオブジェクトに商品のカテゴリ情報が
        フィールド情報として存在する。
        任意のカテゴリ情報の商品配列から商品IDを取得できる
        """
        return response.json()
    return None

def retrieve_item_id(session, category, positive_keywords, negative_keywords, task_name, screenlock):
    """
    商品IDを取得する
    この時、カテゴリ・商品説明から対象を絞り込む。
    商品IDが見つかるまでループする
    """

    while True:
        # stockは在庫情報のJSON
        stock = get_stock(session)
        if stock is not None:
            # 別関数に商品ID取得を委譲する
            item_id = parse_for_ids(stock, category, positive_keywords, negative_keywords, task_name, screenlock)
            if item_id is not None:
                return item_id

        session.event.wait(timeout=1)

def retrieve_style_ids(session, item_id, size, style, task_name, screenlock):
    """
    商品IDに紐づくスタイルIDを取得する
    """

    oos = False

    # 無限ループ
    while True:

        # 在庫がない場合（stock_level = 0）Out Of Stockの意味でparse_for_stylesからoosが返される
        style_return = parse_for_styles(session, item_id, size, style, task_name, screenlock)
        if style_return != "oos":
            return style_return

        if not oos:
            with screenlock:
                print("{}: Waiting for Restock", task_name)
            oos = True


def return_item_ids(session, positive_keywords, negative_keywords, category, size, style, task_name, screenlock):
    """
    カートに格納するのに必要な情報を取得しておく
    具体的には商品ID・サイズID・スタイルID
    chkはいらないと思われる
    """
    item_id = retrieve_item_id(session, category, positive_keywords, negative_keywords, task_name, screenlock)
    size_id, style_id =  retrieve_style_ids(session, item_id, size, style, task_name, screenlock)
    return item_id, size_id, style_id

def check_positive_keywords(itemname, positive_keywords):
    """
    ！！削除可能性あり！！
    商品説明の文言からどのアイテムがほしいかを峻別するための関数
    事前に商品IDがわかる場合はいらない。
    わからない場合は文書で判断する必要がある。
    ただ下記処理を通すと処理が遅くなるので事前に商品IDがわかる場合
    処理事態を削除する
    """
    for keyword in positive_keywords:
        if keyword.lower() not in itemname:
            return False
    return True

def check_negative_keywords(itemname, negative_keywords):
    """
    ！！削除可能性あり！！
    商品説明の文言からどのアイテムがほしいかを峻別するための関数
    事前に商品IDがわかる場合はいらない。
    わからない場合は文書で判断する必要がある。
    ただ下記処理を通すと処理が遅くなるので事前に商品IDがわかる場合
    処理事態を削除する
    """

    if negative_keywords:
        for keywords in negative_keywords:
            if keywords.lower() in itemname:
                return False
    return True

def find_category_lookup_table(category):
    """
    カテゴリの存在チェック
    """

    # 名前が変わったら下記のオブジェクトも変更になる
    # 外部ファイルにすべき
    categories = {
        "bags": "Bags",
        "pants": "Pants",
        "accessories": "Accessories",
        "skate": "Skate",
        "shoes": "Shoes",
        "hats": "Hats",
        "shirts": "Shirts",
        "sweatshirts": "Sweatshirts",
        "tops/sweaters": "Tops/Sweaters",
        "jackets": "Jackets",
        "t-shirts": "T-Shirts",
        "new" : "new"
    }
    value = categories.get(category.lower(), None)
    if value:
        category = categories[category.lower()]
        return category

def find_category_with_stock(stock, task_category):
    """
    定義カテゴリ状に存在するカテゴリの場合はカテゴリ情報を返す
    """

    #事前定義したカテゴリリストに入っていた場合は対象のカテゴリを返す
    category_in_list = [cat for cat in stock["products_and_categories"] if cat.lower() == task_category.lower()]
    if category_in_list:
        category = category_in_list[0]
        return category


def return_category(stock, user_category, task_name, screenlock):
    """
    カテゴリ情報が見つかったら、その情報を返す
    """

    #カテゴリ情報を発見する
    category = find_category_lookup_table(user_category)
    if category:
        return category
    else:
        category = find_category_with_stock(stock, user_category)
        if category:
            return category
        else:
            with screenlock:
                print("{}: Task exiting, category could not be found", task_name)
            sys.exit()

def parse_for_ids(stock, task_category, positive_keywords, negative_keywords, task_name, screenlock):
    """
    商品ID取得処理
    """

    # カテゴリを取得する
    category = return_category(stock, task_category, task_name, screenlock)
    for item in stock["products_and_categories"][category]:
        itemname = item["name"].lower()
        if check_positive_keywords(itemname, positive_keywords) and check_negative_keywords(itemname, negative_keywords):
            return item["id"]

def get_item_variants(session, item_id):
    """
    商品IDをもとにその商品ごとに存在する色ごとの情報で
    必要な情報を取得する
    """

    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 13_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/80.0.3987.95 Mobile/15E148 Safari/604.1",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "ja",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "close",
        "Pragma": "no-cache",
        "Cache-Control": "no-cache",
        "TE": "Trailers"
    }
    item_url = f"https://www.supremenewyork.com/shop/{item_id}.json"

    response = session.get(item_url, headers=headers)
    if response.status_code == 200:
        return response.json()

def parse_for_styles(session, item_id, size, style, task_name, screenlock):
    """
    カートに入れるために必要な情報を返す
    chkは多分いらないので削除対象
    """

    item_variants = get_item_variants(session, item_id)
    for stylename in item_variants["styles"]:
        if stylename["name"].lower() in style.lower():
            for itemsize in stylename["sizes"]:
                if itemsize["name"].lower() == size.lower():
                    if itemsize["stock_level"] != 0:
                        return itemsize["id"], stylename["id"]
                    else:
                        session.event.wait(timeout=0.75)
                        return "oos"
    with screenlock:
        print("{}: Task exiting, could not find style or size", task_name)
    sys.exit()