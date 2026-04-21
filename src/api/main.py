from fastapi import FastAPI, HTTPException, Depends
import psycopg2
import os
import random
from dotenv import load_dotenv
from pydantic import BaseModel, field_validator
from fastapi.middleware.cors import CORSMiddleware

from src.auth.hash_utils import hash_password, verify_password
from src.auth.schemas import UserCreate, UserResponse
from src.auth.jwt_handler import signJWT, decodeJWT
from src.auth.jwt_bearer import JWTBearer

load_dotenv()
app = FastAPI()

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

INTERACTION_WEIGHTS = {
    "view": 0.5,
    "like": 2.0,
    "add_to_cart": 5.0,
    "purchase": 9.0,
}


def get_db_conn():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL is not configured")
    return psycopg2.connect(db_url)


def get_current_user(token: str = Depends(JWTBearer())):
    payload = decodeJWT(token)

    if not payload or "user_id" not in payload:
        raise HTTPException(status_code=403, detail="Invalid user token")

    try:
        return int(payload["user_id"])
    except Exception:
        raise HTTPException(status_code=403, detail="Invalid user id in token")


def table_exists(cur, table_name: str) -> bool:
    cur.execute("SELECT to_regclass(%s)", (table_name,))
    return cur.fetchone()[0] is not None


def serialize_product_row(row):
    return {
        "product_id": row[0],
        "name": row[1],
        "brand": row[2],
        "price": row[3],
        "image_url": row[4],
    }


def serialize_ranked_product_row(row):
    return {
        "product_id": row[0],
        "name": row[1],
        "brand": row[2],
        "price": row[3],
        "image_url": row[4],
        "score": float(row[5]) if row[5] is not None else 0.0,
    }


def fetch_total_products(cur):
    cur.execute("SELECT COUNT(*) FROM products")
    return cur.fetchone()[0]


def fetch_user_interaction_count(cur, user_id: str) -> int:
    cur.execute(
        """
        SELECT COUNT(*)
        FROM interactions
        WHERE user_id::text = %s
        """,
        (user_id,),
    )
    return cur.fetchone()[0]


def fetch_gold_recommendation_count(cur, user_id: str) -> int:
    if not table_exists(cur, "gold_user_recommendations"):
        return 0

    cur.execute(
        """
        SELECT COUNT(*)
        FROM gold_user_recommendations
        WHERE user_id::text = %s
        """,
        (user_id,),
    )
    return cur.fetchone()[0]


def get_weighted_popularity_cte():
    return """
        WITH popularity AS (
            SELECT
                i.product_id::text AS product_id,
                SUM(
                    CASE i.interaction_type
                        WHEN 'view' THEN 0.4
                        WHEN 'like' THEN 1.8
                        WHEN 'add_to_cart' THEN 4.0
                        WHEN 'purchase' THEN 7.0
                        ELSE 0.0
                    END
                    * CASE
                        WHEN i.interaction_type IN ('add_to_cart', 'purchase')
                            THEN LEAST(COALESCE(i.quantity, 1), 5)
                        ELSE 1
                      END
                ) AS popularity_score
            FROM interactions i
            WHERE i.interaction_type IN ('view', 'like', 'add_to_cart', 'purchase')
            GROUP BY i.product_id::text
        )
    """


