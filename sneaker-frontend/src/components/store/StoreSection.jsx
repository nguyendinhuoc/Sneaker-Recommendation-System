import React from 'react';

function getVisiblePages(currentPage, totalPages) {
  if (totalPages <= 7) {
    return Array.from({ length: totalPages }, (_, index) => index + 1);
  }

  if (currentPage <= 4) {
    return [1, 2, 3, 4, 5, '...', totalPages];
  }

  if (currentPage >= totalPages - 3) {
    return [1, '...', totalPages - 4, totalPages - 3, totalPages - 2, totalPages - 1, totalPages];
  }

  return [1, '...', currentPage - 1, currentPage, currentPage + 1, '...', totalPages];
}

function getHomepageTitle(type) {
  if (type === 'personalized_ranking') {
    return 'Dành riêng cho bạn';
  }

  if (type === 'fallback_behavior_ranking') {
    return 'Ưu tiên theo hành vi gần đây';
  }

  return 'Khám phá sản phẩm';
}

function getHomepageSubtitle(type) {
  if (type === 'personalized_ranking') {
    return 'Toàn bộ catalog vẫn được giữ nguyên, nhưng các sản phẩm gần với hành vi xem, thích, thêm giỏ hàng và mua của bạn sẽ được đẩy lên đầu giống cách các web bán giày trực tuyến hiện nay hoạt động.';
  }

  if (type === 'fallback_behavior_ranking') {
    return 'Khi chưa có đủ dữ liệu gold ranking, hệ thống tạm thời ưu tiên những sản phẩm có thương hiệu, loại và mục đích sử dụng gần với hành vi gần đây của bạn.';
  }

  return 'Danh sách mặc định của cửa hàng. Khi bạn bắt đầu tương tác nhiều hơn, hệ thống sẽ dần cá nhân hóa thứ tự hiển thị sản phẩm.';
}

function getHomepageBadge(type) {
  if (type === 'personalized_ranking') {
    return 'Personalized ranking';
  }

  if (type === 'fallback_behavior_ranking') {
    return 'Behavior fallback';
  }

  return 'Default catalog';
}

function formatPrice(value) {
  return `${Number(value || 0).toLocaleString('vi-VN')}$`;
}

function ProductCard({ item, onViewProduct }) {
  return (
    <div className="product-card">
      <div className="product-image-box">
        <img
          src={item.image_url}
          alt={item.name}
          className="product-image"
        />
      </div>

      <div className="product-body">
        <div className="product-brand">{item.brand || 'Sneaker'}</div>

        <h4 className="product-name">{item.name}</h4>

        <p className="product-price">{formatPrice(item.price)}</p>

        {item.score != null ? (
          <p className="product-score">
            Độ phù hợp: {Number(item.score).toFixed(2)}
          </p>
        ) : (
          <p className="product-score neutral">
            Sản phẩm trong catalog
          </p>
        )}

        <button
          onClick={() => onViewProduct(item.product_id)}
          className="detail-btn"
        >
          Xem chi tiết
        </button>
      </div>
    </div>
  );
}

function StoreSection({
  products,
  page,
  totalPages,
  loading,
  onViewProduct,
  onPrevPage,
  onNextPage,
  onGoPage,
  homepageType = 'default',
}) {
  const visiblePages = getVisiblePages(page, totalPages);
  const title = getHomepageTitle(homepageType);
  const subtitle = getHomepageSubtitle(homepageType);
  const badge = getHomepageBadge(homepageType);

  return (
    <div className="store-wrapper">
      <section className="hero-banner">
        <div className="hero-content">
          <span className="hero-kicker">{badge}</span>
          <h1 className="hero-title">{title}</h1>
          <p className="hero-desc">{subtitle}</p>
          <button
            className="hero-btn"
            onClick={() => {
              const storePanel = document.querySelector('.store-panel');
              if (storePanel) {
                storePanel.scrollIntoView({ behavior: 'smooth', block: 'start' });
              }
            }}
          >
            Khám phá ngay
          </button>
        </div>

        <div className="hero-visual">
          <div className="hero-card hero-card-large">
            <div className="hero-shoe" />
          </div>

          <div className="hero-card hero-card-small top">
            <div className="hero-mini-shoe pink" />
          </div>

          <div className="hero-card hero-card-small bottom">
            <div className="hero-mini-shoe dark" />
          </div>
        </div>
      </section>

      <section className="store-panel">
        <div className="store-header">
          <div>
            <h2 className="store-title">{title}</h2>
            <p className="store-subtitle">{subtitle}</p>
          </div>

          <div className="store-header-right">
            <div className={`ranking-badge ${homepageType}`}>
              {badge}
            </div>

            <div className="page-indicator">
              Trang <b>{page}</b> / <b>{totalPages}</b>
            </div>
          </div>
        </div>

        {loading ? (
          <div className="product-grid">
            {Array.from({ length: 10 }).map((_, index) => (
              <div key={index} className="product-card skeleton-card">
                <div className="product-image-box skeleton-box" />
                <div className="product-body">
                  <div className="skeleton-line short" />
                  <div className="skeleton-line" />
                  <div className="skeleton-line medium" />
                  <div className="skeleton-line short" />
                  <div className="skeleton-button" />
                </div>
              </div>
            ))}
          </div>
        ) : products.length === 0 ? (
          <p className="loading-text">Chưa có sản phẩm.</p>
        ) : (
          <>
            <div className="store-meta-row">
              <p className="store-result-text">
                Đang hiển thị <b>{products.length}</b> sản phẩm trên trang này
              </p>
            </div>

            <div className="product-grid">
              {products.map((item) => (
                <ProductCard
                  key={item.product_id}
                  item={item}
                  onViewProduct={onViewProduct}
                />
              ))}
            </div>

            <div className="pagination-footer">
              <button
                onClick={onPrevPage}
                disabled={page <= 1}
                className="page-nav-btn"
              >
                Prev
              </button>

              <div className="page-number-list">
                {visiblePages.map((item, index) =>
                  item === '...' ? (
                    <span key={`dots-${index}`} className="page-dots">
                      ...
                    </span>
                  ) : (
                    <button
                      key={item}
                      onClick={() => onGoPage(item)}
                      className={`page-number-btn ${page === item ? 'active' : ''}`}
                    >
                      {item}
                    </button>
                  )
                )}
              </div>

              <button
                onClick={onNextPage}
                disabled={page >= totalPages}
                className="page-nav-btn"
              >
                Next
              </button>
            </div>
          </>
        )}
      </section>
    </div>
  );
}

export default StoreSection;