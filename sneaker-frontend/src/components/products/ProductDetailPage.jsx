import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  fetchProductDetailApi,
  interactProductApi,
} from '../../services/productService';
import {
  fetchItemRecommendationsApi,
  fetchPersonalizedItemRecommendationsApi,
} from '../../services/recommendationService';

function ProductDetailPage({
  onLike,
  onAddToCart,
  onPurchase,
  onOpenProduct,
}) {
  const { id } = useParams();
  const navigate = useNavigate();

  const [product, setProduct] = useState(null);
  const [recommendations, setRecommendations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadingRecommendations, setLoadingRecommendations] = useState(true);

  const [quantity, setQuantity] = useState(1);
  const [selectedSize, setSelectedSize] = useState('40');

  const sizes = ['40', '40.5', '41', '42', '42.5', '43'];

  const loadRecommendations = async (productId, randomize = false) => {
    setLoadingRecommendations(true);
    try {
      let recs = [];

      try {
        const personalized = await fetchPersonalizedItemRecommendationsApi(productId, randomize);
        if (Array.isArray(personalized) && personalized.length > 0) {
          recs = personalized;
        } else {
          recs = await fetchItemRecommendationsApi(productId, randomize);
        }
      } catch (err) {
        recs = await fetchItemRecommendationsApi(productId, randomize);
      }

      setRecommendations(Array.isArray(recs) ? recs : []);
    } catch (err) {
      console.error('recommendation error:', err);
      setRecommendations([]);
    } finally {
      setLoadingRecommendations(false);
    }
  };

  useEffect(() => {
    let mounted = true;

    const loadProductDetail = async () => {
      setLoading(true);
      setLoadingRecommendations(true);
      setProduct(null);
      setRecommendations([]);
      setQuantity(1);
      setSelectedSize('40');

      try {
        const detail = await fetchProductDetailApi(id);

        if (!mounted) return;
        setProduct(detail);
        setLoading(false);

        interactProductApi(id, 'view', 1).catch((err) => {
          console.error('view interaction error:', err);
        });

        await loadRecommendations(id, false);
      } catch (err) {
        console.error('load product detail error:', err);
        if (mounted) {
          setLoading(false);
          setLoadingRecommendations(false);
          alert('Không tải được chi tiết sản phẩm.');
        }
      }
    };

    loadProductDetail();
    window.scrollTo({ top: 0, behavior: 'smooth' });

    return () => {
      mounted = false;
    };
  }, [id]);

  const handleLikeClick = async () => {
    if (!product) return;
    await onLike(product.product_id);
  };

  const handleAddToCartClick = async () => {
    if (!product) return;
    await onAddToCart(product.product_id, quantity);
  };

  const handlePurchaseClick = async () => {
    if (!product) return;
    await onPurchase(product.product_id, quantity);
  };

  const handleRefreshRecommendations = async () => {
    if (!product) return;
    await loadRecommendations(product.product_id, true);
    alert('Đã làm mới gợi ý!');
  };

  if (loading) {
    return (
      <div className="store-panel">
        <p className="loading-text">Đang tải chi tiết sản phẩm...</p>
      </div>
    );
  }

  if (!product) {
    return (
      <div className="store-panel">
        <p className="loading-text">Không tìm thấy sản phẩm.</p>
      </div>
    );
  }

  const priceText = Number(product.price || 0).toLocaleString('vi-VN');
  const oldPriceText = (Number(product.price || 0) * 1.08).toLocaleString('vi-VN');

  return (
    <div className="product-page">
      <div className="product-page-container">
        <button className="back-btn" onClick={() => navigate(-1)}>
          ← Quay lại
        </button>

        <div className="product-page-main">
          <div className="product-page-left">
            <div className="product-main-image-box-page single-image">
              <img
                src={product.image_url}
                alt={product.name}
                className="product-main-image-page"
              />
            </div>
          </div>

          <div className="product-page-right">
            <h1 className="product-page-title">{product.name}</h1>

            <div className="product-page-price-row">
              <span className="product-page-price">{priceText}$</span>
              <span className="product-page-old-price">{oldPriceText}$</span>
            </div>

            <div className="product-page-meta">
              <div><strong>Brand:</strong> {product.brand || 'N/A'}</div>
              <div><strong>Danh mục:</strong> {product.category || 'N/A'}</div>
              <div><strong>Kiểu:</strong> {product.style || 'N/A'}</div>
              <div><strong>Loại:</strong> {product.type || 'N/A'}</div>
              <div><strong>Mục đích:</strong> {product.purpose || 'N/A'}</div>
              <div><strong>Màu sắc:</strong> {product.color || 'N/A'}</div>
              <div><strong>Chất liệu:</strong> {product.material || 'N/A'}</div>
              <div><strong>Mã SP:</strong> #{product.product_id}</div>
            </div>

            <div className="detail-divider" />

            <div className="product-size-section">
              <h4>Chọn size</h4>
              <div className="size-list">
                {sizes.map((size) => (
                  <button
                    key={size}
                    className={`size-btn ${selectedSize === size ? 'active' : ''}`}
                    onClick={() => setSelectedSize(size)}
                  >
                    {size}
                  </button>
                ))}
              </div>
            </div>

            <div className="product-quantity-row">
              <div className="quantity-box">
                <button onClick={() => setQuantity((prev) => Math.max(1, prev - 1))}>-</button>
                <span>{quantity}</span>
                <button onClick={() => setQuantity((prev) => prev + 1)}>+</button>
              </div>

              <div className="product-stock-note">
                <span className="in-stock">✔ Còn hàng</span>
                <span>Size đang chọn: {selectedSize}</span>
              </div>
            </div>

            <div className="product-action-row">
              <button
                className="primary-action-btn blue"
                onClick={handleAddToCartClick}
              >
                Thêm vào giỏ
              </button>

              <button
                className="primary-action-btn red"
                onClick={handlePurchaseClick}
              >
                Mua ngay
              </button>
            </div>

            <div className="secondary-action-row">
              <button
                className="secondary-btn"
                onClick={handleLikeClick}
              >
                Yêu thích
              </button>

              <button
                className="secondary-btn outline"
                onClick={handleRefreshRecommendations}
              >
                Làm mới gợi ý
              </button>
            </div>
          </div>
        </div>

        <section className="product-related-section">
          <div className="recommendation-header">
            <h3>Gợi ý sản phẩm liên quan</h3>
            <p>Đề xuất theo sản phẩm bạn đang xem</p>
          </div>

          {loadingRecommendations ? (
            <p className="recommendation-loading">Đang tải gợi ý...</p>
          ) : recommendations.length === 0 ? (
            <p className="recommendation-loading">Chưa có gợi ý cho sản phẩm này.</p>
          ) : (
            <div className="recommendation-grid">
              {recommendations.map((item) => (
                <div
                  key={item.product_id}
                  className="recommendation-card"
                  onClick={() => onOpenProduct(item.product_id)}
                >
                  <div className="recommendation-image-box">
                    <img src={item.image_url} alt={item.name} />
                  </div>

                  <div className="recommendation-body">
                    <div className="recommendation-brand">
                      {item.brand || 'Sneaker'}
                    </div>

                    <h4 className="recommendation-name">{item.name}</h4>

                    <p className="recommendation-price">
                      {Number(item.price || 0).toLocaleString('vi-VN')}$
                    </p>

                    <button
                      className="recommendation-btn"
                      onClick={(e) => {
                        e.stopPropagation();
                        onOpenProduct(item.product_id);
                      }}
                    >
                      Xem chi tiết
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

export default ProductDetailPage;