def get_recent_behavioral_homepage(cur, user_id: str, size: int, offset: int):
    cur.execute(
        """
        WITH user_profile AS (
            SELECT
                i.user_id::text AS user_id,
                p.brand,
                p.category,
                p.type,
                p.purpose,
                SUM(
                    CASE i.interaction_type
                        WHEN 'view' THEN 0.5
                        WHEN 'like' THEN 2.0
                        WHEN 'add_to_cart' THEN 5.0
                        WHEN 'purchase' THEN 9.0
                        ELSE 0.0
                    END
                    * CASE
                        WHEN i.interaction_type IN ('add_to_cart', 'purchase')
                            THEN LEAST(COALESCE(i.quantity, 1), 5)
                        ELSE 1
                      END
                ) AS feature_score
            FROM interactions i
            JOIN products p
              ON i.product_id::text = p.product_id::text
            WHERE i.user_id::text = %s
              AND i.interaction_type IN ('view', 'like', 'add_to_cart', 'purchase')
            GROUP BY i.user_id::text, p.brand, p.category, p.type, p.purpose
        ),
        popularity AS (
            SELECT
                i.product_id::text AS product_id,
                SUM(
                    CASE i.interaction_type
                        WHEN 'view' THEN 0.4
                        WHEN 'like' THEN 1.8
                        WHEN 'add_to_cart' THEN 4.0
                        WHEN 'purchase' THEN 7.0
                        ELSE 0.0
                    END
                    * CASE
                        WHEN i.interaction_type IN ('add_to_cart', 'purchase')
                            THEN LEAST(COALESCE(i.quantity, 1), 5)
                        ELSE 1
                      END
                ) AS popularity_score
            FROM interactions i
            WHERE i.interaction_type IN ('view', 'like', 'add_to_cart', 'purchase')
            GROUP BY i.product_id::text
        ),
        product_scores AS (
            SELECT
                p.product_id,
                p.name,
                p.brand,
                p.price,
                p.image_url,
                COALESCE(SUM(
                    CASE WHEN up.brand IS NOT NULL AND up.brand = p.brand THEN up.feature_score * 2.6 ELSE 0 END +
                    CASE WHEN up.category IS NOT NULL AND up.category = p.category THEN up.feature_score * 1.4 ELSE 0 END +
                    CASE WHEN up.type IS NOT NULL AND up.type = p.type THEN up.feature_score * 1.0 ELSE 0 END +
                    CASE WHEN up.purpose IS NOT NULL AND up.purpose = p.purpose THEN up.feature_score * 0.8 ELSE 0 END
                ), 0.0)
                + COALESCE(pop.popularity_score, 0.0) * 0.03 AS user_score
            FROM products p
            LEFT JOIN user_profile up
              ON (
                  (up.brand IS NOT NULL AND up.brand = p.brand)
                  OR (up.category IS NOT NULL AND up.category = p.category)
                  OR (up.type IS NOT NULL AND up.type = p.type)
                  OR (up.purpose IS NOT NULL AND up.purpose = p.purpose)
              )
            LEFT JOIN popularity pop
              ON pop.product_id = p.product_id::text
            GROUP BY p.product_id, p.name, p.brand, p.price, p.image_url, pop.popularity_score
        )
        SELECT product_id, name, brand, price, image_url, user_score
        FROM product_scores
        ORDER BY
            CASE WHEN user_score > 0 THEN 0 ELSE 1 END ASC,
            user_score DESC,
            product_id::int DESC
        LIMIT %s OFFSET %s
        """,
        (user_id, size, offset),
    )
    return cur.fetchall()


def get_gold_homepage(cur, user_id: str, size: int, offset: int):
    cur.execute(
        f"""
        {get_weighted_popularity_cte()}
        SELECT
            p.product_id,
            p.name,
            p.brand,
            p.price,
            p.image_url,
            COALESCE(g.score, 0.0) AS user_score
        FROM products p
        LEFT JOIN gold_user_recommendations g
          ON g.product_id::text = p.product_id::text
         AND g.user_id::text = %s
        LEFT JOIN popularity pop
          ON pop.product_id = p.product_id::text
        ORDER BY
            CASE WHEN g.score IS NOT NULL THEN 0 ELSE 1 END ASC,
            user_score DESC,
            p.product_id::int DESC
        LIMIT %s OFFSET %s
        """,
        (user_id, size, offset),
    )
    return cur.fetchall()


@app.get("/")
def read_root():
    return {"message": "Welcome to Sneaker Recommendation API"}


@app.post("/register", response_model=UserResponse)
def register_user(user: UserCreate):
    conn = get_db_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT user_id FROM users WHERE name = %s", (user.username,))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="Username already registered")

        hashed_password = hash_password(user.password)

        cur.execute(
            """
            INSERT INTO users (name, password, age, gender, created_at)
            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
            RETURNING user_id
            """,
            (user.username, hashed_password, user.age, user.gender),
        )

        user_id = cur.fetchone()[0]
        conn.commit()

        return {"user_id": user_id, "username": user.username}

    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        print(f"REGISTER ERROR: {e}")
        conn.rollback()
        raise HTTPException(status_code=500, detail="Đăng ký thất bại do lỗi hệ thống")
    finally:
        cur.close()
        conn.close()


