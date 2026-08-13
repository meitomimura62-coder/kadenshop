from bottle import Bottle, run, template, request, redirect, response, HTTPResponse, static_file
import base64
import hashlib
import hmac
import os
import time
import pymysql
import json
import urllib.parse
import html
import unicodedata
import traceback

app = Bottle()


def page_template(title: str, content: str, nav_html: str = '', hide_order_history_button: bool = False, hide_home_button: bool = False, hide_product_list_button: bool = False, hide_cart_button: bool = False) -> str:
    # Build header buttons component and remove duplicates from nav_html
    try:
        buttons_html = header_buttons_html(hide_order_history_button=hide_order_history_button, hide_home_button=hide_home_button, hide_product_list_button=hide_product_list_button, hide_cart_button=hide_cart_button)
    except Exception:
        buttons_html = ''

    # Remove moved buttons from nav_html to avoid duplicates
    try:
        # remove details dropdown if present
        if '<details class="nav-dropdown"' in nav_html:
            start = nav_html.find('<details class="nav-dropdown"')
            end = nav_html.find('</details>', start)
            if start != -1 and end != -1:
                nav_html = nav_html[:start] + nav_html[end+len('</details>'):]
        # remove individual anchors
        for frag in ['<a class="button" href="/">ホーム</a>', '<a class="button" href="/products">商品一覧</a>', '<a class="button" href="/cart">カートを見る</a>', '<a class="button" href="/orders">注文履歴</a>', '<a class="button" href="/logout">ログアウト</a>']:
            nav_html = nav_html.replace(frag, '')
    except Exception:
        pass

    return template("""
    <!doctype html>
    <html lang="ja">
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>{{title}}</title>
      <style>
        body { margin:0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background:#f3f4f6; color:#111827; }
        .page { max-width: 1040px; margin: 0 auto; padding: 24px; }
        header { position: sticky; top: 0; z-index: 20; background: #f3f4f6; padding: 16px 0; display:flex; justify-content:space-between; align-items:center; gap:16px; flex-wrap:wrap; border-bottom: 1px solid rgba(148,163,184,0.2); }
        .header-nav { display:flex; flex-wrap:wrap; gap:12px; margin-top: 10px; width: 100%; justify-content:space-between; align-items:center; }
        .header-nav .nav-left, .header-nav .nav-right { display:flex; flex-wrap:wrap; gap:12px; align-items:center; }
        .header-nav .nav-right { justify-content:flex-end; }
        .header-nav .button { margin:0; }
        h1 { margin: 0; font-size: 2rem; letter-spacing: -0.03em; }
        p, li { line-height: 1.7; }
        .card { background:#ffffff; border:1px solid #e5e7eb; border-radius:20px; padding:24px; box-shadow:0 12px 30px rgba(15,23,42,0.08); }
        .button { display:inline-flex; align-items:center; justify-content:center; min-width: 120px; min-height: 48px; padding:0.85rem 1.4rem; border-radius:999px; background:#2563eb; color:#ffffff; text-decoration:none; font-weight:600; transition: background 0.2s ease; border:none; cursor:pointer; white-space: nowrap; box-sizing: border-box; }
        .button:hover { background:#1d4ed8; }
        .nav-dropdown { position: relative; display:inline-block; }
        .nav-dropdown summary { list-style:none; cursor:pointer; }
        .nav-dropdown summary::-webkit-details-marker { display:none; }
        .dropdown-menu { position:absolute; top:calc(100% + 8px); right:0; display:none; min-width:220px; flex-direction:column; gap:8px; padding:10px; background:#ffffff; border:1px solid #e5e7eb; border-radius:14px; box-shadow:0 12px 30px rgba(15,23,42,0.12); z-index:30; }
        .nav-dropdown[open] .dropdown-menu { display:flex; }
        .dropdown-menu .button { display:inline-flex; width:100%; min-width:0; min-height:48px; padding:0.85rem 1.4rem; box-sizing:border-box; justify-content:center; border-radius:999px; margin-left:0; }
        .dropdown-menu .button + .button { margin-left: 0; }
                .header-top { display:flex; justify-content:flex-end; gap:12px; width:100%; margin-bottom:8px; }
        .button-cart { display:inline-flex; align-items:center; gap:8px; padding:0.6rem 0.9rem; border-radius:12px; background:#111827; color:#ffffff; font-weight:700; border:none; cursor:pointer; }
        .button-cart svg { width:18px; height:18px; display:block; }
            .button-cart svg { width:18px; height:18px; display:block; pointer-events:none; }
        .button-cart:disabled, .button-cart[disabled] { opacity:0.5; cursor:not-allowed; }
        .button-danger { background:#dc2626; }
        .button-danger:hover { background:#b91c1c; }
        .link-list { display:flex; flex-wrap:wrap; gap: 12px; list-style:none; padding:0; margin:0; }
        .link-list li { margin:0; }
        .form-grid { display:grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-top: 18px; }
        .field { display:flex; flex-direction:column; }
        .field label { margin-bottom: 6px; font-size: 0.95rem; font-weight: 600; color:#334155; }
        .field input, .field select { border:1px solid #d1d5db; border-radius:12px; padding:0.85rem 1rem; background:#f9fafb; font-size:0.95rem; color:#111827; }
        .field input:focus, .field select:focus { outline:none; border-color:#2563eb; box-shadow:0 0 0 3px rgba(37,99,235,0.15); }
        .grid-actions { display:flex; flex-wrap:wrap; gap:12px; align-items:center; margin-top:18px; }
        .recommend-grid { display:grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-top: 24px; }
        .recommend-card { border:1px solid #e5e7eb; border-radius:20px; overflow:hidden; background:#ffffff; box-shadow:0 10px 24px rgba(15,23,42,0.06); }
        .recommend-card img { width:100%; height:180px; object-fit:cover; display:block; }
        .recommend-card-body { padding:16px; }
        .recommend-card-title { margin:0 0 10px; font-size:1rem; font-weight:700; color:#111827; }
        .recommend-card-text { margin:0 0 12px; color:#475569; line-height:1.5; min-height:44px; }
        .recommend-card-price { font-size:1rem; font-weight:700; color:#111827; }
        .alert { padding:16px; border-radius:14px; margin-bottom:18px; }
        .alert-success { background:#ecfdf5; border:1px solid #a7f3d0; color:#166534; }
        .alert-error { background:#fef2f2; border:1px solid #fecaca; color:#991b1b; }
        .table-wrap { overflow-x:auto; margin-top: 18px; }
        table { width:100%; border-collapse:collapse; min-width: 720px; }
        th, td { padding:14px 16px; border:1px solid #e5e7eb; text-align:left; vertical-align:top; }
        .col-name { width: 260px; min-width: 220px; }
        .col-price { width: 160px; min-width: 160px; }
        th { background:#f9fafb; font-weight:700; color:#111827; }
        tr:nth-child(even) { background:#f8fafc; }
        tr:hover { background:#eef2ff; }
        td { word-break: break-word; }
        .note { margin-top: 16px; color:#475569; }
        .error-box { background:#fdf2f8; border:1px solid #fbcfe8; color:#9d174d; padding:16px; border-radius:14px; }
        a { color:#2563eb; text-decoration:none; }
        a:hover { text-decoration:underline; }
      </style>
    </head>
    <body>
      <div class="page">
                <header>
                    <div class="header-top">{{!buttons_html}}</div>
                    <div>
                        <h1>{{title}}</h1>
                        {{!nav_html}}
                    </div>
                </header>
        <div class="card">{{!content}}</div>
      </div>
    </body>
    </html>
    """, title=title, content=content, nav_html=nav_html, buttons_html=buttons_html)


