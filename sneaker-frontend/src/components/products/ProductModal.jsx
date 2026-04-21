import React, { useMemo, useState, useEffect } from 'react';

function ProductModal({
  product,
  recommendations = [],
  loadingRecommendations = false,
  onClose,
  onLike,
  onAddToCart,
  onPurchase,
  onOpenProduct,
}) {
  const [selectedImage, setSelectedImage] = useState('');
  const [quantity, setQuantity] = useState(1);
  const [selectedSize, setSelectedSize] = useState('40');

  useEffect(() => {
    if (product?.image_url) {
      setSelectedImage(product.image_url);
    }
    setQuantity(1);
    setSelectedSize('40');
  }, [product]);

  const galleryImages = useMemo(() => {
    if (!product?.image_url) return [];

    // Vì dữ liệu hiện tại thường chỉ có 1 ảnh,
    // ta tạm lặp lại ảnh để tạo cảm giác gallery.
    return [
      product.image_url,
      product.image_url,
      product.image_url,
      product.image_url,
      product.image_url,
    ];
  }, [product]);

  if (!product) return null;

  const priceText = Number(product.price || 0).toLocaleString('vi-VN');
  const sizes = ['40', '40.5', '41', '42', '42.5', '43'];

  const handleDecrease = () => {
    setQuantity((prev) => Math.max(1, prev - 1));
  };

  const handleIncrease = () => {
    setQuantity((prev) => prev + 1);
  };

  return (
    <div className="product-modal-overlay" onClick={onClose}>
      <div
        className="product-modal-container"
        onClick={(e) => e.stopPropagation()}
      >
        <button className="product-modal-close" onClick={onClose}>
          ×
        </button>

        <div className="product-modal-main">
          {/* LEFT */}
          <div className="product-modal-left">
            <div className="product-gallery">
              <div className="product-thumbnails">
                {galleryImages.map((img, index) => (
                  <button
                    key={`${img}-${index}`}
                    className={`thumb-btn ${
                      selectedImage === img ? 'active' : ''
                    }`}
                    onClick={() => setSelectedImage(img)}
                  >
                    <img src={img} alt={`${product.name}-${index}`} />
                  </button>
                ))}
              </div>

              <div className="product-main-image-box">
                <img
                  src={selectedImage || product.image_url}
                  alt={product.name}
                  className="product-main-image"
                />
              </div>
            </div>
          </div>

          {/* RIGHT */}
          <div className="product-modal-right">
            <div className="product-detail-top">
              <h2 className="product-detail-title">{product.name}</h2>

              <div className="product-detail-rating">
                <span className="stars">★★★★★</span>
                <span className="review-text">2 đánh giá</span>
              </div>

              <div className="product-detail-price-row">
                <span className="product-detail-price">{priceText}$</span>
                <span className="product-detail-old-price">
                  {(Number(product.price || 0) * 1.08).toLocaleString('vi-VN')}$
                </span>
              </div>

              <div className="product-meta-grid">
                <div><strong>Brand:</strong> {product.brand || 'N/A'}</div>
                <div><strong>Danh mục:</strong> {product.category || 'N/A'}</div>
                <div><strong>Kiểu:</strong> {product.style || 'N/A'}</div>
                <div><strong>Loại:</strong> {product.type || 'N/A'}</div>
                <div><strong>Mục đích:</strong> {product.purpose || 'N/A'}</div>
                <div><strong>Màu sắc:</strong> {product.color || 'N/A'}</div>
                <div><strong>Chất liệu:</strong> {product.material || 'N/A'}</div>
                <div><strong>Mã SP:</strong> #{product.product_id}</div>
              </div>
            </div>

            <div className="detail-divider" />

            <div className="product-size-section">
              <h4>Chọn size</h4>
              <div className="size-list">
                {sizes.map((size) => (
                  <button
                    key={size}
                    className={`size-btn ${
                      selectedSize === size ? 'active' : ''
                    }`}
                    onClick={() => setSelectedSize(size)}
                  >
                    {size}
                  </button>
                ))}
              </div>
            </div>

            <div className="product-quantity-row">
              <div className="quantity-box">
                <button onClick={handleDecrease}>-</button>
                <span>{quantity}</span>
                <button onClick={handleIncrease}>+</button>
              </div>

              <div className="product-stock-note">
                <span className="in-stock">✔ Còn hàng</span>
                <span>Size đang chọn: {selectedSize}</span>
              </div>
            </div>

            <div className="product-action-row">
              <button
                className="primary-action-btn blue"
                onClick={() => onAddToCart(product.product_id)}
              >
                Thêm vào giỏ
              </button>

              <button
                className="primary-action-btn red"
                onClick={() => onPurchase(product.product_id)}
              >
                Mua ngay
              </button>
            </div>

            <div className="secondary-action-row">
              <button
                className="secondary-btn"
                onClick={() => onLike(product.product_id)}
              >
                Yêu thích
              </button>

              <button
                className="secondary-btn outline"
                onClick={() => onOpenProduct(product.product_id)}
              >
                Làm mới gợi ý
              </button>
            </div>

            <div className="why-box">
              <h3>Tại sao nên chọn sản phẩm này?</h3>
              <ul>
                <li>Thiết kế thể thao, hiện đại, phù hợp demo đồ án.</li>
                <li>Thông tin sản phẩm hiển thị rõ ràng, trực quan.</li>
                <li>Dễ kết hợp với tính năng recommendation theo từng đôi giày.</li>
                <li>Trải nghiệm giống website bán hàng thực tế hơn.</li>
              </ul>
            </div>
          </div>
        </div>

        {/* RECOMMENDATIONS */}
        <div className="recommendation-section">
          <div className="recommendation-header">
            <h3>Gợi ý sản phẩm liên quan</h3>
            <p>
              Những sản phẩm được đề xuất dựa trên sản phẩm bạn đang xem
            </p>
          </div>

          {loadingRecommendations ? (
            <p className="recommendation-loading">Đang tải gợi ý...</p>
          ) : recommendations.length === 0 ? (
            <p className="recommendation-loading">
              Chưa có gợi ý cho sản phẩm này.
            </p>
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
        </div>
      </div>
    </div>
  );
}

export default ProductModal;