class LoginRequest(BaseModel):
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Username không được để trống")
        return value

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("Password không được để trống")
        return value


@app.post("/login")
def login_user(req: LoginRequest):
    conn = get_db_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT user_id, password FROM users WHERE name = %s",
            (req.username,),
        )
        row = cur.fetchone()

        if not row:
            raise HTTPException(status_code=401, detail="Sai tên tài khoản hoặc mật khẩu")

        user_id, stored_password = row
        login_success = False

        try:
            if verify_password(req.password, stored_password):
                login_success = True
        except Exception:
            pass

        if not login_success and req.password == stored_password:
            login_success = True
            new_hashed_password = hash_password(req.password)
            cur.execute(
                "UPDATE users SET password = %s WHERE user_id = %s",
                (new_hashed_password, user_id),
            )
            conn.commit()

        if not login_success:
            raise HTTPException(status_code=401, detail="Sai tên tài khoản hoặc mật khẩu")

        return signJWT(user_id)

    finally:
        cur.close()
        conn.close()


class InteractionRequest(BaseModel):
    product_id: str
    action_type: str
    quantity: int = 1


@app.post("/interact")
def interact(
    req: InteractionRequest,
    current_user_id: int = Depends(get_current_user),
):
    conn = get_db_conn()
    cur = conn.cursor()

    try:
        action_type = req.action_type.strip().lower()
        allowed_actions = {"view", "like", "add_to_cart", "purchase"}

        if action_type not in allowed_actions:
            raise HTTPException(status_code=400, detail="Invalid interaction type")

        quantity = req.quantity if req.quantity and req.quantity > 0 else 1

        if action_type in {"view", "like"}:
            quantity = 1

        cur.execute(
            """
            INSERT INTO interactions (user_id, product_id, interaction_type, quantity, interaction_time)
            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
            """,
            (current_user_id, str(req.product_id), action_type, quantity),
        )

        conn.commit()
        return {"message": "Interaction saved successfully"}

    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        print("INTERACT ERROR:", e)
        raise HTTPException(status_code=500, detail="Failed to save interaction")
    finally:
        cur.close()
        conn.close()


