from fastapi import FastAPI, HTTPException, Depends
import psycopg2
import os
from dotenv import load_dotenv
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from src.auth.hash_utils import hash_password, verify_password
from src.auth.schemas import UserCreate, UserResponse
from src.auth.jwt_handler import signJWT
from src.auth.jwt_bearer import JWTBearer

load_dotenv()
app = FastAPI()

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
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

        raw_password = user.password

        cur.execute("""
            INSERT INTO users (name, password, age, gender, created_at) 
            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP) RETURNING user_id
        """, (user.username, raw_password, user.age, user.gender))

        user_id = cur.fetchone()[0]
        conn.commit()

        return {"user_id": user_id, "username": user.username}

    except Exception as e:
        print(f"--- LỖI TẠI ĐÂY: {e} ---")
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


class LoginRequest(BaseModel):
    username: str
    password: str


@app.post("/login")
def login_user(req: LoginRequest):
    conn = get_db_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT user_id, password FROM users WHERE name = %s", (req.username,))
        row = cur.fetchone()

        if not row or req.password != row[1]:
            raise HTTPException(status_code=401, detail="Invalid username or password")

        return signJWT(row[0])
    finally:
        cur.close()
        conn.close()


class InteractRequest(BaseModel):
    product_id: str
    action_type: str


@app.post("/interact", dependencies=[Depends(JWTBearer())])
def record_interaction(req: InteractRequest, token: dict = Depends(JWTBearer())):
    user_id = token.get("user_id")
    conn = get_db_conn()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO interactions (
                user_id,
                product_id,
                interaction_type,
                quantity,
                interaction_time
            )
            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
        """, (
            user_id,
            req.product_id,
            req.action_type,
            1
        ))
        conn.commit()
        return {"message": "Success"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


@app.get("/recommendations/{p_id}")
def get_item_recommendations(p_id: str):
    conn = get_db_conn()
    cur = conn.cursor()
    try:
        # 1. Lấy sản phẩm gốc
        cur.execute("""
            SELECT product_id, brand, category, style, type, purpose, color, material
            FROM products
            WHERE product_id::text = %s
        """, (p_id,))
        base_product = cur.fetchone()

        if not base_product:
            return []

        _, base_brand, base_category, base_style, base_type, base_purpose, base_color, base_material = base_product

        # 2. Candidate từ gold_item_similarity
        cur.execute("""
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
            LIMIT 20
        """, (p_id,))
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

            # lọc cứng bớt item quá lệch
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

            ranked_items.append({
                "product_id": product_id,
                "name": name,
                "price": price,
                "image_url": image_url,
                "brand": brand,
                "category": category,
                "style": style,
                "type": type_,
                "purpose": purpose,
                "color": color,
                "material": material,
                "rank": rank,
                "similarity_score": float(similarity_score),
                "final_score": final_score,
            })

        ranked_items.sort(key=lambda x: x["final_score"], reverse=True)

        result = [
            {
                "product_id": item["product_id"],
                "name": item["name"],
                "price": item["price"],
                "image_url": item["image_url"],
            }
            for item in ranked_items[:5]
        ]

        existing_ids = [str(item["product_id"]) for item in result]
        existing_ids.append(str(p_id))

        # 3. Fallback có chấm điểm rõ ràng
        if len(result) < 5:
            limit_needed = 5 - len(result)

            cur.execute("""
                SELECT
                    product_id,
                    name,
                    price,
                    image_url,
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
            """, (
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

                limit_needed
            ))

            fallback_rows = cur.fetchall()

            for r in fallback_rows:
                result.append({
                    "product_id": r[0],
                    "name": r[1],
                    "price": r[2],
                    "image_url": r[3]
                })

        return result[:5]

    except Exception as e:
        print(f"Lỗi gọi gợi ý item: {e}")
        return []
    finally:
        cur.close()
        conn.close()


@app.get("/recommendations/personalized/{p_id}", dependencies=[Depends(JWTBearer())])
def get_personalized_item_recommendations(
    p_id: str,
    token: dict = Depends(JWTBearer())
):
    user_id = str(token.get("user_id"))
    conn = get_db_conn()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT product_id, brand, category, style, type, purpose, color, material
            FROM products
            WHERE product_id::text = %s
        """, (p_id,))
        base_product = cur.fetchone()

        if not base_product:
            return []

        _, base_brand, base_category, base_style, base_type, base_purpose, base_color, base_material = base_product

        cur.execute("""
            SELECT COUNT(*)
            FROM interactions
            WHERE user_id = %s
        """, (user_id,))
        interaction_count = cur.fetchone()[0]

        if interaction_count < 3:
            cur.execute("""
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
                LIMIT 5
            """, (p_id,))
            rows = cur.fetchall()

            return [
                {
                    "product_id": r[0],
                    "name": r[1],
                    "price": r[2],
                    "image_url": r[3],
                }
                for r in rows
                if str(r[0]) != str(p_id)
            ]

        cur.execute("""
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
        """, (user_id,))
        profile_rows = cur.fetchall()

        interaction_weights = {
            "view": 1,
            "like": 3,
            "add_to_cart": 5,
            "purchase": 8
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

        cur.execute("""
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
            LIMIT 20
        """, (p_id,))
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

            ranked_items.append({
                "product_id": product_id,
                "name": name,
                "price": price,
                "image_url": image_url,
                "final_score": final_score,
            })

        ranked_items.sort(key=lambda x: x["final_score"], reverse=True)

        return ranked_items[:5]

    except Exception as e:
        print(f"Lỗi personalized detail rec: {e}")
        return []
    finally:
        cur.close()
        conn.close()


@app.get("/recommendations/for-you", dependencies=[Depends(JWTBearer())])
def get_recommendations_for_you(token: dict = Depends(JWTBearer())):
    user_id = str(token.get("user_id"))
    conn = get_db_conn()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT COUNT(*) 
            FROM interactions 
            WHERE user_id = %s
        """, (user_id,))
        interaction_count = cur.fetchone()[0]

        if interaction_count >= 3:
            cur.execute("""
                SELECT p.product_id, p.name, p.price, p.image_url, g.score
                FROM gold_user_recommendations g
                JOIN products p ON g.product_id::text = p.product_id
                WHERE g.user_id = %s
                ORDER BY g.score DESC
                LIMIT 10
            """, (user_id,))

            rows = cur.fetchall()

            if rows:
                return {
                    "type": "personalized",
                    "items": [
                        {
                            "product_id": r[0],
                            "name": r[1],
                            "price": r[2],
                            "image_url": r[3],
                            "score": r[4]
                        }
                        for r in rows
                    ]
                }

        cur.execute("""
            SELECT product_id
            FROM interactions
            WHERE user_id = %s
            ORDER BY interaction_id DESC
            LIMIT 1
        """, (user_id,))

        last_product = cur.fetchone()

        if last_product:
            product_id = last_product[0]

            cur.execute("""
                SELECT p.product_id, p.name, p.price, p.image_url
                FROM gold_item_similarity g
                JOIN products p ON g.similar_product_id::text = p.product_id
                WHERE g.product_id::text = %s
                ORDER BY g.rank ASC
                LIMIT 10
            """, (product_id,))

            rows = cur.fetchall()

            return {
                "type": "fallback_item_similarity",
                "items": [
                    {
                        "product_id": r[0],
                        "name": r[1],
                        "price": r[2],
                        "image_url": r[3]
                    }
                    for r in rows
                ]
            }

        return {
            "type": "empty",
            "items": []
        }

    finally:
        cur.close()
        conn.close()


@app.get("/products")
def get_products(page: int = 1, size: int = 24):
    offset = (page - 1) * size
    conn = get_db_conn()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT product_id, name, price, image_url
            FROM products
            ORDER BY product_id::int
            LIMIT %s OFFSET %s
        """, (size, offset))
        rows = cur.fetchall()

        products = [
            {"product_id": r[0], "name": r[1], "price": r[2], "image_url": r[3]}
            for r in rows
        ]

        cur.execute("SELECT COUNT(*) FROM products")
        total = cur.fetchone()[0]

        return {
            "items": products,
            "total_pages": (total + size - 1) // size
        }
    except Exception as e:
        print(f"Lỗi lấy sản phẩm: {e}")
        return {"items": [], "total_pages": 0}
    finally:
        cur.close()
        conn.close()


