<div align="center">

# 👟 Sneaker Recommendation System

### Personalized sneaker recommendation system with FastAPI, React, PostgreSQL, and Machine Learning

<p>
  <img src="https://img.shields.io/badge/Backend-FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/Frontend-React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB" />
  <img src="https://img.shields.io/badge/Database-PostgreSQL-336791?style=for-the-badge&logo=postgresql&logoColor=white" />
  <img src="https://img.shields.io/badge/ML-scikit--learn-F7931E?style=for-the-badge&logo=scikitlearn&logoColor=white" />
  <img src="https://img.shields.io/badge/Automation-GitHub_Actions-2088FF?style=for-the-badge&logo=githubactions&logoColor=white" />
</p>

<p>
  <img src="https://img.shields.io/badge/Status-Active-success?style=flat-square" />
  <img src="https://img.shields.io/badge/Project-Recommendation_System-blue?style=flat-square" />
  <img src="https://img.shields.io/badge/Focus-E--Commerce_Personalization-orange?style=flat-square" />
</p>

**A full-stack sneaker recommendation system that personalizes the homepage and product detail page using real user interactions, product metadata, and hybrid recommendation logic.**

</div>

---

## 📌 Overview

This project is built to simulate how modern online sneaker stores personalize product ranking.

Instead of showing the same homepage to every user, the system learns from real interaction signals such as:

- product views
- likes
- add-to-cart actions
- purchases

Then it uses those signals to:

- reorder the homepage while still keeping the full product catalog visible
- recommend similar products on the product detail page
- generate user-specific ranking outputs through scheduled training

---

## ✨ Highlights

- Personalized homepage ranking
- Similar product recommendation for product detail pages
- Real interaction-based training
- Hybrid recommendation strategy:
  - behavior similarity
  - content similarity
  - feature preference matching
  - popularity boosting
- Automatic production-safe training pipeline
- Full-stack architecture with backend, frontend, data pipeline, and model training

---

## 🖼️ Screenshots

> Replace the image paths below with your real screenshots after uploading them to the repo.

### Homepage
![Homepage Screenshot](./docs/screenshots/homepage.png)

### Product Detail Page
![Product Detail Screenshot](./docs/screenshots/product-detail.png)

### Personalized Ranking Example
![Recommendation Screenshot](./docs/screenshots/personalized-ranking.png)

### Model / Pipeline Demo
![Pipeline Screenshot](./docs/screenshots/pipeline-demo.png)

---

## 🎥 Demo

### Recommended demo flow

1. Register or log in
2. View several products from the same brand
3. Like a few products
4. Add one or more products to cart
5. Trigger training pipeline
6. Refresh homepage
7. Observe how related products move upward in ranking

### Demo scenarios

#### 1. New user
A user has no previous interactions.

**Expected behavior**
- Homepage shows default catalog

#### 2. Returning user with clear preferences
A user repeatedly interacts with Nike or Adidas products.

**Expected behavior**
- Homepage still shows the full catalog
- Products related to the user's recent interests appear earlier

#### 3. Product detail recommendation
A user opens a sneaker detail page.

**Expected behavior**
- Similar products are recommended based on item similarity

#### 4. After retraining
New interactions are recorded and the model is retrained.

**Expected behavior**
- Homepage ranking changes according to fresh behavior data

---

## 🧠 Recommendation Logic

The system uses two main recommendation outputs.

### 1. `gold_item_similarity`
Used for product detail recommendations.

It is generated using a hybrid combination of:

- **behavior similarity** from user-product interaction patterns
- **content similarity** from product metadata such as:
  - name
  - brand
  - category
  - style
  - type
  - purpose
  - color
  - material

### 2. `gold_user_recommendations`
Used for homepage personalization.

It is generated from:

- weighted user-item interaction scores
- item similarity propagation
- user preference profiles
- popularity boosting
- score normalization for more interpretable ranking

---

## 📊 Scoring Strategy

Different user actions contribute differently to the recommendation score.

Example interaction weights:

- `view = 0.5`
- `like = 2.0`
- `add_to_cart = 5.0`
- `purchase = 9.0`

The final score is influenced by:

- interaction strength
- quantity factor
- time decay
- item similarity
- product feature matching
- global popularity

For reporting and demo purposes, the relevance score can be interpreted as:

- higher score = more suitable for the user
- lower score = less relevant

---

## 🏗️ System Architecture

```text
┌──────────────────────┐
│      React Frontend  │
│  - Homepage          │
│  - Product Detail    │
│  - User Interactions │
└──────────┬───────────┘
           │ API Calls
           ▼
┌──────────────────────┐
│     FastAPI Backend  │
│  - Auth              │
│  - Products API      │
│  - Interaction API   │
│  - Recommendation API│
└──────────┬───────────┘
           │ Read / Write
           ▼
┌──────────────────────┐
│  PostgreSQL / Neon   │
│  - users             │
│  - products          │
│  - interactions      │
│  - gold tables       │
└──────────┬───────────┘
           │ Training
           ▼
┌─────────────────────────────┐
│ ML / Training Scripts       │
│ - train_item_similarity     │
│ - train_user_recommendation │
└──────────┬──────────────────┘
           │ Automation
           ▼
┌──────────────────────┐
│ GitHub Actions       │
│ Scheduled Retraining │
└──────────────────────┘