@app.get("/products")
def get_products(page: int = 1, size: int = 30):
    page = max(1, page)
    size = min(max(1, size), 60)
    offset = (page - 1) * size

    conn = get_db_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT product_id, name, brand, price, image_url
            FROM products
            ORDER BY product_id::int DESC
            LIMIT %s OFFSET %s
            """,
            (size, offset),
        )
        rows = cur.fetchall()
        total = fetch_total_products(cur)

        return {
            "type": "default",
            "items": [serialize_product_row(r) for r in rows],
            "total_pages": (total + size - 1) // size,
        }

    except Exception as e:
        print(f"Lỗi lấy sản phẩm: {e}")
        return {"type": "default", "items": [], "total_pages": 0}
    finally:
        cur.close()
        conn.close()


@app.get("/products/homepage")
def get_homepage_products(
    page: int = 1,
    size: int = 30,
    current_user_id: int = Depends(get_current_user),
):
    page = max(1, page)
    size = min(max(1, size), 60)
    user_id = str(current_user_id)
    offset = (page - 1) * size

    conn = get_db_conn()
    cur = conn.cursor()

    try:
        gold_count = fetch_gold_recommendation_count(cur, user_id)

        if gold_count > 0:
            rows = get_gold_homepage(cur, user_id, size, offset)
            total = fetch_total_products(cur)
            return {
                "type": "personalized_ranking",
                "items": [serialize_ranked_product_row(r) for r in rows],
                "total_pages": (total + size - 1) // size,
            }

        interaction_count = fetch_user_interaction_count(cur, user_id)

        if interaction_count > 0:
            rows = get_recent_behavioral_homepage(cur, user_id, size, offset)
            total = fetch_total_products(cur)
            return {
                "type": "fallback_behavior_ranking",
                "items": [serialize_ranked_product_row(r) for r in rows],
                "total_pages": (total + size - 1) // size,
            }

        cur.execute(
            """
            SELECT product_id, name, brand, price, image_url
            FROM products
            ORDER BY product_id::int DESC
            LIMIT %s OFFSET %s
            """,
            (size, offset),
        )
        rows = cur.fetchall()
        total = fetch_total_products(cur)

        return {
            "type": "default",
            "items": [serialize_product_row(r) for r in rows],
            "total_pages": (total + size - 1) // size,
        }

    except Exception as e:
        print(f"Lỗi homepage personalized ranking: {e}")
        return {"type": "default", "items": [], "total_pages": 0}
    finally:
        cur.close()
        conn.close()


@app.get("/products/detail/{p_id}")
def get_product_detail(p_id: str):
    conn = get_db_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM products WHERE product_id::text = %s", (str(p_id),))
        row = cur.fetchone()

        if row:
            col_names = [desc[0] for desc in cur.description]
            return dict(zip(col_names, row))
        return {}

    except Exception as e:
        print(f"Lỗi lấy chi tiết sản phẩm: {e}")
        return {}
    finally:
        cur.close()
        conn.close()


@app.get("/recommendations/{p_id}")
def get_item_recommendations(p_id: str, randomize: bool = False):
    conn = get_db_conn()
    cur = conn.cursor()
    try:
        if not table_exists(cur, "gold_item_similarity"):
            return []

        cur.execute(
            """
            SELECT
                p.product_id,
                p.name,
                p.brand,
                p.price,
                p.image_url,
                g.rank,
                g.similarity_score
            FROM gold_item_similarity g
            JOIN products p
              ON g.similar_product_id::text = p.product_id::text
            WHERE g.product_id::text = %s
            ORDER BY g.rank ASC
            LIMIT 20
            """,
            (str(p_id),),
        )
        rows = cur.fetchall()

        items = [
            {
                "product_id": r[0],
                "name": r[1],
                "brand": r[2],
                "price": r[3],
                "image_url": r[4],
                "rank": int(r[5]),
                "similarity_score": float(r[6]),
            }
            for r in rows
            if str(r[0]) != str(p_id)
        ]

        candidate_pool = items[:16] if len(items) > 16 else items

        if randomize and len(candidate_pool) > 5:
            picked = random.sample(candidate_pool, 5)
            picked.sort(key=lambda x: x.get("similarity_score", 0), reverse=True)
            return picked

        return candidate_pool[:5]

    except Exception as e:
        print(f"Lỗi gọi gợi ý item: {e}")
        return []
    finally:
        cur.close()
        conn.close()


@app.get("/recommendations/personalized/{p_id}")
def get_personalized_item_recommendations(
    p_id: str,
    randomize: bool = False,
    current_user_id: int = Depends(get_current_user),
):
    user_id = str(current_user_id)
    conn = get_db_conn()
    cur = conn.cursor()

    try:
        if not table_exists(cur, "gold_user_recommendations"):
            return []

        cur.execute(
            """
            SELECT
                p.product_id,
                p.name,
                p.brand,
                p.price,
                p.image_url,
                g.score
            FROM gold_user_recommendations g
            JOIN products p
              ON g.product_id::text = p.product_id::text
            WHERE g.user_id::text = %s
              AND g.product_id::text != %s
            ORDER BY g.score DESC
            LIMIT 30
            """,
            (user_id, str(p_id)),
        )
        rows = cur.fetchall()

        items = [
            {
                "product_id": r[0],
                "name": r[1],
                "brand": r[2],
                "price": r[3],
                "image_url": r[4],
                "score": float(r[5]),
            }
            for r in rows
        ]

        if not items:
            return []

        candidate_pool = items[:16] if len(items) > 16 else items

        if randomize and len(candidate_pool) > 5:
            picked = random.sample(candidate_pool, 5)
            picked.sort(key=lambda x: x.get("score", 0), reverse=True)
            return picked

        return candidate_pool[:5]

    except Exception as e:
        print(f"Lỗi personalized detail rec: {e}")
        return []
    finally:
        cur.close()
        conn.close()


@app.get("/recently-viewed")
def get_recently_viewed(current_user_id: int = Depends(get_current_user)):
    conn = get_db_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT DISTINCT ON (p.product_id)
                p.product_id, p.name, p.price, p.image_url, p.brand, i.interaction_id
            FROM interactions i
            JOIN products p ON i.product_id::text = p.product_id::text
            WHERE i.user_id = %s AND i.interaction_type = 'view'
            ORDER BY p.product_id, i.interaction_id DESC
            """,
            (current_user_id,),
        )
        rows = cur.fetchall()

        sorted_rows = sorted(rows, key=lambda x: x[5], reverse=True)

        return [
            {
                "product_id": r[0],
                "name": r[1],
                "price": r[2],
                "image_url": r[3],
                "brand": r[4],
            }
            for r in sorted_rows
        ]
    except Exception as e:
        print(f"Lỗi lấy recently viewed: {e}")
        return []
    finally:
        cur.close()
        conn.close()


