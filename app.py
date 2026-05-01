from flask import Flask, render_template, request, redirect
import sqlite3
import os

app = Flask(__name__)
DB = "inventory.db"


# =========================
# DB接続
# =========================
def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


# =========================
# 一覧（全て統合：カテゴリ＋検索＋ID検索）
# =========================
@app.route("/")
def home():

    category = request.args.get("category", "all")
    keyword = request.args.get("keyword", "").strip()

    conn = get_db()

    try:
        sql = """
        SELECT 
            products.id,
            products.name,
            products.stock,
            products.category_id,
            categories.name AS category_name,
            units.name AS unit_name
        FROM products
        LEFT JOIN categories ON products.category_id = categories.id
        LEFT JOIN units ON products.unit_id = units.id
        WHERE 1=1
        """

        params = []

        # =========================
        # カテゴリ（安全化）
        # =========================
        if category != "all":
            try:
                category_id = int(category)
                sql += " AND products.category_id = ?"
                params.append(category_id)
            except:
                category = "all"

        # =========================
        # 検索（ID + 名前対応）
        # =========================
        if keyword:
            if keyword.isdigit():
                sql += " AND products.id = ?"
                params.append(int(keyword))
            else:
                sql += " AND products.name LIKE ?"
                params.append(f"%{keyword}%")

        products = conn.execute(sql, params).fetchall()

        units = conn.execute("SELECT * FROM units").fetchall()
        categories = conn.execute("SELECT * FROM categories").fetchall()

    except Exception as e:
        print("HOME ERROR:", e)
        products = []
        units = []
        categories = []

    finally:
        conn.close()

    return render_template(
        "inventory.html",
        products=products,
        units=units,
        categories=categories,
        keyword=keyword,
        category=category
    )


# =========================
# 商品追加
# =========================
@app.route("/add", methods=["POST"])
def add():

    name = request.form.get("name", "").strip()
    unit_id = request.form.get("unit_id")
    category_id = request.form.get("category_id")

    if not name:
        return redirect("/")

    conn = get_db()

    try:
        conn.execute(
            "INSERT INTO products (name, stock, unit_id, category_id) VALUES (?, 0, ?, ?)",
            (name, unit_id, category_id)
        )
        conn.commit()

    except Exception as e:
        print("ADD ERROR:", e)

    finally:
        conn.close()

    return redirect("/")


# =========================
# 入庫（履歴付き）
# =========================
@app.route("/in/<int:pid>", methods=["POST"])
def stock_in(pid):

    qty = request.form.get("quantity", "0")

    if not qty.isdigit():
        return redirect("/")

    qty = int(qty)

    conn = get_db()

    try:
        conn.execute(
            "UPDATE products SET stock = stock + ? WHERE id = ?",
            (qty, pid)
        )

        conn.execute(
            "INSERT INTO stock_logs (product_id, action, quantity) VALUES (?, 'IN', ?)",
            (pid, qty)
        )

        conn.commit()

    except Exception as e:
        print("IN ERROR:", e)

    finally:
        conn.close()

    return redirect("/")


# =========================
# 出庫（履歴付き）
# =========================
@app.route("/out/<int:pid>", methods=["POST"])
def stock_out(pid):

    qty = request.form.get("quantity", "0")

    if not qty.isdigit():
        return redirect("/")

    qty = int(qty)

    conn = get_db()

    try:
        conn.execute(
            "UPDATE products SET stock = stock - ? WHERE id = ? AND stock >= ?",
            (qty, pid, qty)
        )

        conn.execute(
            "INSERT INTO stock_logs (product_id, action, quantity) VALUES (?, 'OUT', ?)",
            (pid, qty)
        )

        conn.commit()

    except Exception as e:
        print("OUT ERROR:", e)

    finally:
        conn.close()

    return redirect("/")


# =========================
# 削除
# =========================
@app.route("/delete/<int:pid>")
def delete(pid):

    conn = get_db()

    try:
        conn.execute("DELETE FROM products WHERE id = ?", (pid,))
        conn.commit()

    except Exception as e:
        print("DELETE ERROR:", e)

    finally:
        conn.close()

    return redirect("/")


# =========================
# 履歴（必須ルート）
# =========================
@app.route("/logs")
def logs():

    conn = get_db()

    try:
        logs = conn.execute("""
            SELECT 
                stock_logs.id,
                products.name AS product_name,
                stock_logs.action,
                stock_logs.quantity,
                stock_logs.created_at
            FROM stock_logs
            LEFT JOIN products ON stock_logs.product_id = products.id
            ORDER BY stock_logs.id DESC
        """).fetchall()

    except Exception as e:
        print("LOGS ERROR:", e)
        logs = []

    finally:
        conn.close()

    return render_template("logs.html", logs=logs)


# =========================
# 起動
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

  
    