def admin_nav_html() -> str:
    return """
            <nav class="header-nav">
                <div class="nav-left">
                    <a class="button" href="/">ホーム</a>
                    <a class="button" href="/products">商品一覧</a>
                </div>
        <div class="nav-right">
          <a class="button" href="/admin/products">商品管理</a>
          <a class="button" href="/admin/users">ユーザー管理</a>
          <a class="button" href="/cart">カートを見る</a>
          <a class="button" href="/orders">注文履歴</a>
          <a class="button" href="/logout">ログアウト</a>
        </div>
      </nav>
    """


def header_buttons_html(hide_order_history_button: bool = False, hide_home_button: bool = False, hide_product_list_button: bool = False, hide_cart_button: bool = False) -> str:
    """Return HTML for the top header buttons, including ホーム and common actions."""
    user = get_current_user()
    parts = []
    if not hide_home_button:
        parts.append('<a class="button" href="/">ホーム</a>')
    if not hide_product_list_button:
        parts.append('<a class="button" href="/products">商品一覧</a>')
    if not hide_cart_button:
        parts.append('<a class="button" href="/cart">カートを見る</a>')
    if not hide_order_history_button:
        parts.append('<a class="button" href="/orders">注文履歴</a>')
    if user:
        parts.append('<a class="button" href="/logout">ログアウト</a>')
    else:
        parts.append('<details class="nav-dropdown"><summary class="button">ログイン/新規ユーザー登録</summary><div class="dropdown-menu"><a class="button" href="/login">ログイン</a><a class="button" href="/register">新規ユーザー登録</a></div></details>')
    return '\n'.join(parts)


def has_admin_user() -> bool:
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1 FROM users WHERE role = 'admin' LIMIT 1")
            result = cursor.fetchone()
        conn.close()
        return bool(result)
    except Exception:
        return False


def build_nav_html() -> str:
    user = get_current_user()
    if user:
        if user.get('role') == 'admin':
            return admin_nav_html()
        return """
                    <nav class="header-nav">
                        <div class="nav-left">
                            <a class="button" href="/">ホーム</a>
                            <a class="button" href="/products">商品一覧</a>
                        </div>
            <div class="nav-right">
              <a class="button" href="/cart">カートを見る</a>
              <a class="button" href="/orders">注文履歴</a>
              <a class="button" href="/logout">ログアウト</a>
            </div>
          </nav>
        """

    return """
            <nav class="header-nav">
                <div class="nav-left">
                    <a class="button" href="/">ホーム</a>
                    <a class="button" href="/products">商品一覧</a>
                </div>
        <div class="nav-right">
          <a class="button" href="/cart">カートを見る</a>
          <a class="button" href="/orders">注文履歴</a>
          <details class="nav-dropdown">
            <summary class="button">ログイン/新規ユーザー登録</summary>
            <div class="dropdown-menu">
              <a class="button" href="/login">ログイン</a>
              <a class="button" href="/register">新規ユーザー登録
            </div>
          </details>
        </div>
      </nav>
    """


def get_connection():
    return pymysql.connect(
        host=os.getenv("DB_HOST", "db"),
        port=int(os.getenv("DB_PORT", 3306)),
        database=os.getenv("DB_NAME", "app"),
        user=os.getenv("DB_USER", "app"),
        password=os.getenv("DB_PASS", "apppass"),
        charset="utf8mb4",
        use_unicode=True,
        init_command="SET NAMES utf8mb4",
        cursorclass=pymysql.cursors.DictCursor
    )


def ensure_orders_user_id_column(conn):
    with conn.cursor() as cursor:
        cursor.execute("SHOW COLUMNS FROM orders LIKE 'user_id'")
        if cursor.fetchone():
            return
        cursor.execute("ALTER TABLE orders ADD COLUMN user_id BIGINT UNSIGNED NULL AFTER customer_name")
        cursor.execute("ALTER TABLE orders ADD INDEX idx_orders_user_created (user_id, created_at)")
        cursor.execute("ALTER TABLE orders ADD CONSTRAINT fk_orders_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON UPDATE CASCADE ON DELETE SET NULL")
        conn.commit()


SESSION_COOKIE_NAME = "app_session"
SESSION_EXPIRES_SECONDS = 7 * 24 * 3600
APP_SECRET_KEY = os.getenv("APP_SECRET_KEY", "change-me-please")


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.sha256(salt + password.encode("utf-8")).hexdigest()
    return f"sha256${salt.hex()}${digest}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        scheme, salt_hex, digest = password_hash.split("$", 2)
        if scheme != "sha256":
            return False
        salt = bytes.fromhex(salt_hex)
        computed = hashlib.sha256(salt + password.encode("utf-8")).hexdigest()
        return hmac.compare_digest(computed, digest)
    except Exception:
        return False


def create_session_cookie(user_id: int) -> str:
    expires = str(int(time.time()) + SESSION_EXPIRES_SECONDS)
    payload = f"{user_id}:{expires}"
    signature = hmac.new(APP_SECRET_KEY.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload}:{signature}"


def verify_session_cookie(cookie_value: str):
    try:
        user_id, expires, signature = cookie_value.split(":", 2)
        payload = f"{user_id}:{expires}"
        expected = hmac.new(APP_SECRET_KEY.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, signature):
            return None
        if int(expires) < int(time.time()):
            return None
        return int(user_id)
    except Exception:
        return None


def get_current_user():
    session_value = request.get_cookie(SESSION_COOKIE_NAME)
    if not session_value:
        return None
    user_id = verify_session_cookie(session_value)
    if user_id is None:
        return None
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT user_id, name, email, role FROM users WHERE user_id = %s", (user_id,))
            user = cursor.fetchone()
        conn.close()
        return user
    except Exception:
        return None


def login_user(user_id: int, response_obj=None) -> None:
    cookie_value = create_session_cookie(user_id)
    if response_obj is not None:
        response_obj.set_cookie(SESSION_COOKIE_NAME, cookie_value, path="/", httponly=True, secure=False, max_age=SESSION_EXPIRES_SECONDS)
    else:
        response.set_cookie(SESSION_COOKIE_NAME, cookie_value, path="/", httponly=True, secure=False, max_age=SESSION_EXPIRES_SECONDS)


def redirect_with_session(location: str, user_id: int) -> HTTPResponse:
    resp = HTTPResponse(status=303, headers={'Location': location})
    login_user(user_id, response_obj=resp)
    return resp


def logout_user(response_obj=None) -> None:
    if response_obj is not None:
        response_obj.delete_cookie(SESSION_COOKIE_NAME, path="/")
    else:
        response.delete_cookie(SESSION_COOKIE_NAME, path="/")


@app.hook('before_request')
def require_admin_for_admin_paths():
    if request.path.startswith('/admin/') and request.path not in ('/login', '/logout', '/register'):
        user = get_current_user()
        if not user or user.get('role') != 'admin':
            raise HTTPResponse(status=303, headers={'Location': '/login'})


def fix_mojibake(s: str) -> str:
    """Fix mojibake when UTF-8 bytes were decoded as Latin-1."""
    if not isinstance(s, str):
        return s
    try:
        # Reinterpret bytes as UTF-8 when they were wrongly decoded as Latin-1.
        return s.encode('latin-1').decode('utf-8')
    except Exception:
        return s


