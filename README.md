# Sneaker Recommendation System

Hệ thống gợi ý giày ứng dụng machine learning và dữ liệu hành vi người dùng để cá nhân hóa trải nghiệm mua sắm. Dự án kết hợp backend API, frontend web app, pipeline dữ liệu, huấn luyện mô hình gợi ý và cơ chế serving recommendation cho homepage và product detail page. :contentReference[oaicite:1]{index=1}

## Overview

Mục tiêu của dự án là xây dựng một hệ thống gợi ý giày theo phong cách các website bán giày trực tuyến hiện nay:

- Homepage vẫn hiển thị toàn bộ catalog, nhưng các sản phẩm phù hợp với hành vi người dùng sẽ được đẩy lên đầu.
- Product detail page hiển thị các sản phẩm tương tự dựa trên item similarity.
- Hệ thống tận dụng dữ liệu tương tác thật từ web như `view`, `like`, `add_to_cart`, `purchase` để huấn luyện và cập nhật recommendation. 

## Main Features

### 1. User interaction tracking
Backend ghi nhận các hành vi người dùng trên web thông qua API `/interact`, bao gồm:

- `view`
- `like`
- `add_to_cart`
- `purchase` 

### 2. Homepage personalization
API `/products/homepage` phục vụ danh sách sản phẩm theo 3 mức:

- `personalized_ranking`: dùng `gold_user_recommendations`
- `fallback_behavior_ranking`: dùng heuristic từ hành vi gần đây nếu chưa có bảng gold
- `default`: trả catalog mặc định nếu user chưa có interaction 

### 3. Item-to-item recommendation
API `/recommendations/{p_id}` sử dụng bảng `gold_item_similarity` để gợi ý các sản phẩm tương tự trên trang chi tiết sản phẩm. 

### 4. Personalized detail recommendation
API `/recommendations/personalized/{p_id}` lấy dữ liệu từ `gold_user_recommendations` để gợi ý sản phẩm cá nhân hóa cho user hiện tại. 

### 5. Production-safe training pipeline
Workflow GitHub Actions được dùng để train định kỳ các bảng gold recommendation. Thư mục `.github/workflows` có trong repo, và pipeline production hiện được thiết kế theo hướng chỉ đọc dữ liệu thật từ Neon rồi cập nhật bảng gold, không ghi đè interaction thật. :contentReference[oaicite:7]{index=7}

## Recommendation Architecture

Hệ thống recommendation gồm 2 lớp chính:

### A. `gold_item_similarity`
Bảng này được huấn luyện từ:

- hành vi người dùng
- metadata sản phẩm
- hybrid similarity = behavior similarity + content similarity

Trong đó, script train:
- đọc `interactions`
- chấm điểm hành vi với trọng số theo loại interaction
- áp dụng quantity factor và time decay
- tính content similarity từ metadata như `name`, `brand`, `category`, `style`, `type`, `purpose`, `color`, `material`
- sinh top sản phẩm tương tự cho mỗi item và lưu vào `gold_item_similarity` 

### B. `gold_user_recommendations`
Bảng này được huấn luyện từ:

- lịch sử tương tác user-item
- `gold_item_similarity`
- profile sở thích theo `brand`, `category`, `type`, `purpose`
- popularity boost toàn hệ thống
- normalization điểm recommendation theo từng user

Kết quả được lưu thành danh sách sản phẩm gợi ý cho từng user trong `gold_user_recommendations`. 

## Scoring Logic

Các interaction được gán trọng số khác nhau:

- `view = 0.5`
- `like = 2.0`
- `add_to_cart = 5.0`
- `purchase = 9.0` 

Ngoài ra hệ thống còn áp dụng:

- quantity factor cho `add_to_cart` và `purchase`
- time decay để ưu tiên hành vi gần đây
- event cap để tránh một loại interaction chi phối quá mức
- popularity boost để tăng điểm cho các sản phẩm đang được quan tâm nhiều
- normalization để dễ diễn giải điểm phù hợp trong giao diện và báo cáo 

## Project Structure

Repository hiện có các thư mục và file chính sau: :contentReference[oaicite:12]{index=12}

```bash
Sneaker-Recommendation-System/
├── .github/workflows/        # GitHub Actions workflow
├── archive/                  # Tài nguyên lưu trữ cũ
├── config/                   # Cấu hình
├── data/                     # Dữ liệu
├── hadoop/bin/               # Thành phần liên quan Hadoop
├── notebooks/                # Notebook phân tích / thử nghiệm
├── pipelines/                # Pipeline xử lý dữ liệu
├── sneaker-frontend/         # Frontend React
├── src/                      # Backend API + scripts train
├── requirements.txt          # Python dependencies
└── .gitignore