@app.get("/orders")
def get_orders(current_user_id: int = Depends(get_current_user)):
    conn = get_db_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT p.product_id, p.name, p.price, p.image_url, p.brand, i.quantity
            FROM interactions i
            JOIN products p ON i.product_id::text = p.product_id::text
            WHERE i.user_id = %s AND i.interaction_type = 'purchase'
            ORDER BY i.interaction_id DESC
            """,
            (current_user_id,),
        )
        rows = cur.fetchall()

        return [
            {
                "product_id": r[0],
                "name": r[1],
                "price": r[2],
                "image_url": r[3],
                "brand": r[4],
                "quantity": r[5],
            }
            for r in rows
        ]
    except Exception as e:
        print(f"Lỗi lấy đơn hàng: {e}")
        return []
    finally:
        cur.close()
        conn.close()


@app.get("/cart")
def get_cart(current_user_id: int = Depends(get_current_user)):
    conn = get_db_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT DISTINCT ON (p.product_id)
                p.product_id, p.name, p.price, p.image_url, p.brand, i.quantity, i.interaction_id
            FROM interactions i
            JOIN products p ON i.product_id::text = p.product_id::text
            WHERE i.user_id = %s
              AND i.interaction_type = 'add_to_cart'
              AND NOT EXISTS (
                  SELECT 1
                  FROM interactions i2
                  WHERE i2.user_id = i.user_id
                    AND i2.product_id::text = i.product_id::text
                    AND i2.interaction_type = 'purchase'
              )
            ORDER BY p.product_id, i.interaction_id DESC
            """,
            (current_user_id,),
        )
        rows = cur.fetchall()

        sorted_rows = sorted(rows, key=lambda x: x[6], reverse=True)

        return [
            {
                "product_id": r[0],
                "name": r[1],
                "price": r[2],
                "image_url": r[3],
                "brand": r[4],
                "quantity": r[5],
            }
            for r in sorted_rows
        ]
    except Exception as e:
        print(f"Lỗi lấy giỏ hàng: {e}")
        return []
    finally:
        cur.close()
        conn.close()


@app.get("/favorites")
def get_favorites(current_user_id: int = Depends(get_current_user)):
    conn = get_db_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT DISTINCT ON (p.product_id)
                p.product_id, p.name, p.price, p.image_url, p.brand, i.interaction_id
            FROM interactions i
            JOIN products p ON i.product_id::text = p.product_id::text
            WHERE i.user_id = %s
              AND i.interaction_type = 'like'
            ORDER BY p.product_id, i.interaction_id DESC
            """,
            (current_user_id,),
        )
        rows = cur.fetchall()

        sorted_rows = sorted(rows, key=lambda x: x[5], reverse=True)

        return [
            {
                "product_id": r[0],
                "name": r[1],
                "price": r[2],
                "image_url": r[3],
                "brand": r[4],
            }
            for r in sorted_rows
        ]
    except Exception as e:
        print(f"Lỗi lấy favorites: {e}")
        return []
    finally:
        cur.close()
        conn.close()