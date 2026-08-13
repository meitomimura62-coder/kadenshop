#!/usr/bin/env python3
import os
import pymysql
import html

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

if __name__ == '__main__':
    dry_run = os.getenv('DRY_RUN', '1') != '0'
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT product_id, name, description FROM products")
            rows = cursor.fetchall()
        changed = 0
        for r in rows:
            pid = r['product_id']
            name = r['name'] or ''
            desc = r['description'] or ''
            new_name = html.unescape(name)
            new_desc = html.unescape(desc)
            if new_name != name or new_desc != desc:
                changed += 1
                print(f"Will update {pid}: name changed? {new_name!=name}, desc changed? {new_desc!=desc}")
                if not dry_run:
                    with conn.cursor() as cursor:
                        cursor.execute(
                            "UPDATE products SET name=%s, description=%s WHERE product_id=%s",
                            (new_name, new_desc, pid)
                        )
                    conn.commit()
        print(f"Processed {len(rows)} rows, {changed} would be/was updated (dry_run={dry_run}).")
    finally:
        conn.close()
