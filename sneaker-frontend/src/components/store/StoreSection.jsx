import React from 'react';

function getVisiblePages(currentPage, totalPages) {
  if (totalPages <= 7) {
    return Array.from({ length: totalPages }, (_, i) => i + 1);
  }

  if (currentPage <= 4) {
    return [1, 2, 3, 4, 5, '...', totalPages];
  }

  if (currentPage >= totalPages - 3) {
    return [1, '...', totalPages - 4, totalPages - 3, totalPages - 2, totalPages - 1, totalPages];
  }

  return [1, '...', currentPage - 1, currentPage, currentPage + 1, '...', totalPages];
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
}) {
  const visiblePages = getVisiblePages(page, totalPages);

  return (
    <div className="store-wrapper">
      <section className="hero-banner">
        <div className="hero-content">
          <span className="hero-kicker">Bộ sưu tập mới</span>
          <h1 className="hero-title">
            Sneaker recommendation
            <br />
            dành riêng cho bạn
          </h1>
          <p className="hero-desc">
            Khám phá sản phẩm phù hợp với hành vi tương tác thật, gợi ý thông minh,
            hiển thị gọn và dễ demo cho đồ án.
          </p>
          <button className="hero-btn">Khám phá ngay</button>
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
            <h2 className="store-title">Danh sách sản phẩm</h2>
            <p className="store-subtitle">Mỗi trang hiển thị 30 sản phẩm</p>
          </div>

          <div className="page-indicator">
            Trang <b>{page}</b> / <b>{totalPages}</b>
          </div>
        </div>

        {loading ? (
          <p className="loading-text">Đang tải sản phẩm...</p>
        ) : products.length === 0 ? (
          <p className="loading-text">Chưa có sản phẩm.</p>
        ) : (
          <>
            <div className="product-grid">
              {products.map((item) => (
                <div key={item.product_id} className="product-card">
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

                    <p className="product-price">
                      {Number(item.price).toLocaleString('vi-VN')}$
                    </p>

                    <button
                      onClick={() => onViewProduct(item.product_id)}
                      className="detail-btn"
                    >
                      Xem chi tiết
                    </button>
                  </div>
                </div>
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