@app.get("/products/personalized", dependencies=[Depends(JWTBearer())])
def get_personalized_products(
    page: int = 1,
    size: int = 24,
    token: dict = Depends(JWTBearer())
):
    user_id = str(token.get("user_id"))
    offset = (page - 1) * size

    conn = get_db_conn()
    cur = conn.cursor()

    try:
        cur.execute("""
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
        """, (user_id,))
        profile_rows = cur.fetchall()

        if not profile_rows:
            cur.execute("""
                SELECT product_id, name, price, image_url
                FROM products
                ORDER BY product_id::int
                LIMIT %s OFFSET %s
            """, (size, offset))
            rows = cur.fetchall()

            cur.execute("SELECT COUNT(*) FROM products")
            total = cur.fetchone()[0]

            return {
                "type": "default",
                "items": [
                    {
                        "product_id": r[0],
                        "name": r[1],
                        "price": r[2],
                        "image_url": r[3]
                    }
                    for r in rows
                ],
                "total_pages": (total + size - 1) // size
            }

        interaction_weights = {
            "view": 1,
            "like": 3,
            "add_to_cart": 5,
            "purchase": 8
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

        cur.execute("""
            SELECT product_id, name, price, image_url, brand, category, type, purpose
            FROM products
        """)
        all_products = cur.fetchall()

        ranked = []
        for r in all_products:
            product_id, name, price, image_url, brand, category, type_, purpose = r

            score = 0
            score += brand_scores.get(brand, 0) * 2.2
            score += category_scores.get(category, 0) * 1.0
            score += type_scores.get(type_, 0) * 0.8
            score += purpose_scores.get(purpose, 0) * 0.7

            ranked.append({
                "product_id": product_id,
                "name": name,
                "price": price,
                "image_url": image_url,
                "brand": brand,
                "score": score
            })

        ranked.sort(key=lambda x: (x["score"], -int(x["product_id"])), reverse=True)

        brand_seen = {}
        diversified = []

        for item in ranked:
            brand = item.get("brand")

            adjusted_item = item.copy()
            if brand:
                count = brand_seen.get(brand, 0)
                adjusted_item["score"] = adjusted_item["score"] - (count * 5)
                brand_seen[brand] = count + 1

            diversified.append(adjusted_item)

        diversified.sort(key=lambda x: (x["score"], -int(x["product_id"])), reverse=True)

        total = len(diversified)
        paged = diversified[offset: offset + size]

        return {
            "type": "personalized",
            "items": [
                {
                    "product_id": item["product_id"],
                    "name": item["name"],
                    "price": item["price"],
                    "image_url": item["image_url"]
                }
                for item in paged
            ],
            "total_pages": (total + size - 1) // size
        }

    except Exception as e:
        print(f"Lỗi personalized products: {e}")
        return {
            "type": "error",
            "items": [],
            "total_pages": 0
        }
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
            product_data = dict(zip(col_names, row))
            return product_data
        return {}
    except Exception as e:
        print(f"Lỗi lấy chi tiết Silver: {e}")
        return {}
    finally:
        cur.close()
        conn.close()


@app.get("/recently-viewed", dependencies=[Depends(JWTBearer())])
def get_recently_viewed(token: dict = Depends(JWTBearer())):
    user_id = token.get("user_id")
    conn = get_db_conn()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT DISTINCT ON (p.product_id)
                p.product_id, p.name, p.price, p.image_url, i.interaction_id
            FROM interactions i
            JOIN products p ON i.product_id::text = p.product_id::text
            WHERE i.user_id = %s AND i.interaction_type = 'view'
            ORDER BY p.product_id, i.interaction_id DESC
        """, (user_id,))
        rows = cur.fetchall()

        sorted_rows = sorted(rows, key=lambda x: x[4], reverse=True)

        return [
            {
                "product_id": r[0],
                "name": r[1],
                "price": r[2],
                "image_url": r[3]
            }
            for r in sorted_rows
        ]
    except Exception as e:
        print(f"Lỗi lấy recently viewed: {e}")
        return []
    finally:
        cur.close()
        conn.close()


@app.get("/orders", dependencies=[Depends(JWTBearer())])
def get_orders(token: dict = Depends(JWTBearer())):
    user_id = token.get("user_id")
    conn = get_db_conn()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT p.product_id, p.name, p.price, p.image_url
            FROM interactions i
            JOIN products p ON i.product_id::text = p.product_id::text
            WHERE i.user_id = %s AND i.interaction_type = 'purchase'
            ORDER BY i.interaction_id DESC
        """, (user_id,))
        rows = cur.fetchall()
        return [{"product_id": r[0], "name": r[1], "price": r[2], "image_url": r[3]} for r in rows]
    except Exception as e:
        print(f"Lỗi lấy đơn hàng: {e}")
        return []
    finally:
        cur.close()
        conn.close()