def product_image_url(product_id: int, name: str = '') -> str:
    # Prefer a local image named as the product ID (e.g. 123.jpg) in public/images.
    # Check web app `web/public/images` first, then repository-level `public/images`.
    images_dir_app = os.path.normpath(os.path.join(os.path.dirname(__file__), 'public', 'images'))
    images_dir_root = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'public', 'images'))
    try:
        # First, check both locations for an image named with the product ID.
        for images_dir in (images_dir_app, images_dir_root):
            if os.path.isdir(images_dir):
                for ext in ('.jpg', '.jpeg', '.png', '.webp'):
                    candidate = f"{product_id}{ext}"
                    candidate_path = os.path.join(images_dir, candidate)
                    if os.path.exists(candidate_path):
                        return '/images/' + urllib.parse.quote(candidate)

        # Next, check both locations for the legacy specific image `4k_tv.jpg`.
        for images_dir in (images_dir_app, images_dir_root):
            specific = os.path.join(images_dir, '4k_tv.jpg')
            if os.path.exists(specific):
                return '/images/' + urllib.parse.quote('4k_tv.jpg')

        # If product name mentions 4K, pick any image from either folder.
        if name and '4K' in name:
            for images_dir in (images_dir_app, images_dir_root):
                if os.path.isdir(images_dir):
                    for fn in os.listdir(images_dir):
                        if fn.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                            return '/images/' + urllib.parse.quote(fn)
    except Exception:
        pass

    # Final fallback: placeholder with product name
    return f"https://placehold.co/360x240?text={urllib.parse.quote(name or str(product_id))}&font=roboto&bg=edf2f7&fg=111827"


@app.route('/images/<filename:path>')
def serve_image(filename):
    # Serve image files: try web app's public/images first (only if the file exists),
    # then fall back to repository-level public/images.
    images_dir_app = os.path.normpath(os.path.join(os.path.dirname(__file__), 'public', 'images'))
    images_dir_root = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'public', 'images'))
    app_path = os.path.join(images_dir_app, filename)
    root_path = os.path.join(images_dir_root, filename)
    if os.path.isdir(images_dir_app) and os.path.exists(app_path):
        return static_file(filename, root=images_dir_app)
    if os.path.isdir(images_dir_root) and os.path.exists(root_path):
        return static_file(filename, root=images_dir_root)
    return HTTPResponse(status=404, body='Not Found')


@app.route("/")
def index():
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT product_id, name, description, price, stock FROM products ORDER BY product_id LIMIT 3")
            recommended = cursor.fetchall()
        conn.close()
    except Exception:
        recommended = []

    recommend_html = ''
    if recommended:
        cards = ''
        for product in recommended:
            stock_label = f"在庫 {product['stock']}" if product['stock'] > 0 else '<strong>在庫がありません</strong>'
            cards += f"""
                <article class=\"recommend-card\">
                  <a href=\"/product/{product['product_id']}\" style=\"color:inherit; text-decoration:none; display:block;\">
                    <img src=\"{product_image_url(product['product_id'], product['name'])}\" alt=\"{product['name']}\" />
                    <div class=\"recommend-card-body\">
                      <h2 class=\"recommend-card-title\">{product['name']}</h2>
                      <p class=\"recommend-card-text\">{product['description'] or '説明がありません'}</p>
                      <p class=\"recommend-card-price\">{format_currency(product['price'])}</p>
                      <p>{stock_label}</p>
                    </div>
                  </a>
                </article>
            """
        recommend_html = f"""
            <section>
              <h2>おすすめ商品</h2>
              <div class=\"recommend-grid\">{cards}</div>
            </section>
        """

    status = request.query.get('status', '').strip()
    alert_html = ''
    if status == 'logged_in':
            alert_html = '<div class="alert alert-success">ログインに成功しました</div>'
    elif status == 'logged_out':
            alert_html = '<div class="alert alert-success">ログアウトしました</div>'
    content = f"""
    {alert_html}
    <p>おすすめ商品を以下に表示します。</p>
    {recommend_html}
    """
    nav_html = build_nav_html()
    # If the home link was duplicated, remove the extra copy.
    nav_html = nav_html.replace('<a class="button" href="/">ホーム</a>', '')
    # If the products link appears twice, keep only the first one.
    prod_link = '<a class="button" href="/products">商品一覧</a>'
    try:
        if nav_html.count(prod_link) > 1:
            first_idx = nav_html.find(prod_link)
            nav_html = nav_html[:first_idx+len(prod_link)] + nav_html[first_idx+len(prod_link):].replace(prod_link, '')
    except Exception:
        pass
    return page_template("ショップホーム", content, nav_html=nav_html, hide_order_history_button=False, hide_home_button=True)


@app.route("/product/<product_id:int>")
def product_detail(product_id):
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT product_id, name, description, price, stock FROM products WHERE product_id = %s", (product_id,))
            product = cursor.fetchone()
        conn.close()

        if not product:
            raise ValueError('指定された商品が見つかりません')

        status = request.query.get('status', '').strip()
        alert_html = ''
        if status == 'added':
            alert_html = '<div class="alert alert-success">カートに追加しました</div>'

        stock_label = f"在庫 {product['stock']}" if product['stock'] > 0 else '<strong>在庫がありません</strong>'
        disabled_attr = 'disabled' if product['stock'] == 0 else ''
        content = f"""
            {alert_html}
            <div class=\"recommend-card\" style=\"max-width:760px; margin:0 auto;\">
            <div class=\"recommend-card\" style=\"max-width:760px; margin:0 auto;\">
              <img src=\"{product_image_url(product['product_id'], product['name'])}\" alt=\"{product['name']}\" />
              <div class=\"recommend-card-body\">
                <h2 class=\"recommend-card-title\">{product['name']}</h2>
                <p class=\"recommend-card-text\">{product['description'] or '商品説明がありません'}</p>
                <p class=\"recommend-card-price\">{format_currency(product['price'])}</p>
                <p>{stock_label}</p>
                <form action=\"/cart/add\" method=\"post\" style=\"margin-top:16px; display:flex; gap:12px; align-items:center; flex-wrap:wrap;\">
                  <input type=\"hidden\" name=\"product_id\" value=\"{product['product_id']}\" />
                  <input type=\"hidden\" name=\"return_to\" value=\"/product/{product['product_id']}\" />
                                         <input type=\"number\" name=\"quantity\" min=\"1\" max=\"{product['stock']}\" value=\"1\" style=\"width:80px; padding:0.6rem 0.8rem; border:1px solid #d1d5db; border-radius:12px; background:#f9fafb;\" {disabled_attr} />
                                                                                 <button class=\"button-cart\" type=\"submit\" {disabled_attr} aria-label=\"カートに追加\"><svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.8\" stroke-linecap=\"round\" stroke-linejoin=\"round\" aria-hidden=\"true\"><path d=\"M6 6h14l-1.5 9h-11z\"/><circle cx=\"9\" cy=\"20\" r=\"1.25\"/><circle cx=\"18\" cy=\"20\" r=\"1.25\"/></svg><span>カートに追加</span></button>
                </form>
              </div>
            </div>
        """
        return page_template(product['name'], content, nav_html=build_nav_html())
    except Exception as e:
        content = f"""
            <div class=\"error-box\">商品詳細の読み込み中にエラーが発生しました。</div>
            <pre>{str(e)}</pre>
            <p><a class=\"button\" href=\"/products\">商品一覧へ</a></p>
        """
        return page_template("エラー", content)


@app.route("/db-test")
def db_test():
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT NOW() AS current_time")
            result = cursor.fetchone()
        conn.close()

        content = f"""
            <p>MySQL に接続できました</p>
            <p><strong>現在時刻:</strong> {result['current_time']}</p>
            <p><a class=\"button\" href=\"/\">ホームへ</a></p>
        """
        return page_template("DB接続確認", content, nav_html=build_nav_html())
    except Exception as e:
        content = f"""
            <div class=\"error-box\">DB 接続時にエラーが発生しました。</div>
            <pre>{str(e)}</pre>
            <p><a class=\"button\" href=\"/\">ホームへ</a></p>
        """
        return page_template("DB接続エラー", content, nav_html=build_nav_html())


def format_currency(value):
    if value is None:
        return "\0"
    return f"\{float(value):,.0f}"


