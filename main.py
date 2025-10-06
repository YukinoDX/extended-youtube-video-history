# upload
import sys
import json
from urllib.parse import parse_qs, urlparse
from datetime import datetime
import sqlite3
from sqlite3 import Cursor
import googleapiclient.discovery
from api import API_KEY

# search,UI
from sentence_transformers import SentenceTransformer, util
from flask import Flask, request, render_template, g
import colorsys

# カテゴリID → カテゴリの名前
category_map = {
    "1": "Film & Animation",
    "2": "Autos & Vehicles",
    "10": "Music",
    "15": "Pets & Animals",
    "17": "Sports",
    "18": "Short Movies",
    "19": "Travel & Events",
    "20": "Gaming",
    "21": "Videoblogging",
    "22": "People & Blogs",
    "23": "Comedy",
    "24": "Entertainment",
    "25": "News & Politics",
    "26": "Howto & Style",
    "27": "Education",
    "28": "Science & Technology",
    "29": "Nonprofits & Activism",
    "30": "Movies",
    "31": "Anime/Animation",
    "32": "Action/Adventure",
    "33": "Classics",
    "34": "Comedy",
    "35": "Documentary",
    "36": "Drama",
    "37": "Family",
    "38": "Foreign",
    "39": "Horror",
    "40": "Sci-Fi/Fantasy",
    "41": "Thriller",
    "42": "Shorts",
    "43": "Shows",
    "44": "Trailers",
}

nums_category = {category: num for num, category in enumerate(category_map.values())}
categories = [category for category in category_map.values()] + ["All"]


def add_to_db(cur: Cursor, ids: list[str], times: list[str]):
    youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=API_KEY)

    video_response = (
        youtube.videos().list(part="snippet", id=",".join(set(ids))).execute()
    )

    for item in video_response["items"]:
        if "id" not in item:
            sys.exit(f"not exist id. item: {item}")
        if "snippet" not in item:
            sys.exit(f'not exist snippet. id: {item["id"]}')
        if "title" not in item["snippet"]:
            sys.exit(f'not exist title. id: {item["id"]}')
        if "channelTitle" not in item["snippet"]:
            sys.exit(f'not exist channelTitle. id: {item["id"]}')
        if "channelId" not in item["snippet"]:
            sys.exit(f'not exist channelId. id: {item["id"]}')
        if "categoryId" not in item["snippet"]:
            sys.exit(f'not exist categoryId. id: {item["id"]}')
        if "thumbnails" not in item["snippet"]:
            sys.exit(f'not exist thumbnails. id: {item["id"]}')
        if item["snippet"]["categoryId"] not in category_map:
            sys.exit(f'not exist categoryId. id: {item["id"]}')

    # idに重複があると、len(ids) != len(video_response) なので、id → snippetの mapを先に作る
    id_snippets = {item["id"]: item["snippet"] for item in video_response["items"]}

    assert len(ids) == len(times)
    for id, time in zip(ids, times):
        if id not in id_snippets:  # 非公開や削除された動画は返ってこない
            continue

        snippet = id_snippets[id]
        cur.execute(
            """
            INSERT INTO history (
                title,
                id_video,
                channel,
                id_channel,
                category,
                time_watch,
                thumbnail_url
            ) VALUES (?,?,?,?,?,?,?)
        """,
            (
                snippet["title"],
                id,
                snippet["channelTitle"],
                snippet["channelId"],
                category_map[snippet["categoryId"]],
                datetime.fromisoformat(time.replace("Z", "+00:00")).strftime(
                    "%Y/%m/%d"
                ),
                snippet["thumbnails"]["high"]["url"],
            ),
        )


def upload_takeout():
    loop = 0
    with open("watch-history.json") as f:
        conn = sqlite3.connect("history.db")
        cur = conn.cursor()

        hists = json.load(f)
        ids, times = [], []
        for hist in hists:
            if (
                "視聴しました" not in hist["title"]
                or hist["header"] != "YouTube"
                or "details" in hist
            ):  # details in → 広告の動画
                continue

            url_parsed = urlparse(hist["titleUrl"])
            v_parsed = parse_qs(url_parsed.query).get("v")
            if v_parsed is None:
                continue

            id_video = v_parsed[0]
            ids.append(id_video)
            times.append(hist["time"])
            if len(ids) < 50:
                continue
            add_to_db(cur, ids, times)
            ids, times = [], []

            loop += 1
            print(f"upload {50*loop} videos")
        if ids:
            add_to_db(cur, ids, times)
            print(f"upload {50*loop+len(ids)} videos")

        conn.commit()
        conn.close()


app = Flask(__name__)

DATABASE = "history.db"


def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row

    return db


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()


def query_db(query, args=()):
    cur = get_db().execute(query, args)
    rows = cur.fetchall()
    return rows


def to_color_code(category):
    num = nums_category[category] / len(nums_category)
    r, g, b = colorsys.hsv_to_rgb(num, 0.5, 0.9)
    return "#%02x%02x%02x" % (int(r * 255), int(g * 255), int(b * 255))


def scores_match(rows, query: str):
    model = SentenceTransformer(
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2", device="cpu"
    )
    titles = [row["title"] for row in rows]  # 最初から変わらない. 前計算できる

    embeddings = model.encode(titles, convert_to_tensor=True)
    query_emb = model.encode(query, convert_to_tensor=True)

    scores = util.cos_sim(query_emb, embeddings)

    return scores[0]


@app.route("/search-word", methods=["GET"])
def search_word():
    query = request.args.get("content", "")

    rows = query_db("SELECT * FROM history")  # 前計算できる
    colors = [to_color_code(row["category"]) for row in rows]  # 前計算できる

    if query:
        scores = scores_match(rows, query)
        ids = sorted(range(len(scores)), key=lambda id: scores[id], reverse=True)
        rows = [rows[id] for id in ids]
        colors = [colors[id] for id in ids]

    return render_template(
        "index.html",
        mode="word",
        rows_colors=zip(rows, colors),
        categories=categories,
    )


@app.route("/search-filter", methods=["GET"])
def search_filter():
    title = request.args.get("title", "")
    category = request.args.get("category", "All")
    channel = request.args.get("channel", "")
    since = request.args.get("since", "")
    until = request.args.get("until", "")
    order = request.args.get("order", "DESC")

    conditions = []
    params = {}

    if title:
        conditions.append("title LIKE :title")
        params["title"] = title
    if category != "All":
        conditions.append("category = :category")
        params["category"] = category
    if channel:
        conditions.append("channel LIKE :channel")
        params["channel"] = channel
    if since:
        conditions.append("time_watch >= :since")
        params["since"] = since.replace("-", "/")
    if until:
        conditions.append("time_watch <= :until")
        params["until"] = until.replace("-", "/")

    sql = "SELECT * FROM history" + (
        " WHERE " + " AND ".join(conditions) if conditions else ""
    )

    sql += " ORDER BY time_watch" + (" ASC" if order == "ASC" else " DESC")

    rows = query_db(sql, params)
    colors = [to_color_code(row["category"]) for row in rows]

    return render_template(
        "index.html",
        mode="filter",
        rows_colors=zip(rows, colors),
        categories=categories,
    )


@app.route("/", methods=["GET"])
def index():
    rows = query_db("SELECT * FROM history")  # 前計算できる
    colors = [to_color_code(row["category"]) for row in rows]  # 前計算できる

    return render_template(
        "index.html",
        mode="filter",
        rows_colors=zip(rows, colors),
        categories=categories,
    )


if __name__ == "__main__":
    app.run(port=8080, debug=True)
    # upload_takeout()