@app.get("/cart", dependencies=[Depends(JWTBearer())])
def get_cart(token: dict = Depends(JWTBearer())):
    user_id = token.get("user_id")
    conn = get_db_conn()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT DISTINCT ON (p.product_id)
                p.product_id, p.name, p.price, p.image_url, i.interaction_id
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
        """, (user_id,))
        rows = cur.fetchall()

        sorted_rows = sorted(rows, key=lambda x: x[4], reverse=True)

        return [{"product_id": r[0], "name": r[1], "price": r[2], "image_url": r[3]} for r in sorted_rows]
    except Exception as e:
        print(f"Lỗi lấy giỏ hàng: {e}")
        return []
    finally:
        cur.close()
        conn.close()


@app.get("/favorites", dependencies=[Depends(JWTBearer())])
def get_favorites(token: dict = Depends(JWTBearer())):
    user_id = token.get("user_id")
    conn = get_db_conn()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT DISTINCT ON (p.product_id)
                p.product_id, p.name, p.price, p.image_url, i.interaction_id
            FROM interactions i
            JOIN products p ON i.product_id::text = p.product_id::text
            WHERE i.user_id = %s
              AND i.interaction_type = 'like'
            ORDER BY p.product_id, i.interaction_id DESC
        """, (user_id,))
        rows = cur.fetchall()

        sorted_rows = sorted(rows, key=lambda x: x[4], reverse=True)

        return [
            {
                "product_id": r[0],
                "name": r[1],
                "price": r[2],
                "image_url": r[3]
            }
            for r in sorted_rows
        ]
    except Exception as e:
        print(f"Lỗi lấy favorites: {e}")
        return []
    finally:
        cur.close()
        conn.close()