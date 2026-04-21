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


def get_db_conn():
    return psycopg2.connect(os.environ.get("DATABASE_URL"))


def get_current_user(token: str = Depends(JWTBearer())):
    payload = decodeJWT(token)

    if not payload or "user_id" not in payload:
        raise HTTPException(status_code=403, detail="Invalid user token")

    try:
        return int(payload["user_id"])
    except Exception:
        raise HTTPException(status_code=403, detail="Invalid user id in token")


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
            (current_user_id, req.product_id, action_type, quantity),
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


def _serialize_rec_item(item):
    return {
        "product_id": item["product_id"],
        "name": item["name"],
        "price": item["price"],
        "image_url": item["image_url"],
        "brand": item.get("brand"),
    }


@app.get("/recommendations/{p_id}")
def get_item_recommendations(p_id: str, randomize: bool = False):
    conn = get_db_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT product_id, brand, category, style, type, purpose, color, material
            FROM products
            WHERE product_id::text = %s
            """,
            (p_id,),
        )
        base_product = cur.fetchone()

        if not base_product:
            return []

        _, base_brand, base_category, base_style, base_type, base_purpose, base_color, base_material = base_product

        cur.execute(
            """
            SELECT
                p.product_id,
                p.name,
                p.price,
                p.image_url,
                p.brand,
                p.category,
                p.style,
                p.type,
                p.purpose,
                p.color,
                p.material,
                g.rank,
                g.similarity_score
            FROM gold_item_similarity g
            JOIN products p
              ON g.similar_product_id::text = p.product_id::text
            WHERE g.product_id::text = %s
            ORDER BY g.rank ASC
            LIMIT 30
            """,
            (p_id,),
        )
        rows = cur.fetchall()

        ranked_items = []

        for r in rows:
            product_id, name, price, image_url, brand, category, style, type_, purpose, color, material, rank, similarity_score = r

            if str(product_id) == str(p_id):
                continue

            same_category = category and base_category and category == base_category
            same_type = type_ and base_type and type_ == base_type
            same_purpose = purpose and base_purpose and purpose == base_purpose
            same_style = style and base_style and style == base_style

            if not ((same_category and same_type) or same_purpose or same_style):
                continue

            candidate_name_text = (name or "").lower()

            if base_category and str(base_category).lower() == "men" and "women" in candidate_name_text:
                continue

            meta_bonus = 0

            if brand and base_brand and brand == base_brand:
                meta_bonus += 0.25
            if category and base_category and category == base_category:
                meta_bonus += 0.20
            if type_ and base_type and type_ == base_type:
                meta_bonus += 0.20
            if purpose and base_purpose and purpose == base_purpose:
                meta_bonus += 0.20
            if style and base_style and style == base_style:
                meta_bonus += 0.10
            if material and base_material and material == base_material:
                meta_bonus += 0.03
            if color and base_color and color == base_color:
                meta_bonus += 0.02

            final_score = float(similarity_score) + meta_bonus

            ranked_items.append(
                {
                    "product_id": product_id,
                    "name": name,
                    "price": price,
                    "image_url": image_url,
                    "brand": brand,
                    "final_score": final_score,
                }
            )

        ranked_items.sort(key=lambda x: x["final_score"], reverse=True)

        candidate_pool = ranked_items[:16] if len(ranked_items) > 16 else ranked_items

        if randomize and len(candidate_pool) > 5:
            selected_items = random.sample(candidate_pool, 5)
            selected_items.sort(key=lambda x: x["final_score"], reverse=True)
        else:
            selected_items = candidate_pool[:5]

        result = [_serialize_rec_item(item) for item in selected_items]

        existing_ids = [str(item["product_id"]) for item in result]
        existing_ids.append(str(p_id))

        if len(result) < 5:
            limit_needed = 5 - len(result)

            cur.execute(
                """
                SELECT
                    product_id,
                    name,
                    price,
                    image_url,
                    brand,
                    (
                        CASE WHEN brand = %s THEN 4 ELSE 0 END +
                        CASE WHEN category = %s THEN 3 ELSE 0 END +
                        CASE WHEN type = %s THEN 3 ELSE 0 END +
                        CASE WHEN purpose = %s THEN 2 ELSE 0 END +
                        CASE WHEN style = %s THEN 2 ELSE 0 END +
                        CASE WHEN material = %s THEN 1 ELSE 0 END +
                        CASE WHEN color = %s THEN 1 ELSE 0 END
                    ) AS fallback_score
                FROM products
                WHERE product_id::text != ALL(%s)
                  AND (
                    brand = %s
                    OR category = %s
                    OR type = %s
                    OR purpose = %s
                    OR style = %s
                    OR material = %s
                    OR color = %s
                  )
                ORDER BY fallback_score DESC, product_id::int DESC
                LIMIT %s
                """,
                (
                    base_brand,
                    base_category,
                    base_type,
                    base_purpose,
                    base_style,
                    base_material,
                    base_color,
                    existing_ids,
                    base_brand,
                    base_category,
                    base_type,
                    base_purpose,
                    base_style,
                    base_material,
                    base_color,
                    limit_needed,
                ),
            )

            fallback_rows = cur.fetchall()

            for r in fallback_rows:
                result.append(
                    {
                        "product_id": r[0],
                        "name": r[1],
                        "price": r[2],
                        "image_url": r[3],
                        "brand": r[4],
                    }
                )

        return result[:5]

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
        cur.execute(
            """
            SELECT product_id, brand, category, style, type, purpose, color, material
            FROM products
            WHERE product_id::text = %s
            """,
            (p_id,),
        )
        base_product = cur.fetchone()

        if not base_product:
            return []

        _, base_brand, base_category, base_style, base_type, base_purpose, base_color, base_material = base_product

        cur.execute(
            """
            SELECT COUNT(*)
            FROM interactions
            WHERE user_id = %s
            """,
            (user_id,),
        )
        interaction_count = cur.fetchone()[0]

        if interaction_count < 3:
            cur.execute(
                """
                SELECT
                    p.product_id,
                    p.name,
                    p.price,
                    p.image_url,
                    p.brand
                FROM gold_item_similarity g
                JOIN products p
                  ON g.similar_product_id::text = p.product_id::text
                WHERE g.product_id::text = %s
                ORDER BY g.rank ASC
                LIMIT 20
                """,
                (p_id,),
            )
            rows = cur.fetchall()

            fallback_items = [
                {
                    "product_id": r[0],
                    "name": r[1],
                    "price": r[2],
                    "image_url": r[3],
                    "brand": r[4],
                }
                for r in rows
                if str(r[0]) != str(p_id)
            ]

            candidate_pool = fallback_items[:16] if len(fallback_items) > 16 else fallback_items

            if randomize and len(candidate_pool) > 5:
                return random.sample(candidate_pool, 5)

            return candidate_pool[:5]

        cur.execute(
            """
            SELECT
                p.brand,
                p.category,
                p.type,
                p.purpose,
                i.interaction_type,
                COUNT(*) as cnt
            FROM interactions i
            JOIN products p
              ON i.product_id::text = p.product_id::text
            WHERE i.user_id = %s
              AND i.interaction_type IN ('view', 'like', 'add_to_cart', 'purchase')
            GROUP BY p.brand, p.category, p.type, p.purpose, i.interaction_type
            """,
            (user_id,),
        )
        profile_rows = cur.fetchall()

        interaction_weights = {
            "view": 1,
            "like": 3,
            "add_to_cart": 5,
            "purchase": 8,
        }

        brand_scores = {}
        category_scores = {}
        type_scores = {}
        purpose_scores = {}

        for brand, category, type_, purpose, interaction_type, cnt in profile_rows:
            score = interaction_weights.get(interaction_type, 0) * cnt
            if brand:
                brand_scores[brand] = brand_scores.get(brand, 0) + score
            if category:
                category_scores[category] = category_scores.get(category, 0) + score
            if type_:
                type_scores[type_] = type_scores.get(type_, 0) + score
            if purpose:
                purpose_scores[purpose] = purpose_scores.get(purpose, 0) + score

        cur.execute(
            """
            SELECT
                p.product_id,
                p.name,
                p.price,
                p.image_url,
                p.brand,
                p.category,
                p.style,
                p.type,
                p.purpose,
                p.color,
                p.material,
                g.rank,
                g.similarity_score
            FROM gold_item_similarity g
            JOIN products p
              ON g.similar_product_id::text = p.product_id::text
            WHERE g.product_id::text = %s
            ORDER BY g.rank ASC
            LIMIT 30
            """,
            (p_id,),
        )
        rows = cur.fetchall()

        ranked_items = []

        for r in rows:
            product_id, name, price, image_url, brand, category, style, type_, purpose, color, material, rank, similarity_score = r

            if str(product_id) == str(p_id):
                continue

            meta_bonus = 0
            if brand and base_brand and brand == base_brand:
                meta_bonus += 0.25
            if category and base_category and category == base_category:
                meta_bonus += 0.20
            if type_ and base_type and type_ == base_type:
                meta_bonus += 0.20
            if purpose and base_purpose and purpose == base_purpose:
                meta_bonus += 0.20
            if style and base_style and style == base_style:
                meta_bonus += 0.10
            if material and base_material and material == base_material:
                meta_bonus += 0.03
            if color and base_color and color == base_color:
                meta_bonus += 0.02

            user_bonus = 0
            user_bonus += brand_scores.get(brand, 0) * 0.08
            user_bonus += category_scores.get(category, 0) * 0.05
            user_bonus += type_scores.get(type_, 0) * 0.04
            user_bonus += purpose_scores.get(purpose, 0) * 0.03

            final_score = float(similarity_score) + meta_bonus + user_bonus

            ranked_items.append(
                {
                    "product_id": product_id,
                    "name": name,
                    "price": price,
                    "image_url": image_url,
                    "brand": brand,
                    "final_score": final_score,
                }
            )

        ranked_items.sort(key=lambda x: x["final_score"], reverse=True)

        candidate_pool = ranked_items[:16] if len(ranked_items) > 16 else ranked_items

        if randomize and len(candidate_pool) > 5:
            selected_items = random.sample(candidate_pool, 5)
            selected_items.sort(key=lambda x: x["final_score"], reverse=True)
        else:
            selected_items = candidate_pool[:5]

        return selected_items

    except Exception as e:
        print(f"Lỗi personalized detail rec: {e}")
        return []
    finally:
        cur.close()
        conn.close()


@app.get("/products")
def get_products(page: int = 1, size: int = 30):
    offset = (page - 1) * size
    conn = get_db_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT product_id, name, brand, price, image_url
            FROM products
            ORDER BY product_id::int
            LIMIT %s OFFSET %s
            """,
            (size, offset),
        )
        rows = cur.fetchall()

        products = [
            {
                "product_id": r[0],
                "name": r[1],
                "brand": r[2],
                "price": r[3],
                "image_url": r[4],
            }
            for r in rows
        ]

        cur.execute("SELECT COUNT(*) FROM products")
        total = cur.fetchone()[0]

        return {"items": products, "total_pages": (total + size - 1) // size}

    except Exception as e:
        print(f"Lỗi lấy sản phẩm: {e}")
        return {"items": [], "total_pages": 0}
    finally:
        cur.close()
        conn.close()


@app.get("/products/detail/{p_id}")
def get_product_detail(p_id: str):
    conn = get_db_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM products WHERE product_id::text = %s", (p_id,))
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