def get_cart_items(conn):
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT c.cart_id, c.product_id, c.quantity,
                   p.name, p.description, p.price, p.stock
            FROM cart c
            JOIN products p ON p.product_id = c.product_id
            ORDER BY c.cart_id
            """
        )
        return cursor.fetchall()


@app.route("/products")
def product_list():
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT product_id, name, description, price, stock FROM products ORDER BY product_id")
            products = cursor.fetchall()
        conn.close()

        status = request.query.get('status', '').strip()
        alert_html = ''
        if status == 'added':
            alert_html = '<div class="alert alert-success">商品をカートに追加しました</div>'

        cards = ''
        for product in products:
            stock_label = f"在庫 {product['stock']}" if product['stock'] > 0 else '<strong>在庫がありません</strong>'
            button_disabled = 'disabled' if product['stock'] == 0 else ''
            quantity_input = (
                f"<input type=\"number\" name=\"quantity\" min=\"1\" max=\"{product['stock']}\" value=\"1\" style=\"width:70px; padding:0.6rem 0.8rem; border:1px solid #d1d5db; border-radius:12px; background:#f9fafb;\" {button_disabled} />"
                if product['stock'] > 0 else ''
            )
            cards += f"""
                <article class=\"recommend-card\">
                  <a href=\"/product/{product['product_id']}\" style=\"color:inherit; text-decoration:none; display:block;\">
                    <img src=\"{product_image_url(product['product_id'], product['name'])}\" alt=\"{product['name']}\" />
                  </a>
                  <div class=\"recommend-card-body\">
                    <h2 class=\"recommend-card-title\">{product['name']}</h2>
                    <p class=\"recommend-card-text\">{product['description'] or '商品の説明はありません'}</p>
                    <p class=\"recommend-card-price\">{format_currency(product['price'])}</p>
                    <p>{stock_label}</p>

                  </div>
                </article>
            """

        content = f"""
            <p>商品詳細を確認し、購入数量を入力のうえカートに追加してください。</p>
            {alert_html}
            <div class=\"recommend-grid\">{cards}</div>
        """
        return page_template("商品一覧", content, nav_html=build_nav_html(), hide_home_button=False, hide_order_history_button=False, hide_product_list_button=True)
    except Exception as e:
        content = f"""
            <div class=\"error-box\">商品一覧の読み込み中にエラーが発生しました。</div>
            <pre>{str(e)}</pre>
            <p><a class=\"button\" href=\"/\">戻る</a></p>
        """
        return page_template("エラー", content)


@app.route("/cart")
def cart_view():
    try:
        conn = get_connection()
        cart_items = get_cart_items(conn)
        conn.close()

        if not cart_items:
            content = """
                <p>カートに商品がありません</p>
                <div class="grid-actions">
                  <a class="button" href="/products">商品一覧へ</a>
                  <a class="button" href="/">ホームへ</a>
                </div>
            """
            return page_template("カート", content)

        total_amount = sum(item['price'] * item['quantity'] for item in cart_items)
        rows_html = ''
        for item in cart_items:
            rows_html += f"""
                <tr>
                  <td class="col-name">{item['name']}</td>
                  <td class="col-price">{format_currency(item['price'])}</td>
                  <td>
                    <form action=\"/cart/update\" method=\"post\" style=\"display:flex; align-items:center; gap:8px;\">
                      <input type=\"hidden\" name=\"cart_id\" value=\"{item['cart_id']}\">
                      <input type=\"number\" name=\"quantity\" min=\"1\" max=\"{item['stock']}\" value=\"{item['quantity']}\" style=\"width:70px; padding:0.6rem 0.8rem; border:1px solid #d1d5db; border-radius:12px; background:#f9fafb;\">
                      <button class=\"button\" type=\"submit\">更新</button>
                    </form>
                  </td>
                  <td>{format_currency(item['price'] * item['quantity'])}</td>
                  <td>
                    <form action=\"/cart/update\" method=\"post\" onsubmit=\"return confirm('この商品をカートから削除します。よろしいですか？');\">
                      <input type=\"hidden\" name=\"cart_id\" value=\"{item['cart_id']}\">
                      <input type=\"hidden\" name=\"remove\" value=\"1\">
                      <button class=\"button button-danger\" type=\"submit\">削除</button>
                    </form>
                  </td>
                </tr>
            """

        content = f"""
            <p>カート内の商品を確認し、数量を変更または削除できます。</p>
            <div class=\"table-wrap\">
              <table>
                <thead>
                  <tr>
                    <th class="col-name">商品名</th>
                    <th class="col-price">価格</th>
                    <th>数量</th>
                    <th>小計</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  {rows_html}
                </tbody>
              </table>
            </div>
            <p><strong>合計金額:</strong> {format_currency(total_amount)}</p>
            <form action=\"/order/create\" method=\"post\" style=\"margin-top:18px;\">
              <div class=\"grid-actions\">
                <button class=\"button\" type=\"submit\">注文を確定する</button>
              </div>
            </form>
        """
        return page_template("カート", content, nav_html=build_nav_html(), hide_cart_button=True)
    except Exception as e:
        content = f"""
            <div class=\"error-box\">カートの読み込み中にエラーが発生しました。</div>
            <pre>{str(e)}</pre>
            <p><a class=\"button\" href=\"/\">ホームへ</a></p>
        """
        return page_template("エラー", content)


@app.route("/cart/add", method="POST")
def cart_add():
    try:
        product_id = int(request.forms.get('product_id') or 0)
        quantity = int(request.forms.get('quantity') or 1)
        if quantity < 1:
            quantity = 1

        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT product_id, name, description, price, stock FROM products WHERE product_id = %s", (product_id,))
            product = cursor.fetchone()
            if not product:
                raise ValueError('対象の商品が見つかりません')
            if product['stock'] <= 0:
                raise ValueError('在庫がありません')
            if quantity > product['stock']:
                quantity = product['stock']

            cursor.execute("SELECT * FROM cart WHERE product_id = %s", (product_id,))
            cart_item = cursor.fetchone()
            if cart_item:
                new_quantity = cart_item['quantity'] + quantity
                if new_quantity > product['stock']:
                    new_quantity = product['stock']
                cursor.execute("UPDATE cart SET quantity = %s WHERE cart_id = %s", (new_quantity, cart_item['cart_id']))
            else:
                cursor.execute("INSERT INTO cart (product_id, quantity) VALUES (%s, %s)", (product_id, quantity))
            conn.commit()
        conn.close()

        return_to = request.forms.get('return_to') or request.headers.get('Referer', '')
        if not return_to:
            return_to = '/products'

        if '?' in return_to:
            return HTTPResponse(status=303, headers={'Location': f"{return_to}&status=added"})
        return HTTPResponse(status=303, headers={'Location': f"{return_to}?status=added"})
    except HTTPResponse:
        raise
    except Exception as e:
        content = f"""
            <div class=\"error-box\">カート追加中にエラーが発生しました。</div>
            <pre>{str(e)}</pre>
            <p><a class=\"button\" href=\"/products\">商品一覧へ</a></p>
        """
        return page_template("エラー", content)
@app.route("/cart/update", method="POST")
def cart_update():
    try:
        cart_id = int(request.forms.get('cart_id') or 0)
        remove = request.forms.get('remove')

        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM cart WHERE cart_id = %s", (cart_id,))
            cart_item = cursor.fetchone()
            if not cart_item:
                raise ValueError('対象のカート商品が見つかりません')

            if remove:
                cursor.execute("DELETE FROM cart WHERE cart_id = %s", (cart_id,))
            else:
                quantity = int(request.forms.get('quantity') or 1)
                if quantity < 1:
                    quantity = 1
                cursor.execute("SELECT stock FROM products WHERE product_id = %s", (cart_item['product_id'],))
                product = cursor.fetchone()
                if not product:
                    raise ValueError('商品情報の取得に失敗しました')
                if quantity > product['stock']:
                    quantity = product['stock']
                cursor.execute("UPDATE cart SET quantity = %s WHERE cart_id = %s", (quantity, cart_id))
            conn.commit()
        conn.close()

        return HTTPResponse(status=303, headers={'Location': '/cart'})
    except HTTPResponse:
        raise
    except Exception as e:
        content = f"""
            <div class=\"error-box\">カート更新中にエラーが発生しました。</div>
            <pre>{str(e)}</pre>
            <p><a class=\"button\" href=\"/cart\">カートへ</a></p>
        """
        return page_template("エラー", content)


@app.route("/order/create", method="POST")
def order_create():
    try:
        user = get_current_user()
        if not user:
            raise HTTPResponse(status=303, headers={'Location': '/login'})

        customer_name = user.get('name') or 'ゲスト'

        conn = get_connection()
        with conn.cursor() as cursor:
            ensure_orders_user_id_column(conn)
            cart_items = get_cart_items(conn)
            if not cart_items:
                raise ValueError('カートが空です。')

            for item in cart_items:
                if item['quantity'] > item['stock']:
                    raise ValueError(f"{item['name']} の在庫が不足しています")

            total_amount = sum(item['price'] * item['quantity'] for item in cart_items)
            order_details = [
                {
                    'product_id': item['product_id'],
                    'name': item['name'],
                    'price': float(item['price']),
                    'quantity': item['quantity'],
                    'subtotal': float(item['price'] * item['quantity'])
                }
                for item in cart_items
            ]

            cursor.execute(
                "INSERT INTO orders (customer_name, user_id, total_amount, status, details) VALUES (%s, %s, %s, %s, %s)",
                (customer_name, user['user_id'], total_amount, 'confirmed', json.dumps(order_details))
            )
            order_id = cursor.lastrowid

            for item in cart_items:
                cursor.execute(
                    "UPDATE products SET stock = GREATEST(stock - %s, 0) WHERE product_id = %s",
                    (item['quantity'], item['product_id'])
                )

                cursor.execute("DELETE FROM cart")
            conn.commit()
        conn.close()

        return HTTPResponse(status=303, headers={'Location': f'/orders?status=created&order_id={order_id}'})
    except HTTPResponse:
        raise
    except Exception as e:
        content = f"""
            <div class=\"error-box\">注文処理中にエラーが発生しました。</div>
            <pre>{str(e)}</pre>
            <p><a class=\"button\" href=\"/cart\">カートへ</a></p>
        """
        return page_template("注文エラー", content)


@app.route("/orders")
def order_list():
    try:
        user = get_current_user()
        if not user:
            raise HTTPResponse(status=303, headers={'Location': '/login'})

        conn = get_connection()
        with conn.cursor() as cursor:
            ensure_orders_user_id_column(conn)
            cursor.execute("SELECT * FROM orders WHERE user_id = %s ORDER BY created_at DESC", (user['user_id'],))
            orders = cursor.fetchall()
        conn.close()

        status = request.query.get('status', '').strip()
        alert_html = ''
        if status == 'created':
            order_id = request.query.get('order_id', '').strip()
            if order_id:
                alert_html = f'<div class="alert alert-success">注文を受け付けました。注文ID: {order_id} です</div>'
            else:
                alert_html = '<div class="alert alert-success">注文を受け付けました。</div>'

        rows_html = ''
        for order in orders:
            rows_html += f"""
                <tr>
                  <td>{order['order_id']}</td>
                  <td>{order['customer_name']}</td>
                  <td>{format_currency(order['total_amount'])}</td>
                  <td>{order['created_at']}</td>
                  <td><a class=\"button\" href=\"/order/{order['order_id']}\">詳細</a></td>
                </tr>
            """

        content = f"""
            <p>ご注文履歴を確認できます。</p>
            {alert_html}
            <div class=\"table-wrap\">
              <table>
                <thead>
                  <tr>
                    <th>注文ID</th>
                    <th>お名前</th>
                    <th>合計金額</th>
                    <th>作成日</th>
                    <th>詳細</th>
                  </tr>
                </thead>
                <tbody>
                  {rows_html}
                </tbody>
              </table>
            </div>
        """
        return page_template("注文履歴", content, hide_order_history_button=True)
    except Exception as e:
        content = f"""
            <div class=\"error-box\">注文履歴の読み込み中にエラーが発生しました。</div>
            <pre>{str(e)}</pre>
            <p><a class=\"button\" href=\"/\">ホームへ</a></p>
        """
        return page_template("エラー", content)


@app.route("/order/<order_id:int>")
def order_detail(order_id):
    try:
        user = get_current_user()
        if not user:
            raise HTTPResponse(status=303, headers={'Location': '/login'})

        conn = get_connection()
        with conn.cursor() as cursor:
            ensure_orders_user_id_column(conn)
            cursor.execute("SELECT * FROM orders WHERE order_id = %s AND user_id = %s", (order_id, user['user_id']))
            order = cursor.fetchone()
        conn.close()

        if not order:
            raise ValueError('指定された注文が見つかりません')

        details = order.get('details') or '[]'
        if isinstance(details, str):
            details = json.loads(details)

        detail_rows = ''
        for item in details:
            detail_rows += f"""
                <tr>
                  <td>{item['name']}</td>
                  <td>{format_currency(item['price'])}</td>
                  <td>{item['quantity']}</td>
                  <td>{format_currency(item['subtotal'])}</td>
                </tr>
            """

        content = f"""
            <p>注文ID <strong>{order['order_id']}</strong> の詳細です。</p>
            <div class=\"table-wrap\">
              <table>
                <thead>
                  <tr>
                    <th>商品名</th>
                    <th>価格</th>
                    <th>数量</th>
                    <th>小計</th>
                  </tr>
                </thead>
                <tbody>
                  {detail_rows}
                </tbody>
              </table>
            </div>
            <p><strong>合計金額:</strong> {format_currency(order['total_amount'])}</p>
            <div class=\"grid-actions\">
              <a class=\"button\" href=\"/orders\">注文一覧へ</a>
              <a class=\"button\" href=\"/\">ホームへ</a>
            </div>
        """
        return page_template(f"注文 {order_id} の詳細", content)
    except Exception as e:
        content = f"""
            <div class=\"error-box\">注文詳細の読み込み中にエラーが発生しました。</div>
            <pre>{str(e)}</pre>
            <p><a class=\"button\" href=\"/orders\">注文一覧へ</a></p>
        """
        return page_template("エラー", content)


@app.route("/admin/products")
def admin_product_list():
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT product_id, name, description, price, stock FROM products ORDER BY product_id")
            products = cursor.fetchall()
        conn.close()

        status = request.query.get('status', '').strip()
        alert_html = ''
        if status == 'logged_in':
            alert_html = '<div class="alert alert-success">ログインに成功しました。</div>'
        elif status == 'registered':
            alert_html = '<div class="alert alert-success">新規登録が完了しました。</div>'

        rows_html = ''
        for product in products:
            rows_html += f"""
                <tr>
                  <td>{product['product_id']}</td>
                  <td>{product['name']}</td>
                  <td>{product['description'] or ''}</td>
                  <td>{format_currency(product['price'])}</td>
                  <td>{product['stock']}</td>
                  <td>
                    <a class=\"button\" href=\"/admin/products/edit/{product['product_id']}\">編集</a>
                    <form action=\"/admin/products/delete\" method=\"post\" style=\"display:inline-block; margin:0;\">
                      <input type=\"hidden\" name=\"product_id\" value=\"{product['product_id']}\" />
                      <button class=\"button button-danger\" type=\"submit\" onclick=\"return confirm('この商品を削除しますか？');\">削除</button>
                    </form>
                  </td>
                </tr>
            """

        content = f"""
            {alert_html}
            <div class=\"grid-actions\">
              <a class=\"button\" href=\"/admin/products/new\">新規商品追加</a>
              <a class=\"button\" href=\"/products\">商品一覧に戻る</a>
            </div>
            <div class=\"table-wrap\">
              <table>
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>商品名</th>
                    <th>説明</th>
                    <th>価格</th>
                    <th>在庫</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  {rows_html}
                </tbody>
              </table>
            </div>
        """
        return page_template("商品管理", content, nav_html=admin_nav_html())
    except Exception as e:
        content = f"""
            <div class=\"error-box\">商品管理ページの読み込み中にエラーが発生しました。</div>
            <pre>{str(e)}</pre>
            <p><a class=\"button\" href=\"/\">戻る</a></p>
        """
        return page_template("エラー", content, nav_html=admin_nav_html())


@app.route("/admin/products/new")
def admin_product_new():
    content = """
        <form action=\"/admin/products/create\" method=\"post\">
          <div class=\"form-grid\">
            <div class=\"field\"><label for=\"name\">商品名</label><input id=\"name\" name=\"name\" required></div>
            <div class=\"field\"><label for=\"description\">説明</label><input id=\"description\" name=\"description\"></div>
            <div class=\"field\"><label for=\"price\">価格</label><input id=\"price\" name=\"price\" type=\"number\" step=\"0.01\" min=\"0\" required></div>
            <div class=\"field\"><label for=\"stock\">在庫</label><input id=\"stock\" name=\"stock\" type=\"number\" min=\"0\" required></div>
          </div>
          <div class=\"grid-actions\">
            <button class=\"button\" type=\"submit\">商品を作成</button>
            <a class=\"button\" href=\"/admin/products\">商品管理に戻る</a>
          </div>
        </form>
    """
    return page_template("商品作成", content, nav_html=admin_nav_html())


@app.route("/admin/products/create", method="POST")
def admin_product_create():
    try:
        name = request.forms.get('name', '').strip()
        description = request.forms.get('description', '').strip()
        # Normalize and unescape any HTML entities to avoid double-encoding in DB
        name = html.unescape(name)
        description = html.unescape(description)
        # Fix possible mojibake where UTF-8 bytes were decoded as Latin-1
        name = fix_mojibake(name)
        description = fix_mojibake(description)
        name = unicodedata.normalize('NFC', name)
        description = unicodedata.normalize('NFC', description)
        price = float(request.forms.get('price') or 0)
        stock = int(request.forms.get('stock') or 0)

        # Temporary debug: if DEBUG_SHOW_POST=1, show raw POST payload and parsed form values
        if os.getenv('DEBUG_SHOW_POST', '0') == '1':
            try:
                raw_body = request.body.read().decode('utf-8', 'replace')
            except Exception:
                raw_body = '(unavailable)'
            try:
                parsed = {k: request.forms.get(k) for k in request.forms.keys()}
            except Exception:
                parsed = '(unavailable)'
            content = f"""
                <h3>POST Payload Debug</h3>
                <h4>Parsed form values</h4>
                <pre>{html.escape(json.dumps(parsed, ensure_ascii=False, indent=2))}</pre>
                <h4>Raw body</h4>
                <pre>{html.escape(raw_body)}</pre>
                <p><a class=\"button\" href=\"/admin/products\">商品管理に戻る</a></p>
            """
            return page_template("POSTデバッグ", content, nav_html=admin_nav_html())

        if not name:
            raise ValueError('商品名が空です')
        if len(name) > 255:
            content = f"""
                <div class=\"error-box\">商品名は255文字以下で入力してください。現在{len(name)}文字です。</div>
                <p><a class=\"button\" href=\"/admin/products/new\">戻る</a></p>
            """
            return page_template("入力エラー", content, nav_html=admin_nav_html())

        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO products (name, description, price, stock) VALUES (%s, %s, %s, %s)",
                (name, description, price, stock)
            )
            conn.commit()
        conn.close()

        return HTTPResponse(status=303, headers={'Location': '/admin/products'})
    except HTTPResponse:
        raise
    except Exception as e:
        content = f"""
            <div class=\"error-box\">入力処理でエラーが発生しました。</div>
            <pre>{str(e)}</pre>
            <p><a class=\"button\" href=\"/admin/products/new\">戻る</a></p>
        """
        return page_template("入力エラー", content, nav_html=admin_nav_html())


@app.route("/admin/products/edit/<product_id:int>")
def admin_product_edit(product_id):
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT product_id, name, description, price, stock FROM products WHERE product_id = %s", (product_id,))
            product = cursor.fetchone()
        conn.close()

        if not product:
            raise ValueError('対象の商品が見つかりません')

        escaped_name = html.escape(product['name'] or '', quote=True)
        escaped_description = html.escape(product['description'] or '', quote=True)
        content = f"""
            <form action="/admin/products/update" method="post" accept-charset="utf-8">
              <input type="hidden" name="product_id" value="{product['product_id']}" />
              
                <div class="field"><label for="name">商品名</label><input id="name" name="name" value="{escaped_name}" required></div>
                <div class="field"><label for="description">説明</label><textarea id="description" name="description" rows="4" style="min-height:100px;">{escaped_description}</textarea></div>
                <div class="field"><label for="price">価格</label><input id="price" name="price" type="number" step="0.01" min="0" value="{product['price']}" required></div>
                <div class="field"><label for="stock">在庫</label><input id="stock" name="stock" type="number" min="0" value="{product['stock']}" required></div>
              </div>
              <div class="grid-actions">
                <button class="button" type="submit">更新を保存</button>
                <a class="button" href="/admin/products">商品管理に戻る</a>
              </div>
            </form>
        """
        return page_template(f"商品編集 {product['product_id']}", content, nav_html=admin_nav_html())
    except Exception as e:
        content = f"""
            <div class="error-box">商品編集ページの読み込み中にエラーが発生しました。</div>
            <pre>{str(e)}</pre>
            <p><a class="button" href="/admin/products">商品管理に戻る</a></p>
        """
        return page_template("エラー", content, nav_html=admin_nav_html())
def admin_product_update():
    try:
        product_id = int(request.forms.get('product_id') or 0)
        name = request.forms.get('name', '').strip()
        description = request.forms.get('description', '').strip()
        # Normalize and unescape form inputs to prevent stored double-escaping
        name = html.unescape(name)
        description = html.unescape(description)
        # Fix possible mojibake where UTF-8 bytes were decoded as Latin-1
        name = fix_mojibake(name)
        description = fix_mojibake(description)
        name = unicodedata.normalize('NFC', name)
        description = unicodedata.normalize('NFC', description)
        price = float(request.forms.get('price') or 0)
        stock = int(request.forms.get('stock') or 0)

        if not name:
            raise ValueError('商品名を入力してください')
        # Validate product name length to avoid DB errors (VARCHAR(255)).
        if len(name) > 255:
            content = f"""
                <div class=\"error-box\">商品名は255文字以下で入力してください。現在{len(name)}文字です。</div>
                <p><a class=\"button\" href=\"/admin/products/edit/{product_id}\">戻る</a></p>
            """
            return page_template("入力エラー", content, nav_html=admin_nav_html())

        conn = get_connection()
        try:
            with conn.cursor() as cursor:
                try:
                    cursor.execute(
                        "UPDATE products SET name = %s, description = %s, price = %s, stock = %s WHERE product_id = %s",
                        (name, description, price, stock, product_id)
                    )
                    conn.commit()
                except pymysql.err.DataError as db_e:
                    # Data too long or similar DB-level error
                    conn.rollback()
                    content = f"""
                        <div class=\"error-box\">データ保存時にエラーが発生しました。入力内容を確認してください。</div>
                        <pre>{str(db_e)}</pre>
                        <p><a class=\"button\" href=\"/admin/products/edit/{product_id}\">戻る</a></p>
                    """
                    return page_template("入力エラー", content, nav_html=admin_nav_html())
        finally:
            conn.close()

        return HTTPResponse(status=303, headers={'Location': '/admin/products'})
    except HTTPResponse:
        raise
    except Exception as e:
        # Log traceback to server console for debugging
        tb = traceback.format_exc()
        traceback.print_exc()
        # Safely show received form values to help debugging
        try:
            safe_name = html.escape(name or '')
            safe_description = html.escape(description or '')
            safe_price = html.escape(str(price))
            safe_stock = html.escape(str(stock))
            safe_pid = html.escape(str(product_id))
        except Exception:
            safe_name = safe_description = safe_price = safe_stock = safe_pid = "(unavailable)"

        content = f"""
            <div class=\"error-box\">商品更新処理でエラーが発生しました。詳細を確認してください。</div>
            <h3>送信された値</h3>
            <ul>
              <li>product_id: {safe_pid}</li>
              <li>name (length {len(name) if isinstance(name, str) else 'N/A'}): {safe_name}</li>
              <li>description (length {len(description) if isinstance(description, str) else 'N/A'}): {safe_description}</li>
              <li>price: {safe_price}</li>
              <li>stock: {safe_stock}</li>
            </ul>
            <h3>トレースバック</h3>
            <pre>{html.escape(tb)}</pre>
            <p><a class=\"button\" href=\"/admin/products\">商品管理に戻る</a></p>
        """
        return page_template("入力エラー", content, nav_html=admin_nav_html())


@app.route("/admin/products/delete", method="POST")
def admin_product_delete():
    try:
        product_id = int(request.forms.get('product_id') or 0)
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM products WHERE product_id = %s", (product_id,))
            conn.commit()
        conn.close()
        return HTTPResponse(status=303, headers={'Location': '/admin/products'})
    except Exception as e:
        content = f"""
            <div class=\"error-box\">削除処理でエラーが発生しました。</div>
            <pre>{str(e)}</pre>
            <p><a class=\"button\" href=\"/admin/products\">商品管理に戻る</a></p>
        """
        return page_template("削除エラー", content, nav_html=admin_nav_html())


@app.route("/admin/users")
def admin_user_list():
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT user_id, name, email, role, created_at FROM users ORDER BY user_id")
            users = cursor.fetchall()
        conn.close()

        rows_html = ''
        for user in users:
            rows_html += f"""
                <tr>
                  <td>{user['user_id']}</td>
                  <td>{html.escape(user['name'])}</td>
                  <td>{html.escape(user['email'])}</td>
                  <td>{html.escape(user['role'])}</td>
                  <td>{user['created_at']}</td>
                  <td>
                    <a class=\"button\" href=\"/admin/users/edit/{user['user_id']}\">編集</a>
                    <form action=\"/admin/users/delete\" method=\"post\" style=\"display:inline-block; margin:0;\">
                      <input type=\"hidden\" name=\"user_id\" value=\"{user['user_id']}\" />
                      <button class=\"button button-danger\" type=\"submit\" onclick=\"return confirm('このユーザーを本当に削除しますか？');\">削除</button>
                    </form>
                  </td>
                </tr>
            """

        content = f"""
            <div class=\"grid-actions\">
              <a class=\"button\" href=\"/admin/users/new\">ユーザーを追加</a>
              <a class=\"button\" href=\"/admin/products\">商品管理に戻る</a>
            </div>
            <div class=\"table-wrap\">
              <table>
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>名前</th>
                    <th>メール</th>
                    <th>ロール</th>
                    <th>作成日</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  {rows_html}
                </tbody>
              </table>
            </div>
        """
        return page_template("ユーザー一覧", content, nav_html=admin_nav_html())
    except Exception as e:
        content = f"""
            <div class=\"error-box\">ユーザー一覧の読み込み中にエラーが発生しました。</div>
            <pre>{str(e)}</pre>
            <p><a class=\"button\" href=\"/admin/products\">商品管理に戻る</a></p>
        """
        return page_template("エラー", content, nav_html=admin_nav_html())


@app.route("/admin/users/new")
def admin_user_new():
    content = """
        <form action="/admin/users/create" method="post">
          <div class="form-grid">
            <div class="field"><label for="name">名前</label><input id="name" name="name" required></div>
            <div class="field"><label for="email">メール</label><input id="email" name="email" type="email" required></div>
            <div class="field"><label for="password">パスワード</label><input id="password" name="password" type="password" required></div>
            <div class="field"><label for="role">ロール</label><select id="role" name="role"><option value="member">member</option><option value="admin">admin</option></select></div>
          </div>
          <div class="grid-actions">
            <button class="button" type="submit">ユーザーを作成</button>
            <a class="button" href="/admin/users">ユーザー一覧に戻る</a>
          </div>
        </form>
    """
    return page_template("ユーザー作成", content, nav_html=admin_nav_html())


@app.route("/admin/users/create", method="POST")
def admin_user_create():
    try:
        name = request.forms.get('name', '').strip()
        email = request.forms.get('email', '').strip()
        password = request.forms.get('password', '').strip()
        role = request.forms.get('role', 'member').strip()

        if not name:
            raise ValueError('名前は必須です')
        if not email:
            raise ValueError('メールアドレスは必須です')
        if not password:
            raise ValueError('パスワードは必須です')
        if len(name) > 255:
            raise ValueError('名前は255文字以下で入力してください')
        if len(email) > 255:
            raise ValueError('メールアドレスは255文字以下で入力してください')
        if len(password) > 255:
            raise ValueError('パスワードは255文字以下で入力してください')
        if role not in ('member', 'admin'):
            role = 'member'

        password_hash = hash_password(password)
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                'INSERT INTO users (name, email, password_hash, role) VALUES (%s, %s, %s, %s)',
                (name, email, password_hash, role)
            )
            conn.commit()
        conn.close()

        return HTTPResponse(status=303, headers={'Location': '/admin/users'})
    except HTTPResponse:
        raise
    except Exception as e:
        content = f"""
            <div class=\"error-box\">ユーザー作成時にエラーが発生しました。</div>
            <pre>{str(e)}</pre>
            <p><a class=\"button\" href=\"/admin/users/new\">戻る</a></p>
        """
        return page_template("入力エラー", content, nav_html=admin_nav_html())


@app.route("/admin/users/edit/<user_id:int>")
def admin_user_edit(user_id):
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute('SELECT user_id, name, email, role FROM users WHERE user_id = %s', (user_id,))
            user = cursor.fetchone()
        conn.close()

        if not user:
            raise ValueError('対象のユーザーが見つかりません')

        content = f"""
            <form action="/admin/users/update" method="post" accept-charset="utf-8">
              <input type="hidden" name="user_id" value="{user['user_id']}" />
              <div class="form-grid">
                <div class="field"><label for="name">名前</label><input id="name" name="name" value="{html.escape(user['name'])}" required></div>
                <div class="field"><label for="email">メール</label><input id="email" name="email" type="email" value="{html.escape(user['email'])}" required></div>
                <div class="field"><label for="password">パスワード</label><input id="password" name="password" type="password"></div>
                <div class="field"><label for="role">ロール</label><select id="role" name="role"><option value="member"{' selected' if user['role'] == 'member' else ''}>member</option><option value="admin"{' selected' if user['role'] == 'admin' else ''}>admin</option></select></div>
              </div>
              <p class="note">パスワードを変更しない場合は空のままにしてください。</p>
              <div class="grid-actions">
                <button class="button" type="submit">変更を保存</button>
                <a class="button" href="/admin/users">ユーザー一覧に戻る</a>
              </div>
            </form>
        """
        return page_template("ユーザー編集", content, nav_html=admin_nav_html())
    except Exception as e:
        content = f"""
            <div class=\"error-box\">ユーザー編集ページの読み込み中にエラーが発生しました。</div>
            <pre>{str(e)}</pre>
            <p><a class=\"button\" href=\"/admin/users\">ユーザー一覧に戻る</a></p>
        """
        return page_template("エラー", content, nav_html=admin_nav_html())


@app.route("/admin/users/update", method="POST")
def admin_user_update():
    try:
        user_id = int(request.forms.get('user_id') or 0)
        name = request.forms.get('name', '').strip()
        email = request.forms.get('email', '').strip()
        password = request.forms.get('password', '').strip()
        role = request.forms.get('role', 'member').strip()

        if not name:
            raise ValueError('名前は必須です')
        if not email:
            raise ValueError('メールアドレスは必須です')
        if len(name) > 255:
            raise ValueError('名前は255文字以下で入力してください')
        if len(email) > 255:
            raise ValueError('メールアドレスは255文字以下で入力してください')
        if password and len(password) > 255:
            raise ValueError('パスワードは255文字以下で入力してください')
        if role not in ('member', 'admin'):
            role = 'member'

        conn = get_connection()
        with conn.cursor() as cursor:
            if password:
                password_hash = hash_password(password)
                cursor.execute(
                    'UPDATE users SET name = %s, email = %s, password_hash = %s, role = %s WHERE user_id = %s',
                    (name, email, password_hash, role, user_id)
                )
            else:
                cursor.execute(
                    'UPDATE users SET name = %s, email = %s, role = %s WHERE user_id = %s',
                    (name, email, role, user_id)
                )
            conn.commit()
        conn.close()

        return HTTPResponse(status=303, headers={'Location': '/admin/users'})
    except HTTPResponse:
        raise
    except Exception as e:
        content = f"""
            <div class=\"error-box\">ユーザー更新時にエラーが発生しました。</div>
            <pre>{str(e)}</pre>
            <p><a class=\"button\" href=\"/admin/users\">ユーザー一覧に戻る</a></p>
        """
        return page_template("入力エラー", content, nav_html=admin_nav_html())


@app.route("/admin/users/delete", method="POST")
def admin_user_delete():
    try:
        user_id = int(request.forms.get('user_id') or 0)
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute('DELETE FROM users WHERE user_id = %s', (user_id,))
            conn.commit()
        conn.close()
        return HTTPResponse(status=303, headers={'Location': '/admin/users'})
    except Exception as e:
        content = f"""
            <div class=\"error-box\">ユーザー削除時にエラーが発生しました。</div>
            <pre>{str(e)}</pre>
            <p><a class=\"button\" href=\"/admin/users\">ユーザー一覧に戻る</a></p>
        """
        return page_template("削除エラー", content, nav_html=admin_nav_html())


@app.route("/login")
def login():
    content = """
        <form action="/login" method="post">
          <div class="form-grid">
            <div class="field"><label for="email">メール</label><input id="email" name="email" type="email" required></div>
            <div class="field"><label for="password">パスワード</label><input id="password" name="password" type="password" required></div>
          </div>
          <div class="grid-actions">
            <button class="button" type="submit">ログイン</button>
            <a class="button" href="/">戻る</a>
          </div>
        </form>
    """
    return page_template("ログイン", content, nav_html=build_nav_html())


@app.route("/login/")
def login_slash():
    return HTTPResponse(status=303, headers={'Location': '/login'})


@app.route("/register")
def register():
    if get_current_user():
        return HTTPResponse(status=303, headers={'Location': '/'})

    content = """
        <form action="/register" method="post">
          <div class="form-grid">
            <div class="field"><label for="name">名前</label><input id="name" name="name" required></div>
            <div class="field"><label for="email">メール</label><input id="email" name="email" type="email" required></div>
            <div class="field"><label for="password">パスワード</label><input id="password" name="password" type="password" required></div>
          </div>
          <div class="grid-actions">
            <button class="button" type="submit">登録</button>
            <a class="button" href="/">戻る</a>
          </div>
        </form>
    """
    return page_template("登録", content, nav_html=build_nav_html())


@app.route("/register", method="POST")
def register_post():
    if get_current_user():
        return HTTPResponse(status=303, headers={'Location': '/'})

    name = request.forms.get('name', '').strip()
    email = request.forms.get('email', '').strip()
    password = request.forms.get('password', '').strip()

    if not name or not email or not password:
        content = """
            <div class=\"error-box\">必要な項目が入力されていません。</div>
            <p><a class=\"button\" href=\"/register\">戻る</a></p>
        """
        return page_template("入力エラー", content, nav_html=build_nav_html())

    try:
        password_hash = hash_password(password)
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                'INSERT INTO users (name, email, password_hash, role) VALUES (%s, %s, %s, %s)',
                (name, email, password_hash, 'member')
            )
            user_id = cursor.lastrowid
            conn.commit()
        conn.close()

        return redirect_with_session('/?status=registered', user_id)
    except Exception as e:
        content = f"""
            <div class=\"error-box\">登録処理中にエラーが発生しました。</div>
            <pre>{html.escape(str(e))}</pre>
            <p><a class=\"button\" href=\"/register\">戻る</a></p>
        """
        return page_template("登録エラー", content, nav_html=build_nav_html())


@app.route("/login", method="POST")
def login_post():
    email = (request.forms.get('email') or '').strip()
    password = (request.forms.get('password') or '').strip()

    if not email or not password:
        content = """
            <div class=\"error-box\">メールとパスワードを入力してください。</div>
            <p><a class=\"button\" href=\"/login\">ログイン画面に戻る</a></p>
        """
        return page_template("ログインエラー", content, nav_html=build_nav_html())

    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT user_id, password_hash, role FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()
        conn.close()
        if not user or not verify_password(password, user.get('password_hash', '')):
            content = """
                <div class=\"error-box\">メールアドレスまたはパスワードが正しくありません。</div>
                <p><a class=\"button\" href=\"/login\">ログイン画面に戻る</a></p>
            """
            return page_template("ログインエラー", content, nav_html=build_nav_html())

        if user.get('role') != 'admin':
            content = """
                <div class=\"error-box\">管理者権限が必要です。</div>
                <p><a class=\"button\" href=\"/\">トップページに戻る</a></p>
            """
            return page_template("アクセスエラー", content, nav_html=build_nav_html())

        return redirect_with_session('/?status=logged_in', user['user_id'])
    except Exception as e:
        content = f"""
            <div class=\"error-box\">ログイン処理中にエラーが発生しました。</div>
            <pre>{html.escape(str(e))}</pre>
            <p><a class=\"button\" href=\"/login\">ログイン画面に戻る</a></p>
        """
        return page_template("ログインエラー", content, nav_html=build_nav_html())


@app.route("/logout")
def logout_confirm():
    content = """
        <p>本当にログアウトしますか？</p>
        <form action="/logout" method="post">
          <div class="grid-actions">
            <button class="button button-danger" type="submit">ログアウト</button>
            <a class="button" href="/">トップに戻る</a>
          </div>
        </form>
    """
    return page_template("ログアウト確認", content, nav_html=build_nav_html())


@app.route("/logout", method="POST")
def logout():
    resp = HTTPResponse(status=303, headers={'Location': '/?status=logged_out'})
    logout_user(response_obj=resp)
    return resp


if __name__ == "__main__":
    # Run without Bottle debug mode so HTTPResponse used for redirects
    # does not appear as an exception traceback to users.
    run(app, host="0.0.0.0", port=8080, debug=False, reloader=True)


